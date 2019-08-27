from dataclasses import dataclass
from jembatan.typesys import SpannedAnnotation
from typing import AnyStr


@dataclass
class Document(SpannedAnnotation):
    """ Top level document type """
    pass


@dataclass
class Block(SpannedAnnotation):
    tag: AnyStr = None


@dataclass
class Heading(SpannedAnnotation):
    tag: AnyStr = None


@dataclass
class Paragraph(SpannedAnnotation):
    pass


@dataclass
class Sentence(SpannedAnnotation):
    pass


@dataclass
class Token(SpannedAnnotation):
    lemma: AnyStr = None
    stem: AnyStr = None
    pos: AnyStr = None
    tag: AnyStr = None

