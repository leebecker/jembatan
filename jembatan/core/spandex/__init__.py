import bisect
import json as json_

from collections import namedtuple
from jembatan.core.spandex.typesys_base import Span, Annotation, AnnotationScope
from pathlib import Path
from typing import ClassVar, Dict, Iterable, Optional, Union


SpandexConstants = namedtuple("SpandexContstants", ["SPANDEX_DEFAULT_VIEW", "SPANDEX_URI_VIEW"])

constants = SpandexConstants("_SpandexDefaultView", "_SpandexUriView")


# object is mutable for performant reasons
class Spandex(object):
    """
    Spandex - data structure for holding a view of data, its content, and annotations
    """

    def __init__(self, parent: "Jembatan", content_string: str=None, content_mime: str = None, viewname=None):
        self._parent = parent
        self._content_string = content_string
        self._content_mime = content_mime
        self._annotations = []
        self._annotation_keys = []
        self.viewname = viewname

    def __repr__(self):
        return "<{}/{} at 0x{:x}>".format(self.__class__.__name__, self.viewname, id(self))

    @property
    def parent(self) -> "JembatanDoc":
        return self._parent

    @property
    def content_string(self) -> str:
        return self._content_string

    @content_string.setter
    def content_string(self, value: str):
        self._content_string = value

    @property
    def content_mime(self) -> str:
        return self._content_mime

    @content_mime.setter
    def content_mime(self, value: str):
        self._content_mime = value

    @property
    def annotations(self):
        return self._annotations

    #def get_view(self, viewname: str):
    #    return self.viewops.get_view(self, viewname)
    #
    #def get_or_create_view(self, viewname: str):
    #    try:
    #        view = self.get_view(viewname)
    #    except KeyError:
    #        view = self.create_view(viewname)
    #    return view
    #
    #def __getitem__(self, viewname: str):
    #    return self.get_view(viewname)
    #
    #def create_view(self, viewname: str, content_string: str=None, content_mime: str=None):
    #    return self.viewops.create_view(self, viewname, content_string=content_string, content_mime=content_mime)

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


class JembatanDoc(object):
    """
    Top level container for processing.  The JembatanDoc roughly describes /manages a document or artifact.
    It is responsible for managing views.
    """

    def __init__(self, metadata: Dict=None, content_string: str=None, content_mime: str=None):
        self.metadata = metadata
        self._views = {}

        self.create_view(
            constants.SPANDEX_DEFAULT_VIEW,
            content_string=content_string,
            content_mime=content_mime,
        )

    @property
    def default_view(self):
        return self.get_view(constants.SPANDEX_DEFAULT_VIEW)

    def get_view(self, viewname: str):
        view = None

        try:
            view = self.views[viewname]
        except KeyError as e:
            raise KeyError("No view named '{}' in Jembatan {}".format(viewname, self))

        return view

    def get_or_create_view(self, viewname: str):
        try:
            view = self.get_view(viewname)
        except KeyError:
            view = self.create_view(viewname)
        return view

    def __getitem__(self, viewname: str):
        return self.get_view(viewname)

    def create_view(self, viewname: str, content_string: str=None, content_mime: str=None):

        if viewname in self.views:
            raise KeyError("View {} already exists in Jembatan{}".format(viewname, self))

        new_view_spndx = Spandex(content_string=content_string, content_mime=content_mime, parent=self, viewname=viewname)
        self.views[viewname] = new_view_spndx
        return new_view_spndx

    @property
    def views(self):
        return self._views


class ViewMappedSpandex(object):

    def __init__(self, spandex: Spandex, view_mapped_parent: JembatanDoc):
        '''
        Wrapper constructor.
        @param obj: object to wrap
        '''
        # wrap the object
        self._wrapped_spandex = spandex
        self._wrapped_parent = view_mapped_parent

        if view_mapped_parent.wrapped != self.wrapped.parent:
            raise ValueError("Can not wrap parent from different Jembatans")

    def __getattr__(self, attr):
        # see if this object has attr
        # NOTE do not use hasattr, it goes into
        # infinite recurrsion
        if attr in self.__dict__:
            # this object has it
            return getattr(self, attr)
        # proxy to the wrapped object
        return getattr(self.wrapped, attr)

    def __repr__(self):
        return "<{}/{} at 0x{:x}>".format(self.__class__.__name__, self.viewname, id(self))

    @property
    def wrapped(self):
        return self._wrapped_spandex

    @property
    def parent(self):
        return self._wrapped_parent


class ViewMappedJembatanDoc(object):
    '''
    Object wrapper class.
    This a wrapper for objects. It is initialiesed with the object to wrap
    and then proxies the unhandled getattribute methods to it.
    Other classes are to inherit from it.
    '''
    def __init__(self, jemdoc: JembatanDoc, view_map):
        '''
        Wrapper constructor.
        @param obj: object to wrap
        '''
        # wrap the object
        self._wrapped_jemdoc = jemdoc
        self.view_map = view_map

    def __getattr__(self, attr):
        # see if this object has attr
        # NOTE do not use hasattr, it goes into
        # infinite recurrsion
        if attr in self.__dict__:
            # this object has it
            return getattr(self, attr)
        # proxy to the wrapped object
        return getattr(self._wrapped_jemdoc, attr)

    @property
    def wrapped(self):
        return self._wrapped_jemdoc

    def get_view(self, viewname):
        mapped_viewname = self.view_map[viewname]
        view = self.wrapped.get_view(mapped_viewname)

        # we need to wrap the view so that if it references its parent it can get back to the ViewMapped version
        # instead of the original one
        return ViewMappedSpandex(view, self)

    def create_view(self, viewname):
        if viewname in self.view_map:
            mapped_viewname = self.view_map[viewname]
            view = self.wrapped.create_view(mapped_viewname)
        else:
            view = self.wrapped.create_view(viewname)

        return ViewMappedSpandex(view, parent=self)


__all__ = ['errors', 'encoders']
