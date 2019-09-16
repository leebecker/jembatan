from collections import defaultdict
from jembatan.core import spandex
from typing import Mapping, Sequence

import bson
import importlib
import jembatan.typesys as jemtypes
import json
import numbers
import uuid


JEMBATAN_TYPE_STR = "jembatan"
SPANDEX_TYPE_STR = "spandex"
SPANDEX_ANNOTATION_TYPE_STR = "spandex_annotation"


class JembatanJsonEncoder(json.JSONEncoder):

    def default(self, obj):
        return self.encode_obj(obj)

    def encode_annotation_id(self, id_):
        return str(id_)

    def encode_annotation(self, obj, inside_field):
            if inside_field:
                ref = jemtypes.AnnotationRef(obj=obj) if obj is not None else obj
                return self.encode_obj(ref, inside_field=True)
            else:
                annotation_obj = {}
                annotation_obj['_type'] = SPANDEX_ANNOTATION_TYPE_STR
                annotation_obj['_annotation_type'] = f"{obj.__class__.__module__}.{obj.__class__.__name__}"
                annotation_obj['_fields'] = [
                    self.encode_annotation_field(getattr(obj, fname), f)
                    for fname, f in obj.__dataclass_fields__.items()
                ]
                annotation_obj['id'] = self.encode_annotation_id(obj.id)
                annotation_obj['scope'] = self.encode_obj(obj.scope)

                return annotation_obj

    def encode_annotation_field(self, obj, field):
        encoded_value = self.encode_obj(obj, inside_field=True)

        return {
            'name': field.name,
            'value': encoded_value
        }

    def encode_obj(self, obj, inside_field=False):
        if isinstance(obj, spandex.JembatanDoc):
            jembatan_obj = {
                '_type': JEMBATAN_TYPE_STR,
                'metadata': obj.metadata,
                'views': []
            }

            for viewname, view in obj.views.items():
                view_obj = self.encode_obj(view, inside_field)
                jembatan_obj['views'].append(view_obj)

            return jembatan_obj

        if isinstance(obj, spandex.Spandex):

            spandex_obj = {
                "_type": SPANDEX_TYPE_STR,
                "name": obj.viewname,
                "content_string": obj.content_string,
                "content_mime": obj.content_mime,
            }

            annotations = [self.encode_obj(annotation, inside_field) for annotation in obj.annotations]
            spandex_obj['annotations'] = annotations

            return spandex_obj

        elif isinstance(obj, Sequence) and not isinstance(obj, str):
            # handle non-string sequences (like lists or iterators)
            return [self.encode_obj(i, inside_field) for i in obj]
        elif isinstance(obj, jemtypes.AnnotationScope):
            return str(obj.to_json())
        elif isinstance(obj, jemtypes.Annotation):
            return self.encode_annotation(obj, inside_field)
        elif isinstance(obj, jemtypes.AnnotationRef):
            if obj.obj is None:
                return None
            else:
                return {
                    "ref": {
                        "id": self.encode_obj((obj.obj.id if obj.obj else None), inside_field)
                    },
                    "_type": "annotation_ref",
                    "_annotation_type": f"{obj.obj.__class__.__module__}.{obj.obj.__class__.__name__}",
                }

        elif isinstance(obj, Mapping):
            # convert fields that are mappings / dictionaries into JSON dictionaries
            return {
                self.encode_obj(k, inside_field): self.encode_obj(v, inside_field) for k, v in obj.items()
            }
        elif isinstance(obj, (str, int, float, numbers.Number)) or obj is None:
            return obj

        # Bottom out encoding
        return json.JSONEncoder.default(self, obj)


class JembatanJsonDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(self, object_hook=self.object_hook, *args, **kwargs)
        self.reset_layers()

    def reset_layers(self):
        # FIXME not multithreaded in any way
        self.layer_registry = dict()

    def decode(self, s):
        # If this is not overridden it does weird things where it attempts to serialize things piecemeal
        obj = json.loads(s)
        return self.object_hook(obj)

    def decode_annotation_field(self, fieldval_obj):

        if isinstance(fieldval_obj, Sequence) and not isinstance(fieldval_obj, str):
            # turn non-string Sequences into lists.
            seq = [self.decode_annotation_field(i) for i in fieldval_obj]
            return seq
        elif isinstance(fieldval_obj, Mapping):
            obj_type = fieldval_obj.get('_type', None)
            if obj_type == 'annotation_ref':
                # The serialized JSON has an annotation ref, instead of returning an annotation ref
                # return the annotation itself
                annotation_type = fieldval_obj['_annotation_type']
                ref_id = fieldval_obj['ref']['id']
                if ref_id in self.layer_registry:
                    # annotation exists already
                    annotation = self.layer_registry[ref_id]
                else:
                    # annotation does not exist, go ahead and create it,
                    # later this should get populated in other layers
                    module_name, class_name = annotation_type.rsplit('.', 1)
                    module = importlib.import_module(module_name)
                    annotation_type = getattr(module, class_name)
                    annotation = annotation_type(id=ref_id)
                    self.layer_registry[ref_id] = annotation
                return annotation
            else:
                # This is likely a nested dictionary so decode as needed
                return {
                    self.decode_annotation_field(k): self.decode_annotation_field(v) for k, v in fieldval_obj.items()
                }
        else:
            # for everything else (int, str, float, None, etc) return as it came in
            return fieldval_obj

    def decode_annotation(self, annotation_obj, inside_field=False):
        annotation_type_str = annotation_obj['_annotation_type']
        module_name, class_name = annotation_type_str.rsplit('.', 1)
        module = importlib.import_module(module_name)
        annotation_type = getattr(module, class_name)
        annotation_id = annotation_obj.get('id', None)

        if annotation_id in self.layer_registry:
            # we've previously encountered the annotation from a reference
            annotation = self.layer_registry[annotation_id]
        else:
            annotation = annotation_type()
            annotation.id = annotation_id

        # now fill out fields
        for field in annotation_obj['_fields']:
            name = field['name']
            if name in ['begin', 'end']:
                # Force begin and end spans to
                valstr = field['value']
                val = None if valstr == "null" else int(valstr)
                setattr(annotation, name, val)
            elif name in annotation_type.__dataclass_fields__:
                field_value = self.decode_annotation_field(field['value'])
                setattr(annotation, name, field_value)
        return annotation

    def object_hook(self, obj):

        obj_type = obj['_type']

        if obj_type == JEMBATAN_TYPE_STR:
            metadata = self.object_hook(obj['metadata']) if obj.get('metadata', None) else {}
            jemdoc = spandex.JembatanDoc(metadata=metadata)

            for view_obj in obj['views']:
                viewname = view_obj['name']

                if viewname == spandex.constants.SPANDEX_DEFAULT_VIEW:
                    # default view exists by way of constructor
                    view = jemdoc.get_view(viewname)
                    view.content_string = view_obj['content_string']
                    view.content_mime = view_obj['content_mime']
                else:
                    # for other views create and set content
                    view = jemdoc.create_view(
                        viewname=viewname,
                        content_string=view_obj['content_string'],
                        content_mime=view_obj['content_mime'])

                # reset layer registry - this is used for lookup by ID when resolving references
                # in the JSON structure
                # FIXME - this should be revisited with respect to having all objects in memory
                # versus those indexed by the view
                self.reset_layers()

                annotations = []

                for annotation_obj in view_obj['annotations']:
                    annotation_obj_type = annotation_obj.get("_type", None)

                    # FIXME raise exception or print error
                    assert annotation_obj_type == SPANDEX_ANNOTATION_TYPE_STR

                    if annotation_obj:
                        annotation_type = annotation_obj['_annotation_type']

                        module_name, class_name = annotation_type.rsplit('.', 1)
                        module = importlib.import_module(module_name)
                        annotation = self.decode_annotation(annotation_obj)
                        annotation_type = getattr(module, class_name)
                        self.layer_registry[annotation.id] = annotation
                        annotations.append(annotation)

                view.add_annotations(*annotations)

            # reset layer registry
            self.reset_layers()

            return jemdoc
