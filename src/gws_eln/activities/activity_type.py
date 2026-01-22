from enum import Enum


class ActivityType(Enum):
    """
    Enum representing the types of inventory activities.

    - RECEIVE: New batch received from supplier
    - MOVE: Change location of a batch
    - CONSUME: Use consumable material (decrements quantity)
    - USE: Use non-consumable material (reference only, no decrement)
    - DISCARD: Remove batch with reason
    - ALIQUOT: Create child batch from parent
    - RELABEL: Change label of a batch
    """

    RECEIVE = "receive"
    MOVE = "move"
    CONSUME = "consume"
    USE = "use"
    DISCARD = "discard"
    ALIQUOT = "aliquot"
    RELABEL = "relabel"
