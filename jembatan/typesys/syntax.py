from collections import deque
from dataclasses import dataclass, field
from jembatan.typesys import Annotation, AnnotationRef
from jembatan.typesys.segmentation import Token
from typing import List, Iterator


# Placeholder before redefining below
class DependencyNode(Annotation):
    pass


class ConstituencyNode(Annotation):
    pass


@dataclass
class DependencyEdge(Annotation):
    label: str = None
    head_ref: AnnotationRef[DependencyNode] = None
    child_ref: AnnotationRef[DependencyNode] = None

    @AnnotationRef.deref_property
    def head(self):
        return self.head_ref

    @head.setter
    def head(self, node: DependencyNode):
        self.head_ref = AnnotationRef(node)

    @AnnotationRef.deref_property
    def child(self):
        return self.child_ref

    @child.setter
    def child(self, node: DependencyNode):
        self.child_ref = AnnotationRef(node)

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
        return self.head_edge and self.head_edge.obj.head == self


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

    def __iter__(self, depth_first=True) -> Iterator[ConstituencyNode]:

        to_process = deque([self.children])
        while to_process:
            node = to_process.popleft()
            yield node.obj

            if depth_first:
                to_process.extendleft(node.children)
            else:
                to_process.extend(node.children)
