from collections.abc import Callable, Coroutine
from typing import Any

import reflex as rx
from gws_eln.suppliers.supplier import Supplier
from gws_eln.suppliers.supplier_dto import CreateSupplierDTO, SupplierDTO, UpdateSupplierDTO
from gws_eln.suppliers.supplier_service import SupplierService
from gws_reflex_main import FormDialogState, ReflexMainState

FormDialogCloseCallback = Callable[[SupplierDTO], Coroutine[Any, Any, None]]


class SupplierFormDialogState(FormDialogState, rx.State):
    """State management for the create/update supplier dialog functionality."""

    # Supplier being edited (None for create mode)
    _editing_supplier: SupplierDTO | None = None

    # Form field default values
    form_name: str = ""
    form_description: str = ""

    _callback_after_close: FormDialogCloseCallback | None = None

    @rx.event
    async def open_create_dialog(self):
        """Open the dialog in create mode."""
        # Reset to create mode
        self.is_update_mode = False

        # Open the dialog
        self.dialog_opened = True

    @rx.event
    async def open_update_dialog(self, supplier: SupplierDTO):
        """Open the dialog in update mode with existing supplier data.

        Args:
            supplier: The supplier to update
        """
        # Store the supplier being edited
        self._editing_supplier = supplier

        # Initialize form fields with supplier data
        self.form_name = supplier.name
        self.form_description = supplier.description or ""

        # Mark as editing
        self.is_update_mode = True

        # Open the dialog
        await self.open_dialog()

    def _validate_form_data(self, form_data: dict) -> tuple[str, str | None]:
        """Validate and parse form data.

        Args:
            form_data: Dictionary containing form fields (name, description)

        Returns:
            Tuple of (name, description) if validation succeeds

        Raises:
            Exception: If validation fails
        """
        # Get values from form data
        name = form_data.get("name", "").strip()
        description = form_data.get("description", "").strip() or None

        # Validate required fields
        if not name:
            raise Exception("Supplier name is required")

        return name, description

    async def _create(self, form_data: dict):
        """Create a new supplier using the form data.

        Args:
            form_data: Dictionary containing form fields (name, description)

        Yields:
            Reflex events (rx.toast)
        """
        # Validate and parse form data
        name, description = self._validate_form_data(form_data)

        main_state: ReflexMainState
        async with self:
            main_state = await self.get_state(ReflexMainState)

        # Create the supplier
        supplier: Supplier
        with await main_state.authenticate_user():
            supplier_service = SupplierService()
            dto = CreateSupplierDTO(name=name, description=description)
            supplier = supplier_service.create_supplier(dto)

        # Show success toast
        yield rx.toast.success("Supplier created successfully")

        if self._callback_after_close:
            await self._callback_after_close(supplier.to_dto())

    async def _update(self, form_data: dict):
        """Update an existing supplier using the form data.

        Args:
            form_data: Dictionary containing form fields (name, description)

        Yields:
            Reflex events (rx.toast)
        """
        # Validate and parse form data
        name, description = self._validate_form_data(form_data)

        main_state: ReflexMainState
        async with self:
            main_state = await self.get_state(ReflexMainState)

        # Update the supplier
        supplier: Supplier
        with await main_state.authenticate_user():
            supplier_service = SupplierService()
            dto = UpdateSupplierDTO(name=name, description=description)
            supplier = supplier_service.update_supplier(self._editing_supplier.id, dto)

        # Show success toast
        yield rx.toast.success("Supplier updated successfully")

        if self._callback_after_close:
            await self._callback_after_close(supplier.to_dto())

    async def _clear_form_state(self):
        """Clear all form state after successful operation."""
        self._editing_supplier = None
        self.form_name = ""
        self.form_description = ""
        self.is_update_mode = False

    def set_callback_after_close(self, callback: FormDialogCloseCallback | None):
        """Set the callback to invoke after the dialog closes successfully.

        This callback is called after a successful create or update operation,
        typically used to refresh a list or navigate to the created/updated item.

        Args:
            callback: The async callback function to invoke, or None to clear
        """
        self._callback_after_close = callback
