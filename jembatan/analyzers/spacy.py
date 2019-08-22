import re
#from jembatan.spandex import (Span, Spandex)
#from ..spandex.types import (Document, Sentence, Token, PartOfSpeech, NounChunk, DependencyEdge, Entity)
import itertools
import functools

from enum import auto, Flag
from jembatan.core.spandex import (Span, Spandex)
from jembatan.core.af import AnalysisFunction
from jembatan.typesys import AnnotationRef
from jembatan.typesys.chunking import NounChunk, Entity
from jembatan.typesys.segmentation import (Document, Sentence, Token)
from jembatan.typesys.syntax import (DependencyEdge, DependencyNode, DependencyParse)


class AnnotationLayers(Flag):
    """Enumerated type useful for turning on/off behavior in Spacy Analyzers
    """
    DOCUMENT = auto()
    SENTENCE = auto()
    TOKEN = auto()
    DEPPARSE = auto()
    ENTITY = auto()
    NOUN_CHUNK = auto()

    @classmethod
    def NONE(cls):
        return functools.reduce(lambda x, y: x | y, [f for f in cls])

    @classmethod
    def ALL(cls):
        return functools.reduce(lambda x, y: x | y, [f for f in cls])

    @classmethod
    def contains(flagset, flag):
        return bool(flagset & flag)


class SpacyToJson(object):


    def __init__(self):
        pass


    def serialize_token(self, t): #, token_lookup, sent_idx):
        res = {}
        text = {
            "content": t.text,
            "beginOffset": t.idx
        }

        partOfSpeech = {
            "tag": t.pos_,  # This switch is to make naming consistent with Google Natural Language API
            "pos": t.tag_   # This is not a field in Google's API, but the original Treebank
        }


        depEdge = {
            "headTokenIndex": t.head.i,
            "label": t.dep_
        }
        
        return {
                "text": text,
                "partOfSpeech": partOfSpeech,
                "lemma": t.lemma_,
                "dependencyEdge": depEdge
        }

    def serialize_sentence(self, s):
        return {
            "text": {
                "content": s.text,
                "beginOffset": s.start_char
            },
            "sentiment": {}
        }


    def serialize_entity(self, e):
        return {
            "name": e.text,
            "type": e.label_,
            "metadata": { },
            "salience": -1,
            "mentions": [ {"content": e.text, "beginOffset": e.start_char, "type": "PROPER"}]
        }


    def to_json(self, spacydoc):

        sentences = [self.serialize_sentence(s) for s in spacydoc.sents]
        tokens = [self.serialize_token(t) for t in spacydoc]
        entities = [self.serialize_entity(e) for e in spacydoc.ents]

        return {
            "sentences": sentences,
            "tokens": tokens,
            "entities": entities,
            "documentSentiment": {},
            "language": "unk"
        }


