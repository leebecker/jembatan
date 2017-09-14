import re
#from jembatan.spandex import (Span, Spandex)
#from ..spandex.types import (Document, Sentence, Token, PartOfSpeech, NounChunk, DependencyEdge, Entity)
import itertools
import functools

from enum import auto, Flag
from jembatan.core.spandex import (Span, Spandex)
from jembatan.core.af import AnalysisFunction
from jembatan.typesys import (Document, Sentence, Token, PartOfSpeech, NounChunk, DependencyEdge, Entity)

class AnnotationLayers(Flag):
    """Enumerated type useful for turning on/off behavior in Spacy Analyzers
    """
    DOCUMENT=auto()
    SENTENCE=auto()
    TOKEN=auto()
    DEPPARSE=auto()
    ENTITY=auto()
    NOUN_CHUNK=auto()

    @classmethod
    def NONE(cls):
        return functools.reduce(lambda x,y: x|y, [f for f in cls])

    @classmethod
    def ALL(cls):
        return functools.reduce(lambda x,y: x|y, [f for f in cls])

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
            "documentSentiment": { },
            "language": "unk"
        }


#class JsonToSpandex(object):
#
#    def create(self, content, jsondata):
#        spndx = Spandex(content)
#
#        # Extract sentences
#        spndx.add_layer(Sentence, [self.convert_sentence(s) for s in jsondata['sentences']])
#
#        # Extract tokens and dependency parse
#        json_toks = jsondata['tokens']
#        all_toks = [self.convert_token(t) for t in json_toks]
#        toks = [tok for (tok, json_tok) in zip(all_toks, json_toks) if not self.token_is_space(json_tok)]
#        spndx.add_layer(Token, toks)
#        spndx.add_layer_alias("dependency_nodes", Token)
#        
#        depedges = []
#        for ((tok_span, tok), json_tok) in zip(all_toks, json_toks):
#            json_depedge = json_tok.get("dependencyEdge", None)
#            if json_depedge:
#                head_idx = json_depedge['headTokenIndex']
#                headtok_span, headtok = all_toks[head_idx]
#                depspan = Span(begin=min(tok_span.begin, headtok_span.begin), end=max(tok_span.end, headtok_span.end))
#                depedge = DependencyEdge(label=json_depedge['label'], head=(headtok_span, headtok), child=(tok_span, tok))
#                tok.headDependencyEdges.append(depedge)
#                headtok.childDependencyEdges.append(depedge)
#                depedges.append((depspan, depedge))
#        spndx.add_layer(DependencyEdge, depedges)
#
#        # Extract entities
#        entities = list(itertools.chain.from_iterable([self.convert_entity(e) for e in jsondata.get('entities', [])]))
#        spndx.add_layer(Entity, entities)
#
#        return spndx
#
#        
#
#    def convert_sentence(self, jsonsent):
#        begin = jsonsent['text']['beginOffset']
#        end = begin + len(jsonsent['text']['content'])
#        return Span(begin, end), Sentence(sentiment=None)
#        
#    def convert_token(self, jsontok):
#        begin = jsontok['text']['beginOffset']
#        end = begin + len(jsontok['text']['content'])
#        span = Span(begin, end)
#        lemma = jsontok.get('lemma', None)
#        pos = jsontok.get('partOfSpeech', {}).get('pos', None)
#        tag = jsontok.get('partOfSpeech', {}).get('tag', None)
#        postag = PartOfSpeech(pos=pos, tag=tag)
#
#        tok = Token(lemma=lemma, partOfSpeech=postag, headDependencyEdges=[], childDependencyEdges=[])
#        return span, tok
#
#    def token_is_space(self, jsontok):
#        return jsontok.get('partOfSpeech', {}).get('pos', None) == "SP"
#
#    def convert_entity(self, entity):
#        # we don't have coref chain from spacy, but we will convert each mention to its own
#        # entity  Perhaps better to have entity and links to mentions.
#        # To revisit 
#        entities = []
#        entity['type']
#        entity['mentions'][0]
#        for mention in entity['mentions']:
#            begin = mention['beginOffset']
#            end = begin + len(mention['content'])
#            entities.append((Span(begin, end), Entity(name=None, salience=None, type=entity['type'])))
#        return entities
#
#    def convert_noun_chunk(self, noun_chunk):
#        return Span(noun_chunk.start_char, noun_chunk.end_char), NounChunk(type=noun_chunk.label_)

