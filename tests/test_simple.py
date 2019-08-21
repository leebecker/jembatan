from jembatan.analyzers import simple
from jembatan.readers.textreader import text_to_spandex
from jembatan.typesys.segmentation import Sentence, Token


def test_simple_tokenizer(sample_texts):

    text = "This has four words"
    cas = text_to_spandex(text)

    tokenizer = simple.SimpleTokenizer()
    tokenizer.process(cas)

    tokens = cas.select(Token)
    assert len(list(tokens)) == 4


def test_simple_sentence_segmenter():
    text = "This is sentence 1.  This is sentence 2.  This is sentence 3."
    cas = text_to_spandex(text)

    segmenter = simple.SimpleSentenceSegmenter()

    segmenter.process(cas)
    sentences = cas.select(Sentence)
    assert len(list(sentences)) == 3
