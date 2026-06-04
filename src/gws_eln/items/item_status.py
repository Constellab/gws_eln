from enum import Enum


class ItemStatus(Enum):
    """
    Enum representing the status of an item.

    - ACTIVE: Item is available for use
    - DISCARDED: Item has been discarded (soft deleted)
    """

    ACTIVE = "active"
    DISCARDED = "discarded"
