from jembatan.analyzers import spacy as jemspacy
from jembatan.readers.textreader import text_to_spandex
from jembatan.core.spandex import json as jemjson

import json
import jembatan.typesys as jemtypes


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

    for expected, node in zip(expected_graph, spndx.select(jemtypes.syntax.DependencyNode)):
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

    spndx = text_to_spandex(text)

    spacy_analyzer = jemspacy.SpacyAnalyzer(spacy_pipeline=spacy_pipeline)

    spacy_analyzer.process(spndx)

    encoder = jemjson.SpandexJsonEncoder()
    
    x = json.dumps(spndx, cls=jemjson.SpandexJsonEncoder)
    from pprint import pprint
    encoder.default(spndx)
    print(x)
    assert False


