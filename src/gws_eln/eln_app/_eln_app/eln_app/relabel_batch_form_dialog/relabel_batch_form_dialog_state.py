"""State management for relabel batch form dialog."""

from collections.abc import Callable, Coroutine
from typing import Any

import reflex as rx
from gws_eln.materials.material_batch_dto import MaterialBatchDTO, RelabelBatchDTO
from gws_eln.materials.material_batch_service import MaterialBatchService
from gws_reflex_main import FormDialogState, ReflexMainState

FormDialogCloseCallback = Callable[[MaterialBatchDTO], Coroutine[Any, Any, None]]


class RelabelBatchFormDialogState(FormDialogState, rx.State):
    """State management for the relabel batch dialog functionality.

    This dialog is used to relabel a batch (change batch_number and/or label).
    The batch must be provided when opening the dialog.
    """

    # Batch being relabeled (required input)
    _batch: MaterialBatchDTO | None = None

    # Form fields
    form_batch_number: str = ""
    form_label: str = ""

    _callback_after_close: FormDialogCloseCallback | None = None

    @rx.var
    def current_batch_number(self) -> str:
        """Get the current batch number for display."""
        if self._batch:
            return self._batch.batch_number
        return ""

    @rx.var
    def current_label(self) -> str:
        """Get the current label for display."""
        if self._batch:
            return self._batch.label or "(No label)"
        return ""

    @rx.var
    def material_name(self) -> str:
        """Get the material name for display."""
        if self._batch and self._batch.material:
            return self._batch.material.name
        return ""

    @rx.event
    async def open_relabel_dialog(self, batch: MaterialBatchDTO):
        """Open the dialog to relabel the specified batch.

        Args:
            batch: The batch to relabel (required)
        """
        # Store the batch being relabeled
        self._batch = batch

        # Initialize form fields with current values
        self.form_batch_number = batch.batch_number
        self.form_label = batch.label or ""

        # Set to create mode (not update mode for this dialog)
        self.is_update_mode = False

        # Open the dialog
        self.dialog_opened = True

    def _validate_form_data(self, form_data: dict) -> RelabelBatchDTO:
        """Validate and parse form data.

        Args:
            form_data: Dictionary containing form fields

        Returns:
            RelabelBatchDTO if validation succeeds

        Raises:
            Exception: If validation fails
        """
        # Get values from form data
        batch_number = form_data.get("batch_number", "").strip()
        label = form_data.get("label", "").strip()

        # Validate batch_number is not empty
        if not batch_number:
            raise Exception("Batch number is required")

        # Check if anything changed
        batch_number_changed = batch_number != self._batch.batch_number if self._batch else True
        label_changed = label != (self._batch.label or "") if self._batch else True

        if not batch_number_changed and not label_changed:
            raise Exception("No changes detected")

        return RelabelBatchDTO(
            batch_number=batch_number if batch_number_changed else None,
            label=label if label_changed else None,
        )

    async def _create(self, form_data: dict):
        """Relabel the batch with form data.

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

        # Relabel the batch
        with await main_state.authenticate_user():
            batch_service = MaterialBatchService()
            result = batch_service.relabel_batch(self._batch.id, dto)

        # Show success toast
        yield rx.toast.success("Batch relabeled successfully")

        if self._callback_after_close:
            await self._callback_after_close(result.batch.to_dto())

    async def _update(self, form_data: dict):
        """Not implemented - this dialog only supports create (relabel)."""
        raise NotImplementedError("Update is not supported by this dialog")

    async def _clear_form_state(self):
        """Clear all form state after successful operation."""
        self._batch = None
        self.form_batch_number = ""
        self.form_label = ""
        self.is_update_mode = False

    def set_callback_after_close(self, callback: FormDialogCloseCallback | None):
        """Set the callback to invoke after the dialog closes successfully.

        Args:
            callback: The async callback function to invoke, or None to clear
        """
        self._callback_after_close = callback
