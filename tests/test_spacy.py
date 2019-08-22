from jembatan.analyzers import spacy as jemspacy
from jembatan.readers.textreader import text_to_spandex
from jembatan.core.spandex import json as jemjson

import json
import jembatan.typesys as jemtypes


def compare_dep_annotations(spndx, dep_parse, expected_graph, expected_pos_tags, expected_lemmas):
    for expected, node in zip(expected_graph, spndx.select_covered(jemtypes.syntax.DependencyNode, dep_parse)):
        node_text = spndx.spanned_text(node)

        if expected[1] == "ROOT":
            assert node.is_root
        else:
            assert not node.is_root

        relation = node.head_edge.label
        head_node = node.head_edge.head
        head_text = spndx.spanned_text(head_node)
        assert expected == (node_text, relation, head_text)

        # ensure we connected the graph both ways
        child_relations = []
        for i, child_relation in enumerate(head_node.child_edges):
            assert child_relation.head == head_node
            child_node = child_relation.child
            child_text = spndx.spanned_text(child_node)
            child_relations.append((child_text, child_relation.label, head_text))
        assert expected in child_relations


def test_spacy_dep(spacy_pipeline):
    text = "John gave the ball to Mary."
    expected_graph = [
        ("John", "nsubj", "gave"),
        ("gave", "ROOT", "gave"),
        ("the", "det", "ball"),
        ("ball", "dobj", "gave"),
        ("to", "dative", "gave"),
        ("Mary", "pobj", "to"),
        (".", "punct", "gave")
    ]

    expected_pos_tags = ['NNP', 'VBD', 'DT', 'NN', 'IN', 'NNP', '.']
    expected_lemmas = ['john', 'give', 'the', 'ball', 'to', 'mary', '.']

    spndx = text_to_spandex(text)

    spacy_analyzer = jemspacy.SpacyAnalyzer(spacy_pipeline=spacy_pipeline)

    spacy_analyzer.process(spndx)

    # pull out annotations and check values
    tokens = spndx.select(jemtypes.segmentation.Token)
    sentences = spndx.select(jemtypes.segmentation.Sentence)
    parses = spndx.select(jemtypes.syntax.DependencyParse)
    for exp_pos, exp_lemma, t in zip(expected_pos_tags, expected_lemmas, tokens):
        assert exp_pos == t.pos
        assert exp_lemma == t.lemma

    assert len(expected_graph) == len(tokens)
    assert len(sentences) == len(parses)
    assert len(sentences) == 1
    assert (sentences[0].end - sentences[0].begin) == len(spndx.content_string)

    # pull out dependency annotations and check parse
    rootnode = parses[0].root
    assert rootnode.child_edges[0].head == rootnode

    compare_dep_annotations(spndx, parses[0], expected_graph, expected_pos_tags, expected_lemmas)


def test_spacy_json_serialization(spacy_pipeline):
    text = "John gave the ball to Mary."
    expected_graph = [
        ("John", "nsubj", "gave"),
        ("gave", "ROOT", "gave"),
        ("the", "det", "ball"),
        ("ball", "dobj", "gave"),
        ("to", "dative", "gave"),
        ("Mary", "pobj", "to"),
        (".", "punct", "gave")
    ]

    expected_pos_tags = ['NNP', 'VBD', 'DT', 'NN', 'IN', 'NNP', '.']
    expected_lemmas = ['john', 'give', 'the', 'ball', 'to', 'mary', '.']

    spndx_in = text_to_spandex(text)

    spacy_analyzer = jemspacy.SpacyAnalyzer(spacy_pipeline=spacy_pipeline)

    spacy_analyzer.process(spndx_in)

    encoder = jemjson.SpandexJsonEncoder()

    serialized_spndx_str = json.dumps(spndx_in, cls=jemjson.SpandexJsonEncoder)

    spndx_out = json.loads(serialized_spndx_str, cls=jemjson.SpandexJsonDecoder)

    sentences_in = spndx_in.select(jemtypes.segmentation.Sentence)
    sentences_out = spndx_out.select(jemtypes.segmentation.Sentence)
    assert len(sentences_in) == len(sentences_out)

    for sentence_in, sentence_out in zip(sentences_in, sentences_out):
        tokens_in = spndx_in.select_covered(jemtypes.segmentation.Token, sentence_in)
        tokens_out = spndx_out.select_covered(jemtypes.segmentation.Token, sentence_out)
        assert len(tokens_in) == len(tokens_out)

        assert sentence_in == sentence_out

        for token_in, token_out in zip(tokens_in, tokens_out):
            assert token_in == token_out
            assert token_in.pos == token_out.pos
            assert token_in.lemma == token_out.lemma
            assert spndx_in.spanned_text(token_in) == spndx_out.spanned_text(token_out)

    parses = spndx_out.select(jemtypes.syntax.DependencyParse)
    compare_dep_annotations(spndx_out, parses[0], expected_graph, expected_pos_tags, expected_lemmas)
