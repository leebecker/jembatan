from collections import deque
from dataclasses import dataclass, field
from jembatan.core.spandex import Span, Spandex
from jembatan.typesys import Annotation, AnnotationRef
from jembatan.typesys.segmentation import Token
from typing import List, Iterable, Iterator, Tuple


# Placeholder before redefining below
class DependencyNode(Annotation):
    pass


class ConstituencyNode(Annotation):
    pass


def deref_span_property(prop_func):
    def get_span():
        return prop_func().span
    return property(get_span)


def deref_property(val_func):
    """
    Decorator function that will dereference an annotation reference and wrap it in a property.
    """

    def get_ref(obj: Annotation):
        """
        Run passed in function on object and pull out span and annotation
        """
        v = val_func(obj)
        return v.span, v.ref
    return property(get_ref)


@dataclass
class DependencyEdge(Annotation):
    label: str = None
    head_ref: AnnotationRef[DependencyNode] = None
    child_ref: AnnotationRef[DependencyNode] = None

    @deref_property
    def head(self):
        return self.head_ref.span

    @head.setter
    def head(self, span_val: Tuple[Span, DependencyNode]):
        self.head_ref = AnnotationRef(span_val[0], span_val[1])

    @deref_property
    def child(self):
        return self.head_ref

    @child.setter
    def child(self, span_val: Tuple[Span, DependencyNode]):
        self.head_ref = AnnotationRef(span_val[0], span_val[1])

    def to_triple_str(self, spndx):
        head_text = self.head.span.spanned_text(spndx)
        child_text = self.child.span.spanned_text(spndx)
        return f"{self.label}({child_text},{head_text})"


@dataclass
class DependencyNode(Annotation):
    token: AnnotationRef[Token] = None

    head_edge: AnnotationRef[DependencyEdge] = None
    child_edges: List[AnnotationRef[DependencyEdge]] = field(default_factory=list)

    @property
    def is_root(self):
        self.head_edge.ref.head.ref == self
        return self.head_edge and self.head_edge.ref.head == self


@dataclass
class DependencyParse(Annotation):
    root: AnnotationRef[DependencyNode] = None
    edges: List[AnnotationRef[DependencyEdge]] = field(default_factory=list)
    nodes: List[AnnotationRef[DependencyNode]] = field(default_factory=list)
    flavor: str = "unknown"


@dataclass
class ConstituencyNode(Annotation):
    token: AnnotationRef[Token] = None
    type_: str = None
    parent: AnnotationRef[ConstituencyNode] = None
    children: List[AnnotationRef[ConstituencyNode]] = field(default_factory=list)

    @property
    def is_leaf(self):
        return not self.children


@dataclass
class ConstituencyParse(Annotation):
    """
    Typically Spans the full sentence
    """
    token: AnnotationRef[Token] = None
    type_: str = None
    children: List[AnnotationRef[ConstituencyNode]] = field(default_factory=list)

    def __iter__(self, depth_first=True) -> Iterator[Tuple[Span, ConstituencyNode]]:

        to_process = deque([self.children])
        while to_process:
            node = to_process.popleft()
            yield node.span, node.ref

            if depth_first:
                to_process.extendleft(node.children)
            else:
                to_process.extend(node.children)
