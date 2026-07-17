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

    # Form field for the reason (controlled so it can be validated on submit).
    form_notes: str = ""

    # Whether deleting this item would discard it (soft delete) rather than hard
    # delete it - in that case a reason is mandatory. Computed when the dialog opens.
    will_discard: bool = False

    _callback_after_close: FormDialogCloseCallback | None = None

    @rx.event
    def set_notes(self, value: str):
        """Update the controlled reason field."""
        self.form_notes = value

    @rx.var
    def code(self) -> str:
        """Get the item code for display."""
        if self._item:
            return self._item.code
        return ""

    @rx.var
    def label(self) -> str:
        """Get the item label (human-readable name) for display."""
        if self._item:
            return self._item.label
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

        # Resolve whether this delete will discard the item (reason required).
        main_state = await self.get_state(ReflexMainState)
        with await main_state.authenticate_user():
            self.will_discard = ItemService().will_discard_item(item.id)

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

        # Read the reason from the controlled field (a text_area is not reliably
        # captured by the form submit). It is mandatory when the item is discarded.
        notes = self.form_notes.strip() or None
        if self.will_discard and not notes:
            raise ReflexAppException("A reason is required to discard this item")

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
            # The callback may be an async generator (yields events) or a plain
            # coroutine (just reloads) - support both.
            callback_result = self._callback_after_close(result)
            if hasattr(callback_result, "__aiter__"):
                async for event in callback_result:
                    yield event
            else:
                await callback_result

    async def _update(self, form_data: dict):
        """Not implemented - this dialog only supports delete."""
        raise NotImplementedError("Update is not supported by this dialog")

    async def _clear_form_state(self):
        """Clear all form state after successful operation."""
        self._item = None
        self.form_notes = ""
        self.will_discard = False
        self.is_update_mode = False

    def set_callback_after_close(self, callback: FormDialogCloseCallback | None):
        """Set the callback to invoke after the dialog closes successfully.

        Args:
            callback: The async callback function to invoke, or None to clear
        """
        self._callback_after_close = callback
