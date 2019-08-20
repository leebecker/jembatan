from dataclasses import dataclass, field
from functools import total_ordering
from jembatan.core.spandex import Span
from typing import Generic, TypeVar
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
@total_ordering
class Annotation:
    id: uuid.UUID = field(default_factory=uuid.uuid4)

    def __lt__(self, other):
        return id(self) < id(other)


# Create template Type variable
T = T = TypeVar('T')


@dataclass(repr=False)
class AnnotationRef(Generic[T]):
    span: Span = None
    ref: T = None

    def __repr__(self):
        return f"<AnnotationRef[{self.ref.__class__.__module__}.{self.ref.__class__.__name__}]: {self.ref.id}>"
