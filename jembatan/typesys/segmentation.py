from jembatan.typesys import SpannedAnnotation
from typing import AnyStr


class Document(SpannedAnnotation):
    """ Top level document type """
    pass


class Block(SpannedAnnotation):
    tag: AnyStr = None


class Heading(SpannedAnnotation):
    tag: AnyStr = None


class Paragraph(SpannedAnnotation):
    pass


class Sentence(SpannedAnnotation):
    pass


class Token(SpannedAnnotation):
    lemma: AnyStr = None
    stem: AnyStr = None
    pos: AnyStr = None
    tag: AnyStr = None

