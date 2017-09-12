import bisect
from collections import namedtuple
from functools import total_ordering

@total_ordering
class Span(namedtuple("Span", ['begin', 'end'])):

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

DEFAULT_VIEW = "SpandexDefaultView"


# object is mutable for performant reasons
class Spandex(object):

    def __init__(self, text, root=None, viewname=None):
        self.content = text 
        self.annotations = {}
        self.annotation_keys = {}
        self.aliases = {}

        if not root:
            self.viewname = DEFAULT_VIEW
            self.views = {
                DEFAULT_VIEW: self
            }
        else:
            self.viewname = viewname
            self.views = None

        self.root = root

    def get_view(self, viewname):
        root = self if not self.root else self.root

        view = None
        try:
            view = root.views[viewname]
        except KeyError as e:
            raise KeyError("No view named '{}' in Spandex {}".format(viewname, root))

        return view

    def create_view(self, viewname, content):
        new_view_spndx = Spandex(content, self, viewname)
        self.views[viewname] = new_view_spndx


    def compute_keys(self, layer_annotations):
        return [a[0][0] for a in layer_annotations]
        

    def spanned(self, span):
        return self.content[span.begin:span.end]


    def append(self, layer, *span_obj_pairs):
        layer = self.aliases.get(layer, layer)
        items = sorted(self.annotations[layer] + span_obj_pairs)
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
