"""State management for the note activity form dialog.

This dialog allows adding a item activity from within a note.
The user selects a item, an activity type, and fills in the
type-specific sub-form before submitting.
"""

from collections.abc import Callable, Coroutine
from decimal import Decimal
from typing import Any

import reflex as rx
from gws_core import Note, RichTextDTO
from gws_eln.activities.activity_type import ActivityType
from gws_eln.core.unit_type import UnitType
from gws_eln.items.item_sheet import ItemSheet
from gws_eln.items.item_dto import ItemDTO
from gws_eln.items.item_sheet_dto import ItemSheetDTO
from gws_eln.notes.eln_note_dto import AddNoteActivityDTO
from gws_eln.notes.eln_note_service import ElnNoteService
from gws_eln.utils.units_converter import UnitConverter
from gws_reflex_main import FormDialogState, ReflexMainState
from gws_reflex_main.gws_components import InputSearchResultDTO

NoteActivityCallback = Callable[[Note], Coroutine[Any, Any, None]]


class NoteActivityFormDialogState(FormDialogState, rx.State):
    """State for the note activity form dialog.

    Two-step form:
    1. Select a item and an activity type
    2. Fill in the activity-specific sub-form
    """

    # Note context (set when opening the dialog)
    _note_id: str = ""
    _note_block_id: str = ""
    _rich_text_content: RichTextDTO | None = None

    # Step 1: item and activity type selection
    form_item: InputSearchResultDTO | None = None
    form_activity_type: str = ""

    # For CREATE activity: select item_sheet instead of item
    form_item_sheet: InputSearchResultDTO | None = None
    _item_sheet: ItemSheetDTO | None = None

    # Resolved item (loaded after selection)
    _item: ItemDTO | None = None

    # Sub-form fields for receive/consume
    form_unit_type: str = UnitType.COUNT.value
    form_unit: str = UnitConverter.get_default_unit(UnitType.COUNT)
    form_notes: str = ""

    # Sub-form fields for move
    form_location_id: str = ""

    # Sub-form fields for relabel
    form_item_number: str = ""
    form_label: str = ""

    # Sub-form fields for aliquot
    form_source_unit: str = UnitConverter.get_default_unit(UnitType.COUNT)
    form_aliquot_unit_type: str = UnitType.COUNT.value  # Target item_sheet unit type (for aliquot)
    form_aliquot_unit: str = UnitConverter.get_default_unit(UnitType.COUNT)
    form_target_item_sheet: InputSearchResultDTO | None = (
        None  # Required target item_sheet for the aliquot
    )
    form_supplier_id: str = ""

    _callback_after_close: NoteActivityCallback | None = None

    # --- Computed properties ---
    @rx.var
    def item(self) -> ItemDTO | None:
        """Get the parent item for display."""
        if self._item:
            return self._item
        return None

    @rx.var
    def current_quantity(self) -> str:
        """Current quantity of selected item for display."""
        if self._item:
            return self._item.pretty_quantity
        return ""

    @rx.var
    def current_location_name(self) -> str:
        """Current location of selected item for display."""
        if self._item and self._item.location:
            return self._item.location.name
        return ""

    @rx.var
    def show_create_form(self) -> bool:
        """Whether to show the create item sub-form (requires item_sheet to be selected)."""
        return self.form_activity_type == ActivityType.CREATE.value

    @rx.var
    def show_item_select(self) -> bool:
        """Whether to show the item/item_sheet selection field.

        For CREATE activity: show item_sheet selection
        For other activities: show item selection
        """

        return bool(self.form_activity_type) and self.form_activity_type not in [
            ActivityType.CREATE.value,
            ActivityType.ALIQUOT.value,
        ]

    @rx.var
    def show_receive_consume_form(self) -> bool:
        """Whether to show the receive/consume sub-form."""
        return self.form_activity_type in (
            ActivityType.RECEIVE.value,
            ActivityType.CONSUME.value,
        )

    @rx.var
    def show_move_form(self) -> bool:
        """Whether to show the move sub-form."""
        return self.form_activity_type == ActivityType.MOVE.value

    @rx.var
    def show_use_discard_form(self) -> bool:
        """Whether to show the use/discard sub-form (notes only)."""
        return self.form_activity_type in (
            ActivityType.USE.value,
            ActivityType.DISCARD.value,
        )

    @rx.var
    def show_relabel_form(self) -> bool:
        """Whether to show the relabel sub-form."""
        return self.form_activity_type == ActivityType.RELABEL.value

    @rx.var
    def show_aliquot_form(self) -> bool:
        """Whether to show the aliquot sub-form."""
        return self.form_activity_type == ActivityType.ALIQUOT.value

    @rx.var
    def quantity_label(self) -> str:
        """Label for the quantity field based on activity type."""
        if self.form_activity_type == ActivityType.RECEIVE.value:
            return "Quantity to Receive"
        if self.form_activity_type == ActivityType.CONSUME.value:
            return "Quantity to Consume"
        return "Quantity"

    # --- Event handlers ---

    def open_dialog(
        self, note_id: str, note_block_id: str, rich_text_content: RichTextDTO | None = None
    ):
        """Open the dialog for a specific note and block.

        Args:
            note_id: The note ID
            note_block_id: The note block ID
            rich_text_content: The current rich text content of the note
        """
        self._note_id = note_id
        self._note_block_id = note_block_id
        self._rich_text_content = rich_text_content
        self._item = None
        self.form_item = None
        self.form_activity_type = ""
        self._reset_sub_form_fields()
        self.is_update_mode = False
        self.dialog_opened = True

    @rx.event
    async def set_item(self, value: dict):
        """Handle item selection change. Load item details for the sub-form."""
        if not value:
            self.form_item = None
            self._item = None
            return
        self.form_item = InputSearchResultDTO.from_json_object(value, ItemDTO)
        self._item = self.form_item.object
        main_state: ReflexMainState
        async with self:
            main_state = await self.get_state(ReflexMainState)
        with await main_state.authenticate_user():
            self.form_unit_type = self._item.unit_type.value
            best_unit = self._get_best_unit_for_quantity(
                self._item.quantity, self._item.unit_type
            )
            self.form_unit = best_unit
            self.form_source_unit = best_unit
            # Initialize target item_sheet and aliquot unit type from item's item_sheet
            self.form_target_item_sheet = InputSearchResultDTO(
                id=self._item.item_sheet.id,
                display_text=self._item.item_sheet.name,
                object=self._item.item_sheet,
            )
            self.form_aliquot_unit_type = self._item.unit_type.value
            self.form_aliquot_unit = best_unit
            if self._item.location:
                self.form_location_id = self._item.location.id
            self.form_item_number = self._item.item_number
            self.form_label = self._item.label or ""

    @rx.event
    def set_activity_type(self, value: str):
        """Handle activity type selection change."""
        self.form_activity_type = value
        self._reset_sub_form_fields()
        # Reset item/item_sheet selection when activity type changes
        if value == ActivityType.CREATE.value:
            self.form_item = None
            self._item = None
        else:
            self.form_item_sheet = None
            self._item_sheet = None

    @rx.event
    async def set_item_sheet(self, value: dict):
        """Handle item_sheet selection change for CREATE activity."""
        if not value:
            self.form_item_sheet = None
            self._item_sheet = None
            return
        self.form_item_sheet = InputSearchResultDTO.from_json_object(value, ItemSheetDTO)
        self._item_sheet = self.form_item_sheet.object
        main_state: ReflexMainState
        async with self:
            main_state = await self.get_state(ReflexMainState)
        with await main_state.authenticate_user():
            item_sheet = ItemSheet.get_by_id_and_check(self.form_item_sheet.id)
            self.form_unit_type = item_sheet.default_unit_type.value
            self.form_unit = UnitConverter.get_default_unit(item_sheet.default_unit_type)

    @rx.event
    def set_unit(self, value: str):
        """Handle unit selection change for receive/consume."""
        self.form_unit = value

    @rx.event
    def set_location_id(self, value: str):
        """Handle location selection change for move."""
        self.form_location_id = value

    @rx.event
    def set_source_unit(self, value: str):
        """Handle source unit selection change for aliquot."""
        self.form_source_unit = value

    @rx.event
    def set_aliquot_unit(self, value: str):
        """Handle aliquot unit selection change for aliquot."""
        self.form_aliquot_unit = value

    @rx.event
    def set_supplier_id(self, value: str):
        """Handle supplier selection change for aliquot."""
        self.form_supplier_id = value

    @rx.event
    def set_target_item_sheet(self, value: dict):
        """Handle target item_sheet selection change for aliquot.

        Updates the aliquot unit type based on the selected item_sheet's default_unit_type.
        """
        if not value:
            self.form_target_item_sheet = None
            return
        self.form_target_item_sheet = InputSearchResultDTO.from_json_object(value, ItemSheetDTO)
        item_sheet: ItemSheetDTO = self.form_target_item_sheet.object
        if item_sheet:
            self.form_aliquot_unit_type = item_sheet.default_unit_type.value
            self.form_aliquot_unit = UnitConverter.get_default_unit(item_sheet.default_unit_type)

    # --- Form submission ---

    async def _create(self, form_data: dict):
        """Submit the activity via ElnNoteService.add_activity().

        Builds the activity_data dict from form_data + state fields,
        then calls the service.
        """
        if not self.form_activity_type:
            raise Exception("Please select an activity type")

        # For CREATE activity, require item_sheet; for others, require item
        if self.form_activity_type == ActivityType.CREATE.value:
            if not self.form_item_sheet:
                raise Exception("Please select a item_sheet")
        elif not self.form_item:
            raise Exception("Please select a item")

        activity_data = self._build_activity_data(form_data)

        main_state: ReflexMainState
        async with self:
            main_state = await self.get_state(ReflexMainState)

        with await main_state.authenticate_user():
            service = ElnNoteService()
            dto = AddNoteActivityDTO(
                note_id=self._note_id,
                note_block_id=self._note_block_id,
                item_id=self.form_item.id if self.form_item else None,
                activity_type=ActivityType(self.form_activity_type),
                activity_data=activity_data,
                rich_text_content=self._rich_text_content,
            )
            result = service.add_activity(dto)

        yield rx.toast.success("Activity added successfully")

        if self._callback_after_close:
            await self._callback_after_close(result)

    async def _update(self, form_data: dict):
        """Not implemented - this dialog only creates activities."""
        raise NotImplementedError("Update is not supported by this dialog")

    async def _clear_form_state(self):
        """Clear all form state after successful operation."""
        self._note_id = ""
        self._note_block_id = ""
        self._rich_text_content = None
        self._item = None
        self._item_sheet = None
        self.form_item = None
        self.form_item_sheet = None
        self.form_activity_type = ""
        self._reset_sub_form_fields()

    def set_callback_after_close(self, callback: NoteActivityCallback | None):
        """Set the callback to invoke after the dialog closes successfully."""
        self._callback_after_close = callback

    # --- Private helpers ---

    def _reset_sub_form_fields(self):
        """Reset all sub-form fields to defaults."""
        self.form_notes = ""
        self.form_location_id = ""
        self.form_item_number = ""
        self.form_label = ""
        self.form_target_item_sheet = None
        self.form_aliquot_unit_type = UnitType.COUNT.value
        self.form_supplier_id = ""

    def _get_best_unit_for_quantity(self, quantity: Decimal, unit_type: UnitType) -> str:
        """Select a readable unit for the given quantity."""
        if quantity == 0:
            return UnitConverter.get_default_unit(unit_type)

        unit_order = UnitConverter.UNIT_ORDER.get(unit_type, ["units"])
        for unit in unit_order:
            converted = UnitConverter.from_base_unit(quantity, unit, unit_type)
            abs_converted = abs(converted)
            if Decimal("1") <= abs_converted < Decimal("1000"):
                return unit

        return UnitConverter.get_default_unit(unit_type)

    def _build_activity_data(self, form_data: dict) -> dict[str, Any]:
        """Build the activity_data dict based on the selected activity type."""
        activity_type = self.form_activity_type
        data: dict[str, Any] = {}

        if activity_type == ActivityType.CREATE.value:
            data = self._build_create_data(form_data)

        elif activity_type in (ActivityType.RECEIVE.value, ActivityType.CONSUME.value):
            quantity_str = form_data.get("quantity", "").strip()
            if not quantity_str:
                raise Exception("Quantity is required")
            try:
                quantity = Decimal(quantity_str)
                if quantity <= 0:
                    raise Exception("Quantity must be positive")
            except (ValueError, ArithmeticError):
                raise Exception("Invalid quantity value")
            if not self.form_unit:
                raise Exception("Unit is required")
            data["quantity"] = quantity
            data["unit"] = self.form_unit
            data["notes"] = form_data.get("notes", "").strip() or None

        elif activity_type == ActivityType.MOVE.value:
            if not self.form_location_id:
                raise Exception("Destination location is required")
            data["to_location_id"] = self.form_location_id

        elif activity_type in (ActivityType.USE.value, ActivityType.DISCARD.value):
            data["notes"] = form_data.get("notes", "").strip() or None

        elif activity_type == ActivityType.RELABEL.value:
            item_number = form_data.get("item_number", "").strip()
            label = form_data.get("label", "").strip()
            if not item_number:
                raise Exception("Item number is required")
            data["item_number"] = item_number
            data["label"] = label or None

        elif activity_type == ActivityType.ALIQUOT.value:
            data = self._build_aliquot_data(form_data)

        return data

    def _build_create_data(self, form_data: dict) -> dict[str, Any]:
        """Build activity_data for item creation."""
        if not self.form_item_sheet:
            raise Exception("ItemSheet is required")

        item_number = form_data.get("item_number", "").strip()
        if not item_number:
            raise Exception("Item number is required")

        quantity_str = form_data.get("quantity", "").strip()
        if not quantity_str:
            raise Exception("Quantity is required")

        try:
            quantity = Decimal(quantity_str)
            if quantity <= 0:
                raise Exception("Quantity must be positive")
        except (ValueError, ArithmeticError):
            raise Exception("Invalid quantity value")

        if not self.form_unit:
            raise Exception("Unit is required")

        return {
            "item_sheet_id": self.form_item_sheet.id,
            "item_number": item_number,
            "quantity": quantity,
            "unit": self.form_unit,
            "location_id": self.form_location_id or None,
            "supplier_id": self.form_supplier_id or None,
            "label": form_data.get("label", "").strip() or None,
            "notes": form_data.get("notes", "").strip() or None,
        }

    def _build_aliquot_data(self, form_data: dict) -> dict[str, Any]:
        """Build activity_data for aliquot creation."""
        source_qty_str = form_data.get("source_quantity", "").strip()
        aliquot_qty_str = form_data.get("aliquot_quantity", "").strip()

        if not self.form_target_item_sheet:
            raise Exception("Target item_sheet is required")
        if not source_qty_str:
            raise Exception("Source quantity is required")
        if not aliquot_qty_str:
            raise Exception("Aliquot quantity is required")

        try:
            source_quantity = Decimal(source_qty_str)
            if source_quantity <= 0:
                raise Exception("Source quantity must be positive")
        except (ValueError, ArithmeticError):
            raise Exception("Invalid source quantity value")

        try:
            aliquot_quantity = Decimal(aliquot_qty_str)
            if aliquot_quantity <= 0:
                raise Exception("Aliquot quantity must be positive")
        except (ValueError, ArithmeticError):
            raise Exception("Invalid aliquot quantity value")

        supplier_id = self.form_supplier_id if self.form_supplier_id else None
        if supplier_id == "__none__":
            supplier_id = None

        return {
            "parent_item_id": self.form_item.id if self.form_item else None,
            "target_item_sheet_id": self.form_target_item_sheet.id,
            "source_quantity": source_quantity,
            "source_unit": self.form_source_unit,
            "aliquot_quantity": aliquot_quantity,
            "aliquot_unit": self.form_aliquot_unit,
            "aliquot_item_number": form_data.get("aliquot_item_number", "").strip() or None,
            "label": form_data.get("label", "").strip() or None,
            "location_id": self.form_location_id or None,
            "supplier_id": supplier_id,
            "notes": form_data.get("notes", "").strip() or None,
        }
