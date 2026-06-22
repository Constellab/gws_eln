from enum import Enum


class ActivityType(Enum):
    """
    Enum representing the types of inventory activities.

    - RECEIVE: New item received from supplier
    - CONSUME: Use consumable item (decrements quantity)
    - USE: Use non-consumable item (reference only, no decrement)
    - MOVE: Change location of an item
    - RELABEL: Change label of an item
    - DISCARD: Remove item
    - SPLIT: Split an item into multiple items
    - COMBINE: Combine multiple items into one
    - DILUTE: Dilute an item (change quantity and concentration)
    - CONCENTRATE: Concentrate an item (change quantity and concentration)
    - TRANSFORM: Generic transformation consuming N inputs into M new outputs
    """

    RECEIVE = "receive"
    CONSUME = "consume"
    USE = "use"
    MOVE = "move"
    RELABEL = "relabel"
    DISCARD = "discard"
    SPLIT = "split"
    COMBINE = "combine"
    DILUTE = "dilute"
    CONCENTRATE = "concentrate"
    TRANSFORM = "transform"
