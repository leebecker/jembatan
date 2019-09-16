from jembatan.analyzers import simple
from jembatan.core.spandex import constants as jemconst
from jembatan.readers.textreader import text_to_jembatan_doc
from jembatan.typesys.segmentation import Sentence, Token


def test_simple_tokenizer(sample_texts):

    text = "This has four words"
    jemdoc = text_to_jembatan_doc(text)

    tokenizer = simple.SimpleTokenizer()
    tokenizer.process(jemdoc)

    spndx = jemdoc.get_view(jemconst.SPANDEX_DEFAULT_VIEW)
    tokens = spndx.select(Token)
    assert len(list(tokens)) == 4


def test_simple_sentence_segmenter():
    text = "This is sentence 1.  This is sentence 2.  This is sentence 3."
    jemdoc = text_to_jembatan_doc(text)

    segmenter = simple.SimpleSentenceSegmenter()

    spndx = jemdoc.get_view(jemconst.SPANDEX_DEFAULT_VIEW)
    segmenter.process(jemdoc)
    sentences = spndx.select(Sentence)
    assert len(list(sentences)) == 3
