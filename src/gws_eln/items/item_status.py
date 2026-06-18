from enum import Enum


class ItemStatus(Enum):
    """
    Enum representing the status of an item.

    - ACTIVE: Item is available for use (quantity > 0)
    - EXHAUSTED: Consumable item fully used up (quantity == 0)
    - DISCARDED: Item has been discarded (soft deleted) - terminal, user-set
    """

    ACTIVE = "active"
    EXHAUSTED = "exhausted"
    DISCARDED = "discarded"
