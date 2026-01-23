"""State management for delete batch form dialog."""

from collections.abc import AsyncGenerator, Callable
from typing import Any

import reflex as rx
from gws_eln.materials.material_batch_dto import DeleteBatchResultDTO, MaterialBatchDTO
from gws_eln.materials.material_batch_service import MaterialBatchService
from gws_reflex_main import FormDialogState, ReflexMainState

FormDialogCloseCallback = Callable[[DeleteBatchResultDTO], AsyncGenerator[Any, None]]


class DeleteBatchFormDialogState(FormDialogState, rx.State):
    """State management for the delete batch dialog functionality.

    This dialog is used to delete or discard a batch.
    The batch must be provided when opening the dialog.
    """

    # Batch being deleted (required input)
    _batch: MaterialBatchDTO | None = None

    # Form field for optional notes when discarding
    form_notes: str = ""

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

    @rx.var
    def current_quantity(self) -> str:
        """Get the current quantity for display."""
        if self._batch:
            return self._batch.pretty_quantity
        return ""

    @rx.event
    async def open_delete_dialog(self, batch: MaterialBatchDTO):
        """Open the dialog to delete the specified batch.

        Args:
            batch: The batch to delete (required)
        """
        # Store the batch being deleted
        self._batch = batch

        # Reset form fields
        self.form_notes = ""

        # Set to create mode (not update mode for this dialog)
        self.is_update_mode = False

        # Open the dialog
        self.dialog_opened = True

    async def _create(self, form_data: dict):
        """Delete the batch.

        Args:
            form_data: Dictionary containing form fields

        Yields:
            Reflex events (rx.toast)
        """
        if not self._batch:
            raise Exception("Batch is required")

        # Get notes from form data
        notes = form_data.get("notes", "").strip() or None

        main_state: ReflexMainState
        async with self:
            main_state = await self.get_state(ReflexMainState)

        # Delete the batch
        with await main_state.authenticate_user():
            batch_service = MaterialBatchService()
            result = batch_service.delete_batch(self._batch.id, notes=notes)

        # Show appropriate success toast
        if result == DeleteBatchResultDTO.DELETED:
            yield rx.toast.success("Batch deleted successfully")
        else:
            yield rx.toast.success("Batch discarded successfully")

        if self._callback_after_close:
            async for event in self._callback_after_close(result):
                yield event

    async def _update(self, form_data: dict):
        """Not implemented - this dialog only supports delete."""
        raise NotImplementedError("Update is not supported by this dialog")

    async def _clear_form_state(self):
        """Clear all form state after successful operation."""
        self._batch = None
        self.form_notes = ""
        self.is_update_mode = False

    def set_callback_after_close(self, callback: FormDialogCloseCallback | None):
        """Set the callback to invoke after the dialog closes successfully.

        Args:
            callback: The async callback function to invoke, or None to clear
        """
        self._callback_after_close = callback
