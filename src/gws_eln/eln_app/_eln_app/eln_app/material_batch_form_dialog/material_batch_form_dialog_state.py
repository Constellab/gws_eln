from collections.abc import Callable, Coroutine
from datetime import date
from decimal import Decimal
from typing import Any

import reflex as rx
from gws_eln.core.unit_type import UnitType
from gws_eln.materials.material_batch import MaterialBatch
from gws_eln.materials.material_batch_dto import CreateBatchDTO, MaterialBatchDTO
from gws_eln.materials.material_batch_service import MaterialBatchService
from gws_eln.materials.material_dto import MaterialDTO
from gws_eln.materials.material_service import MaterialService
from gws_eln.utils.units_converter import UnitConverter
from gws_reflex_main import FormDialogState, ReflexMainState

FormDialogCloseCallback = Callable[[MaterialBatchDTO], Coroutine[Any, Any, None]]


class MaterialBatchFormDialogState(FormDialogState, rx.State):
    """State management for the create material batch dialog functionality.

    This dialog is used to create new material batches. The material must be
    provided when opening the dialog (material_id is a required input).
    """

    # Constant for "no supplier" option
    NO_SUPPLIER_VALUE: str = "__none__"

    # Material for which we're creating a batch (required input)
    _material: MaterialDTO | None = None

    # Form field default values
    form_batch_number: str = ""
    form_unit_type: str = UnitType.COUNT.value
    form_unit: str = UnitConverter.get_default_unit(UnitType.COUNT)
    form_location_id: str = ""
    form_supplier_id: str = "__none__"
    form_expiry_date: str = ""
    form_label: str = ""
    form_notes: str = ""

    _callback_after_close: FormDialogCloseCallback | None = None

    @rx.var
    def material_name(self) -> str:
        """Get the name of the material for display."""
        if self._material:
            return self._material.name
        return ""

    @rx.event
    async def open_create_dialog(self, material_id: str):
        """Open the dialog to create a batch for the specified material.

        Args:
            material_id: The ID of the material for which to create a batch (required)
        """
        main_state: ReflexMainState
        async with self:
            main_state = await self.get_state(ReflexMainState)

        # Load the material
        with await main_state.authenticate_user():
            material_service = MaterialService()
            material = material_service.get_material(material_id)
            self._material = material.to_dto()

        # Reset form fields to defaults
        self.form_batch_number = ""
        self.form_label = ""
        self.form_notes = ""
        self.form_expiry_date = ""
        self.form_location_id = ""

        # Set unit type and default unit from material
        self.form_unit_type = self._material.default_unit_type.value
        self.form_unit = UnitConverter.get_default_unit(self._material.default_unit_type)

        # Use material's default supplier if available
        if self._material.default_supplier:
            self.form_supplier_id = self._material.default_supplier.id
        else:
            self.form_supplier_id = self.NO_SUPPLIER_VALUE

        # Set to create mode
        self.is_update_mode = False

        # Open the dialog
        self.dialog_opened = True

    @rx.event
    def set_location_id(self, value: str):
        """Handle location selection change."""
        self.form_location_id = value

    @rx.event
    def set_supplier_id(self, value: str):
        """Handle supplier selection change."""
        self.form_supplier_id = value

    @rx.event
    def set_unit(self, value: str):
        """Handle unit selection change."""
        self.form_unit = value

    @rx.event
    def set_expiry_date(self, value: str):
        """Handle expiry date change."""
        self.form_expiry_date = value

    def _validate_form_data(
        self, form_data: dict
    ) -> tuple[str, Decimal, str, str, str | None, date | None, str | None, str | None]:
        """Validate and parse form data.

        Args:
            form_data: Dictionary containing form fields

        Returns:
            Tuple of (batch_number, quantity, unit, location_id,
                     supplier_id, expiry_date, label, notes) if validation succeeds

        Raises:
            Exception: If validation fails
        """
        # Get values from form data
        batch_number = form_data.get("batch_number", "").strip()
        quantity_str = form_data.get("quantity", "").strip()
        label = form_data.get("label", "").strip() or None
        notes = form_data.get("notes", "").strip() or None

        # Get values from state (for select components)
        location_id = self.form_location_id
        supplier_id = (
            self.form_supplier_id
            if self.form_supplier_id and self.form_supplier_id != self.NO_SUPPLIER_VALUE
            else None
        )
        unit = self.form_unit

        # Parse expiry date
        expiry_date = None
        if self.form_expiry_date:
            try:
                expiry_date = date.fromisoformat(self.form_expiry_date)
            except ValueError:
                raise Exception("Invalid expiry date format")

        # Validate required fields
        if not batch_number:
            raise Exception("Batch number is required")

        if not quantity_str:
            raise Exception("Quantity is required")

        try:
            quantity = Decimal(quantity_str)
            if quantity <= 0:
                raise Exception("Quantity must be positive")
        except (ValueError, ArithmeticError):
            raise Exception("Invalid quantity value")

        if not location_id:
            raise Exception("Location is required")

        if not unit:
            raise Exception("Unit is required")

        return (
            batch_number,
            quantity,
            unit,
            location_id,
            supplier_id,
            expiry_date,
            label,
            notes,
        )

    async def _create(self, form_data: dict):
        """Create a new material batch using the form data.

        Args:
            form_data: Dictionary containing form fields

        Yields:
            Reflex events (rx.toast)
        """
        if not self._material:
            raise Exception("Material is required")

        # Validate and parse form data
        (
            batch_number,
            quantity,
            unit,
            location_id,
            supplier_id,
            expiry_date,
            label,
            notes,
        ) = self._validate_form_data(form_data)

        main_state: ReflexMainState
        async with self:
            main_state = await self.get_state(ReflexMainState)

        # Create the batch
        batch: MaterialBatch
        with await main_state.authenticate_user():
            batch_service = MaterialBatchService()
            dto = CreateBatchDTO(
                material_id=self._material.id,
                batch_number=batch_number,
                quantity=quantity,
                unit=unit,
                location_id=location_id,
                supplier_id=supplier_id,
                expiry_date=expiry_date,
                label=label,
                notes=notes,
            )
            batch = batch_service.create_batch(dto)

        # Show success toast
        yield rx.toast.success("Material batch created successfully")

        if self._callback_after_close:
            await self._callback_after_close(batch.to_dto())

    async def _update(self, form_data: dict):
        """Not implemented - update is handled by a separate dialog."""
        raise NotImplementedError("Update is not supported by this dialog")

    async def _clear_form_state(self):
        """Clear all form state after successful operation."""
        self._material = None
        self.form_batch_number = ""
        self.form_unit_type = UnitType.COUNT.value
        self.form_unit = UnitConverter.get_default_unit(UnitType.COUNT)
        self.form_location_id = ""
        self.form_supplier_id = self.NO_SUPPLIER_VALUE
        self.form_expiry_date = ""
        self.form_label = ""
        self.form_notes = ""
        self.is_update_mode = False

    def set_callback_after_close(self, callback: FormDialogCloseCallback | None):
        """Set the callback to invoke after the dialog closes successfully.

        This callback is called after a successful create operation,
        typically used to refresh a list or navigate to the created item.

        Args:
            callback: The async callback function to invoke, or None to clear
        """
        self._callback_after_close = callback
