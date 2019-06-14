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
                view_obj = {"name": viewname, "layers": layers, "content": view.content, "_type": "spandex_view"}
                for layer_class, annotation_pairs in view.annotations.items():
                    layer_name = '.'.join([layer_class.__module__, layer_class.__name__])
                    annotations = [
                        {
                            'span': self.default(span),
                            'annotation': self.default(annotation)
                        } for span, annotation in annotation_pairs
                    ]
                    layer_obj = {
                        'name': layer_name,
                        'annotations': annotations,
                        '_type': 'spandex_layer'
                    }
                    layers.append(layer_obj)
                spandex_obj['views'].append(view_obj)
            return spandex_obj

        elif isinstance(obj, spandex.Span):
            return [obj.begin, obj.end]
        elif isinstance(obj, Sequence) and not isinstance(obj, str):
            # handle non-string sequences (like lists or iterators)
            return [self.default(i) for i in obj]
        elif isinstance(obj, jemtypes.Annotation):
            annotation_obj = {f: self.default(getattr(obj, f)) for f in obj.__dataclass_fields__}
            annotation_obj['_type'] = "spandex_annotation"
            annotation_obj['_annotation_type'] = f"{obj.__class__.__module__}.{obj.__class__.__name__}"
            return annotation_obj
        elif isinstance(obj, jemtypes.AnnotationRef):
            return {
                "span": self.default(obj.span),
                "ref": {
                    "id": self.default(obj.ref.id if obj.ref else None)
                },
                "_type": "annotation_ref",
                "_annotation_type": f"{obj.ref.__class__.__module__}.{obj.ref.__class__.__name__}",
            }
        elif isinstance(obj, uuid.UUID):
            return str(obj)
        elif isinstance(obj, str):
            return obj
        elif isinstance(obj, numbers.Number):
            return float(obj)
        elif obj is None:
            return obj
        return json.JSONEncoder.default(self, obj)


class SpandexJsonDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(self, object_hook=self.object_hook, *args, **kwargs)
        # FIXME not multithreaded in any way
        self.layer_registry = {}

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
            spndx = spandex.Spandex(text='')  # create empty spandex structure for now

            for view_obj in obj['views']:
                viewname = view_obj['name']
                if viewname == spandex.constants.SPANDEX_DEFAULT_VIEW:
                    # default view is the root spandex, so no need to create
                    # just set the content
                    spndx.content = view_obj['content']
                else:
                    # for other views create and set content
                    spndx.create_view(viewname, view_obj['content'])

                # reset layer registry - this is used for lookup by ID when resolving references
                # in the JSON structure
                self.layer_registry = defaultdict(dict)
                for layer in view_obj['layers']:
                    # add annotations layer by layer
                    layer_name = layer['name']
                    module_name, class_name = layer_name.rsplit('.', 1)
                    module = importlib.import_module(module_name)
                    for span_annotation_obj in layer['annotations']:
                        annotation_obj = span_annotation_obj['annotation']
                        annotation = self.object_hook(annotation_obj)
                        span_obj = span_annotation_obj['span']
                        annotation_type = getattr(module, class_name)
                        span = spandex.Span(int(span_obj[0]), int(span_obj[1]))
                        self.layer_registry[layer_name][annotation.id] = (span, annotation)

                    spndx.add_layer(annotation_type, self.layer_registry[layer_name].values())

            # reset layer registry
            self.layer_registry = {}
            return spndx

        elif obj_type == 'spandex_annotation':
            layer_name = obj['_annotation_type']
            module_name, class_name = layer_name.rsplit('.', 1)
            module = importlib.import_module(module_name)
            annotation_type = getattr(module, class_name)
            annotation_id = uuid.UUID(obj['id'])
            if annotation_id in self.layer_registry[layer_name]:
                # we've previously encountered the annotation from a reference
                span, annotation = self.layer_registry[layer_name][annotation_id]
            else:
                annotation = annotation_type(id=annotation_id)

            # now fill out fields
            for fieldname, field in annotation_type.__dataclass_fields__.items():
                if fieldname == "id":
                    continue
                setattr(annotation, fieldname, self.object_hook(obj[fieldname]))
            return annotation

        elif obj_type == 'annotation_ref':
            layer_name = obj['_annotation_type']
            ref_id = uuid.UUID(obj['ref']['id'])
            if ref_id in self.layer_registry[layer_name]:
                span, annotation = self.layer_registry[layer_name][ref_id]
            else:
                module_name, class_name = layer_name.rsplit('.', 1)
                module = importlib.import_module(module_name)
                annotation_type = getattr(module, class_name)
                span = spandex.Span(*obj['span'])
                annotation = annotation_type(id=ref_id)
                self.layer_registry[layer_name][ref_id] = (span, annotation)
            annotation_ref = jemtypes.AnnotationRef(span=span, ref=annotation)
            return annotation_ref



