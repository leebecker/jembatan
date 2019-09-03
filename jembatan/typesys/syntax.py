from collections import deque
from dataclasses import dataclass, field
from jembatan.typesys import SpannedAnnotation, AnnotationRef
from jembatan.typesys.segmentation import Token
from typing import List, Iterator


# Placeholder before redefining below
class DependencyNode(SpannedAnnotation):
    pass


class ConstituencyNode(SpannedAnnotation):
    pass


class DependencyEdge(SpannedAnnotation):
    label: str = None
    head: DependencyNode = None
    child: DependencyNode = None

    """
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
    """

    def to_triple_str(self, spndx):
        head_text = self.head.span.spanned_text(spndx)
        child_text = self.child.span.spanned_text(spndx)
        return f"{self.label}({child_text},{head_text})"


class DependencyNode(SpannedAnnotation):
    token: Token = None

    head_edge: DependencyEdge = None
    child_edges: List[DependencyEdge] = field(default_factory=list)

    @property
    def is_root(self):
        return self.head_edge and self.head_edge.head == self


class DependencyParse(SpannedAnnotation):
    root: DependencyNode = None
    flavor: str = "unknown"


class ConstituencyNode(SpannedAnnotation):
    token: AnnotationRef[Token] = None
    type_: str = None
    parent: AnnotationRef[ConstituencyNode] = None
    children: List[AnnotationRef[ConstituencyNode]] = field(default_factory=list)

    @property
    def is_leaf(self):
        return not self.children


class ConstituencyParse(SpannedAnnotation):
    """
    Typically Spans the full sentence
    """
    token_ref: AnnotationRef[Token] = None
    type_: str = None
    children_refs: List[AnnotationRef[ConstituencyNode]] = field(default_factory=list)

    @AnnotationRef.deref_property
    def token(self):
        return self.token_ref

    @AnnotationRef.iter_deref_property
    def children(self):
        return self.children_refs

    def add_child(self, node: ConstituencyNode):
        self.children_refs.append(node)

    def __iter__(self, depth_first=True) -> Iterator[ConstituencyNode]:

        to_process = deque([self.children])
        while to_process:
            node = to_process.popleft()
            yield node

            if depth_first:
                to_process.extendleft(node.children)
            else:
                to_process.extend(node.children)
