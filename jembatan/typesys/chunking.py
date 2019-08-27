from dataclasses import dataclass
from jembatan.typesys import SpannedAnnotation


@dataclass
class Entity(SpannedAnnotation):
    name: str = None
    salience: str = None
    label: str = None


@dataclass
class NounChunk(Entity):
    pass
