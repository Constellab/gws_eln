"""State management for use item form dialog."""

from collections.abc import Callable, Coroutine
from typing import Any

import reflex as rx
from gws_eln.items.item_dto import ItemDTO, UseItemDTO
from gws_eln.items.item_service import ItemService
from gws_reflex_main import FormDialogState, ReflexMainState

from ...notes.note_linkable_dialog_state import NoteLinkableDialogState

FormDialogCloseCallback = Callable[[ItemDTO], Coroutine[Any, Any, None]]


class UseItemFormDialogState(NoteLinkableDialogState, FormDialogState, rx.State):
    """State management for the use item dialog functionality.

    Records a USE activity on a non-consumable instrument (reference only, no
    quantity change). The item must be provided when opening the dialog.
    """

    # Item being used (required input)
    _item: ItemDTO | None = None

    # Form fields
    form_notes: str = ""

    _callback_after_close: FormDialogCloseCallback | None = None

    @rx.var
    def current_code(self) -> str:
        """Get the current code for display (read-only)."""
        if self._item:
            return self._item.code
        return ""

    @rx.var
    def item_sheet_name(self) -> str:
        """Get the item_sheet name for display."""
        if self._item and self._item.item_sheet:
            return self._item.item_sheet.name
        return ""

    @rx.event
    async def open_use_dialog(self, item: ItemDTO):
        """Open the dialog to record a use of the specified item.

        Args:
            item: The item to use (required)
        """
        self._item = item
        self.form_notes = ""

        # This dialog only creates (records a use), never updates
        self.is_update_mode = False
        self.dialog_opened = True

    def _validate_form_data(self, form_data: dict) -> UseItemDTO:
        """Validate and parse form data.

        Args:
            form_data: Dictionary containing form fields

        Returns:
            UseItemDTO if validation succeeds
        """
        notes = form_data.get("notes", "").strip() or None
        return UseItemDTO(notes=notes)

    async def _create(self, form_data: dict):
        """Record the use of the item with form data.

        Args:
            form_data: Dictionary containing form fields

        Yields:
            Reflex events (rx.toast)
        """
        if not self._item:
            raise Exception("Item is required")

        dto = self._validate_form_data(form_data)
        dto.note_id = self.note_dto_id

        main_state: ReflexMainState
        async with self:
            main_state = await self.get_state(ReflexMainState)

        with await main_state.authenticate_user():
            item_service = ItemService()
            result = item_service.use_item(self._item.id, dto)
            linked_note = self._link_note_activity(result.activity.id)

        yield rx.toast.success("Item use recorded successfully")
        await self._after_note_link(linked_note)

        if self._callback_after_close:
            await self._callback_after_close(result.item.to_dto())

    async def _update(self, form_data: dict):
        """Not implemented - this dialog only records a use."""
        raise NotImplementedError("Update is not supported by this dialog")

    async def _clear_form_state(self):
        """Clear all form state after successful operation."""
        self._item = None
        self.form_notes = ""
        self.clear_note_context()
        self.is_update_mode = False

    def set_callback_after_close(self, callback: FormDialogCloseCallback | None):
        """Set the callback to invoke after the dialog closes successfully.

        Args:
            callback: The async callback function to invoke, or None to clear
        """
        self._callback_after_close = callback
