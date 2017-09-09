import collections
def namedtuple_with_defaults(typename, field_names, default_values=()):
    T = collections.namedtuple(typename, field_names)
    T.__new__.__defaults__ = (None,) * len(T._fields)
    if isinstance(default_values, collections.Mapping):
        prototype = T(**default_values)
    else:
        prototype = T(*default_values)
    T.__new__.__defaults__ = tuple(prototype)
    return T


class Document(namedtuple_with_defaults("Document", ["other"])): 
    """ Top level document type """
    pass

class Block(namedtuple_with_defaults("Block", ["tag", "other"])):
    pass

class Sentence(namedtuple_with_defaults("Sentence", ["other"])): 
    pass

class Token(namedtuple_with_defaults("Token", ["lemma", "partOfSpeech", "headDependencyEdges", "childDependencyEdges", "other"])): 
    def __repr__(self):
        return "<{}:{}>".format(self.__class__.__name__, id(self))

class PartOfSpeech(namedtuple_with_defaults("PartOfSpeech", ["pos", "tag", "other"])): 
    pass

class DependencyEdge(namedtuple_with_defaults("DependencyEdge", ["label", "head", "child", "other"])): 
    pass

class Entity(namedtuple_with_defaults("Entity", ["name", "salience", "type", "other"])): 
    pass

class NounChunk(namedtuple_with_defaults("Entity", ["type", "other"])): 
    pass
