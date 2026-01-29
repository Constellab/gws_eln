from dataclasses import dataclass

import reflex as rx
from gws_eln.materials.batch_status import BatchStatus


@dataclass
class BatchStatusSelectDTO:
    value: str
    label: str


class BatchStatusSelectState(rx.State):
    """State for managing batch status selection."""

    @rx.var
    def statuses(self) -> list[BatchStatusSelectDTO]:
        """Get all batch statuses for the select dropdown."""
        return [
            BatchStatusSelectDTO(value=BatchStatus.ACTIVE.value, label="Active"),
            BatchStatusSelectDTO(value=BatchStatus.DISCARDED.value, label="Discarded"),
        ]
