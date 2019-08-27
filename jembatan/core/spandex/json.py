from collections import defaultdict
from collections.abc import Sequence
from jembatan.core import spandex

import importlib
import jembatan.typesys as jemtypes
import json
import numbers
import uuid



class SpandexJsonEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, spandex.Spandex):

            spandex_obj = {"_type": "spandex", 'views': []}

            for viewname, view in obj.views.items():
                layers = []
                view_obj = {
                    "name": viewname,
                    "layers": layers,
                    "content_string": view.content_string,
                    "content_mime": view.content_mime,
                    "_type": "spandex_view",
                    "view_annotations": {
                        "_type": "spandex_view_annotations",
                        "annotations": self.default(view.view_annotations)
                    }
                }
                for layer_class, annotation_objs in view.annotations.items():
                    layer_name = '.'.join([layer_class.__module__, layer_class.__name__])
                    annotations = [self.default(annotation) for annotation in annotation_objs]
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
            return [self.default(i) for i in obj]
        elif isinstance(obj, jemtypes.AnnotationScope):
            return str(obj.to_json())
        elif isinstance(obj, jemtypes.SpannedAnnotation):
            annotation_obj = {}
            annotation_obj['_type'] = "spandex_annotation"
            annotation_obj['_annotation_type'] = f"{obj.__class__.__module__}.{obj.__class__.__name__}"
            annotation_obj['_fields'] = [
                {
                    '_type': 'annotation_field',
                    'name': f,
                    'value': self.default(getattr(obj, f))
                } for f in obj.__dataclass_fields__ if f not in ['id', 'scope']
            ]
            annotation_obj['id'] = str(obj.id)
            annotation_obj['scope'] = obj.scope.value

            return annotation_obj
        elif isinstance(obj, jemtypes.AnnotationRef):
            return {
                "ref": {
                    "id": self.default(obj.obj.id if obj.obj else None)
                },
                "_type": "annotation_ref",
                "_annotation_type": f"{obj.obj.__class__.__module__}.{obj.obj.__class__.__name__}",
            }
        elif isinstance(obj, uuid.UUID):
            return str(obj)
        elif isinstance(obj, str):
            return obj
        elif isinstance(obj, numbers.Number):
            return float(obj)
        elif isinstance(obj, dict):
            return {k: self.default(v) for k, v in obj.items()}
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
        if isinstance(obj, (str, int, float, bool)) or obj is None:
            # simply return basic types
            return obj
        elif isinstance(obj, Sequence):
            # turn non-string Sequences into lists.
            return [self.object_hook(i) for i in obj]
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
                        annotation = self.object_hook(annotation_obj)
                        annotation_type = getattr(module, class_name)
                        self.layer_registry[layer_name][annotation.id] = annotation

                    view.add_layer(annotation_type, self.layer_registry[layer_name].values())

                view_annotations_obj = view_obj['view_annotations']
                print("VIEW_ANNOTS", view_annotations_obj)
                print("VIEW_ANNOTS_THING", self.object_hook(view_annotations_obj))
                #view.view_annotations = 

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
            annotation_id = uuid.UUID(obj['id'])
            if annotation_id in self.layer_registry[layer_name]:
                # we've previously encountered the annotation from a reference
                annotation = self.layer_registry[layer_name][annotation_id]
            else:
                annotation = annotation_type(id=annotation_id)

            # now fill out fields
            for field in obj['_fields']:
                name = field['name']
                if name in ['begin', 'end']:
                    # Force begin and end spans to
                    valstr = field['value']
                    val = None if valstr == "null" else int(valstr)
                    setattr(annotation, name, val)
                elif name in ['scope']:
                    val = jemtypes.AnnotationScope.from_str(field['value'])
                    setattr(annotation, name, val)
                elif name in annotation_type.__dataclass_fields__:
                    setattr(annotation, name, self.object_hook(field['value']))

            return annotation

        elif obj_type == 'annotation_ref':
            layer_name = obj['_annotation_type']
            ref_id = uuid.UUID(obj['ref']['id'])
            if ref_id in self.layer_registry[layer_name]:
                annotation = self.layer_registry[layer_name][ref_id]
            else:
                module_name, class_name = layer_name.rsplit('.', 1)
                module = importlib.import_module(module_name)
                annotation_type = getattr(module, class_name)
                annotation = annotation_type(id=ref_id)
                self.layer_registry[layer_name][ref_id] = annotation
            annotation_ref = jemtypes.AnnotationRef(obj=annotation)
            return annotation_ref
