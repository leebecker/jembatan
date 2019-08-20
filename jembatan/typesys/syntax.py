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


@dataclass
class DependencyEdge(Annotation):
    label: str = None
    head: AnnotationRef[DependencyNode] = None
    child: AnnotationRef[DependencyNode] = None

    @property
    def to_triple_str(self, spndx):
        head_text = self.head.span.spanned_text(spndx)
        child_text = self.child.span.spanned_text(spndx)
        return f"{self.label}({child_text},{head_text})"


@dataclass
class DependencyNode(Annotation):
    token: AnnotationRef[Token] = None
    head_edge: AnnotationRef[DependencyEdge] = None
    child_edges: List[AnnotationRef[DependencyEdge]] = field(default_factory=list)


@dataclass
class DependencyParse(Annotation):
    root: AnnotationRef[DependencyNode] = None
    edges: List[DependencyEdge] = []
    nodes: List[AnnotationRef[DependencyNode]] = []


@dataclass
class ConstituencyNode(Annotation):
    token: AnnotationRef[Token] = None
    type_: str = None
    parent: AnnotationRef[ConstituencyNode]
    children: List[AnnotationRef[ConstituencyNode]]

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
    children: List[AnnotationRef[ConstituencyNode]]

    def __iter__(self, depth_first=True) -> Iterator[Tuple[Span, ConstituencyNode]]:

        to_process = deque([self.children])
        while to_process:
            node = to_process.popleft()
            yield node.span, node.ref

            if depth_first:
                to_process.extendleft(node.children)
            else:
                to_process.extend(node.children)
