from bson import ObjectId
from dataclasses import dataclass
from jembatan.core.spandex import Span, Spandex
from jembatan.typesys import Annotation, DocumentAnnotation, SpannedAnnotation


@dataclass
class FooSpanAnnotation(SpannedAnnotation):
    prop1: int = 0
    prop2: str = "foo"


@dataclass
class BarSpanAnnotation(SpannedAnnotation):
    prop_a: int = "a"
    prop_b: str = "b"


@dataclass
class BlahDocAnnotation(DocumentAnnotation):
    prop_c: int = 42


ANNOTATION_IDS = [
    ObjectId('5d657267b2870f18471ad12e'),
    ObjectId('5d657267b2870f18471ad12f'),
    ObjectId('5d657267b2870f18471ad130'),
    ObjectId('5d657267b2870f18471ad131'),
    ObjectId('5d657267b2870f18471ad132'),
    ObjectId('5d657267b2870f18471ad133'),
    ObjectId('5d657267b2870f18471ad134')
]


def test_typesys():

    # note we are forcing ANNOTATION_IDS for consistent testcase ordering
    foo1 = FooSpanAnnotation(id=ANNOTATION_IDS[0])
    assert foo1.prop1 == 0
    assert foo1.prop2 == "foo"

    foo2 = FooSpanAnnotation(id=ANNOTATION_IDS[1], begin=10, end=15)

    assert foo1 == foo1
    assert foo1 < foo2

    bar1 = BarSpanAnnotation(id=ANNOTATION_IDS[2])
    bar2 = BarSpanAnnotation(id=ANNOTATION_IDS[3], prop_a="A", prop_b="B", begin=5, end=9)

    assert bar1 != bar2

    blah1 = BlahDocAnnotation(id=ANNOTATION_IDS[4])

    unknown = Annotation(id=ANNOTATION_IDS[5])

    expected_order = [unknown, blah1, foo1, bar1, bar2, foo2]
    actual_order = sorted([foo1, bar1, bar2, foo2, blah1, unknown])

    for expected, actual in zip(expected_order, actual_order):
        assert expected.id == actual.id


def test_spandex():
    content_string = ''.join(str(s % 10) for s in range(500))
    spndx = Spandex(content_string=content_string)

    # make Foos cover all character offsets with range 5-8
    for i in range(50):
        begin = i * 10 + 5
        end = i*10 + 8
        spndx.add_annotations(FooSpanAnnotation, FooSpanAnnotation(begin=begin, end=end))

    # make Bars cover spans of 100 characters
    for i in range(5):
        begin = i * 100
        end = begin + 100
        spndx.add_annotations(BarSpanAnnotation, BarSpanAnnotation(begin=begin, end=end))

    # make blah Document level annotations
    blah1 = BlahDocAnnotation()
    blah2 = BlahDocAnnotation()
    spndx.add_annotations(BlahDocAnnotation, blah1)
    spndx.add_annotations(BlahDocAnnotation, blah2)

    for bar in spndx.select(BarSpanAnnotation):
        foos = spndx.select_covered(FooSpanAnnotation, bar)
        assert len(foos) == 10

        for foo in foos:
            foo.spanned_text(spndx) == '567'
            spndx.spanned_text(foo) == '567'

        foos = spndx.select_covered(FooSpanAnnotation, Span(bar.begin, bar.end))
        assert len(foos) == 10

    blahs = spndx.select(BlahDocAnnotation)
    assert len(blahs) == 2
