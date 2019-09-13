import bisect
import json as json_

from collections import namedtuple
from jembatan.core.spandex.typesys_base import Span, Annotation, AnnotationScope
from pathlib import Path
from typing import ClassVar, Dict, Iterable, Optional, Union


class DefaultViewOps(object):
    """
    Defines behaviors we can perform on a view.  This is intended to be used for the root (default) Spandex that
    governs all views
    """

    def __init__(self):
        pass

    def get_view(self, spndx, viewname: str):

        root = spndx.root

        view = None

        try:
            view = root.views[viewname]
        except KeyError as e:
            raise KeyError("No view named '{}' in Spandex {}".format(viewname, root))

        return view

    def create_view(self, spndx: "Spandex", viewname: str, content_string: str=None, content_mime: str=None):
        root = spndx if not spndx.root else spndx.root

        new_view_spndx = Spandex(content_string=content_string, content_mime=content_mime, root=root, viewname=viewname)
        if viewname in root.views:
            raise KeyError("View {} already exists in Spandex{}".format(viewname, root))
        root.views[viewname] = new_view_spndx
        return new_view_spndx


class ViewMappedViewOps(DefaultViewOps):
    """
    Overrides ViewOps by resolving view names by way of a view_map

    This is the mechanism that allows us to say, run this analysis that normally
    runs on view X and instead run it on view Y.
    """
    def __init__(self, view_map: Dict[str, str]=None):
        self.view_map = view_map or {}

    def get_view(self, spndx: "Spandex", viewname: str):
        # Attempt to map view from given view map.  If none exists, pass through the unmappped view name
        mapped_viewname = self.view_map.get(viewname, viewname)
        return super(ViewMappedViewOps, self).get_view(spndx, mapped_viewname)

    def create_view(self, root_spndx: "Spandex", viewname: str, content_string: str=None, content_mime: str=None):
        """

        """
        mapped_viewname = self.view_map[viewname]
        return super(ViewMappedViewOps, self).create_view(root_spndx,
                                                          viewname=mapped_viewname,
                                                          content_string=content_string,
                                                          content_mime=content_mime)


SpandexConstants = namedtuple("SpandexContstants", ["SPANDEX_DEFAULT_VIEW", "SPANDEX_URI_VIEW"])

constants = SpandexConstants("_SpandexDefaultView", "_SpandexUriView")


