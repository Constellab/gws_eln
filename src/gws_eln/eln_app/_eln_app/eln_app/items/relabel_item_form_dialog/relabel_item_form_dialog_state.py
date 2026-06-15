"""State management for relabel item form dialog."""

from collections.abc import Callable, Coroutine
from typing import Any

import reflex as rx
from gws_eln.items.item_dto import ItemDTO, RelabelItemDTO
from gws_eln.items.item_service import ItemService
from gws_reflex_main import FormDialogState, ReflexMainState

from ...notes.note_linkable_dialog_state import NoteLinkableDialogState

FormDialogCloseCallback = Callable[[ItemDTO], Coroutine[Any, Any, None]]


class RelabelItemFormDialogState(NoteLinkableDialogState, FormDialogState, rx.State):
    """State management for the relabel item dialog functionality.

    This dialog is used to relabel a item (change item_number and/or label).
    The item must be provided when opening the dialog.
    """

    # Item being relabeled (required input)
    _item: ItemDTO | None = None

    # Form fields
    form_item_number: str = ""
    form_label: str = ""

    _callback_after_close: FormDialogCloseCallback | None = None

    @rx.var
    def current_item_number(self) -> str:
        """Get the current item number for display."""
        if self._item:
            return self._item.item_number
        return ""

    @rx.var
    def current_label(self) -> str:
        """Get the current label for display."""
        if self._item:
            return self._item.label or "(No label)"
        return ""

    @rx.var
    def item_sheet_name(self) -> str:
        """Get the item_sheet name for display."""
        if self._item and self._item.item_sheet:
            return self._item.item_sheet.name
        return ""

    @rx.event
    async def open_relabel_dialog(self, item: ItemDTO):
        """Open the dialog to relabel the specified item.

        Args:
            item: The item to relabel (required)
        """
        # Store the item being relabeled
        self._item = item

        # Initialize form fields with current values
        self.form_item_number = item.item_number
        self.form_label = item.label or ""

        # Set to create mode (not update mode for this dialog)
        self.is_update_mode = False

        # Open the dialog
        self.dialog_opened = True

    def _validate_form_data(self, form_data: dict) -> RelabelItemDTO:
        """Validate and parse form data.

        Args:
            form_data: Dictionary containing form fields

        Returns:
            RelabelItemDTO if validation succeeds

        Raises:
            Exception: If validation fails
        """
        # Get values from form data
        item_number = form_data.get("item_number", "").strip()
        label = form_data.get("label", "").strip()

        # Validate item_number is not empty
        if not item_number:
            raise Exception("Item number is required")

        # Check if anything changed
        item_number_changed = item_number != self._item.item_number if self._item else True
        label_changed = label != (self._item.label or "") if self._item else True

        if not item_number_changed and not label_changed:
            raise Exception("No changes detected")

        return RelabelItemDTO(
            item_number=item_number if item_number_changed else None,
            label=label if label_changed else None,
        )

    async def _create(self, form_data: dict):
        """Relabel the item with form data.

        Args:
            form_data: Dictionary containing form fields

        Yields:
            Reflex events (rx.toast)
        """
        if not self._item:
            raise Exception("Item is required")

        # Validate and parse form data
        dto = self._validate_form_data(form_data)
        dto.note_id = self.note_dto_id

        main_state: ReflexMainState
        async with self:
            main_state = await self.get_state(ReflexMainState)

        # Relabel the item
        with await main_state.authenticate_user():
            item_service = ItemService()
            result = item_service.relabel_item(self._item.id, dto)
            linked_note = self._link_note_activity(result.activity.id)

        # Show success toast
        yield rx.toast.success("Item relabeled successfully")
        await self._after_note_link(linked_note)

        if self._callback_after_close:
            await self._callback_after_close(result.item.to_dto())

    async def _update(self, form_data: dict):
        """Not implemented - this dialog only supports create (relabel)."""
        raise NotImplementedError("Update is not supported by this dialog")

    async def _clear_form_state(self):
        """Clear all form state after successful operation."""
        self._item = None
        self.form_item_number = ""
        self.form_label = ""
        self.clear_note_context()
        self.is_update_mode = False

    def set_callback_after_close(self, callback: FormDialogCloseCallback | None):
        """Set the callback to invoke after the dialog closes successfully.

        Args:
            callback: The async callback function to invoke, or None to clear
        """
        self._callback_after_close = callback
