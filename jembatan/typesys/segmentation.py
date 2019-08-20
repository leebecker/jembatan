from dataclasses import dataclass
from jembatan.typesys import Annotation
from typing import AnyStr


@dataclass
class Document(Annotation):
    """ Top level document type """
    pass


@dataclass
class Block(Annotation):
    tag: AnyStr = None


@dataclass
class Heading(Annotation):
    tag: AnyStr = None


@dataclass
class Paragraph(Annotation):
    pass


@dataclass
class Sentence(Annotation):
    pass


@dataclass
class Token(Annotation):
    lemma: AnyStr = None
    stem: AnyStr = None
    pos: AnyStr = None
    tag: AnyStr = None

