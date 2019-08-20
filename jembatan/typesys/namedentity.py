from dataclasses import dataclass
from jembatan.typesys import Annotation


@dataclass
class NamedEntity(Annotation):
    """
    Named entities refer e.g. to persons, locations, organizations and so on. They often consist of multiple tokens.


    Fields:
    value: The class/category of the named entity, e.g. person, location, etc.
    identifier: Identifier of the named entity, e.g. a reference into a person database.
    """

    value: str = None
    identifier: str = None
