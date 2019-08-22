from dataclasses import dataclass, field
from functools import total_ordering
from typing import Generic, Iterable, TypeVar

import math
import uuid


@dataclass
@total_ordering
class Span:
    """
    A class defining offsets and spans over textual content.  The ordering of these
    allows for convenient query within a Spandex, it has two named fields
    `begin` and `end`.

    Examples:
        # construction
        span1 = Span(begin=1, end=10)
        span2 = Span(5, 10)
    """
    begin: int = None
    end: int = None

    @property
    def topair(self):
        return (self.begin, self.end)

    @property
    def isempty(self):
        return self.end == self.begin

    @property
    def length(self):
        return self.end - self.begin

    def contains(self, pos: int):
        return pos >= self.begin and pos < self.end

    def crosses(self, other: "Span"):
        return (self.begin < other.begin and self.end < other.end and self.end > other.begin) or \
            (other.begin < self.begin and other.end < self.end and other.end > self.begin)

    def __eq__(self, other: "Span"):
        return self.begin == other.begin and self.end == other.end

    def __lt__(self, other: "Span"):

        if other is None:
            return True

        if not isinstance(other, Span):
            return NotImplemented

        tuple1 = (
            self.begin if self.begin is not None else -math.inf,
            self.end if self.end is not None else -math.inf,
        )

        tuple2 = (
            other.begin if other.begin is not None else -math.inf,
            other.end if other.end is not None else -math.inf,
        )

        return tuple1 < tuple2

    def __hash__(self):
        return (self.begin, self.end).__hash__()

    def to_json(self):
        return self._asdict()

    def spanned_text(self, spndx: "Spandex"):
        return spndx.spanned_text(self)

    @classmethod
    def from_json(self, obj):
        return Span(**obj)


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
