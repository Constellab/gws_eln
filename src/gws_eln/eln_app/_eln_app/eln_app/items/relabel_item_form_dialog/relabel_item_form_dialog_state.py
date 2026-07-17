"""State management for relabel item form dialog."""

from collections.abc import Callable, Coroutine
from typing import Any

import reflex as rx
from gws_eln.items.item_dto import ItemDTO, RelabelItemDTO
from gws_eln.items.item_service import ItemService
from gws_reflex_base import ReflexAppException
from gws_reflex_main import FormDialogState, ReflexMainState
from gws_reflex_main.gws_components import InputSearchResultDTO

from ...notes.note_linkable_dialog_state import NoteLinkableDialogState

FormDialogCloseCallback = Callable[[ItemDTO], Coroutine[Any, Any, None]]


class RelabelItemFormDialogState(NoteLinkableDialogState, FormDialogState, rx.State):
    """State management for the relabel item dialog functionality.

    This dialog is used to relabel a item (change its label).
    The item is either provided when opening the dialog (launched from that
    item), or picked in the dialog itself (launched from a note's activity
    chooser, which knows no item).
    """

    # Item being relabeled
    _item: ItemDTO | None = None
    # Item picker, only shown when the dialog was opened without an item.
    form_item: InputSearchResultDTO | None = None
    _item_is_selectable: bool = False

    # Form fields
    form_label: str = ""

    _callback_after_close: FormDialogCloseCallback | None = None

    @rx.var
    def item_is_selectable(self) -> bool:
        """Whether the dialog picks its own item (opened without one)."""
        return self._item_is_selectable

    @rx.var
    def has_item(self) -> bool:
        """Whether an item is set, either passed in or picked."""
        return self._item is not None

    @rx.var
    def current_code(self) -> str:
        """Get the current code for display (read-only)."""
        if self._item:
            return self._item.code
        return ""

    @rx.var
    def current_label(self) -> str:
        """Get the current label for display."""
        if self._item:
            return self._item.label or "(No label)"
        return ""

    def open_dialog_for_item(self, item: ItemDTO | None):
        """Open the dialog, picking the item in-dialog when none is given.

        :param item: The item to relabel, or None to let the user pick one
        :type item: ItemDTO | None
        """
        self._item = item
        self.form_item = None
        self._item_is_selectable = item is None
        self.form_label = (item.label or "") if item else ""
        self.is_update_mode = False
        self.dialog_opened = True

    @rx.event
    async def open_relabel_dialog(self, item: ItemDTO):
        """Open the dialog to relabel the specified item.

        Args:
            item: The item to relabel (required)
        """
        self.open_dialog_for_item(item)

    @rx.event
    def set_item(self, value: dict):
        """Pick the item to relabel, prefilling the label with its current one."""
        if not value:
            self.form_item = None
            self._item = None
            self.form_label = ""
            return
        self.form_item = InputSearchResultDTO.from_json_object(value, ItemDTO)
        self._item = self.form_item.object
        self.form_label = self._item.label or ""

    @rx.event
    def set_label(self, value: str):
        """Handle the new-label input change."""
        self.form_label = value

    def _validate_form_data(self, form_data: dict) -> RelabelItemDTO:
        """Validate and parse form data.

        Args:
            form_data: Dictionary containing form fields

        Returns:
            RelabelItemDTO if validation succeeds

        Raises:
            Exception: If validation fails
        """
        # Read the label from the state: the field is controlled, so it holds the
        # value prefilled when the item was picked.
        label = self.form_label.strip()

        # Check if the label changed
        label_changed = label != (self._item.label or "") if self._item else True

        if not label_changed:
            raise ReflexAppException("No changes detected")

        return RelabelItemDTO(label=label)

    async def _create(self, form_data: dict):
        """Relabel the item with form data.

        Args:
            form_data: Dictionary containing form fields

        Yields:
            Reflex events (rx.toast)
        """
        if not self._item:
            raise ReflexAppException("Please select an item")

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
        self.form_item = None
        self._item_is_selectable = False
        self.form_label = ""
        self.clear_note_context()
        self.is_update_mode = False

    def set_callback_after_close(self, callback: FormDialogCloseCallback | None):
        """Set the callback to invoke after the dialog closes successfully.

        Args:
            callback: The async callback function to invoke, or None to clear
        """
        self._callback_after_close = callback
