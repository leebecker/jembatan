from collections import deque
from dataclasses import dataclass, field, Field
from functools import total_ordering
from typing import get_type_hints, Any, Generic, Iterable, List, Mapping, Optional, Sequence, TypeVar, Union

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
    def topair(self):
        return (self.begin, self.end)

    @property
    def isempty(self):
        return self.end == self.begin

    @property
    def length(self) -> int:
        return self.end - self.begin

    def contains(self, pos: int):
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

    def to_json(self):
        return self._asdict()

    def spanned_text(self, spndx: "Spandex"):
        return spndx.spanned_text(self)

    @classmethod
    def from_json(self, obj):
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
    Metaclass used to define special construction of Annotation types.
    """

    @classmethod
    def create_post(metacls, scope):
        def __post_init__(self):
            self._scope = scope
        return __post_init__

    def __new__(metacls, name, bases, namespace, **kwds):
        # Create a new class type
        newclass = super().__new__(metacls, name, bases, dict(namespace))

        # attach a post init method to initialize scope
        if 'scope' in kwds:
            setattr(newclass, '__post_init__', AnnotationMeta.create_post(kwds['scope']))

        # now wrap the new class in a dataclass
        dataclass(repr=False)(newclass)
        return newclass


def generate_annotation_id():
    # For now using bson to align with possible mongo db integration
    return str(bson.ObjectId())


@total_ordering
class Annotation(metaclass=AnnotationMeta, scope=AnnotationScope.UNKNOWN):
    id: str = field(default_factory=generate_annotation_id)

    # Define fields that get special status in the __repr__ command
    _SPECIAL_FIELDS = ['id']

    @property
    def scope(self) -> AnnotationScope:
        # FIXME should this go in the metaclass?
        return self._scope

    def __lt__(self, other: "Annotation"):
        if not isinstance(other, Annotation):
            return NotImplemented

        if self.scope == other.scope:
            return self.id < other.id
        return self.scope < other.scope

    @property
    def index_key(self):
        return (self.scope, None)

    def encode_field_val_for_repr(self, val):
        """
        Function for encoding dataclass field values
        """
        # FIXME put this in metaclass because Annotation should not know about dataclasses inherently
        if isinstance(val, Annotation):
            return f"{val.__class__.__name__}(id={val.id})"
        elif isinstance(val, Sequence) and not isinstance(val, str):
            return '[' + ', '.join([self.encode_field_val_for_repr(v) for v in val]) + ']'
        elif isinstance(val, Mapping):
            key_val_str = ', '.join(f"{k}: {self.encode_field_val_for_repr(v)}" for k, v in val.items())
            return '{' + key_val_str + '}'
        else:
            return repr(val)

    def __repr__(self):
        # Compute special encoding. Not using out of the box __repr__ that comes with
        special_field_val_pairs = (
            (fieldname, getattr(self, fieldname)) for fieldname in self._SPECIAL_FIELDS
        )
        field_val_pairs = (
            (fieldname, getattr(self, fieldname)) for fieldname in self.__dataclass_fields__
            if fieldname not in self._SPECIAL_FIELDS
        )
        encoded_field_val_pairs = (
            (f, self.encode_field_val_for_repr(v)) for (f, v) in
            itertools.chain(special_field_val_pairs, field_val_pairs)
        )
        fields_str = ', '.join(f"{f}={v}" for (f, v) in encoded_field_val_pairs)

        return f"{self.__class__.__name__}({fields_str})"


class DocumentAnnotation(Annotation, metaclass=AnnotationMeta, scope=AnnotationScope.DOCUMENT):
    pass


@total_ordering
class SpannedAnnotation(Annotation, Span, metaclass=AnnotationMeta, scope=AnnotationScope.SPAN):

    # Define fields that get special status in the __repr__ command
    _SPECIAL_FIELDS = ['id', 'begin', 'end']

    @property
    def span(self):
        return Span(self.begin, self.end)

    @span.setter
    def span(self, span: Span):
        self.begin = span.begin
        self.end = span.end

    def __lt__(self, other: Union[Span, "SpannedAnnotation", Annotation]):
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
    def index_key(self):
        return (self.scope, self.begin)


# Create template Type variable
T = T = TypeVar('T')


@dataclass(repr=False)
class AnnotationRef(Generic[T]):
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

            #match = src_origin == tgt_origin

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



def _create_annot_ref(annot: Annotation) -> Optional[AnnotationRef]:

    """ Convert annotation into AnnotationRef """
    return AnnotationRef(obj=v) if v is not None else v


def _create_deref_prop(attribute_name):
    """
    Given an attribute name, this will create a convenience property for getting
    and setting the underlying annotation for the reference
    """
    @property
    def prop(self) -> Annotation:
        ref = getattr(self, attribute_name)
        return ref.obj if ref is not None else ref

    @prop.setter
    def prop(self, v: Annotation) -> None:
        setattr(self, attribute_name, _create_annot_ref(v))

    prop.__doc__ = f"""
    Dereference convenience property for getting/setting contents of {attribute_name} AnnotationRef
    """
    return prop


def _create_list_deref_prop(attribute_name):
    """
    Given an attribute name, this will create a convenience property for getting
    and setting the underlying annotation for the reference
    """
    @property
    def prop(self) -> Annotation:
        refs = getattr(self, attribute_name)

        if refs is None:
            return []
        else:
            return [ref.obj if ref is not None else ref for ref in refs]

    @prop.setter
    def prop(self, values: List[Annotation]) -> None:
        if values is not None:
            setattr(self, attribute_name, [_create_annot_ref(v) for v in values])
        else:

            setattr(self, attribute_name, [])

    prop.__doc__ = f"""
    Dereference convenience property for getting/setting List of AnnotationRefs in {attribute_name}
    """
    return prop


def make_it_annotation(cls):
    """
    Decorator that coverts class into an annotation.


    Examples:

    @SpandexAnnotation
    class MyAnnotation:
        value: int = 1

        previous_annot_ref: AnnotationRef["MyAnnotation"] = None
    """

    # parse out class definition
    # look for annotations of type AnnotationRef
    ref_suffix = '_ref'
    ref_plural_suffix = '_refs'
    for attribute_name, attribute in get_type_hints(cls).items():
        print(attribute)

        try:
            attr = getattr(cls, attribute_name)
        except AttributeError:
            raise AttributeError(
                f"Annotation field {attribute_name} does not have a valid default value.  "
                "Refer to :func:`~dataclasses.field` for more information.")
        prop_name = None
        prop_is_list = False
        if attribute == AnnotationRef:
            if isinstance(attr, Field) and 'deref_prop_name' in attr.metadata:
                # If field metadata specifies property name, use that
                prop_name = attr.metadata['deref_prop_name']
            elif attribute_name.endswith(ref_suffix):
                # Back off to convention of naming by dropping ref
                prop_name = attribute_name[:-len(ref_suffix)]

        elif _get_args_chain(attribute)[0:2] == [List, AnnotationRef]:
            prop_is_list = True
            if isinstance(attr, Field) and 'deref_prop_name' in attr.metadata:
                # If field metadata specifies property name, use that
                prop_name = attr.metadata['deref_prop_name']
            elif attribute_name.endswith(ref_plural_suffix):
                # Back off to convention of naming by dropping ref
                prop_name = attribute_name[:-len(ref_plural_suffix)]

        if prop_name:
            create_func = _create_list_deref_prop if prop_is_list else _create_deref_prop
            prop = create_func(attribute_name)
            setattr(cls, prop_name, prop)

    # convert it into a dataclass
    dataclass(cls)

    return cls
