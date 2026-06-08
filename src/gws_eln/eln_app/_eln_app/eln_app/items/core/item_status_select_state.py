from dataclasses import dataclass

import reflex as rx
from gws_eln.items.item_status import ItemStatus


@dataclass
class ItemStatusSelectDTO:
    value: str
    label: str


class ItemStatusSelectState(rx.State):
    """State for managing item status selection."""

    @rx.var
    def statuses(self) -> list[ItemStatusSelectDTO]:
        """Get all item statuses for the select dropdown."""
        return [
            ItemStatusSelectDTO(value=ItemStatus.ACTIVE.value, label="Active"),
            ItemStatusSelectDTO(value=ItemStatus.DISCARDED.value, label="Discarded"),
        ]
