"""Reusable mixin adding an optional multi-instrument picker to a form dialog.

Several activities (the transforms, and later notes) may record 1..N
non-consumable items as INSTRUMENT inputs alongside their main effect
(§12 rule 7). A dialog opts in by mixing this in, rendering
``instrument_picker_component(ThisState)`` in its form, passing
``self.selected_instrument_ids`` into its service DTO's ``instrument_item_ids``,
and calling ``self.clear_instruments()`` from ``_clear_form_state``.

The picker only ever proposes active non-consumable items (see
``InstrumentSelectState``); the activity layer re-validates that every
INSTRUMENT input is a non-consumable, non-discarded item.
"""

from dataclasses import dataclass

import reflex as rx
from gws_eln.items.item_dto import ItemDTO
from gws_reflex_main.gws_components import InputSearchResultDTO


@dataclass
class InstrumentRow:
    """One selected instrument shown as a chip in the picker."""

    item_id: str = ""
    display: str = ""


def _instrument_display(item: ItemDTO) -> str:
    """Human-readable label for a selected instrument."""
    if item.label:
        return f"{item.code} ({item.label})"
    return item.code


class InstrumentPickerMixin(rx.State, mixin=True):
    """Mixin holding the optional list of INSTRUMENT inputs for a dialog."""

    # Selected instruments (non-consumable items). Empty when none chosen.
    instruments: list[InstrumentRow] = []

    @property
    def selected_instrument_ids(self) -> list[str]:
        """The ids of the selected instruments, for the service DTO."""
        return [row.item_id for row in self.instruments]

    @rx.event
    def add_instrument(self, event_data: dict):
        """Add the picked instrument (ignores duplicates)."""
        result = InputSearchResultDTO.from_json_object(event_data, ItemDTO)
        item = result.object
        if any(row.item_id == item.id for row in self.instruments):
            return
        self.instruments.append(
            InstrumentRow(item_id=item.id, display=_instrument_display(item))
        )

    @rx.event
    def remove_instrument(self, index: int):
        """Remove the instrument at the given index."""
        if 0 <= index < len(self.instruments):
            del self.instruments[index]

    def clear_instruments(self):
        """Reset the picker (call from ``_clear_form_state``)."""
        self.instruments = []
