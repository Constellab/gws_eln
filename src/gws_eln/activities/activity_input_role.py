from enum import Enum


class ActivityInputRole(Enum):
    """
    Role of an item consumed/referenced by an activity.

    - INGREDIENT: contributes mass/volume to the activity; part of lineage
    - INSTRUMENT: equipment reference only; excluded from lineage
    """

    INGREDIENT = "ingredient"
    INSTRUMENT = "instrument"