class SpacyToSpandexUtils:

    @staticmethod
    def convert_sentence(spacysent):
        begin = spacysent.start_char
        end = begin + len(spacysent.text)
        return Span(begin, end), Sentence(other=None)

    @staticmethod
    def convert_token(spacytok):
        span = Span(spacytok.idx, spacytok.idx + len(spacytok))  
        postag = PartOfSpeech(pos=spacytok.tag_, tag=spacytok.pos_)
        tok = Token(lemma=spacytok.lemma_, partOfSpeech=postag, headDependencyEdges=[], childDependencyEdges=[])
        return span, tok

    @staticmethod
    def convert_entity(entity):
        return Span(entity.start_char, entity.end_char), Entity(name=None, salience=None, type=entity.label_)

    @staticmethod
    def convert_noun_chunk(noun_chunk):
        return Span(noun_chunk.start_char, noun_chunk.end_char), NounChunk(type=noun_chunk.label_)

    @staticmethod
    def spacy_to_spandex(spacy_doc, spndx=None, annotation_layers=AnnotationLayers.ALL()):

        if not spndx:
            spndx = Spandex(spacy_doc.text_with_ws)

        if annotation_layers & AnnotationLayers.DOCUMENT:
            spndx.add_layer(
                Document, 
                [(Span(0, len(spndx.content)), Document(other={'sentiment': spacy_doc.sentiment}))])

        if annotation_layers & AnnotationLayers.SENTENCE:
            spndx.add_layer(
                Sentence, 
                [SpacyToSpandexUtils.convert_sentence(s) for s in spacy_doc.sents])

        # Extract tokens and dependency parse
        spacy_toks = [t for t in spacy_doc]
        if annotation_layers & AnnotationLayers.TOKEN:
            all_toks = [SpacyToSpandexUtils.convert_token(t) for t in spacy_toks]
            toks = [tok for (tok, spacy_tok) in zip(all_toks, spacy_toks) if not spacy_tok.is_space]
            spndx.add_layer(Token, toks)

            if annotation_layers & AnnotationLayers.DEPPARSE:
                spndx.add_layer_alias("dependency_nodes", Token)
     
                depedges = []
                for ((tok_span, tok), spacy_tok) in zip(all_toks, spacy_toks):
                    if not spacy_tok.is_space:
                        headtok_span, headtok = all_toks[spacy_tok.head.i]
                        depspan = Span(begin=min(tok_span.begin, headtok_span.begin), end=max(tok_span.end, headtok_span.end))
                        depedge = DependencyEdge(label=spacy_tok.dep_, head=(headtok_span, headtok), child=(tok_span, tok))
                        tok.headDependencyEdges.append(depedge)
                        headtok.childDependencyEdges.append(depedge)
                        depedges.append((depspan, depedge))
                spndx.add_layer(DependencyEdge, depedges)

        if annotation_layers & AnnotationLayers.ENTITY:
            spndx.add_layer(Entity, [SpacyToSpandexUtils.convert_entity(e) for e in spacy_doc.ents])

        if annotation_layers & AnnotationLayers.NOUN_CHUNK:
            spndx.add_layer(NounChunk, [SpacyToSpandexUtils.convert_noun_chunk(n) for n in spacy_doc.noun_chunks])



class SpacyAnalyzer(AnalysisFunction):
    """
    Instances of this class accept a spandex operator at run Spacy on the spandex text
    Spacy analyses are then converted into a common typesystem
    """
    

    def __init__(self, spacy_pipeline=None, annotation_layers = AnnotationLayers.ALL()):
        """

        Args:
            spacy_pipeline: a spacy model pipeline function which accepts text 
                and returns a spacy document.  Default value of None will trigger
                creation and initialization of the Spacy English model.
            annotation_layers: Bitwise mask of AnnotationLayers indicating
                which layers to populate in Spandex.  Default value is 
                AnnotationLayers.ALL()

        Example:
            # only populate Document, Sentence and Token layers in Spandex
            layers = AnnotationLayers.DOCUMENT | AnnotationLayers.SENTENCE \
                    | AnnotationLayers.TOKEN
            spacy_analyzer = SpacyAnalyzer(en_nlp, layers)


        """
        if spacy_pipeline:
            self.spacy_pipeline = spacy_pipeline
        else:
            # no pipeline is specified so go ahead and initialize one
            import spacy
            from spacy.en import English 
            self.spacy_pipeline = English()

        self.document_layer=True,
        self.annotation_layers = annotation_layers

    def process(self, spndx):
        spacy_doc = self.spacy_pipeline(spndx.content)
        SpacyToSpandexUtils.spacy_to_spandex(spacy_doc, spndx, self.annotation_layers)
