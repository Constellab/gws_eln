from attr import dataclass
from gws_core import BaseModelDTO

from gws_eln.activities.activity import Activity
from gws_eln.activities.activity_dto import ActivityDTO
from gws_eln.materials.material_batch import MaterialBatch
from gws_eln.materials.material_batch_dto import MaterialBatchDTO


class BatchActivityResponseDTO(BaseModelDTO):
    """Response DTO containing both batch and activity information.

    Returned by controller endpoints that update a batch and create an activity.
    """

    batch: MaterialBatchDTO
    activity: ActivityDTO | None = None


@dataclass
class BatchActivityResult:
    """Result of a batch operation that creates an activity.

    Holds both the updated batch and the created activity,
    so callers can access either without re-querying.
    """

    batch: MaterialBatch
    activity: Activity | None = None

    def to_dto(self) -> BatchActivityResponseDTO:
        return BatchActivityResponseDTO(
            batch=self.batch.to_dto(), activity=self.activity.to_dto() if self.activity else None
        )
