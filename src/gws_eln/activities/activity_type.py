from enum import Enum


class ActivityType(Enum):
    """
    Enum representing the types of inventory activities.

    - CREATE: Create a new item corresponding to an item sheet
    - RECEIVE: New item received from supplier
    - MOVE: Change location of an item
    - CONSUME: Use consumable item (decrements quantity)
    - USE: Use non-consumable item (reference only, no decrement)
    - DISCARD: Remove item
    - ALIQUOT: Quantity taken from parent item to create an aliquot (logged on parent)
    - ALIQUOT_CREATED: Aliquot created from a parent item (logged on the new aliquot)
    - RELABEL: Change label of an item
    """

    CREATE = "create"
    RECEIVE = "receive"
    MOVE = "move"
    CONSUME = "consume"
    USE = "use"
    DISCARD = "discard"
    ALIQUOT = "aliquot"
    ALIQUOT_CREATED = "aliquot_created"
    RELABEL = "relabel"
