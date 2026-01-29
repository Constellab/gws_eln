"""State management for aliquot creation form dialog."""

from collections.abc import Callable, Coroutine
from decimal import Decimal
from typing import Any

import reflex as rx
from gws_eln.core.unit_type import UnitType
from gws_eln.materials.material_batch import MaterialBatch
from gws_eln.materials.material_batch_dto import (
    CreateAliquotDTO,
    MaterialBatchDTO,
)
from gws_eln.materials.material_batch_service import MaterialBatchService
from gws_eln.materials.material_dto import MaterialDTO
from gws_eln.utils.units_converter import UnitConverter
from gws_reflex_main import FormDialogState, ReflexMainState
from gws_reflex_main.gws_components import InputSearchResultDTO

FormDialogCloseCallback = Callable[[MaterialBatchDTO], Coroutine[Any, Any, None]]


class AliquotFormDialogState(FormDialogState, rx.State):
    """State management for the aliquot creation dialog functionality.

    This dialog handles creating aliquots from a parent batch.
    The parent batch must be provided when opening the dialog.
    """

    # Parent batch from which we're creating the aliquot
    _batch: MaterialBatchDTO | None = None

    # Form field default values
    form_unit_type: str = UnitType.COUNT.value  # Parent batch unit type (for source)
    form_source_unit: str = UnitConverter.get_default_unit(UnitType.COUNT)
    form_aliquot_unit_type: str = UnitType.COUNT.value  # Target material unit type (for aliquot)
    form_aliquot_unit: str = UnitConverter.get_default_unit(UnitType.COUNT)
    form_target_material: InputSearchResultDTO | None = (
        None  # Required target material for the aliquot
    )
    form_location_id: str = ""
    form_supplier_id: str = ""
    form_notes: str = ""

    _callback_after_close: FormDialogCloseCallback | None = None

    @rx.var
    def batch(self) -> MaterialBatchDTO | None:
        """Get the parent batch number for display."""
        if self._batch:
            return self._batch
        return None

    @rx.var
    def dialog_title(self) -> str:
        """Get the dialog title."""
        return "Create Aliquot"

    @rx.var
    def dialog_description(self) -> str:
        """Get the dialog description."""
        return "Create a new aliquot from this batch. The source quantity will be deducted from the parent batch."

    def _get_best_unit_for_quantity(self, quantity: Decimal, unit_type: UnitType) -> str:
        """Determine the best unit based on the current quantity.

        Selects a unit that gives a readable value (between 1 and 1000 when possible).

        :param quantity: The quantity in base units
        :param unit_type: The unit type
        :return: The best unit symbol
        """
        if quantity == 0:
            return UnitConverter.get_default_unit(unit_type)

        unit_order = UnitConverter.UNIT_ORDER.get(unit_type, ["units"])

        for unit in unit_order:
            converted = UnitConverter.from_base_unit(quantity, unit, unit_type)
            abs_converted = abs(converted)
            if Decimal("1") <= abs_converted < Decimal("1000"):
                return unit

        # If no unit gives a value in range, use the default
        return UnitConverter.get_default_unit(unit_type)

    def open_dialog(self, batch: MaterialBatchDTO):
        """Open the dialog for creating an aliquot from the given batch.

        Args:
            batch: The parent batch DTO
        """
        # Store parent batch
        self._batch = batch

        # Reset form fields
        self.form_notes = ""

        # Set unit type from batch (for source quantity)
        self.form_unit_type = batch.unit_type.value

        # Determine the best unit based on current quantity
        best_unit = self._get_best_unit_for_quantity(batch.quantity, batch.unit_type)
        self.form_source_unit = best_unit

        # Default target material to parent's material
        self.form_target_material = InputSearchResultDTO(
            id=batch.material.id,
            display_text=batch.material.name,
            object=batch.material,
        )
        self.form_aliquot_unit_type = batch.unit_type.value
        self.form_aliquot_unit = best_unit

        # Default location to parent's location
        self.form_location_id = batch.location.id

        # Default supplier to empty (optional)
        self.form_supplier_id = ""

        # Set to create mode
        self.is_update_mode = False

        # Open the dialog
        self.dialog_opened = True

    @rx.event
    def set_batch(self, value: dict):
        """Handle batch selection change (no-op since batch is already selected)."""
        # This is a no-op because the batch is already set when opening the dialog
        # and the batch select component is disabled
        pass

    @rx.event
    def set_source_unit(self, value: str):
        """Handle source unit selection change."""
        self.form_source_unit = value

    @rx.event
    def set_aliquot_unit(self, value: str):
        """Handle aliquot unit selection change."""
        self.form_aliquot_unit = value

    @rx.event
    def set_location_id(self, value: str):
        """Handle location selection change."""
        self.form_location_id = value

    @rx.event
    def set_supplier_id(self, value: str):
        """Handle supplier selection change."""
        self.form_supplier_id = value

    @rx.event
    def set_target_material(self, value: dict):
        """Handle target material selection change.

        Updates the aliquot unit type based on the selected material's default_unit_type.
        """
        if not value:
            self.form_target_material = None
            return
        self.form_target_material = InputSearchResultDTO.from_json_object(value, MaterialDTO)
        material: MaterialDTO = self.form_target_material.object
        if material:
            self.form_aliquot_unit_type = material.default_unit_type.value
            self.form_aliquot_unit = UnitConverter.get_default_unit(material.default_unit_type)

    def _validate_form_data(
        self, form_data: dict
    ) -> tuple[
        str, Decimal, str, Decimal, str, str | None, str | None, str | None, str | None, str | None
    ]:
        """Validate and parse form data.

        Args:
            form_data: Dictionary containing form fields

        Returns:
            Tuple of (target_material_id, source_quantity, source_unit, aliquot_quantity, aliquot_unit,
                     aliquot_batch_number, label, location_id, supplier_id, notes) if validation succeeds

        Raises:
            Exception: If validation fails
        """
        # Get values from form data
        source_quantity_str = form_data.get("source_quantity", "").strip()
        aliquot_quantity_str = form_data.get("aliquot_quantity", "").strip()
        aliquot_batch_number = form_data.get("aliquot_batch_number", "").strip() or None
        label = form_data.get("label", "").strip() or None
        notes = form_data.get("notes", "").strip() or None

        # Get target material from state
        target_material_id = self.form_target_material.id if self.form_target_material else None

        # Get units from state
        source_unit = self.form_source_unit
        aliquot_unit = self.form_aliquot_unit

        # Get location and supplier from state
        location_id = self.form_location_id if self.form_location_id else None
        supplier_id = self.form_supplier_id if self.form_supplier_id else None

        if supplier_id == "__none__":
            supplier_id = None

        # Validate required fields
        if not target_material_id:
            raise Exception("Target material is required")

        if not source_quantity_str:
            raise Exception("Source quantity is required")

        if not aliquot_quantity_str:
            raise Exception("Aliquot quantity is required")

        try:
            source_quantity = Decimal(source_quantity_str)
            if source_quantity <= 0:
                raise Exception("Source quantity must be positive")
        except (ValueError, ArithmeticError):
            raise Exception("Invalid source quantity value")

        try:
            aliquot_quantity = Decimal(aliquot_quantity_str)
            if aliquot_quantity <= 0:
                raise Exception("Aliquot quantity must be positive")
        except (ValueError, ArithmeticError):
            raise Exception("Invalid aliquot quantity value")

        if not source_unit:
            raise Exception("Source unit is required")

        if not aliquot_unit:
            raise Exception("Aliquot unit is required")

        return (
            target_material_id,
            source_quantity,
            source_unit,
            aliquot_quantity,
            aliquot_unit,
            aliquot_batch_number,
            label,
            location_id,
            supplier_id,
            notes,
        )

    async def _create(self, form_data: dict):
        """Execute the aliquot creation using the form data.

        Args:
            form_data: Dictionary containing form fields

        Yields:
            Reflex events (rx.toast)
        """
        if not self._batch:
            raise Exception("Parent batch is required")

        # Validate and parse form data
        (
            target_material_id,
            source_quantity,
            source_unit,
            aliquot_quantity,
            aliquot_unit,
            aliquot_batch_number,
            label,
            location_id,
            supplier_id,
            notes,
        ) = self._validate_form_data(form_data)

        main_state: ReflexMainState
        async with self:
            main_state = await self.get_state(ReflexMainState)

        # Execute the aliquot creation
        aliquot: MaterialBatch
        with await main_state.authenticate_user():
            batch_service = MaterialBatchService()

            dto = CreateAliquotDTO(
                parent_batch_id=self._batch.id,
                target_material_id=target_material_id,
                source_quantity=source_quantity,
                source_unit=source_unit,
                aliquot_quantity=aliquot_quantity,
                aliquot_unit=aliquot_unit,
                aliquot_batch_number=aliquot_batch_number,
                label=label,
                location_id=location_id,
                supplier_id=supplier_id,
                notes=notes,
            )
            result = batch_service.create_aliquot(dto)
            yield rx.toast.success(f"Aliquot '{result.batch.batch_number}' created successfully")

            # Refresh the parent batch to show updated quantity
            parent_batch = batch_service.get_batch(self._batch.id)

        if self._callback_after_close:
            await self._callback_after_close(parent_batch.to_dto())

    async def _update(self, form_data: dict):
        """Not implemented - this dialog only creates aliquots."""
        raise NotImplementedError("Update is not supported by this dialog")

    async def _clear_form_state(self):
        """Clear all form state after successful operation."""
        self._batch = None
        self.form_unit_type = UnitType.COUNT.value
        self.form_source_unit = UnitConverter.get_default_unit(UnitType.COUNT)
        self.form_aliquot_unit_type = UnitType.COUNT.value
        self.form_aliquot_unit = UnitConverter.get_default_unit(UnitType.COUNT)
        self.form_target_material = None
        self.form_location_id = ""
        self.form_supplier_id = ""
        self.form_notes = ""
        self.is_update_mode = False

    def set_callback_after_close(self, callback: FormDialogCloseCallback | None):
        """Set the callback to invoke after the dialog closes successfully.

        This callback is called after a successful aliquot creation,
        typically used to refresh the batch detail or list.

        Args:
            callback: The async callback function to invoke, or None to clear
        """
        self._callback_after_close = callback
