from collections import deque
from dataclasses import dataclass, field
from functools import total_ordering
from typing import get_type_hints, Any, Generic, Iterable, List, Mapping, Optional, Sequence, Tuple, TypeVar, Union

import bson
import enum
import itertools
import math
import typing
import typing_inspect


@dataclass(repr=False)
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
    def topair(self) -> Tuple[int, int]:
        return (self.begin, self.end)

    @property
    def isempty(self) -> bool:
        return self.end == self.begin

    @property
    def length(self) -> int:
        return self.end - self.begin

    def contains(self, pos: int) -> bool:
        return pos >= self.begin and pos < self.end

    def crosses(self, other: "Span") -> bool:
        return (self.begin < other.begin and self.end < other.end and self.end > other.begin) or \
            (other.begin < self.begin and other.end < self.end and other.end > self.begin)

    def __eq__(self, other: "Span") -> bool:
        return self.begin == other.begin and self.end == other.end

    def __lt__(self, other: "Span") -> bool:

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

    def to_json(self) -> dict:
        return self._asdict()

    def spanned_text(self, spndx: "Spandex") -> str:
        return spndx.spanned_text(self)

    @classmethod
    def from_json(self, obj: dict) -> "Span":
        return Span(**obj)


@total_ordering
class AnnotationScope(enum.Enum):
    UNKNOWN = "UNKNOWN"
    DOCUMENT = "DOCUMENT"
    SPAN = "SPAN"

    def to_json(self):
        return self.value

    def __lt__(self, other: "AnnotationScope"):
        ordering = [self.UNKNOWN, self.DOCUMENT, self.SPAN]
        return ordering.index(self) < ordering.index(other)

    @staticmethod
    def from_str(label):
        try:
            return AnnotationScope[label.upper()]
        except KeyError:
            return AnnotationScope.UNKNOWN


class AnnotationMeta(type):
    """
    Metaclass used to define special construction of Annotation types.  In most cases
    this should not be used outside of this module
    """

    @classmethod
    def create_post_fn(metacls, scope: str):
        """
        Factory function for creating a __post_init__ method that is used in conjunction w/ dataclass __init__
        """
        def __post_init__(self):
            self._scope = scope
        return __post_init__

    @classmethod
    def create_scope_property(metacls):
        """
        Factory function for creating a scope property
        """
        def scope(self):
            return self._scope

        return property(scope)

    @classmethod
    def encode_field_val_for_repr(metacls, val):
        """
        Function for encoding dataclass field values.  This is used by the __repr__ function created below
        """
        # FIXME put this in metaclass because Annotation should not know about dataclasses inherently
        if isinstance(val, Annotation):
            return f"{val.__class__.__name__}(id={val.id})"
        elif isinstance(val, Sequence) and not isinstance(val, str):
            return '[' + ', '.join([metacls.encode_field_val_for_repr(v) for v in val]) + ']'
        elif isinstance(val, Mapping):
            key_val_str = ', '.join(f"{k}: {metacls.encode_field_val_for_repr(v)}" for k, v in val.items())
            return '{' + key_val_str + '}'
        else:
            return repr(val)

    @classmethod
    def create_repr_fn(metacls):
        """
        Factory function for creating a __repr__ method in the new class.  This essentially does the
        equivalent encoding provided by dataclass, but stubs out annotations linked from other annotations
        to avoid recursion
        """
        def __repr__(self):
            # Compute special encoding. Not using out of the box __repr__ that comes with dataclass
            special_field_val_pairs = (
                (fieldname, getattr(self, fieldname)) for fieldname in self._SPECIAL_FIELDS
            )
            field_val_pairs = (
                (fieldname, getattr(self, fieldname)) for fieldname in self.__dataclass_fields__
                if fieldname not in self._SPECIAL_FIELDS
            )
            encoded_field_val_pairs = (
                (f, metacls.encode_field_val_for_repr(v)) for (f, v) in
                itertools.chain(special_field_val_pairs, field_val_pairs)
            )
            fields_str = ', '.join(f"{f}={v}" for (f, v) in encoded_field_val_pairs)

            return f"{self.__class__.__name__}({fields_str})"

        return __repr__

    def __new__(metacls, name, bases, namespace, **kwds):
        # Create a new class type
        newclass = super().__new__(metacls, name, bases, dict(namespace))

        # attach a post init method to initialize scope
        if 'scope' in kwds:
            setattr(newclass, '__post_init__', AnnotationMeta.create_post_fn(kwds['scope']))
            setattr(newclass, 'scope', AnnotationMeta.create_scope_property())

        # set the __repr__ function so we don't get recursion
        # _SPECIAL_FIELDS are fields that get first priority in display
        special_fields = kwds.get('special_fields', None)
        if special_fields:
            # if special fields is not specified we will assume it and the __repr__ function are
            # inherited from a parent class
            setattr(newclass, '__repr__', AnnotationMeta.create_repr_fn())
            setattr(newclass, '_SPECIAL_FIELDS', special_fields)

        # lastly wrap the new class in a dataclass
        dataclass(repr=False)(newclass)
        return newclass