class SpacyToSpandexUtils:

    @staticmethod
    def convert_sentence(spacysent, window_span=None):
        begin = spacysent.start_char
        end = begin + len(spacysent.text)

        if window_span:
            sent_span = Span(begin=window_span.begin + begin, end=window_span.begin + end)
        else:
            sent_span = Span(begin=begin, end=end)

        sent = Sentence()
        sent.span = sent_span
        sent.source = spacysent
        return sent

    @staticmethod
    def convert_token(spacytok, window_span=None):
        span = Span(spacytok.idx, spacytok.idx + len(spacytok))
        if window_span:
            span = Span(window_span.begin + span.begin, window_span.begin + span.end)
        tok = Token(lemma=spacytok.lemma_, pos=spacytok.tag_, tag=spacytok.pos_)
        tok.span = span
        tok.source = spacytok
        return tok

    @staticmethod
    def convert_entity(entity, window_span=None):
        if window_span:
            entity_span = Span(window_span.begin + entity.start_char,
                               window_span.begin + entity.end_char)
        else:
            entity_span = Span(entity.start_char,
                               entity.end_char)

        entity = Entity(name=None, salience=None, label=entity.label_)
        entity.span = entity_span
        entity.source = entity
        return entity

    @staticmethod
    def convert_noun_chunk(noun_chunk, window_span=None):

        if window_span:
            noun_chunk_span = Span(window_span.begin + noun_chunk.start_char,
                                   window_span.begin + noun_chunk.end_char)
        else:
            noun_chunk_span = Span(noun_chunk.start_char, noun_chunk.end_char)
        noun_chunk = NounChunk(label=noun_chunk.label_)
        noun_chunk.span = noun_chunk_span
        return noun_chunk

    @staticmethod
    def spacy_to_spandex(spacy_doc, spndx=None, annotation_layers=AnnotationLayers.ALL(), window_span=None):

        if not spndx:
            spndx = Spandex(spacy_doc.text_with_ws)

        if annotation_layers & AnnotationLayers.DOCUMENT:
            if window_span:
                doc = Document(begin=window_span.begin, end=window_span.end)
            else:
                doc_span = Span(0, len(spndx.content_string))
                doc = Document(begin=doc_span.begin, end=doc_span.end)

            spndx.add_annotations(Document, doc)

        if annotation_layers & AnnotationLayers.SENTENCE:
            spndx.add_annotations(
                Sentence,
                *[SpacyToSpandexUtils.convert_sentence(s, window_span) for s in spacy_doc.sents])

        # Extract tokens and dependency parse
        spacy_toks = [t for t in spacy_doc]
        if annotation_layers & AnnotationLayers.TOKEN:
            all_toks = [SpacyToSpandexUtils.convert_token(t, window_span) for t in spacy_toks]
            word_toks = [(tok, spacy_tok) for (tok, spacy_tok) in zip(all_toks, spacy_toks) if not spacy_tok.is_space]
            toks = [tok for (tok, spacy_tok) in word_toks]
            spndx.add_annotations(Token, *toks)

            if annotation_layers & AnnotationLayers.DEPPARSE:
                # Pull out dependency graphs
                span_to_nodes = {tok.span: DependencyNode(begin=tok.begin, end=tok.end) for tok in toks}

                depedges = []
                depnodes = []
                depnode_spans = set()
                for (tok, spacy_tok) in word_toks:
                    headtok = all_toks[spacy_tok.head.i]
                    head_node = span_to_nodes[headtok.span]
                    head_ref = AnnotationRef(obj=head_node)
                    child_span = tok.span
                    child_node = span_to_nodes[child_span]
                    child_ref = AnnotationRef(obj=child_node)

                    # get span for full dependency
                    depspan = Span(begin=min(tok.begin, headtok.begin),
                                   end=max(tok.end, headtok.end))
                    # Build edges
                    depedge = DependencyEdge(label=spacy_tok.dep_, head_ref=head_ref, child_ref=child_ref)
                    depedge.span = depspan
                    child_node.head_edge = depedge
                    head_node.add_child_edge(depedge)
                    if headtok.span not in depnode_spans:
                        depnodes.append(head_node)
                        depnode_spans.add(head_node.span)

                    if child_span not in depnode_spans:
                        depnodes.append(child_node)
                        depnode_spans.add(child_span)
                    depedges.append(depedge)
                # push dependency graph onto spandex
                spndx.add_annotations(DependencyEdge, *depedges)
                spndx.add_annotations(DependencyNode, *depnodes)

                dep_parses = []
                for sent in spndx.select(Sentence):
                    dep_parse = DependencyParse(begin=sent.begin, end=sent.end)
                    dep_nodes = [n for n in spndx.select_covered(DependencyNode, dep_parse)]
                    for dep_node in dep_nodes:
                        if not dep_parse.root and dep_node.is_root:
                            # found the root
                            dep_parse.root = dep_node
                    dep_parses.append(dep_parse)

                spndx.add_annotations(DependencyParse, *dep_parses)

        if annotation_layers & AnnotationLayers.ENTITY:
            spndx.add_annotations(Entity, *[SpacyToSpandexUtils.convert_entity(e, window_span) for e in spacy_doc.ents])

        if annotation_layers & AnnotationLayers.NOUN_CHUNK:
            spndx.add_annotations(
                NounChunk, *[SpacyToSpandexUtils.convert_noun_chunk(n, window_span) for n in spacy_doc.noun_chunks])


class SpacyAnalyzer(AnalysisFunction):
    """
    Instances of this class accept a spandex operator at run Spacy on the spandex text
    Spacy analyses are then converted into a common typesystem
    """

    def __init__(self, spacy_pipeline=None, window_type=None):
        """
        @param spacy_pipeline: a spacy model pipeline function which accepts text
                and returns a spacy document.  Default value of None will trigger
                creation and initialization of the Spacy English model.

        Example:
            # initialize pipeline
            spacy_analyzer = SpacyAnalyzer(en_nlp)

            # only populate Document, Sentence and Token layers in Spandex
            layers = AnnotationLayers.DOCUMENT | AnnotationLayers.SENTENCE \
                    | AnnotationLayers.TOKEN
            spacy_analyzer(spndx, annotation_layers=layers)
        """
        if spacy_pipeline:
            self.spacy_pipeline = spacy_pipeline
        else:
            # no pipeline is specified so go ahead and initialize one
            import spacy
            self.spacy_pipeline = spacy.load("en_core_web_sm")

        self.window_type = window_type

    def process(self, spndx, **kwargs):
        """
        Args:
            **kwargs: Keyword Arguments

        Keyword Args:
            annotation_layers (:obj:`AnnotationLayer`): Bitwise mask of AnnotationLayers
                indicating which layers to populate in Spandex.  Default value is
                AnnotationLayers.ALL()

            window_type (str or type): Class Type of object to run processing
                over.  A common use case would be to run on boundaries already
                defined prior to processing.  For example processing a document
                by subsection boundaries  Default of None means to process the
                full contents of the Spandex.
        """
        #window_type = kwargs.get('window_type', None)
        annotation_layers = kwargs.get('annotation_layers', AnnotationLayers.ALL())

        if not self.window_type:
            # process full document
            spacy_doc = self.spacy_pipeline(spndx.content_string)
            SpacyToSpandexUtils.spacy_to_spandex(spacy_doc, spndx, annotation_layers)
        else:
            # process over windows
            for window in spndx.select(self.window_type):
                print(window)
                window_text = spndx.spanned_text(window)
                spacy_doc = self.spacy_pipeline(window_text)
                SpacyToSpandexUtils.spacy_to_spandex(spacy_doc, spndx, annotation_layers, window)

