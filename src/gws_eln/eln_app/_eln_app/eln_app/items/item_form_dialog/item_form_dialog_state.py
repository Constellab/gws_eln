from collections.abc import Callable, Coroutine
from datetime import date
from decimal import Decimal
from typing import Any

import reflex as rx
from gws_eln.core.unit_type import UnitType
from gws_eln.items.item import Item
from gws_eln.items.item_dto import CreateItemDTO, ItemDTO
from gws_eln.items.item_service import ItemService
from gws_eln.items.item_sheet_dto import ItemSheetDTO
from gws_eln.items.item_sheet_service import ItemSheetService
from gws_eln.utils.units_converter import UnitConverter
from gws_reflex_main import FormDialogState, ReflexMainState

FormDialogCloseCallback = Callable[[ItemDTO], Coroutine[Any, Any, None]]


class ItemFormDialogState(FormDialogState, rx.State):
    """State management for the create item_sheet item dialog functionality.

    This dialog is used to create new item_sheet items. The item_sheet must be
    provided when opening the dialog (item_sheet_id is a required input).
    """

    # Constant for "no supplier" option
    NO_SUPPLIER_VALUE: str = "__none__"

    # Constant for "no concentration unit" option
    NO_CONCENTRATION_VALUE: str = "__none__"

    # ItemSheet for which we're creating a item (required input)
    _item_sheet: ItemSheetDTO | None = None

    # Form field default values
    form_unit_type: str = UnitType.COUNT.value
    form_unit: str = UnitConverter.get_default_unit(UnitType.COUNT)
    form_concentration_unit: str = "__none__"
    form_location_id: str = ""
    form_supplier_id: str = "__none__"
    form_expiry_date: str = ""
    form_label: str = ""
    form_notes: str = ""

    _callback_after_close: FormDialogCloseCallback | None = None

    @rx.var
    def item_sheet_name(self) -> str:
        """Get the name of the item_sheet for display."""
        if self._item_sheet:
            return self._item_sheet.name
        return ""

    @rx.var
    def code_preview(self) -> str:
        """Best-effort preview of the auto-generated code (informative only).

        The authoritative code is assigned by the backend at creation.
        This preview shows the sheet prefix + current year pattern.
        """
        if self._item_sheet:
            return f"{self._item_sheet.code}-{date.today().year}-XXXX"
        return ""

    @rx.event
    async def open_create_dialog(self, item_sheet_id: str):
        """Open the dialog to create a item for the specified item_sheet.

        Args:
            item_sheet_id: The ID of the item_sheet for which to create a item (required)
        """
        main_state: ReflexMainState
        async with self:
            main_state = await self.get_state(ReflexMainState)

        # Load the item_sheet
        with await main_state.authenticate_user():
            item_sheet_service = ItemSheetService()
            item_sheet = item_sheet_service.get_item_sheet(item_sheet_id)
            self._item_sheet = item_sheet.to_dto()

        # Reset form fields to defaults
        self.form_label = ""
        self.form_notes = ""
        self.form_expiry_date = ""
        self.form_location_id = ""
        self.form_concentration_unit = self.NO_CONCENTRATION_VALUE

        # Set unit type and default unit from item_sheet
        self.form_unit_type = self._item_sheet.default_unit_type.value
        self.form_unit = UnitConverter.get_default_unit(self._item_sheet.default_unit_type)

        # Use item_sheet's default supplier if available
        if self._item_sheet.default_supplier:
            self.form_supplier_id = self._item_sheet.default_supplier.id
        else:
            self.form_supplier_id = self.NO_SUPPLIER_VALUE

        # Set to create mode
        self.is_update_mode = False

        # Open the dialog
        self.dialog_opened = True

    @rx.event
    def set_location_id(self, value: str):
        """Handle location selection change."""
        self.form_location_id = value

    @rx.event
    def set_supplier_id(self, value: str):
        """Handle supplier selection change."""
        self.form_supplier_id = value

    @rx.event
    def set_unit(self, value: str):
        """Handle unit selection change."""
        self.form_unit = value

    @rx.event
    def set_concentration_unit(self, value: str):
        """Handle concentration unit selection change."""
        self.form_concentration_unit = value

    @rx.event
    def set_expiry_date(self, value: str):
        """Handle expiry date change."""
        self.form_expiry_date = value

    def _validate_form_data(
        self, form_data: dict
    ) -> tuple[
        Decimal, str, Decimal | None, str, str | None, date | None, str | None, str | None
    ]:
        """Validate and parse form data.

        Args:
            form_data: Dictionary containing form fields

        Returns:
            Tuple of (quantity, unit, concentration, location_id,
                     supplier_id, expiry_date, label, notes) if validation succeeds

        Raises:
            Exception: If validation fails
        """
        # Get values from form data
        quantity_str = form_data.get("quantity", "").strip()
        concentration_str = form_data.get("concentration", "").strip()
        label = form_data.get("label", "").strip() or None
        notes = form_data.get("notes", "").strip() or None

        # Get values from state (for select components)
        location_id = self.form_location_id
        supplier_id = (
            self.form_supplier_id
            if self.form_supplier_id and self.form_supplier_id != self.NO_SUPPLIER_VALUE
            else None
        )
        unit = self.form_unit

        # Parse expiry date
        expiry_date = None
        if self.form_expiry_date:
            try:
                expiry_date = date.fromisoformat(self.form_expiry_date)
            except ValueError:
                raise Exception("Invalid expiry date format")

        # Validate required fields
        if not quantity_str:
            raise Exception("Quantity is required")

        try:
            quantity = Decimal(quantity_str)
            if quantity <= 0:
                raise Exception("Quantity must be positive")
        except (ValueError, ArithmeticError):
            raise Exception("Invalid quantity value")

        # Concentration is optional. Empty string means "no concentration".
        concentration: Decimal | None = None
        if concentration_str:
            try:
                concentration = Decimal(concentration_str)
            except (ValueError, ArithmeticError):
                raise Exception("Invalid concentration value")
            if concentration <= 0:
                raise Exception("Concentration must be positive")

        if not location_id:
            raise Exception("Location is required")

        if not unit:
            raise Exception("Unit is required")

        return (
            quantity,
            unit,
            concentration,
            location_id,
            supplier_id,
            expiry_date,
            label,
            notes,
        )

    async def _create(self, form_data: dict):
        """Create a new item_sheet item using the form data.

        Args:
            form_data: Dictionary containing form fields

        Yields:
            Reflex events (rx.toast)
        """
        if not self._item_sheet:
            raise Exception("ItemSheet is required")

        # Validate and parse form data
        (
            quantity,
            unit,
            concentration,
            location_id,
            supplier_id,
            expiry_date,
            label,
            notes,
        ) = self._validate_form_data(form_data)

        main_state: ReflexMainState
        async with self:
            main_state = await self.get_state(ReflexMainState)

        # Concentration unit (optional). "__none__" means no unit.
        concentration_unit = (
            self.form_concentration_unit
            if self.form_concentration_unit
            and self.form_concentration_unit != self.NO_CONCENTRATION_VALUE
            else None
        )

        # Create the item
        item: Item
        with await main_state.authenticate_user():
            item_service = ItemService()
            dto = CreateItemDTO(
                item_sheet_id=self._item_sheet.id,
                quantity=quantity,
                unit=unit,
                concentration=concentration,
                concentration_unit=concentration_unit,
                location_id=location_id,
                supplier_id=supplier_id,
                expiry_date=expiry_date,
                label=label,
                notes=notes,
            )
            item = item_service.create_item(dto)

        # Show success toast
        yield rx.toast.success("ItemSheet item created successfully")

        if self._callback_after_close:
            await self._callback_after_close(item.to_dto())

    async def _update(self, form_data: dict):
        """Not implemented - update is handled by a separate dialog."""
        raise NotImplementedError("Update is not supported by this dialog")

    async def _clear_form_state(self):
        """Clear all form state after successful operation."""
        self._item_sheet = None
        self.form_unit_type = UnitType.COUNT.value
        self.form_unit = UnitConverter.get_default_unit(UnitType.COUNT)
        self.form_concentration_unit = self.NO_CONCENTRATION_VALUE
        self.form_location_id = ""
        self.form_supplier_id = self.NO_SUPPLIER_VALUE
        self.form_expiry_date = ""
        self.form_label = ""
        self.form_notes = ""
        self.is_update_mode = False

    def set_callback_after_close(self, callback: FormDialogCloseCallback | None):
        """Set the callback to invoke after the dialog closes successfully.

        This callback is called after a successful create operation,
        typically used to refresh a list or navigate to the created item.

        Args:
            callback: The async callback function to invoke, or None to clear
        """
        self._callback_after_close = callback
