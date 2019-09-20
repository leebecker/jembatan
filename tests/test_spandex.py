from bson import ObjectId
from dataclasses import field
from jembatan.core.spandex import Span
from jembatan.core.spandex import constants as jemconst
from jembatan.core.spandex import json as spandex_json
from jembatan.readers.textreader import text_to_jembatan_doc
from jembatan.typesys import Annotation, AnnotationScope, DocumentAnnotation, SpannedAnnotation
from typing import Dict, List

import json


class FooSpanAnnotation(SpannedAnnotation):
    prop1: int = 0
    prop2: str = "foo"
    prev: "FooSpanAnnotation" = None
    seq_prop: List["FooSpanAnnotation"] = field(default_factory=list)
    map_prop: Dict[str, "FooSpanAnnotation"] = field(default_factory=dict)


class BarSpanAnnotation(SpannedAnnotation):
    prop_a: int = "a"
    prop_b: str = "b"


class FooOneExtended(FooSpanAnnotation):
    pass


class FooTwoExtended(FooSpanAnnotation):
    pass


class BlahDocAnnotation(DocumentAnnotation):
    prop_c: int = 42


ANNOTATION_IDS = [
    str(ObjectId('5d657267b2870f18471ad12e')),
    str(ObjectId('5d657267b2870f18471ad12f')),
    str(ObjectId('5d657267b2870f18471ad130')),
    str(ObjectId('5d657267b2870f18471ad131')),
    str(ObjectId('5d657267b2870f18471ad132')),
    str(ObjectId('5d657267b2870f18471ad133')),
    str(ObjectId('5d657267b2870f18471ad134'))
]


def test_typesys():

    assert Annotation().scope == AnnotationScope.UNKNOWN
    assert SpannedAnnotation().scope == AnnotationScope.SPAN
    assert DocumentAnnotation().scope == AnnotationScope.DOCUMENT

    # note we are forcing ANNOTATION_IDS for consistent testcase ordering
    foo1 = FooSpanAnnotation(id=ANNOTATION_IDS[0])
    assert foo1.prop1 == 0
    assert foo1.prop2 == "foo"
    assert foo1.scope == AnnotationScope.SPAN

    foo2 = FooSpanAnnotation(id=ANNOTATION_IDS[1], begin=10, end=15)

    assert foo1 == foo1
    assert foo1 < foo2

    bar1 = BarSpanAnnotation(id=ANNOTATION_IDS[2])
    bar2 = BarSpanAnnotation(id=ANNOTATION_IDS[3], prop_a="A", prop_b="B", begin=5, end=9)

    assert bar1 != bar2

    blah1 = BlahDocAnnotation(id=ANNOTATION_IDS[4])
    assert blah1.scope == AnnotationScope.DOCUMENT
    doc1 = DocumentAnnotation()
    assert doc1.scope == AnnotationScope.DOCUMENT

    unknown = Annotation(id=ANNOTATION_IDS[5])
    assert unknown.scope == AnnotationScope.UNKNOWN

    expected_order = [unknown, blah1, foo1, bar1, bar2, foo2]
    actual_order = sorted([foo1, bar1, bar2, foo2, blah1, unknown])

    for expected, actual in zip(expected_order, actual_order):
        assert expected.id == actual.id


def test_typesys_inheritance():

    content_string = ''.join(str(s % 10) for s in range(500))
    jemdoc = text_to_jembatan_doc(content_string)
    spndx = jemdoc.get_view(jemconst.SPANDEX_DEFAULT_VIEW)

    foo = FooSpanAnnotation(begin=100, end=200)
    foo_one = FooOneExtended(begin=200, end=300)
    foo_two = FooTwoExtended(begin=300, end=400)
    bar = BarSpanAnnotation(begin=105, end=205)

    spndx.add_annotations(foo, foo_one, foo_two, bar)

    assert len(spndx.select_covered(FooSpanAnnotation, Span(0, 500))) == 3
    assert len(spndx.select_covered(FooOneExtended, Span(0, 500))) == 1
    assert len(spndx.select_covered(FooTwoExtended, Span(0, 500))) == 1
    assert len(spndx.select_covered(BarSpanAnnotation, Span(0, 500))) == 1


