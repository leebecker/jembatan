from collections import namedtuple
from functools import total_ordering
from typing import ClassVar, Iterable
from dataclasses import dataclass

import bisect
import itertools
import math


@dataclass
@total_ordering
class Span:
    """
    A class defining offsets and spans over textual content.  The ordering of these
    allows for convenient query within a Spandex, it has two named fields
    `begin` and `end`.

    Examples:
        # construction
        span1 = Span(begin=1, end=10)
        span2 = Span(5, 10)
    """
    begin: int = None
    end: int = None

    @property
    def topair(self):
        return (self.begin, self.end)

    @property
    def isempty(self):
        return self.end == self.begin

    @property
    def length(self):
        return self.end - self.begin

    def contains(self, pos: int):
        return pos >= self.begin and pos < self.end

    def crosses(self, other: "Span"):
        return (self.begin < other.begin and self.end < other.end and self.end > other.begin) or \
            (other.begin < self.begin and other.end < self.end and other.end > self.begin)

    def __eq__(self, other: "Span"):
        return self.begin == other.begin and self.end == other.end

    def __lt__(self, other: "Span"):

        if other is None:
            return True

        if not isinstance(other, Span):
            return NotImplemented

        tuple1 = (
            self.begin if self.begin is not None else -math.inf,
            self.end if self.end is not None else -math.inf,
        )

        tuple2 = (
            other.begin if other.begin is not None else -math.inf,
            other.end if other.end is not None else -math.inf,
        )

        return tuple1 < tuple2

    def __hash__(self):
        return (self.begin, self.end).__hash__()

    def to_json(self):
        return self._asdict()

    def spanned_text(self, spndx):
        return spndx.spanned_text(self)

    @classmethod
    def from_json(self, obj):
        return Span(**obj)


class DefaultViewOps(object):

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

    def create_view(self, spndx, viewname: str, content_string: str=None, content_mime: str=None):
        root = spndx if not spndx.root else spndx.root

        new_view_spndx = Spandex(content_string=content_string, content_mime=content_mime, root=root, viewname=viewname)
        if viewname in root.views:
            raise KeyError("View {} already exists in Spandex{}".format(viewname, root))
        root.views[viewname] = new_view_spndx
        return new_view_spndx


class ViewMappedViewOps(DefaultViewOps):
    """ Overrides ViewOps by resolving view names by way of a view_map
    """

    def __init__(self, view_map):
        self.view_map = view_map

    def get_view(self, spndx, viewname):
        mapped_viewname = self.view_map[viewname]
        return super(ViewMappedViewOps, self).get_view(spndx, mapped_viewname)

    def create_view(self, spndx, viewname: str, content_string: str=None, content_mime: str=None):
        mapped_viewname = self.view_map[viewname]
        return super(ViewMappedViewOps, self).create_view(spndx,
                                                          viewname=mapped_viewname,
                                                          content_string=content_string,
                                                          content_mime=content_mime)


SpandexConstants = namedtuple("SpandexContstants", ["SPANDEX_DEFAULT_VIEW", "SPANDEX_URI_VIEW"])

constants = SpandexConstants("_SpandexDefaultView", "_SpandexUriView")


# object is mutable for performant reasons
class Spandex(object):
    from jembatan.typesys import Annotation
    """
    Spandex - data structure for holding views of data, its content, and annotations
    """

    def __init__(self, content_string: str=None, content_mime: str = None, root=None, viewname=None):
        self._content_string = content_string
        self._content_mime = content_mime
        self._annotations = {}
        self._view_annotations = {}
        self.annotation_keys = {}
        self.aliases = {}
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

    @property
    def view_annotations(self):
        return self._view_annotations

    def get_view(self, viewname: str):
        return self.viewops.get_view(self, viewname)

    def __getitem__(self, viewname: str):
        return self.get_view(viewname)

    def create_view(self, viewname: str, content_string: str=None, content_mime: str=None):
        return self.viewops.create_view(self, viewname, content_string=content_string, content_mime=content_mime)

    def compute_keys(self, layer_annotations: Iterable[Annotation]):
        return [a.begin for a in layer_annotations]

    def spanned_text(self, span: Span):
        """
        Return text covered by the span
        """
        return self.content_string[span.begin:span.end]

    def add_annotations(self, layer: ClassVar[Annotation], *annotations: Annotation):
        layer = self.aliases.get(layer, layer)
        items = sorted(self._annotations.get(layer, []) + list(annotations))
        keys = self.compute_keys(items)
        self.annotations[layer] = items
        self.annotation_keys[layer] = keys

    def add_layer(self, layer: ClassVar[Annotation], annotations: Iterable[Annotation]):
        layer = self.aliases.get(layer, layer)
        self.add_annotations(layer, *annotations)

    def remove_layer(self, layer: ClassVar[Annotation]):
        self.annotations.pop(layer)
        self.annotation_keys.pop(layer)

    def select(self, layer: ClassVar[Annotation]) -> Iterable[Annotation]:
        """
        Return all annotations in a layer
        """
        layer = self.aliases.get(layer, layer)
        return self.annotations.get(layer, [])

    def select_covered(self, layer: ClassVar[Annotation], span: Span) -> Iterable[Annotation]:
        """
        Return all annotations in a layer that are covered by the input span
        """
        layer = self.aliases.get(layer, layer)
        begin = bisect.bisect_left(self.annotation_keys[layer], span.begin)
        end = bisect.bisect_left(self.annotation_keys[layer], span.end)
        return self.annotations[layer][begin:end]

    def select_preceeding(self, layer: ClassVar[Annotation], span: Span) -> Iterable[Annotation]:
        """
        Return all annotations in a layer that precede the input span
        """
        layer = self.aliases.get(layer, layer)
        end = bisect.bisect_left(self.annotation_keys[layer], span.begin)
        return self.annotations[layer][0:end]

    def select_following(self, layer: ClassVar[Annotation], span: Span) -> Iterable[Annotation]:
        """
        Return all annotations in a layer that follow the input span
        """
        layer = self.aliases.get(layer, layer)
        end = bisect.bisect_right(self.annotation_keys[layer], span.end)
        return self.annotations[layer][end:]

    def select_all(self, span: Span) -> Iterable[Annotation]:
        """
        Return all annotations in a view
        """
        return itertools.chain([annotations for layer, annotations in self.annotations.items()])


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
