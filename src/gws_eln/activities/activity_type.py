from enum import Enum


class ActivityType(Enum):
    """
    Enum representing the types of inventory activities.

    - RECEIVE: New batch received from supplier
    - MOVE: Change location of a batch
    - CONSUME: Use consumable material (decrements quantity)
    - USE: Use non-consumable material (reference only, no decrement)
    - DISCARD: Remove batch with reason
    - ALIQUOT: Quantity taken from parent batch to create an aliquot (logged on parent)
    - ALIQUOT_CREATED: Aliquot created from a parent batch (logged on the new aliquot)
    - RELABEL: Change label of a batch
    """

    RECEIVE = "receive"
    MOVE = "move"
    CONSUME = "consume"
    USE = "use"
    DISCARD = "discard"
    ALIQUOT = "aliquot"
    ALIQUOT_CREATED = "aliquot_created"
    RELABEL = "relabel"
