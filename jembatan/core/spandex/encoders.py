from jembatan.core import spandex

import jembatan.typesys as jemtypes
import json
import numbers
import uuid


class SpandexJsonEncoder(json.JSONEncoder):

    def default(self, obj):

        if isinstance(obj, spandex.Spandex):

            spandex_obj = {}

            for viewname, view in obj.views.items():
                layers = []
                view_obj = {"name": viewname, "layers": layers, "content": view.content}
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
                        'annotations': annotations
                    }
                    layers.append(layer_obj)
                spandex_obj[viewname] = view_obj
            return spandex_obj

        elif isinstance(obj, spandex.Span):
            return [obj.begin, obj.end]
        elif isinstance(obj, jemtypes.Annotation):
            return {f: self.default(getattr(obj, f)) for f in obj.__dataclass_fields__}
        elif isinstance(obj, jemtypes.AnnotationRef):
            return {
                "span": self.default(obj.span),
                "ref": {
                    "annotation_type": f"{obj.ref.__class__.__module__}.{obj.ref.__class__.__name__}",
                    "id": self.default(obj.ref.id if obj.ref else None)
                }
            }
        elif isinstance(obj, uuid.UUID):
            return str(obj)
        elif isinstance(obj, str):
            return obj
        elif isinstance(obj, numbers.Number):
            return float(obj)
        return json.JSONEncoder.encode(self, obj)


class SpandexJsonDecoder(json.JSONDecoder):

    def object_hook(self, obj):
        pass
