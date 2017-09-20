import collections

class HasSourceRef(object):
    """ Simple Trait Class to add a source field via inheritance.
    The source field is intends to be an easy way to communicate
    between services
    """
    source = None



def namedtuple_with_defaults(typename, field_names, default_values=()):
    T = collections.namedtuple(typename, field_names)
    T.__new__.__defaults__ = (None,) * len(T._fields)
    if isinstance(default_values, collections.Mapping):
        prototype = T(**default_values)
    else:
        prototype = T(*default_values)
    T.__new__.__defaults__ = tuple(prototype)
    return T


class Document(namedtuple_with_defaults("Document", [])): 
    """ Top level document type """
    pass

class Block(namedtuple_with_defaults("Block", ["tag"])):
    pass

class Sentence(namedtuple_with_defaults("Sentence", []), HasSourceRef):
    pass

class Token(
        namedtuple_with_defaults("Token", ["lemma", "partOfSpeech", "headDependencyEdges", "childDependencyEdges"]),
        HasSourceRef): 
    def __repr__(self):
        return "<{}:{}>".format(self.__class__.__name__, id(self))

class PartOfSpeech(namedtuple_with_defaults("PartOfSpeech", ["pos", "tag"])): 
    pass

class DependencyEdge(namedtuple_with_defaults("DependencyEdge", ["label", "head", "child"])): 
    pass

class Entity(
        namedtuple_with_defaults("Entity", ["name", "salience", "type"]),
        HasSourceRef
        ): 
    pass

class NounChunk(namedtuple_with_defaults("Entity", ["type"]), HasSourceRef): 
    pass
