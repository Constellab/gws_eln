"""State management for the note activity form dialog.

This dialog allows adding a batch activity from within a note.
The user selects a batch, an activity type, and fills in the
type-specific sub-form before submitting.
"""

from collections.abc import Callable, Coroutine
from decimal import Decimal
from typing import Any

import reflex as rx
from gws_core import Note, RichTextDTO
from gws_eln.activities.activity_type import ActivityType
from gws_eln.core.unit_type import UnitType
from gws_eln.materials.material import Material
from gws_eln.materials.material_batch_dto import MaterialBatchDTO
from gws_eln.materials.material_batch_service import MaterialBatchService
from gws_eln.materials.material_dto import MaterialDTO
from gws_eln.notes.eln_note_dto import AddNoteActivityDTO
from gws_eln.notes.eln_note_service import ElnNoteService
from gws_eln.utils.units_converter import UnitConverter
from gws_reflex_main import FormDialogState, ReflexMainState

NoteActivityCallback = Callable[[Note], Coroutine[Any, Any, None]]


class NoteActivityFormDialogState(FormDialogState, rx.State):
    """State for the note activity form dialog.

    Two-step form:
    1. Select a batch and an activity type
    2. Fill in the activity-specific sub-form
    """

    # Note context (set when opening the dialog)
    _note_id: str = ""
    _note_block_id: str = ""
    _rich_text_content: RichTextDTO | None = None

    # Step 1: batch and activity type selection
    form_batch_id: str = ""
    form_activity_type: str = ""

    # For CREATE activity: select material instead of batch
    form_material_id: str = ""
    _material: MaterialDTO | None = None

    # Resolved batch (loaded after selection)
    _batch: MaterialBatchDTO | None = None

    # Sub-form fields for receive/consume
    form_unit_type: str = UnitType.COUNT.value
    form_unit: str = UnitConverter.get_default_unit(UnitType.COUNT)
    form_notes: str = ""

    # Sub-form fields for move
    form_location_id: str = ""

    # Sub-form fields for relabel
    form_batch_number: str = ""
    form_label: str = ""

    # Sub-form fields for aliquot
    form_source_unit: str = UnitConverter.get_default_unit(UnitType.COUNT)
    form_aliquot_unit_type: str = UnitType.COUNT.value  # Target material unit type (for aliquot)
    form_aliquot_unit: str = UnitConverter.get_default_unit(UnitType.COUNT)
    form_target_material_id: str = ""  # Required target material for the aliquot
    form_supplier_id: str = ""

    _callback_after_close: NoteActivityCallback | None = None

    # --- Computed properties ---

    @rx.var
    def batch_number(self) -> str:
        """Selected batch number for display."""
        if self._batch:
            return self._batch.batch_number
        return ""

    @rx.var
    def current_quantity(self) -> str:
        """Current quantity of selected batch for display."""
        if self._batch:
            return self._batch.pretty_quantity
        return ""

    @rx.var
    def current_location_name(self) -> str:
        """Current location of selected batch for display."""
        if self._batch and self._batch.location:
            return self._batch.location.name
        return ""

    @rx.var
    def show_create_form(self) -> bool:
        """Whether to show the create batch sub-form (requires material to be selected)."""
        return (
            self.form_activity_type == ActivityType.CREATE.value
            and bool(self.form_material_id)
        )

    @rx.var
    def is_create_activity(self) -> bool:
        """Whether the selected activity type is CREATE."""
        return self.form_activity_type == ActivityType.CREATE.value

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
    def show_sub_form(self) -> bool:
        """Whether any sub-form should be shown.

        For CREATE: requires material_id and activity type
        For other activities: requires batch_id and activity type
        """
        if self.form_activity_type == ActivityType.CREATE.value:
            return bool(self.form_material_id and self.form_activity_type)
        return bool(self.form_batch_id and self.form_activity_type)

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
        self._batch = None
        self.form_batch_id = ""
        self.form_activity_type = ""
        self._reset_sub_form_fields()
        self.is_update_mode = False
        self.dialog_opened = True

    @rx.event
    async def set_batch_id(self, value: str):
        """Handle batch selection change. Load batch details for the sub-form."""
        self.form_batch_id = value
        if value:
            main_state: ReflexMainState
            async with self:
                main_state = await self.get_state(ReflexMainState)
            with await main_state.authenticate_user():
                batch_service = MaterialBatchService()
                batch = batch_service.get_batch(value)
                self._batch = batch.to_dto()
                self.form_unit_type = batch.unit_type.value
                best_unit = self._get_best_unit_for_quantity(batch.quantity, batch.unit_type)
                self.form_unit = best_unit
                self.form_source_unit = best_unit
                # Initialize target material and aliquot unit type from batch's material
                self.form_target_material_id = batch.material.id
                self.form_aliquot_unit_type = batch.unit_type.value
                self.form_aliquot_unit = best_unit
                if batch.location:
                    self.form_location_id = batch.location.id
                self.form_batch_number = batch.batch_number
                self.form_label = batch.label or ""
        else:
            self._batch = None

    @rx.event
    def set_activity_type(self, value: str):
        """Handle activity type selection change."""
        self.form_activity_type = value
        self._reset_sub_form_fields()
        # Reset batch/material selection when activity type changes
        if value == ActivityType.CREATE.value:
            self.form_batch_id = ""
            self._batch = None
        else:
            self.form_material_id = ""
            self._material = None

    @rx.event
    async def set_material_id(self, value: str):
        """Handle material selection change for CREATE activity."""
        self.form_material_id = value
        if value:
            main_state: ReflexMainState
            async with self:
                main_state = await self.get_state(ReflexMainState)
            with await main_state.authenticate_user():
                material = Material.get_by_id_and_check(value)
                self._material = material.to_dto()
                self.form_unit_type = material.default_unit_type.value
                self.form_unit = UnitConverter.get_default_unit(material.default_unit_type)
        else:
            self._material = None

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
    def set_target_material_id(self, value: str):
        """Handle target material selection change for aliquot.

        Updates the aliquot unit type based on the selected material's default_unit_type.
        """
        self.form_target_material_id = value
        if value:
            material = Material.get_by_id_or_none(value)
            if material:
                self.form_aliquot_unit_type = material.default_unit_type.value
                self.form_aliquot_unit = UnitConverter.get_default_unit(material.default_unit_type)

    # --- Form submission ---

    async def _create(self, form_data: dict):
        """Submit the activity via ElnNoteService.add_activity().

        Builds the activity_data dict from form_data + state fields,
        then calls the service.
        """
        if not self.form_activity_type:
            raise Exception("Please select an activity type")

        # For CREATE activity, require material_id; for others, require batch_id
        if self.form_activity_type == ActivityType.CREATE.value:
            if not self.form_material_id:
                raise Exception("Please select a material")
        elif not self.form_batch_id:
            raise Exception("Please select a batch")

        activity_data = self._build_activity_data(form_data)

        main_state: ReflexMainState
        async with self:
            main_state = await self.get_state(ReflexMainState)

        with await main_state.authenticate_user():
            service = ElnNoteService()
            dto = AddNoteActivityDTO(
                note_id=self._note_id,
                note_block_id=self._note_block_id,
                batch_id=self.form_batch_id if self.form_batch_id else None,
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
        self._batch = None
        self._material = None
        self.form_batch_id = ""
        self.form_material_id = ""
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
        self.form_batch_number = ""
        self.form_label = ""
        self.form_target_material_id = ""
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
            batch_number = form_data.get("batch_number", "").strip()
            label = form_data.get("label", "").strip()
            if not batch_number:
                raise Exception("Batch number is required")
            data["batch_number"] = batch_number
            data["label"] = label or None

        elif activity_type == ActivityType.ALIQUOT.value:
            data = self._build_aliquot_data(form_data)

        return data

    def _build_create_data(self, form_data: dict) -> dict[str, Any]:
        """Build activity_data for batch creation."""
        if not self.form_material_id:
            raise Exception("Material is required")

        batch_number = form_data.get("batch_number", "").strip()
        if not batch_number:
            raise Exception("Batch number is required")

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
            "material_id": self.form_material_id,
            "batch_number": batch_number,
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

        if not self.form_target_material_id:
            raise Exception("Target material is required")
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
            "parent_batch_id": self.form_batch_id,
            "target_material_id": self.form_target_material_id,
            "source_quantity": source_quantity,
            "source_unit": self.form_source_unit,
            "aliquot_quantity": aliquot_quantity,
            "aliquot_unit": self.form_aliquot_unit,
            "aliquot_batch_number": form_data.get("aliquot_batch_number", "").strip() or None,
            "label": form_data.get("label", "").strip() or None,
            "location_id": self.form_location_id or None,
            "supplier_id": supplier_id,
            "notes": form_data.get("notes", "").strip() or None,
        }
