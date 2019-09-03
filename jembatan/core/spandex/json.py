from collections import defaultdict
from jembatan.core import spandex
from typing import Mapping, Sequence

import bson
import importlib
import jembatan.typesys as jemtypes
import json
import numbers
import uuid


class SpandexJsonEncoder(json.JSONEncoder):

    def encode_annotation_id(self, id_):
        return str(id_)

    def encode_annotation(self, obj, inside_field):
            if inside_field:
                ref = jemtypes.AnnotationRef(obj=obj) if obj is not None else obj
                return self.encode_obj(ref, inside_field=True)
            else:
                annotation_obj = {}
                annotation_obj['_type'] = "spandex_annotation"
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

    def default(self, obj):
        return self.encode_obj(obj)

    def encode_obj(self, obj, inside_field=False):
        if isinstance(obj, spandex.Spandex):

            spandex_obj = {"_type": "spandex", 'views': []}

            for viewname, view in obj.views.items():
                layers = []
                view_obj = {
                    "name": viewname,
                    "layers": layers,
                    "content_string": view.content_string,
                    "content_mime": view.content_mime,
                    "_type": "spandex_view"
                }
                for layer_class, annotation_objs in view.annotations.items():
                    layer_name = '.'.join([layer_class.__module__, layer_class.__name__])
                    annotations = [self.encode_obj(annotation, inside_field) for annotation in annotation_objs]
                    layer_obj = {
                        'name': layer_name,
                        'annotations': annotations,
                        '_type': 'spandex_layer'
                    }
                    layers.append(layer_obj)
                spandex_obj['views'].append(view_obj)
            return spandex_obj

        elif isinstance(obj, Sequence) and not isinstance(obj, str):
            # handle non-string sequences (like lists or iterators)
            return [self.encode_obj(i, inside_field) for i in obj]
        elif isinstance(obj, Mapping):
            # convert fields that are mappings / dictionaries into JSON dictionaries
            return {
                self.encode_obj(k, inside_field): self.encode_obj(k, inside_field) for k, v in obj.items()
            }
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
        elif isinstance(obj, str):
            return obj
        elif isinstance(obj, numbers.Number):
            return float(obj)
        elif isinstance(obj, dict):
            return {k: self.encode_obj(v, inside_field) for k, v in obj.items()}
        elif obj is None:
            return obj

        return json.JSONEncoder.default(self, obj)


class SpandexJsonDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(self, object_hook=self.object_hook, *args, **kwargs)
        self.reset_layers()

    def reset_layers(self):
        # FIXME not multithreaded in any way
        self.layer_registry = defaultdict(dict)

    def decode(self, s):
        # If this is not overridden it does weird things where it attempts to serialize things piecemeal
        obj = json.loads(s)
        return self.object_hook(obj)

    def object_hook(self, obj):
        return self.decode_obj(obj, inside_field=False)

    def decode_obj(self, obj, inside_field=False):
        if isinstance(obj, (str, int, float, bool)) or obj is None:
            # simply return basic types
            return obj
        elif isinstance(obj, Sequence):
            # turn non-string Sequences into lists.
            seq = [self.decode_obj(i, inside_field) for i in obj]
            return seq
        elif '_type' not in obj:
            # if it's a dictionary without a '_type', return as is
            return obj

        obj_type = obj['_type']
        if obj_type == 'spandex':
            spndx = spandex.Spandex()  # create empty spandex structure for now

            for view_obj in obj['views']:
                viewname = view_obj['name']
                if viewname == spandex.constants.SPANDEX_DEFAULT_VIEW:
                    view = spndx
                    # default view is the root spandex, so no need to create
                    # just set the content
                    spndx.content_string = view_obj['content_string']
                    spndx.content_mime = view_obj['content_mime']
                else:
                    # for other views create and set content
                    view = spndx.create_view(viewname=viewname,
                                             content_string=view_obj['content_string'],
                                             content_mime=view_obj['content_mime'])

                # reset layer registry - this is used for lookup by ID when resolving references
                # in the JSON structure
                self.reset_layers()
                for layer in view_obj['layers']:
                    # add annotations layer by layer
                    layer_name = layer['name']
                    module_name, class_name = layer_name.rsplit('.', 1)
                    module = importlib.import_module(module_name)
                    for annotation_obj in layer['annotations']:
                        if annotation_obj:
                            annotation = self.decode_obj(annotation_obj)
                            annotation_type = getattr(module, class_name)
                            self.layer_registry[layer_name][annotation.id] = annotation

                    view.add_layer(annotation_type, self.layer_registry[layer_name].values())

            # reset layer registry
            self.reset_layers()
            return spndx

        elif obj_type == 'spandex_view_annotations':
            return self.object_hook(obj['annotations'])

        elif obj_type == 'spandex_annotation':
            layer_name = obj['_annotation_type']
            module_name, class_name = layer_name.rsplit('.', 1)
            module = importlib.import_module(module_name)
            annotation_type = getattr(module, class_name)
            annotation_id = obj.get('id', None)
            """
            id_type = obj_id.get('_id_type', None)
            id_val = obj_id.get('_value', None)

            if id_type == "uuid":
                    annotation_id = uuid.UUID(id_val)
            elif id_type == "objectId":
                    annotation_id = bson.ObjectId(id_val)
            else:
                annotation_id = id_val
            """
            if annotation_id in self.layer_registry[layer_name]:
                # we've previously encountered the annotation from a reference
                annotation = self.layer_registry[layer_name][annotation_id]
            else:
                annotation = annotation_type()
                annotation.id = annotation_id

            # now fill out fields
            for field in obj['_fields']:
                name = field['name']
                if name in ['begin', 'end']:
                    # Force begin and end spans to
                    valstr = field['value']
                    val = None if valstr == "null" else int(valstr)
                    setattr(annotation, name, val)
                elif name in annotation_type.__dataclass_fields__:
                    field_value = self.decode_obj(field['value'], inside_field=True)
                    setattr(annotation, name, field_value)

            return annotation

        elif obj_type == 'annotation_ref':
            layer_name = obj['_annotation_type']
            ref_id = obj['ref']['id']
            if ref_id in self.layer_registry[layer_name]:
                annotation = self.layer_registry[layer_name][ref_id]
            else:
                module_name, class_name = layer_name.rsplit('.', 1)
                module = importlib.import_module(module_name)
                annotation_type = getattr(module, class_name)
                annotation = annotation_type(id=ref_id)
                self.layer_registry[layer_name][ref_id] = annotation
            annotation_ref = jemtypes.AnnotationRef(obj=annotation)
            if inside_field:
                return annotation
            return annotation_ref
