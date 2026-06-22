"""State management for the generic Transform dialog (N inputs -> M outputs).

Inputs (existing item/instrument + quantity) are built in place. Outputs delegate
to the existing dialogs: the ItemSheet creation dialog for a new sheet, and the
item creation dialog in *collect mode* (it returns a CreateItemDTO instead of
persisting) so the Transform itself creates the output items on save.
"""

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import reflex as rx
from gws_eln.core.unit_type import UnitType
from gws_eln.items.item_dto import (
    CreateItemDTO,
    ItemDTO,
    TransformInputDTO,
    TransformItemsDTO,
    TransformOutputDTO,
)
from gws_eln.items.item_service import ItemService
from gws_eln.items.item_sheet_dto import ItemSheetDTO
from gws_eln.locations.location_service import LocationService
from gws_eln.utils.units_converter import UnitConverter
from gws_reflex_main import FormDialogState, ReflexMainState
from gws_reflex_main.gws_components import InputSearchResultDTO

from ...item_sheets.item_sheet_form_dialog.item_sheet_form_dialog_state import (
    ItemSheetFormDialogState,
)
from ...notes.note_linkable_dialog_state import NoteLinkableDialogState
from ..item_form_dialog.item_form_dialog_state import ItemFormDialogState

FormDialogCloseCallback = Callable[[ItemDTO], Coroutine[Any, Any, None]]


@dataclass
class TransformInputRow:
    """One committed input (item or instrument) consumed by the transform."""

    id: str
    item_id: str
    code: str
    label: str
    loc: str
    is_consumable: bool
    qty: str  # raw, for DTO (empty for instruments)
    unit: str  # raw, for DTO
    consumed: str  # display, e.g. "4 units" or "instrument"


@dataclass
class TransformOutputRow:
    """One committed output (new item) produced by the transform."""

    id: str
    sheet_id: str
    sheet_code: str
    sheet_name: str
    label: str
    loc: str
    qty: str  # raw, for DTO
    unit: str  # raw, for DTO
    location_id: str  # raw, for DTO
    conc: str  # raw, for DTO
    conc_unit: str  # raw, for DTO ("" when none)
    code_preview: str
    produced: str  # display


