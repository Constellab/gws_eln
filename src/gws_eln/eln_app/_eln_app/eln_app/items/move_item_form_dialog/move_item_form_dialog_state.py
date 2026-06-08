from collections.abc import Callable, Coroutine
from typing import Any

import reflex as rx
from gws_eln.items.item_dto import ItemDTO, MoveItemDTO
from gws_eln.items.item_service import ItemService
from gws_reflex_main import FormDialogState, ReflexMainState

FormDialogCloseCallback = Callable[[ItemDTO], Coroutine[Any, Any, None]]


class MoveItemFormDialogState(FormDialogState, rx.State):
    """State management for the move item dialog functionality.

    This dialog is used to move a item to a different location.
    The item must be provided when opening the dialog.
    """

    # Item being moved (required input)
    _item: ItemDTO | None = None

    # Form field for destination location
    form_location_id: str = ""

    _callback_after_close: FormDialogCloseCallback | None = None

    @rx.var
    def item_number(self) -> str:
        """Get the item number for display."""
        if self._item:
            return self._item.item_number
        return ""

    @rx.var
    def current_location_name(self) -> str:
        """Get the current location name for display."""
        if self._item and self._item.location:
            return self._item.location.name
        return ""

    @rx.event
    async def open_move_dialog(self, item: ItemDTO):
        """Open the dialog to move the specified item.

        Args:
            item: The item to move (required)
        """
        # Store the item being moved
        self._item = item

        # Reset form fields
        self.form_location_id = ""

        # Set to create mode (not update mode)
        self.is_update_mode = False

        # Open the dialog
        self.dialog_opened = True

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
            raise Exception("Destination location is required")

        # Validate not moving to the same location
        if self._item and self._item.location and location_id == self._item.location.id:
            raise Exception("Item is already at this location")

        return location_id

    async def _create(self, form_data: dict):
        """Move the item to the new location.

        Args:
            form_data: Dictionary containing form fields

        Yields:
            Reflex events (rx.toast)
        """
        if not self._item:
            raise Exception("Item is required")

        # Validate and parse form data
        location_id = self._validate_form_data(form_data)

        main_state: ReflexMainState
        async with self:
            main_state = await self.get_state(ReflexMainState)

        # Move the item
        with await main_state.authenticate_user():
            item_service = ItemService()
            dto = MoveItemDTO(to_location_id=location_id)
            result = item_service.move_item(self._item.id, dto)

        # Show success toast
        yield rx.toast.success("Item moved successfully")

        if self._callback_after_close:
            await self._callback_after_close(result.item.to_dto())

    async def _update(self, form_data: dict):
        """Not implemented - this dialog only supports move operation."""
        raise NotImplementedError("Update is not supported by this dialog")

    async def _clear_form_state(self):
        """Clear all form state after successful operation."""
        self._item = None
        self.form_location_id = ""
        self.is_update_mode = False

    def set_callback_after_close(self, callback: FormDialogCloseCallback | None):
        """Set the callback to invoke after the dialog closes successfully.

        This callback is called after a successful move operation,
        typically used to refresh the item details.

        Args:
            callback: The async callback function to invoke, or None to clear
        """
        self._callback_after_close = callback
