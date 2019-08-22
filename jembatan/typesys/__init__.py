from dataclasses import dataclass, field
from functools import total_ordering
from jembatan.core.spandex import Span
from typing import Generic, Iterable, TypeVar
import collections
import math
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
class Annotation(Span):
    id: uuid.UUID = field(default_factory=uuid.uuid4)

    @property
    def span(self):
        return Span(self.begin, self.end)

    @span.setter
    def span(self, span: Span):
        self.begin = span.begin
        self.end = span.end

    def __lt__(self, other: Span):
        if not isinstance(other, Span):
            return NotImplemented

        span1 = Span(self.begin, self.end)
        span2 = Span(other.begin, other.end)
        if isinstance(other, Annotation):
            return (span1, self.id) < (span2, other.id)
        else:
            return span1 < span2

    def __hash__(self):
        return (self.id, self.begin, self.end).__hash__()


# Create template Type variable
T = T = TypeVar('T')


@dataclass(repr=False)
class AnnotationRef(Generic[T]):
    obj: T = None

    def __repr__(self):
        return f"<AnnotationRef[{self.obj.__class__.__module__}.{self.obj.__class__.__name__}]: {self.obj.id}>"

    @classmethod
    def deref_property(cls, val_func):
        """
        Decorator function that will dereference an annotation reference and wrap it in a property.
        """

        def get_ref(obj: Annotation):
            """
            Run passed in function on object and pull out span and annotation
            """

            v = val_func(obj)
            if v is None:
                return None
            return v.obj
        return property(get_ref)

    @classmethod
    def iter_deref_property(cls, val_func):
        """
        Decorator function that will dereference an annotation reference and wrap it in a property.
        """

        def get_ref(obj: Iterable[AnnotationRef]):
            """
            Run passed in function on object and pull out span and annotation
            """

            annotation_refs = val_func(obj)
            if annotation_refs is None:
                return []
            else:
                return [v.obj if v is not None else v for v in annotation_refs]

        return property(get_ref)