class TransformItemFormDialogState(NoteLinkableDialogState, FormDialogState, rx.State):
    """State for the generic Transform dialog (N inputs -> M outputs)."""

    # Committed rows
    inputs: list[TransformInputRow] = []
    outputs: list[TransformOutputRow] = []

    # ---- input draft ----
    show_input_draft: bool = False
    in_item_id: str = ""
    in_item_code: str = ""
    in_item_label: str = ""
    in_item_consumable: bool = True
    in_unit_type: str = UnitType.COUNT.value
    in_qty: str = ""
    in_unit: str = UnitConverter.get_default_unit(UnitType.COUNT)

    # ---- output draft (sheet selection only; item fields live in the item dialog) ----
    show_output_draft: bool = False
    out_sheet_id: str = ""
    out_sheet_code: str = ""
    out_sheet_name: str = ""

    # id (str) -> name, to display the location on committed output rows
    _loc_names: dict[str, str] = {}

    _callback_after_close: FormDialogCloseCallback | None = None

    # ------------------------------------------------------------------ vars

    @rx.var
    def input_count(self) -> int:
        return len(self.inputs)

    @rx.var
    def output_count(self) -> int:
        return len(self.outputs)

    @rx.var
    def inputs_empty_hint(self) -> bool:
        return len(self.inputs) == 0 and not self.show_input_draft

    @rx.var
    def outputs_empty_hint(self) -> bool:
        return len(self.outputs) == 0 and not self.show_output_draft

    @rx.var
    def create_input_visible(self) -> bool:
        return not self.show_input_draft

    @rx.var
    def create_output_visible(self) -> bool:
        return not self.show_output_draft

    @rx.var
    def input_has_sel(self) -> bool:
        return bool(self.in_item_id)

    @rx.var
    def input_is_instrument(self) -> bool:
        return bool(self.in_item_id) and not self.in_item_consumable

    @rx.var
    def has_output_sheet(self) -> bool:
        return bool(self.out_sheet_id)

    @rx.var
    def has_any(self) -> bool:
        return len(self.inputs) > 0 or len(self.outputs) > 0

    @rx.var
    def summary_str(self) -> str:
        return f"{len(self.inputs)} input(s) · {len(self.outputs)} output(s)"

    # ------------------------------------------------------------------ open

    async def _load_locations(self):
        """Load locations (id -> name) for displaying committed output rows."""
        main_state = await self.get_state(ReflexMainState)
        with await main_state.authenticate_user():
            self._loc_names = {loc.id: loc.name for loc in LocationService().list_locations()}

    @rx.event
    async def open_transform_dialog(self, item: ItemDTO):
        """Open the dialog. Inputs and outputs start empty (built in place).

        :param item: The item the transform was launched from (context only)
        :type item: ItemDTO
        """
        self._reset_state()
        await self._load_locations()
        self.is_update_mode = False
        self.dialog_opened = True

    # ------------------------------------------------------------------ inputs

    @rx.event
    def start_input(self):
        """Open the draft card to add an input."""
        self.show_input_draft = True
        self.in_item_id = ""
        self.in_item_code = ""
        self.in_item_label = ""
        self.in_item_consumable = True
        self.in_unit_type = UnitType.COUNT.value
        self.in_qty = ""
        self.in_unit = UnitConverter.get_default_unit(UnitType.COUNT)

    @rx.event
    def select_input_item(self, event_data: dict):
        """Set the selected input item from the search component."""
        result = InputSearchResultDTO.from_json_object(event_data, ItemDTO)
        item = result.object
        self.in_item_id = item.id
        self.in_item_code = item.code
        self.in_item_label = item.label or "(sans label)"
        self.in_item_consumable = item.item_sheet.is_consumable
        self.in_unit_type = item.unit_type.value
        self.in_unit = UnitConverter.get_default_unit(item.unit_type)

    @rx.event
    def set_input_qty(self, value: str):
        self.in_qty = value

    @rx.event
    def set_input_unit(self, value: str):
        self.in_unit = value

    @rx.event
    def cancel_input(self):
        self.show_input_draft = False

    @rx.event
    def commit_input(self):
        """Validate the draft and append it to the inputs list."""
        if not self.in_item_id:
            return
        if self.in_item_consumable and not self.in_qty.strip():
            return
        consumed = (
            "instrument"
            if not self.in_item_consumable
            else f"{self.in_qty.strip()} {self.in_unit}"
        )
        self.inputs = self.inputs + [
            TransformInputRow(
                id=f"in{len(self.inputs)}_{self.in_item_id}",
                item_id=self.in_item_id,
                code=self.in_item_code,
                label=self.in_item_label,
                loc="",
                is_consumable=self.in_item_consumable,
                qty=self.in_qty.strip(),
                unit=self.in_unit,
                consumed=consumed,
            )
        ]
        self.show_input_draft = False

    @rx.event
    def remove_input(self, index: int):
        if 0 <= index < len(self.inputs):
            del self.inputs[index]

    # ------------------------------------------------------------------ outputs

    @rx.event
    def start_output(self):
        """Open the output draft (sheet selection)."""
        self.show_output_draft = True
        self.out_sheet_id = ""
        self.out_sheet_code = ""
        self.out_sheet_name = ""

    @rx.event
    def cancel_output(self):
        self.show_output_draft = False

    @rx.event
    def select_output_sheet(self, event_data: dict):
        """Set the output sheet from the item-sheet search component."""
        result = InputSearchResultDTO.from_json_object(event_data, ItemSheetDTO)
        sheet = result.object
        self.out_sheet_id = sheet.id
        self.out_sheet_code = sheet.code
        self.out_sheet_name = sheet.name

    @rx.event
    async def open_create_sheet_dialog(self):
        """Open the existing ItemSheet creation dialog; its result is selected."""
        dialog_state = await self.get_state(ItemSheetFormDialogState)
        dialog_state.set_callback_after_close(self._on_sheet_created)
        await dialog_state.open_create_dialog()

    async def _on_sheet_created(self, sheet: ItemSheetDTO):
        """Callback after a new ItemSheet is created: select it for the output."""
        self.out_sheet_id = sheet.id
        self.out_sheet_code = sheet.code
        self.out_sheet_name = sheet.name

    @rx.event
    async def open_output_item_dialog(self):
        """Open the item creation dialog in collect mode for the chosen sheet."""
        if not self.out_sheet_id:
            return
        dialog_state = await self.get_state(ItemFormDialogState)
        await dialog_state.open_create_dialog(self.out_sheet_id)
        dialog_state.set_collect_callback(self._on_output_item_collected)

    async def _on_output_item_collected(self, dto: CreateItemDTO):
        """Callback from the item dialog (collect mode): add the output row."""
        loc_name = self._loc_names.get(dto.location_id, "—") if dto.location_id else "—"
        self.outputs = self.outputs + [
            TransformOutputRow(
                id=f"out{len(self.outputs)}_{self.out_sheet_code}",
                sheet_id=dto.item_sheet_id,
                sheet_code=self.out_sheet_code,
                sheet_name=self.out_sheet_name,
                label=dto.label or "(sans label)",
                loc=loc_name,
                qty=str(dto.quantity),
                unit=dto.unit,
                location_id=dto.location_id or "",
                conc=str(dto.concentration) if dto.concentration is not None else "",
                conc_unit=dto.concentration_unit or "",
                code_preview=f"{self.out_sheet_code}-XXXX",
                produced=f"{dto.quantity} {dto.unit}",
            )
        ]
        self.show_output_draft = False

    @rx.event
    def remove_output(self, index: int):
        if 0 <= index < len(self.outputs):
            del self.outputs[index]

    # ------------------------------------------------------------------ global

    @rx.event
    def clear_all(self):
        self.inputs = []
        self.outputs = []
        self.show_input_draft = False
        self.show_output_draft = False

    async def _create(self, form_data: dict):
        """Build the TransformItemsDTO and call the service."""
        if not self.inputs or not self.outputs:
            return

        input_dtos = [
            TransformInputDTO(
                item_id=row.item_id,
                quantity=Decimal(row.qty) if (row.is_consumable and row.qty) else None,
                unit=row.unit if row.is_consumable else None,
            )
            for row in self.inputs
        ]
        output_dtos = [
            TransformOutputDTO(
                output_item_sheet_id=row.sheet_id,
                quantity=Decimal(row.qty),
                unit=row.unit,
                location_id=row.location_id or None,
                label=row.label if row.label != "(sans label)" else None,
                concentration=Decimal(row.conc) if row.conc else None,
                concentration_unit=row.conc_unit or None,
            )
            for row in self.outputs
        ]
        notes = form_data.get("notes", "").strip() or None
        dto = TransformItemsDTO(
            inputs=input_dtos, outputs=output_dtos, notes=notes, note_id=self.note_dto_id
        )

        main_state: ReflexMainState
        async with self:
            main_state = await self.get_state(ReflexMainState)

        with await main_state.authenticate_user():
            result = ItemService().transform_items(dto)
            linked_note = self._link_note_activity(result.activity.id)

        yield rx.toast.success(
            f"Transform enregistré — {len(input_dtos)} input(s) → {len(output_dtos)} output(s)"
        )
        await self._after_note_link(linked_note)

        if self._callback_after_close and result.inputs:
            await self._callback_after_close(result.inputs[0].to_dto())

    async def _update(self, form_data: dict):
        """Not implemented - this dialog only creates transforms."""
        raise NotImplementedError("Update is not supported by this dialog")

    def _reset_state(self):
        self.inputs = []
        self.outputs = []
        self.show_input_draft = False
        self.show_output_draft = False
        self.out_sheet_id = ""
        self.out_sheet_code = ""
        self.out_sheet_name = ""

    async def _clear_form_state(self):
        self._reset_state()
        self.clear_note_context()
        self.is_update_mode = False

    def set_callback_after_close(self, callback: FormDialogCloseCallback | None):
        """Set the callback invoked after a successful transform (e.g. to refresh)."""
        self._callback_after_close = callback
