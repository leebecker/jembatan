from dataclasses import dataclass, field
from jembatan.core.spandex import Span
from typing import List, Generic, TypeVar
import collections
import uuid


class HasSourceRef(object):
    """ Simple Trait Class to add a source field via inheritance.
    The source field is intends to be an easy way to communicate
    between services
    """
    source = None


def namedtuple_with_defaults(typename, field_names, default_values=()):
    T = collections.namedtuple(typename, field_names)
    T.__new__.__defaults__ = (None,) * len(T._fields)
    if isinstance(default_values, collections.Mapping):
        prototype = T(**default_values)
    else:
        prototype = T(*default_values)
    T.__new__.__defaults__ = tuple(prototype)
    return T


@dataclass
class Annotation:
    id: uuid.UUID = field(default_factory=uuid.uuid4)


# Create template Type variable
T = T = TypeVar('T')


@dataclass(repr=False)
class AnnotationRef(Generic[T]):
    span: Span = None
    ref: T = None

    def __repr__(self):
        return f"<AnnotationRef[{self.ref.__class__.__module__}.{self.ref.__class__.__name__}]: {self.ref.id}>"


@dataclass
class Document(Annotation):
    """ Top level document type """
    pass


@dataclass
class Block(Annotation):
    tag: str = None


@dataclass
class Sentence(Annotation):
    pass


@dataclass
class Token(Annotation):
    lemma: str = None
    pos: str = None
    tag: str = None


# Placeholder before redefining below
class DependencyNode(Annotation):
    pass


@dataclass
class DependencyEdge(Annotation):
    label: str = None
    head: AnnotationRef[DependencyNode] = None
    child: AnnotationRef[DependencyNode] = None


@dataclass
class DependencyNode(Annotation):
    head_edge: AnnotationRef[DependencyEdge] = None
    child_edges: List[AnnotationRef[DependencyEdge]] = field(default_factory=list)


@dataclass
class Entity(Annotation):
    name: str = None
    salience: str = None
    label: str = None


@dataclass
class NounChunk(Entity):
    pass
