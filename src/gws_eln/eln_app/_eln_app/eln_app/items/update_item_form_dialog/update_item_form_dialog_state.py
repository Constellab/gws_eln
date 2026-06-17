"""State management for update item form dialog."""

from collections.abc import Callable, Coroutine
from datetime import date
from decimal import Decimal
from typing import Any

import reflex as rx
from gws_eln.items.item_dto import ItemDTO, UpdateItemDTO
from gws_eln.items.item_service import ItemService
from gws_reflex_main import FormDialogState, ReflexMainState

FormDialogCloseCallback = Callable[[ItemDTO], Coroutine[Any, Any, None]]


class UpdateItemFormDialogState(FormDialogState, rx.State):
    """State management for the update item dialog functionality.

    This dialog is used to update item metadata (notes, expiry_date, supplier).
    The item must be provided when opening the dialog.
    """

    NO_CONCENTRATION_VALUE = "__none__"

    # Item being updated (required input)
    _item: ItemDTO | None = None

    # Form fields
    form_notes: str = ""
    form_expiry_date: str = ""
    form_supplier_id: str = ""
    form_concentration: str = ""
    form_concentration_unit: str = ""
    form_storage_conditions: str = ""

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

    @rx.event
    async def open_update_dialog(self, item: ItemDTO):
        """Open the dialog to update the specified item.

        Args:
            item: The item to update (required)
        """
        # Store the item being updated
        self._item = item

        # Initialize form fields with current values
        self.form_notes = item.notes or ""
        self.form_expiry_date = item.expiry_date.isoformat() if item.expiry_date else ""
        self.form_supplier_id = item.supplier.id if item.supplier else "__none__"
        # Decimal -> input string, stripping trailing zeros and avoiding scientific notation
        self.form_concentration = (
            f"{item.concentration.normalize():f}" if item.concentration is not None else ""
        )
        self.form_concentration_unit = item.concentration_unit or "__none__"
        self.form_storage_conditions = item.storage_conditions or ""

        # Set to update mode
        self.is_update_mode = True

        # Open the dialog
        self.dialog_opened = True

    @rx.event
    def set_supplier_id(self, value: str):
        """Handle supplier selection change."""
        self.form_supplier_id = value

    @rx.event
    def set_expiry_date(self, value: str):
        """Handle expiry date change."""
        self.form_expiry_date = value

    @rx.event
    def set_concentration_unit(self, value: str):
        """Handle concentration unit selection change."""
        self.form_concentration_unit = value

    def _validate_form_data(self, form_data: dict) -> UpdateItemDTO:
        """Validate and parse form data.

        Args:
            form_data: Dictionary containing form fields

        Returns:
            UpdateItemDTO if validation succeeds

        Raises:
            Exception: If validation fails
        """
        # Get notes from form data
        notes = form_data.get("notes", "").strip() or None

        # Parse expiry date from state (input type=date stores in state)
        expiry_date: date | None = None
        if self.form_expiry_date:
            try:
                expiry_date = date.fromisoformat(self.form_expiry_date)
            except ValueError as err:
                raise Exception("Invalid expiry date format") from err

        # Get supplier_id from state
        supplier_id = self.form_supplier_id if self.form_supplier_id != "__none__" else None

        # Concentration value (optional). Empty string means "no concentration".
        concentration_str = form_data.get("concentration", "").strip()
        concentration: Decimal | None = None
        if concentration_str:
            try:
                concentration = Decimal(concentration_str)
            except (ValueError, ArithmeticError) as exc:
                raise Exception("Invalid concentration value") from exc
            if concentration <= 0:
                raise Exception("Concentration must be positive")

        # Concentration unit (optional). "__none__" means no unit.
        concentration_unit = (
            self.form_concentration_unit
            if self.form_concentration_unit != self.NO_CONCENTRATION_VALUE
            else None
        )

        storage_conditions = form_data.get("storage_conditions", "").strip() or None

        return UpdateItemDTO(
            notes=notes,
            expiry_date=expiry_date,
            supplier_id=supplier_id,
            concentration=concentration,
            concentration_unit=concentration_unit,
            storage_conditions=storage_conditions,
        )

    async def _create(self, form_data: dict):
        """Not implemented - this dialog only supports update."""
        raise NotImplementedError("Create is not supported by this dialog")

    async def _update(self, form_data: dict):
        """Update the item with form data.

        Args:
            form_data: Dictionary containing form fields

        Yields:
            Reflex events (rx.toast)
        """
        if not self._item:
            raise Exception("Item is required")

        # Validate and parse form data
        dto = self._validate_form_data(form_data)

        main_state: ReflexMainState
        async with self:
            main_state = await self.get_state(ReflexMainState)

        # Update the item
        with await main_state.authenticate_user():
            item_service = ItemService()
            item = item_service.update_item(self._item.id, dto)

        # Show success toast
        yield rx.toast.success("Item updated successfully")

        if self._callback_after_close:
            await self._callback_after_close(item.to_dto())

    async def _clear_form_state(self):
        """Clear all form state after successful operation."""
        self._item = None
        self.form_notes = ""
        self.form_expiry_date = ""
        self.form_supplier_id = ""
        self.form_concentration = ""
        self.form_concentration_unit = self.NO_CONCENTRATION_VALUE
        self.form_storage_conditions = ""
        self.is_update_mode = False

    def set_callback_after_close(self, callback: FormDialogCloseCallback | None):
        """Set the callback to invoke after the dialog closes successfully.

        Args:
            callback: The async callback function to invoke, or None to clear
        """
        self._callback_after_close = callback
