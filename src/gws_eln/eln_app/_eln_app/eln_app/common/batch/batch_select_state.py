from dataclasses import dataclass

import reflex as rx
from gws_eln.materials.batch_status import BatchStatus
from gws_eln.materials.material_batch import MaterialBatch


@dataclass
class BatchSelectDTO:
    value: str
    label: str


class BatchSelectState(rx.State):
    """State for managing material batch selection and loading batches from database."""

    _batches: list[BatchSelectDTO] = []

    @rx.var
    def batches(self) -> list[BatchSelectDTO]:
        """Load all active batches from the database, sorted by batch number."""
        if not self._batches:
            batch_list = list(
                MaterialBatch.select()
                .where(MaterialBatch.status == BatchStatus.ACTIVE)
                .order_by(MaterialBatch.batch_number)
            )
            self._batches = [
                BatchSelectDTO(
                    value=str(batch.id),
                    label=batch.batch_number,
                )
                for batch in batch_list
            ]

        return self._batches
