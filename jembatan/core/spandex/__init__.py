import bisect
from collections import namedtuple
from functools import total_ordering

@total_ordering
class Span(namedtuple("Span", ['begin', 'end'])):
    """
    A class defining offsets and spans over textual content.  The ordering of these
    allows for convenient query within a Spandex
    """

    @property
    def topair(self):
        return (self.begin, self.end)

    @property
    def isempty(self):
        return self.end == self.begin

    @property
    def length(self):
        return self.end - self.begin

    def contains(self, pos):
        return pos >= self.begin and pos < self.end

    def crosses(self, other):
        return (self.begin < other.begin and self.end < other.end and self.end > other.begin) or \
            (other.begin < self.begin and other.end < self.end and other.end > self.begin)

    def __str__(self):
        return "Span({0}, {1})".format(self.begin, self.end)

    def __eq__(self, other):
        return self.begin == other.begin and self.end == other.end

    def __lt__(self, other):
        if not isinstance(other, Span):
            return NotImplemented
        if self.begin == other.begin:
            return self.end < other.end
        else:
            return self.begin < other.begin

class DefaultViewOps(object):

    def __init__(self):
        pass

    def get_view(self, spndx, viewname):

        root = spndx.root

        view = None

        try:
            view = root.views[viewname]
        except KeyError as e:
            raise KeyError("No view named '{}' in Spandex {}".format(viewname, root))

        return view

    def create_view(self, spndx, viewname, content):
        root = spndx if not spndx.root else spndx.root

        new_view_spndx = Spandex(content, root, viewname)
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

    def create_view(self, spndx, viewname, content):
        mapped_viewname = self.view_map[viewname]
        return super(ViewMappedViewOps, self).create_view(spndx, mapped_viewname, content)


SpandexConstants = namedtuple("SpandexContstants", 
        ["SPANDEX_DEFAULT_VIEW", "SPANDEX_URI_VIEW"])
constants = SpandexConstants("_SpandexDefaultView", "_SpandexUriView")


# object is mutable for performant reasons
class Spandex(object):

    def __init__(self, text, root=None, viewname=None):
        self._content = text 
        self._annotations = {}
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
    def content(self):
        return self._content

    @content.setter
    def content(self, value):
        self._content = value

    @property
    def annotations(self):
        return self._annotations

    def get_view(self, viewname):
        return self.viewops.get_view(self, viewname)

    def __getitem__(self, viewname):
        return self.get_view(viewname)

    def create_view(self, viewname, content):
        return self.viewops.create_view(self, viewname, content)
    

    def compute_keys(self, layer_annotations):
        return [a[0][0] for a in layer_annotations]
        

    def spanned(self, span):
        return self.content[span.begin:span.end]


    def append(self, layer, *span_obj_pairs):
        layer = self.aliases.get(layer, layer)
        items = sorted(self._annotations.get(layer, []) + list(span_obj_pairs))
        keys = self.compute_keys(items)
        self.annotations[layer] = items
        self.annotation_keys[layer] = keys

    def has_layer(self, layer):
        layer = self.aliases.get(layer, layer)
        self.aliases[alias] = layer
        return layer in self.annotations

    def add_layer_alias(self, alias, layer):
        self.aliases[alias] = layer

    def add_layer(self, layer, span_obj_pairs):
        layer = self.aliases.get(layer, layer)
        items = sorted(span_obj_pairs)
        self.annotations[layer] = items
        self.annotation_keys[layer] = self.compute_keys(items)

    def remove_layer(self, layer):
        self.annotations.pop(layer)
        self.annotation_keys.pop(layer)


    def select(self, layer):
        layer = self.aliases.get(layer, layer)
        return self.annotations[layer]

    def covered(self, layer, span):
        layer = self.aliases.get(layer, layer)
        begin = bisect.bisect_left(self.annotation_keys[layer], span.begin)
        end = bisect.bisect_left(self.annotation_keys[layer], span.end)
        return self.annotations[layer][begin:end]

    def preceeding(self, layer, span):
        layer = self.aliases.get(layer, layer)
        end = bisect.bisect_left(spannedex.annotation_keys[layer], span.begin)
        return self.annotations[layer][0:end]

    def following(self, layer, span):
        layer = self.aliases.get(layer, layer)
        end = bisect.bisect_right(spannedex.annotation_keys[layer], span.end)
        return self.annotations[layer][end:]


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
        return self._wrapped_spandex._content

    @content.setter
    def content(self, value):
        self._wrapped_spandex._content = value

    def get_view(self, viewname):
        view = self.viewops.get_view(self._wrapped_spandex, viewname)
        return ViewMappedSpandex(view, self.viewops)

    def __getitem__(self, viewname):
        return self.get_view(viewname)

    def create_view(self, viewname, content):
        view = self.viewops.create_view(self._wrapped_spandex, viewname, content)
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

__all__= ['errors']
