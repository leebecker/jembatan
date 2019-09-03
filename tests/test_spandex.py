from bson import ObjectId
from dataclasses import dataclass, field
from jembatan.core.spandex import Span, Spandex
from jembatan.core.spandex import json as spandex_json
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


def test_serialization():
    content_string = ''.join(str(s % 10) for s in range(100))
    spndx = Spandex(content_string=content_string)

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
        spndx.add_annotations(FooSpanAnnotation, foo)
        prev = foo

    # make Bars cover spans of 100 characters
    for i in range(5):
        begin = i * 100
        end = begin + 100
        spndx.add_annotations(BarSpanAnnotation, BarSpanAnnotation(begin=begin, end=end))

    # make blah Document level annotations
    blah1 = BlahDocAnnotation()
    blah2 = BlahDocAnnotation()
    spndx.add_annotations(BlahDocAnnotation, blah1, blah2)

    spndx_in = spndx

    serialized_spndx_str = json.dumps(spndx_in, cls=spandex_json.SpandexJsonEncoder)

    # deserialize spandex and validate
    spndx_out = json.loads(serialized_spndx_str, cls=spandex_json.SpandexJsonDecoder)
    for bar in spndx_out.select(BarSpanAnnotation):
        foos = spndx_out.select_covered(FooSpanAnnotation, bar)
        assert len(foos) == 10

        for foo in foos:
            foo.spanned_text(spndx) == '567'
            spndx.spanned_text(foo) == '567'

        foos = spndx.select_covered(FooSpanAnnotation, Span(bar.begin, bar.end))
        assert len(foos) == 10

    blahs = spndx.select(BlahDocAnnotation)
    assert len(blahs) == 2