def test_spandex():
    content_string = ''.join(str(s % 10) for s in range(500))
    jemdoc = text_to_jembatan_doc(content_string)
    spndx = jemdoc.get_view(jemconst.SPANDEX_DEFAULT_VIEW)

    # make Foos cover all character offsets with range 5-8
    for i in range(50):
        begin = i * 10 + 5
        end = i*10 + 8
        spndx.add_annotations(FooSpanAnnotation(begin=begin, end=end))

    # make Bars cover spans of 100 characters
    for i in range(5):
        begin = i * 100
        end = begin + 100
        spndx.add_annotations(BarSpanAnnotation(begin=begin, end=end))

    # make blah Document level annotations
    blah1 = BlahDocAnnotation()
    blah2 = BlahDocAnnotation()
    spndx.add_annotations(blah1)
    spndx.add_annotations(blah2)

    for i, bar in enumerate(spndx.select(BarSpanAnnotation)):
        foos = spndx.select_covered(FooSpanAnnotation, bar)
        assert len(foos) == 10

        for foo in foos:
            assert foo.spanned_text(spndx) == '567'
            assert spndx.spanned_text(foo) == '567'

        foos = spndx.select_covered(FooSpanAnnotation, Span(bar.begin, bar.end))
        assert len(foos) == 10

        preceding_foos = spndx.select_preceding(FooSpanAnnotation, bar)
        assert len(preceding_foos) == i * 10

        following_foos = spndx.select_following(FooSpanAnnotation, bar)
        assert len(following_foos) == 40 - (i * 10)

    blahs = spndx.select(BlahDocAnnotation)
    assert len(blahs) == 2


def test_serialization():
    content_string = ''.join(str(s % 10) for s in range(100))

    jemdoc = text_to_jembatan_doc(content_string)
    spndx = jemdoc.get_view(jemconst.SPANDEX_DEFAULT_VIEW)

    # make Foos cover all character offsets with range 5-8
    prev = None
    for i in range(50):
        begin = i * 10 + 5
        end = i*10 + 8
        foo = FooSpanAnnotation(begin=begin, end=end)
        foo.prev = prev
        foo.seq_prop.append(prev)
        foo.seq_prop.append(foo)
        foo.map_prop['prev'] = prev
        spndx.add_annotations(foo)
        prev = foo

    # make Bars cover spans of 100 characters
    for i in range(5):
        begin = i * 100
        end = begin + 100
        spndx.add_annotations(BarSpanAnnotation(begin=begin, end=end))

    # make blah Document level annotations
    blah1 = BlahDocAnnotation()
    blah2 = BlahDocAnnotation()
    spndx.add_annotations(blah1, blah2)

    jemdoc_in = jemdoc

    serialized_spndx_str = json.dumps(jemdoc_in, cls=spandex_json.JembatanDocJsonEncoder)

    # deserialize spandex and validate
    jem_out = json.loads(serialized_spndx_str, cls=spandex_json.JembatanDocJsonDecoder)
    spndx_out = jem_out.get_view(jemconst.SPANDEX_DEFAULT_VIEW)

    assert len(spndx_out.select(BarSpanAnnotation)) == 5
    for bar in spndx_out.select(BarSpanAnnotation):
        foos = spndx_out.select_covered(FooSpanAnnotation, bar)
        assert len(foos) == 10

        for foo in foos:
            foo.spanned_text(spndx) == '567'
            spndx.spanned_text(foo) == '567'

            assert isinstance(foo.seq_prop, list)
            assert isinstance(foo.map_prop, dict)

        foos = spndx.select_covered(FooSpanAnnotation, Span(bar.begin, bar.end))
        assert len(foos) == 10

    blahs = spndx.select(BlahDocAnnotation)
    assert len(blahs) == 2