def generate_annotation_id():
    # For now using bson to align with possible mongo db integration
    return str(bson.ObjectId())


@total_ordering
class Annotation(metaclass=AnnotationMeta,
                 scope=AnnotationScope.UNKNOWN,
                 special_fields=['id']):
    """
    Base class for defining Annotations.  In most cases a new type will not inherit from this one
    """
    # define base ID field
    id: str = field(default_factory=generate_annotation_id)

    def __lt__(self, other: "Annotation") -> bool:
        if not isinstance(other, Annotation):
            return NotImplemented

        if self.scope == other.scope:
            return self.id < other.id
        return self.scope < other.scope

    @property
    def index_key(self) -> Tuple[AnnotationScope, Union[int, None]]:
        """
        value used for indexing within Spandex layers
        """
        return (self.scope, None)


class DocumentAnnotation(Annotation, metaclass=AnnotationMeta, scope=AnnotationScope.DOCUMENT):
    """
    Base class for defining document level annotations.
    """
    pass


@total_ordering
class SpannedAnnotation(Annotation, Span,
                        metaclass=AnnotationMeta,
                        scope=AnnotationScope.SPAN,
                        special_fields=['id', 'begin', 'end']):
    """
    Base class for defining span-level annotations.  Derive from this any time you have a scope
    that is a character offset
    """

    @property
    def span(self):
        return Span(self.begin, self.end)

    @span.setter
    def span(self, span: Span):
        self.begin = span.begin
        self.end = span.end

    def __lt__(self, other: Union[Span, "SpannedAnnotation", Annotation]) -> bool:
        if isinstance(other, Span):
            span1 = Span(self.begin, self.end)
            span2 = Span(other.begin, other.end)
            if isinstance(other, SpannedAnnotation):
                return (span1, self.id) < (span2, other.id)
            else:
                return span1 < span2
        elif isinstance(other, Annotation):
            return super(Annotation, self).__lt__(other)
        else:
            return NotImplemented

    def __hash__(self):
        return (self.id, self.begin, self.end).__hash__()

    @property
    def index_key(self) -> Tuple[AnnotationScope, Union[int, None]]:
        return (self.scope, self.begin)


# Create template Type variable
T = T = TypeVar('T')


@dataclass(repr=False)
class AnnotationRef(Generic[T]):
    """
    Class for wrapping Annotations as a reference. These have disappeared from type definitions as their need has
    been obfuscated with better serialization.  At present the json spandex serializers still rely on this class
    """
    obj: T = None

    def __repr__(self):
        if self.obj is None:
            return f"<AnnotationRef[{self.obj}]>"

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


def _get_args_chain(cls):
    """
    Extracts out DFS ordering of type hint hierarchy.  This gives sufficient information
    to perform inspection of python field declarations for type hint matching like List[AnnotationRef]
    when the declarations may be more like List[AnnotationRef[Token]]
    """
    arg_chain = []
    to_process = deque([cls])

    while to_process:
        curr = to_process.popleft()
        curr_origin = getattr(curr, '__origin__', curr)
        arg_chain.append(curr_origin)
        args = [a for a in getattr(curr, '__args__', [])]
        to_process.extendleft(reversed(args))
    return arg_chain


def type_match(src_type, tgt_type):
    """
    Compares two type hints to see if they overlap.  This does not require exact matches if the target type

    type_match(

    """

    match = False
    if tgt_type == Any:
        match = True
    elif not issubclass(tgt_type.__class__, typing.GenericMeta):
        # if the target type is not a generic template, see if we have a subclass match
        match = issubclass(src_type, tgt_type)
    else:
        # check classes are the same
        match = src_type.__class__ == tgt_type.__class__

        if match:
            src_origin = typing_inspect.get_last_origin(src_type)
            tgt_origin = typing_inspect.get_last_origin(tgt_type)

            match = typing_inspect.get_origin(Union[src_origin, tgt_origin]) != Union

    if not match:
        return False

    src_args = typing_inspect.get_last_args(src_type)
    tgt_args = typing_inspect.get_last_args(tgt_type)

    if len(tgt_args) == 0:
        return True

    if len(src_args) != len(tgt_args):
        return False

    for src_arg, tgt_arg in zip(src_args, tgt_args):
        if not type_match(src_arg, tgt_arg):
            return False

    return True
