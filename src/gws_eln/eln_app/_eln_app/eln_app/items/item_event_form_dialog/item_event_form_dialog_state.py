"""State management for item event form dialog (Receive, Consume)."""

from collections.abc import Callable, Coroutine
from decimal import Decimal
from enum import Enum
from typing import Any

import reflex as rx
from gws_eln.core.unit_type import UnitType
from gws_eln.items.item_dto import (
    DecrementQuantityDTO,
    ItemDTO,
    ReceiveItemDTO,
)
from gws_eln.items.item_service import ItemService
from gws_eln.utils.units_converter import UnitConverter
from gws_reflex_main import FormDialogState, ReflexMainState

from ...notes.note_linkable_dialog_state import NoteLinkableDialogState

FormDialogCloseCallback = Callable[[ItemDTO], Coroutine[Any, Any, None]]


class ItemEventType(str, Enum):
    """Types of item events that can be performed."""

    RECEIVE = "receive"
    CONSUME = "consume"


class ItemEventFormDialogState(NoteLinkableDialogState, FormDialogState, rx.State):
    """State management for the item event dialog functionality.

    This dialog handles Receive and Consume operations on items.
    The item and event type must be provided when opening the dialog.
    """

    # Item for which we're performing the event
    _item: ItemDTO | None = None

    # Event type being performed
    _event_type: ItemEventType = ItemEventType.RECEIVE

    # Form field default values
    form_unit_type: str = UnitType.COUNT.value
    form_unit: str = UnitConverter.get_default_unit(UnitType.COUNT)
    form_notes: str = ""

    _callback_after_close: FormDialogCloseCallback | None = None

    @rx.var
    def item_number(self) -> str:
        """Get the item number for display."""
        if self._item:
            return self._item.item_number
        return ""

    @rx.var
    def current_quantity(self) -> str:
        """Get the current quantity for display."""
        if self._item:
            return self._item.pretty_quantity
        return ""

    @rx.var
    def event_type_value(self) -> str:
        """Get the event type value as string."""
        return self._event_type.value

    @rx.var
    def dialog_title(self) -> str:
        """Get the dialog title based on event type."""
        titles = {
            ItemEventType.RECEIVE: "Receive Stock",
            ItemEventType.CONSUME: "Consume Stock",
        }
        return titles.get(self._event_type, "Item Event")

    @rx.var
    def dialog_description(self) -> str:
        """Get the dialog description based on event type."""
        descriptions = {
            ItemEventType.RECEIVE: "Add stock received from a supplier to this item.",
            ItemEventType.CONSUME: "Record consumption of stock from this item.",
        }
        return descriptions.get(self._event_type, "")

    @rx.var
    def quantity_label(self) -> str:
        """Get the quantity label based on event type."""
        labels = {
            ItemEventType.RECEIVE: "Quantity to Receive",
            ItemEventType.CONSUME: "Quantity to Consume",
        }
        return labels.get(self._event_type, "Quantity")

    def _get_best_unit_for_quantity(self, quantity: Decimal, unit_type: UnitType) -> str:
        """Determine the best unit based on the current quantity.

        Selects a unit that gives a readable value (between 1 and 1000 when possible).

        :param quantity: The quantity in base units
        :param unit_type: The unit type
        :return: The best unit symbol
        """
        if quantity == 0:
            return UnitConverter.get_default_unit(unit_type)

        unit_order = UnitConverter.UNIT_ORDER.get(unit_type, ["units"])

        for unit in unit_order:
            converted = UnitConverter.from_base_unit(quantity, unit, unit_type)
            abs_converted = abs(converted)
            if Decimal("1") <= abs_converted < Decimal("1000"):
                return unit

        # If no unit gives a value in range, use the default
        return UnitConverter.get_default_unit(unit_type)

    def open_dialog_for_event(self, item: ItemDTO, event_type: ItemEventType):
        """Open the dialog for a specific item event.

        Args:
            item: The item DTO
            event_type: The event type (ItemEventType enum)
        """
        # Store item
        self._item = item

        # Set event type
        self._event_type = event_type

        # Reset form fields
        self.form_notes = ""

        # Set unit type from item
        self.form_unit_type = item.unit_type.value

        # Determine the best unit based on current quantity
        self.form_unit = self._get_best_unit_for_quantity(item.quantity, item.unit_type)

        # Set to create mode (we're always creating an event, not updating)
        self.is_update_mode = False

        # Open the dialog
        self.dialog_opened = True

    @rx.event
    def set_unit(self, value: str):
        """Handle unit selection change."""
        self.form_unit = value

    def _validate_form_data(self, form_data: dict) -> tuple[Decimal, str, str | None]:
        """Validate and parse form data.

        Args:
            form_data: Dictionary containing form fields

        Returns:
            Tuple of (quantity, unit, notes) if validation succeeds

        Raises:
            Exception: If validation fails
        """
        # Get values from form data
        quantity_str = form_data.get("quantity", "").strip()
        notes = form_data.get("notes", "").strip() or None

        # Get unit from state
        unit = self.form_unit

        # Validate required fields
        if not quantity_str:
            raise Exception("Quantity is required")

        try:
            quantity = Decimal(quantity_str)
            if quantity <= 0:
                raise Exception("Quantity must be positive")
        except (ValueError, ArithmeticError):
            raise Exception("Invalid quantity value")

        if not unit:
            raise Exception("Unit is required")

        return quantity, unit, notes

    async def _create(self, form_data: dict):
        """Execute the item event using the form data.

        Args:
            form_data: Dictionary containing form fields

        Yields:
            Reflex events (rx.toast)
        """
        if not self._item:
            raise Exception("Item is required")

        # Validate and parse form data
        quantity, unit, notes = self._validate_form_data(form_data)

        main_state: ReflexMainState
        async with self:
            main_state = await self.get_state(ReflexMainState)

        # Execute the appropriate event
        linked_note = None
        with await main_state.authenticate_user():
            item_service = ItemService()

            if self._event_type == ItemEventType.RECEIVE:
                dto = ReceiveItemDTO(
                    quantity=quantity, unit=unit, notes=notes, note_id=self.note_dto_id
                )
                result = item_service.receive_item(self._item.id, dto)
                linked_note = self._link_note_activity(result.activity.id)
                yield rx.toast.success("Stock received successfully")

            elif self._event_type == ItemEventType.CONSUME:
                dto = DecrementQuantityDTO(
                    quantity=quantity, unit=unit, notes=notes, note_id=self.note_dto_id
                )
                result = item_service.consume_quantity(self._item.id, dto)
                linked_note = self._link_note_activity(result.activity.id)
                yield rx.toast.success("Stock consumed successfully")

        await self._after_note_link(linked_note)

        if self._callback_after_close:
            await self._callback_after_close(result.item.to_dto())

    async def _update(self, form_data: dict):
        """Not implemented - this dialog only creates events."""
        raise NotImplementedError("Update is not supported by this dialog")

    async def _clear_form_state(self):
        """Clear all form state after successful operation."""
        self._item = None
        self._event_type = ItemEventType.RECEIVE
        self.form_unit_type = UnitType.COUNT.value
        self.form_unit = UnitConverter.get_default_unit(UnitType.COUNT)
        self.form_notes = ""
        self.clear_note_context()
        self.is_update_mode = False

    def set_callback_after_close(self, callback: FormDialogCloseCallback | None):
        """Set the callback to invoke after the dialog closes successfully.

        This callback is called after a successful event operation,
        typically used to refresh the item detail or list.

        Args:
            callback: The async callback function to invoke, or None to clear
        """
        self._callback_after_close = callback
