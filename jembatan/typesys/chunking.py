from dataclasses import dataclass
from jembatan.typesys import Annotation


@dataclass
class Entity(Annotation):
    name: str = None
    salience: str = None
    label: str = None


@dataclass
class NounChunk(Entity):
    pass
