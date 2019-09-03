from dataclasses import dataclass
from jembatan.typesys import SpannedAnnotation


class Entity(SpannedAnnotation):
    name: str = None
    salience: str = None
    label: str = None


class NounChunk(Entity):
    pass
