"""State management for the note activity form dialog.

This dialog allows adding a item activity from within a note.
The user selects an activity type and (depending on it) either an existing item
or an item sheet (to receive a brand-new item), then fills in the type-specific
sub-form before submitting.
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
    1. Select an activity type and (existing item or item sheet)
    2. Fill in the activity-specific sub-form

    RECEIVE creates a brand-new item from a selected item sheet (the only way to
    bring an item into the inventory). The other activity types operate on an
    existing selected item.
    """

    # Note context (set when opening the dialog)
    _note_id: str = ""
    _note_block_id: str = ""
    _rich_text_content: RichTextDTO | None = None

    # Step 1: item and activity type selection
    form_item: InputSearchResultDTO | None = None
    form_activity_type: str = ""

    # For RECEIVE: receive into an existing item ("existing") or create a new one ("new")
    form_receive_mode: str = "existing"

    # For RECEIVE "new": select an item_sheet to create a new item
    form_item_sheet: InputSearchResultDTO | None = None
    _item_sheet: ItemSheetDTO | None = None

    # Resolved item (loaded after selection)
    _item: ItemDTO | None = None

    # Sub-form fields for receive (create) / consume
    form_unit_type: str = UnitType.COUNT.value
    form_unit: str = UnitConverter.get_default_unit(UnitType.COUNT)
    form_notes: str = ""

    # Sub-form fields for move / create
    form_location_id: str = ""

    # Sub-form fields for relabel
    form_item_number: str = ""
    form_label: str = ""

    # Sub-form field for receive (create): supplier (optional)
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
    def show_receive_mode_toggle(self) -> bool:
        """Whether to show the RECEIVE mode toggle (existing item vs new item)."""
        return self.form_activity_type == ActivityType.RECEIVE.value

    @rx.var
    def show_create_form(self) -> bool:
        """Whether to show the create-new-item form (RECEIVE 'new')."""
        return (
            self.form_activity_type == ActivityType.RECEIVE.value
            and self.form_receive_mode == "new"
        )

    @rx.var
    def show_item_select(self) -> bool:
        """Whether to show the existing-item selection field.

        Shown for activities operating on an existing item, including RECEIVE
        into an existing item (increment).
        """
        receive_existing = (
            self.form_activity_type == ActivityType.RECEIVE.value
            and self.form_receive_mode == "existing"
        )
        return receive_existing or self.form_activity_type in (
            ActivityType.CONSUME.value,
            ActivityType.MOVE.value,
            ActivityType.USE.value,
            ActivityType.DISCARD.value,
            ActivityType.RELABEL.value,
        )

    @rx.var
    def show_receive_consume_form(self) -> bool:
        """Whether to show the quantity sub-form (RECEIVE into existing, or CONSUME)."""
        receive_existing = (
            self.form_activity_type == ActivityType.RECEIVE.value
            and self.form_receive_mode == "existing"
        )
        return receive_existing or self.form_activity_type == ActivityType.CONSUME.value

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
    def quantity_label(self) -> str:
        """Label for the quantity field based on activity type."""
        if self.form_activity_type == ActivityType.CONSUME.value:
            return "Quantity to Consume"
        if self.form_activity_type == ActivityType.RECEIVE.value:
            return "Quantity to Receive"
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
            if self._item.location:
                self.form_location_id = self._item.location.id
            self.form_item_number = self._item.item_number
            self.form_label = self._item.label or ""

    @rx.event
    def set_activity_type(self, value: str):
        """Handle activity type selection change."""
        self.form_activity_type = value
        self._reset_sub_form_fields()
        # Reset item / item_sheet selection when activity type changes
        self.form_item = None
        self._item = None
        self.form_item_sheet = None
        self._item_sheet = None

    @rx.event
    def set_receive_mode(self, value: str | list[str]):
        """Handle RECEIVE mode change (existing item vs new item)."""
        # segmented_control passes str | list[str]; normalize to a single value
        self.form_receive_mode = value if isinstance(value, str) else (value[0] if value else "existing")
        # Reset both selections when switching mode
        self.form_item = None
        self._item = None
        self.form_item_sheet = None
        self._item_sheet = None

    @rx.event
    async def set_item_sheet(self, value: dict):
        """Handle item_sheet selection change for RECEIVE (new item)."""
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
        """Handle location selection change for move / create."""
        self.form_location_id = value

    @rx.event
    def set_supplier_id(self, value: str):
        """Handle supplier selection change for receive (create)."""
        self.form_supplier_id = value

    # --- Form submission ---

    async def _create(self, form_data: dict):
        """Submit the activity via ElnNoteService.add_activity().

        Builds the activity_data dict from form_data + state fields,
        then calls the service.
        """
        if not self.form_activity_type:
            raise Exception("Please select an activity type")

        # RECEIVE "new" requires an item_sheet; everything else requires an existing item
        is_receive_new = (
            self.form_activity_type == ActivityType.RECEIVE.value
            and self.form_receive_mode == "new"
        )
        if is_receive_new:
            if not self.form_item_sheet:
                raise Exception("Please select an item sheet")
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
        self.form_supplier_id = ""
        self.form_receive_mode = "existing"

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

        if activity_type == ActivityType.RECEIVE.value:
            if self.form_receive_mode == "new":
                data = self._build_create_data(form_data)
            else:
                # Receive into an existing item: increment its quantity
                data = self._build_quantity_data(form_data)

        elif activity_type == ActivityType.CONSUME.value:
            data = self._build_quantity_data(form_data)

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

        return data

    def _build_quantity_data(self, form_data: dict) -> dict[str, Any]:
        """Build activity_data for quantity-based actions (RECEIVE into existing, CONSUME)."""
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
            "quantity": quantity,
            "unit": self.form_unit,
            "notes": form_data.get("notes", "").strip() or None,
        }

    def _build_create_data(self, form_data: dict) -> dict[str, Any]:
        """Build activity_data for receiving a new item (RECEIVE)."""
        if not self.form_item_sheet:
            raise Exception("Item sheet is required")

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
