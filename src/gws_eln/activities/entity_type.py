from enum import Enum


class EntityType(Enum):
    """
    Enum representing the types of entities that can have activities.

    For MVP, only material_batch is supported.
    """

    METARIAL_BATCH = "metarial_batch"
