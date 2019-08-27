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


@dataclass
class DependencyEdge(SpannedAnnotation):
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
class DependencyNode(SpannedAnnotation):
    token: AnnotationRef[Token] = None

    head_edge_ref: AnnotationRef[DependencyEdge] = None
    child_edge_refs: List[AnnotationRef[DependencyEdge]] = field(default_factory=list)

    @AnnotationRef.deref_property
    def head_edge(self):
        return self.head_edge_ref

    @head_edge.setter
    def head_edge(self, edge: DependencyEdge):
        self.head_edge_ref = AnnotationRef(obj=edge)

    def add_child_edge(self, edge: DependencyEdge):
        self.child_edge_refs.append(AnnotationRef(obj=edge))

    @AnnotationRef.iter_deref_property
    def child_edges(self):
        return self.child_edge_refs

    @property
    def is_root(self):
        return self.head_edge and self.head_edge.head == self


@dataclass
class DependencyParse(SpannedAnnotation):
    root_ref: AnnotationRef[DependencyNode] = None
    flavor: str = "unknown"

    @AnnotationRef.deref_property
    def root(self):
        return self.root_ref

    @root.setter
    def root(self, node: DependencyNode):
        self.root_ref = AnnotationRef(obj=node)


@dataclass
class ConstituencyNode(SpannedAnnotation):
    token: AnnotationRef[Token] = None
    type_: str = None
    parent: AnnotationRef[ConstituencyNode] = None
    children: List[AnnotationRef[ConstituencyNode]] = field(default_factory=list)

    @property
    def is_leaf(self):
        return not self.children


@dataclass
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
