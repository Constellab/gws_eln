from collections.abc import Callable, Coroutine
from typing import Any

import reflex as rx
from gws_eln.items.item_dto import ItemDTO, MoveItemDTO
from gws_eln.items.item_service import ItemService
from gws_reflex_base import ReflexAppException
from gws_reflex_main import FormDialogState, ReflexMainState
from gws_reflex_main.gws_components import InputSearchResultDTO

from ...notes.note_linkable_dialog_state import NoteLinkableDialogState

FormDialogCloseCallback = Callable[[ItemDTO], Coroutine[Any, Any, None]]


class MoveItemFormDialogState(NoteLinkableDialogState, FormDialogState, rx.State):
    """State management for the move item dialog functionality.

    This dialog is used to move a item to a different location.
    The item is either provided when opening the dialog (launched from that
    item), or picked in the dialog itself (launched from a note's activity
    chooser, which knows no item).
    """

    # Item being moved
    _item: ItemDTO | None = None
    # Item picker, only shown when the dialog was opened without an item.
    form_item: InputSearchResultDTO | None = None
    _item_is_selectable: bool = False

    # Form field for destination location
    form_location_id: str = ""

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
    def current_location_name(self) -> str:
        """Get the current location name for display."""
        if self._item and self._item.location:
            return self._item.location.name
        return ""

    def open_dialog_for_item(self, item: ItemDTO | None):
        """Open the dialog, picking the item in-dialog when none is given.

        :param item: The item to move, or None to let the user pick one
        :type item: ItemDTO | None
        """
        self._item = item
        self.form_item = None
        self._item_is_selectable = item is None
        self.form_location_id = ""
        self.is_update_mode = False
        self.dialog_opened = True

    @rx.event
    async def open_move_dialog(self, item: ItemDTO):
        """Open the dialog to move the specified item.

        Args:
            item: The item to move (required)
        """
        self.open_dialog_for_item(item)

    @rx.event
    def set_item(self, value: dict):
        """Pick the item to move."""
        if not value:
            self.form_item = None
            self._item = None
            return
        self.form_item = InputSearchResultDTO.from_json_object(value, ItemDTO)
        self._item = self.form_item.object

    @rx.event
    def set_location_id(self, value: str):
        """Handle location selection change."""
        self.form_location_id = value

    def _validate_form_data(self, form_data: dict) -> str:
        """Validate and parse form data.

        Args:
            form_data: Dictionary containing form fields

        Returns:
            The destination location ID if validation succeeds

        Raises:
            Exception: If validation fails
        """
        # Get location from state (for select components)
        location_id = self.form_location_id

        # Validate required fields
        if not location_id:
            raise ReflexAppException("Destination location is required")

        # Validate not moving to the same location
        if self._item and self._item.location and location_id == self._item.location.id:
            raise ReflexAppException("Item is already at this location")

        return location_id

    async def _create(self, form_data: dict):
        """Move the item to the new location.

        Args:
            form_data: Dictionary containing form fields

        Yields:
            Reflex events (rx.toast)
        """
        if not self._item:
            raise ReflexAppException("Please select an item")

        # Validate and parse form data
        location_id = self._validate_form_data(form_data)

        main_state: ReflexMainState
        async with self:
            main_state = await self.get_state(ReflexMainState)

        # Move the item
        with await main_state.authenticate_user():
            item_service = ItemService()
            dto = MoveItemDTO(to_location_id=location_id, note_id=self.note_dto_id)
            result = item_service.move_item(self._item.id, dto)
            linked_note = self._link_note_activity(result.activity.id)

        # Show success toast
        yield rx.toast.success("Item moved successfully")
        await self._after_note_link(linked_note)

        if self._callback_after_close:
            await self._callback_after_close(result.item.to_dto())

    async def _update(self, form_data: dict):
        """Not implemented - this dialog only supports move operation."""
        raise NotImplementedError("Update is not supported by this dialog")

    async def _clear_form_state(self):
        """Clear all form state after successful operation."""
        self._item = None
        self.form_item = None
        self._item_is_selectable = False
        self.form_location_id = ""
        self.clear_note_context()
        self.is_update_mode = False

    def set_callback_after_close(self, callback: FormDialogCloseCallback | None):
        """Set the callback to invoke after the dialog closes successfully.

        This callback is called after a successful move operation,
        typically used to refresh the item details.

        Args:
            callback: The async callback function to invoke, or None to clear
        """
        self._callback_after_close = callback
