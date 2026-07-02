"""State management for delete item form dialog."""

from collections.abc import AsyncGenerator, Callable
from typing import Any

import reflex as rx
from gws_eln.items.item_dto import DeleteItemResultDTO, ItemDTO
from gws_eln.items.item_service import ItemService
from gws_reflex_base import ReflexAppException
from gws_reflex_main import FormDialogState, ReflexMainState

FormDialogCloseCallback = Callable[[DeleteItemResultDTO], AsyncGenerator[Any, None]]


class DeleteItemFormDialogState(FormDialogState, rx.State):
    """State management for the delete item dialog functionality.

    This dialog is used to delete or discard a item.
    The item must be provided when opening the dialog.
    """

    # Item being deleted (required input)
    _item: ItemDTO | None = None

    # Form field for optional notes when discarding
    form_notes: str = ""

    _callback_after_close: FormDialogCloseCallback | None = None

    @rx.var
    def code(self) -> str:
        """Get the item number for display."""
        if self._item:
            return self._item.code
        return ""

    @rx.var
    def item_sheet_name(self) -> str:
        """Get the item_sheet name for display."""
        if self._item and self._item.item_sheet:
            return self._item.item_sheet.name
        return ""

    @rx.var
    def current_quantity(self) -> str:
        """Get the current quantity for display."""
        if self._item:
            return self._item.pretty_quantity
        return ""

    @rx.event
    async def open_delete_dialog(self, item: ItemDTO):
        """Open the dialog to delete the specified item.

        Args:
            item: The item to delete (required)
        """
        # Store the item being deleted
        self._item = item

        # Reset form fields
        self.form_notes = ""

        # Set to create mode (not update mode for this dialog)
        self.is_update_mode = False

        # Open the dialog
        self.dialog_opened = True

    async def _create(self, form_data: dict):
        """Delete the item.

        Args:
            form_data: Dictionary containing form fields

        Yields:
            Reflex events (rx.toast)
        """
        if not self._item:
            raise ReflexAppException("Item is required")

        # Get notes from form data
        notes = form_data.get("notes", "").strip() or None

        main_state: ReflexMainState
        async with self:
            main_state = await self.get_state(ReflexMainState)

        # Delete the item
        with await main_state.authenticate_user():
            item_service = ItemService()
            result = item_service.delete_item(self._item.id, notes=notes)

        # Show appropriate success toast
        if result == DeleteItemResultDTO.DELETED:
            yield rx.toast.success("Item deleted successfully")
        else:
            yield rx.toast.success("Item discarded successfully")

        if self._callback_after_close:
            async for event in self._callback_after_close(result):
                yield event

    async def _update(self, form_data: dict):
        """Not implemented - this dialog only supports delete."""
        raise NotImplementedError("Update is not supported by this dialog")

    async def _clear_form_state(self):
        """Clear all form state after successful operation."""
        self._item = None
        self.form_notes = ""
        self.is_update_mode = False

    def set_callback_after_close(self, callback: FormDialogCloseCallback | None):
        """Set the callback to invoke after the dialog closes successfully.

        Args:
            callback: The async callback function to invoke, or None to clear
        """
        self._callback_after_close = callback
