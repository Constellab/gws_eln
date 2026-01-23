"""State management for update batch form dialog."""

from collections.abc import Callable, Coroutine
from datetime import date
from typing import Any

import reflex as rx
from gws_eln.materials.material_batch_dto import MaterialBatchDTO, UpdateBatchDTO
from gws_eln.materials.material_batch_service import MaterialBatchService
from gws_reflex_main import FormDialogState, ReflexMainState

FormDialogCloseCallback = Callable[[MaterialBatchDTO], Coroutine[Any, Any, None]]


class UpdateBatchFormDialogState(FormDialogState, rx.State):
    """State management for the update batch dialog functionality.

    This dialog is used to update batch metadata (notes, expiry_date, supplier).
    The batch must be provided when opening the dialog.
    """

    # Batch being updated (required input)
    _batch: MaterialBatchDTO | None = None

    # Form fields
    form_notes: str = ""
    form_expiry_date: str = ""
    form_supplier_id: str = ""

    _callback_after_close: FormDialogCloseCallback | None = None

    @rx.var
    def batch_number(self) -> str:
        """Get the batch number for display."""
        if self._batch:
            return self._batch.batch_number
        return ""

    @rx.var
    def material_name(self) -> str:
        """Get the material name for display."""
        if self._batch and self._batch.material:
            return self._batch.material.name
        return ""

    @rx.event
    async def open_update_dialog(self, batch: MaterialBatchDTO):
        """Open the dialog to update the specified batch.

        Args:
            batch: The batch to update (required)
        """
        # Store the batch being updated
        self._batch = batch

        # Initialize form fields with current values
        self.form_notes = batch.notes or ""
        self.form_expiry_date = batch.expiry_date.isoformat() if batch.expiry_date else ""
        self.form_supplier_id = batch.supplier.id if batch.supplier else "__none__"

        # Set to update mode
        self.is_update_mode = True

        # Open the dialog
        self.dialog_opened = True

    @rx.event
    def set_supplier_id(self, value: str):
        """Handle supplier selection change."""
        self.form_supplier_id = value

    @rx.event
    def set_expiry_date(self, value: str):
        """Handle expiry date change."""
        self.form_expiry_date = value

    def _validate_form_data(self, form_data: dict) -> UpdateBatchDTO:
        """Validate and parse form data.

        Args:
            form_data: Dictionary containing form fields

        Returns:
            UpdateBatchDTO if validation succeeds

        Raises:
            Exception: If validation fails
        """
        # Get notes from form data
        notes = form_data.get("notes", "").strip() or None

        # Parse expiry date from state (input type=date stores in state)
        expiry_date: date | None = None
        if self.form_expiry_date:
            try:
                expiry_date = date.fromisoformat(self.form_expiry_date)
            except ValueError:
                raise Exception("Invalid expiry date format")

        # Get supplier_id from state
        supplier_id = self.form_supplier_id if self.form_supplier_id != "__none__" else None

        return UpdateBatchDTO(
            notes=notes,
            expiry_date=expiry_date,
            supplier_id=supplier_id,
        )

    async def _create(self, form_data: dict):
        """Not implemented - this dialog only supports update."""
        raise NotImplementedError("Create is not supported by this dialog")

    async def _update(self, form_data: dict):
        """Update the batch with form data.

        Args:
            form_data: Dictionary containing form fields

        Yields:
            Reflex events (rx.toast)
        """
        if not self._batch:
            raise Exception("Batch is required")

        # Validate and parse form data
        dto = self._validate_form_data(form_data)

        main_state: ReflexMainState
        async with self:
            main_state = await self.get_state(ReflexMainState)

        # Update the batch
        with await main_state.authenticate_user():
            batch_service = MaterialBatchService()
            batch = batch_service.update_batch(self._batch.id, dto)

        # Show success toast
        yield rx.toast.success("Batch updated successfully")

        if self._callback_after_close:
            await self._callback_after_close(batch.to_dto())

    async def _clear_form_state(self):
        """Clear all form state after successful operation."""
        self._batch = None
        self.form_notes = ""
        self.form_expiry_date = ""
        self.form_supplier_id = ""
        self.is_update_mode = False

    def set_callback_after_close(self, callback: FormDialogCloseCallback | None):
        """Set the callback to invoke after the dialog closes successfully.

        Args:
            callback: The async callback function to invoke, or None to clear
        """
        self._callback_after_close = callback
