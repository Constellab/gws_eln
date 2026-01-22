from enum import Enum


class BatchStatus(Enum):
    """
    Enum representing the status of a material batch.

    - ACTIVE: Batch is available for use
    - DISCARDED: Batch has been discarded (soft deleted)
    """

    ACTIVE = "active"
    DISCARDED = "discarded"