# object is mutable for performant reasons
class Spandex(object):
    """
    Spandex - data structure for holding views of data, its content, and annotations
    """

    def __init__(self, content_string: str=None, content_mime: str = None, root=None, viewname=None):
        self._content_string = content_string
        self._content_mime = content_mime
        self._annotations = []
        self._annotation_keys = []
        self.viewops = DefaultViewOps()

        if not root:
            self.viewname = constants.SPANDEX_DEFAULT_VIEW
            self._views = {
                constants.SPANDEX_DEFAULT_VIEW: self
            }
            self.root = self
        else:
            self.viewname = viewname
            self._views = None
            self.root = root

    def __repr__(self):
        return "<{}/{} at 0x{:x}>".format(self.__class__.__name__, self.viewname, id(self))

    @property
    def is_root(self):
        return self.root == self

    @property
    def views(self):
        return self.root._views

    @property
    def content_string(self):
        return self._content_string

    @content_string.setter
    def content_string(self, value):
        self._content_string = value

    @property
    def content_mime(self):
        return self._content_mime

    @content_mime.setter
    def content_mime(self, value):
        self._content_mime = value

    @property
    def annotations(self):
        return self._annotations

    def get_view(self, viewname: str):
        return self.viewops.get_view(self, viewname)

    def get_or_create_view(self, viewname: str):
        try:
            view = self.get_view(viewname)
        except KeyError:
            view.create_view(viewname)
        return view

    def __getitem__(self, viewname: str):
        return self.get_view(viewname)

    def create_view(self, viewname: str, content_string: str=None, content_mime: str=None):
        return self.viewops.create_view(self, viewname, content_string=content_string, content_mime=content_mime)

    def compute_keys(self, layer_annotations: Iterable[Annotation]):
        return [a.index_key for a in layer_annotations]

    def spanned_text(self, span: Span):
        """
        Return text covered by the span
        """
        return self.content_string[span.begin:span.end]

    def add_annotations(self, *annotations: Annotation):
        items = sorted(self._annotations + list(annotations))
        keys = self.compute_keys(items)
        self._annotations = items
        self._annotation_keys = keys

    def index_annotations(self, *annotations: Annotation):
        return self.add_annotations(annotations)

    def select(self, layer: ClassVar[Annotation]) -> Iterable[Annotation]:
        """
        Return all annotations in a layer
        """
        return [a for a in self.annotations if isinstance(a, layer)]

    def select_covered(self, layer: ClassVar[Annotation], span: Span) -> Iterable[Annotation]:
        """
        Return all annotations in a layer that are covered by the input span
        """
        begin = bisect.bisect_left(self._annotation_keys, (AnnotationScope.SPAN, span.begin))
        end = bisect.bisect_left(self._annotation_keys, (AnnotationScope.SPAN, span.end))
        return [a for a in self.annotations[begin:end] if isinstance(a, layer)]

    def select_preceding(self, layer: ClassVar[Annotation], span: Span, count: int=None) -> Iterable[Annotation]:
        """
        Return all annotations in a layer that precede the input span
        """
        precede_span = Span(begin=0, end=span.begin)
        preceding = self.select_covered(layer, precede_span)
        return preceding if count is None else preceding[-count:]

    def select_following(self, layer: ClassVar[Annotation], span: Span, count: int=None) -> Iterable[Annotation]:
        """
        Return all annotations in a layer that follow the input span
        """
        follow_span = Span(begin=span.end+1, end=len(self.content_string))
        following = self.select_covered(layer, follow_span)
        return following if count is None else following[0:count]

    def select_all(self, span: Span) -> Iterable[Annotation]:
        """
        Return all annotations in a view
        """
        return self.annotations

    def to_json(self, path: Union[str, Path, None] = None, pretty_print: bool = False) -> Optional[str]:
        """Creates a JSON representation of this Spandex.
        Args:
            path: File path, if `None` is provided the result is returned as a string
            pretty_print: `True` if the resulting JSON should be pretty-printed, else `False`
        Returns:
            If `path` is None, then the JSON representation of this Spandex is returned as a string
        """
        from jembatan.core.spandex.json import SpandexJsonEncoder

        indent = 4 if pretty_print else None
        # If `path` is None, then serialize to a string and return it
        if path is None:
            return json_.dumps(self, cls=SpandexJsonEncoder, indent=indent)
        elif isinstance(path, str):
            with open(path, "w") as f:
                json_.dump(self, f, cls=SpandexJsonEncoder, indent=indent)
        elif isinstance(path, Path):
            with path.open("w") as f:
                json_.dump(self, f, cls=SpandexJsonEncoder, indent=indent)
        else:
            raise TypeError("`path` needs to be one of [str, None, Path], but was <{0}>".format(type(path)))


class ViewMappedSpandex(object):

    def __init__(self, wrapped_spandex, view_map):
        """
        Wraps a Spandex object so we can override its view names for use by
        an analysis function

        Args:
        wrapped_spandex (Spandex) - The original Spandex which we want to inject
            a view mapping
        view_map (dict) - A map between the names used by the
            analyzer function and the names specified by the pipeline
        """
        self._wrapped_spandex = wrapped_spandex
        self.viewops = ViewMappedViewOps(view_map)

    @property
    def content(self):
        return self._wrapped_spandex._content_string

    @content.setter
    def content(self, value):
        self._wrapped_spandex._content_string = value

    def get_view(self, viewname):
        view = self.viewops.get_view(self._wrapped_spandex, viewname)
        return ViewMappedSpandex(view, self.viewops)

    def __getitem__(self, viewname: str):
        return self.get_view(viewname)

    def create_view(self, viewname: str, content_string: str=None, content_mime: str=None):
        view = self.viewops.create_view(self._wrapped_spandex,
                                        viewname,
                                        content_string=content_string,
                                        content_mime=content_mime)
        return ViewMappedSpandex(view, self.viewops)

    def __getattr__(self, attr):
        # see if this object has attr
        # NOTE do not use hasattr, it goes into
        # infinite recurrsion
        if attr in self.__dict__:
            # this object has it
            return getattr(self, attr)

        # proxy to the wrapped object
        return getattr(self._wrapped_spandex, attr)


__all__ = ['errors', 'encoders']
