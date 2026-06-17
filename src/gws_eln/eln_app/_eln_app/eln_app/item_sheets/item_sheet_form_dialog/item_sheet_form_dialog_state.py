from collections.abc import Callable, Coroutine
from typing import Any

import reflex as rx
from gws_eln.core.unit_type import UnitType
from gws_eln.items.item_sheet import ItemSheet
from gws_eln.items.item_sheet_dto import CreateItemSheetDTO, ItemSheetDTO, UpdateItemSheetDTO
from gws_eln.items.item_sheet_service import ItemSheetService
from gws_eln.suppliers.supplier_dto import SupplierDTO
from gws_eln.suppliers.supplier_search_builder import SupplierSearchBuilder
from gws_reflex_main import FormDialogState, ReflexMainState

FormDialogCloseCallback = Callable[[ItemSheetDTO], Coroutine[Any, Any, None]]


class ItemSheetFormDialogState(FormDialogState, rx.State):
    """State management for the create/update item_sheet dialog functionality."""

    # ItemSheet being edited (None for create mode)
    _editing_item_sheet: ItemSheetDTO | None = None

    # Constant for "no supplier" option
    NO_SUPPLIER_VALUE: str = "__none__"

    # Form field default values
    form_name: str = ""
    form_code: str = ""
    form_description: str = ""
    form_supplier_id: str = "__none__"
    form_is_consumable: bool = True
    form_unit_type: str = UnitType.COUNT.value

    # In update mode, the unit_type is locked once the sheet already has items
    # (it is immutable then). Drives the disabled state of the selector.
    unit_type_locked: bool = False

    # Available suppliers for dropdown
    available_suppliers: list[SupplierDTO] = []

    _callback_after_close: FormDialogCloseCallback | None = None

    @rx.var
    def unit_type_options(self) -> list[dict[str, str]]:
        """Get unit type options for the select dropdown."""
        return [
            {"value": UnitType.COUNT.value, "label": "Count (units)"},
            {"value": UnitType.MASS.value, "label": "Mass (g, kg, mg)"},
            {"value": UnitType.VOLUME.value, "label": "Volume (L, mL, uL)"},
            {"value": UnitType.LENGTH.value, "label": "Length (m, cm, mm)"},
        ]

    async def _load_suppliers(self):
        """Load available suppliers for the dropdown."""
        main_state: ReflexMainState
        async with self:
            main_state = await self.get_state(ReflexMainState)

        with await main_state.authenticate_user():
            search_builder = SupplierSearchBuilder()
            suppliers = search_builder.search_all()
            self.available_suppliers = [supplier.to_dto() for supplier in suppliers]

    @rx.event
    async def open_create_dialog(self):
        """Open the dialog in create mode."""
        # Load suppliers for dropdown
        await self._load_suppliers()

        # Reset form fields to defaults
        self.form_name = ""
        self.form_code = ""
        self.form_description = ""
        self.form_supplier_id = self.NO_SUPPLIER_VALUE
        self.form_is_consumable = True
        self.form_unit_type = UnitType.COUNT.value
        self.unit_type_locked = False

        # Reset to create mode
        self.is_update_mode = False

        # Open the dialog
        self.dialog_opened = True

    @rx.event
    async def open_update_dialog(self, item_sheet: ItemSheetDTO):
        """Open the dialog in update mode with existing item_sheet data.

        Args:
            item_sheet: The item_sheet to update
        """
        # Load suppliers for dropdown
        await self._load_suppliers()

        # Store the item_sheet being edited
        self._editing_item_sheet = item_sheet

        # The unit_type is immutable once items reference the sheet: lock
        # the selector in that case.
        main_state: ReflexMainState
        async with self:
            main_state = await self.get_state(ReflexMainState)
        with await main_state.authenticate_user():
            self.unit_type_locked = ItemSheetService().has_items(item_sheet.id)

        # Initialize form fields with item_sheet data
        self.form_name = item_sheet.name
        self.form_code = item_sheet.code
        self.form_description = item_sheet.description or ""
        self.form_supplier_id = (
            item_sheet.default_supplier.id if item_sheet.default_supplier else self.NO_SUPPLIER_VALUE
        )
        self.form_is_consumable = item_sheet.is_consumable
        self.form_unit_type = item_sheet.unit_type.value

        # Mark as editing
        self.is_update_mode = True

        # Open the dialog
        await self.open_dialog()

    @rx.event
    def set_form_name(self, value: str):
        """Handle item sheet name change."""
        self.form_name = value

    @rx.event
    def set_form_code(self, value: str):
        """Handle code change (kept uppercase to match the stored format)."""
        self.form_code = value.upper()

    @rx.event
    async def suggest_code_from_name(self, name_value: str = ""):
        """Auto-suggest a code from the name when leaving the name field.

        Only fills in create mode and when the user hasn't already entered a
        code, so a manual entry is never overwritten.
        """
        if self.is_update_mode or self.form_code.strip():
            return
        name = (name_value or self.form_name).strip()
        if not name:
            return
        main_state: ReflexMainState
        async with self:
            main_state = await self.get_state(ReflexMainState)
        with await main_state.authenticate_user():
            self.form_code = ItemSheetService().suggest_code(name)

    @rx.event
    def set_supplier_id(self, value: str):
        """Handle supplier selection change."""
        self.form_supplier_id = value

    @rx.event
    def set_is_consumable(self, value: bool):
        """Handle consumable checkbox change."""
        self.form_is_consumable = value

    @rx.event
    def set_unit_type(self, value: str):
        """Handle unit type selection change."""
        self.form_unit_type = value

    def _validate_form_data(
        self, form_data: dict
    ) -> tuple[str, str | None, str | None, bool, UnitType]:
        """Validate and parse form data.

        Args:
            form_data: Dictionary containing form fields

        Returns:
            Tuple of (name, description, supplier_id, is_consumable, unit_type) if validation succeeds

        Raises:
            Exception: If validation fails
        """
        # Get values from form data
        name = form_data.get("name", "").strip()
        description = form_data.get("description", "").strip() or None

        # Get values from state (for select/checkbox components)
        # Convert __none__ back to None for the service
        supplier_id = (
            self.form_supplier_id
            if self.form_supplier_id and self.form_supplier_id != self.NO_SUPPLIER_VALUE
            else None
        )
        is_consumable = self.form_is_consumable
        unit_type = UnitType(self.form_unit_type)

        # Validate required fields
        if not name:
            raise Exception("ItemSheet name is required")

        return name, description, supplier_id, is_consumable, unit_type

    async def _create(self, form_data: dict):
        """Create a new item_sheet using the form data.

        Args:
            form_data: Dictionary containing form fields

        Yields:
            Reflex events (rx.toast)
        """
        # Validate and parse form data
        name, description, supplier_id, is_consumable, unit_type = self._validate_form_data(
            form_data
        )

        main_state: ReflexMainState
        async with self:
            main_state = await self.get_state(ReflexMainState)

        # Create the item_sheet
        item_sheet: ItemSheet
        with await main_state.authenticate_user():
            item_sheet_service = ItemSheetService()
            dto = CreateItemSheetDTO(
                name=name,
                code=form_data.get("code", "").strip(),
                description=description,
                supplier_id=supplier_id,
                is_consumable=is_consumable,
                unit_type=unit_type,
            )
            item_sheet = item_sheet_service.create_item_sheet(dto)

        # Show success toast
        yield rx.toast.success("ItemSheet created successfully")

        if self._callback_after_close:
            await self._callback_after_close(item_sheet.to_dto())

    async def _update(self, form_data: dict):
        """Update an existing item_sheet using the form data.

        Args:
            form_data: Dictionary containing form fields

        Yields:
            Reflex events (rx.toast)
        """
        # Validate and parse form data
        name, description, supplier_id, is_consumable, unit_type = self._validate_form_data(
            form_data
        )

        main_state: ReflexMainState
        async with self:
            main_state = await self.get_state(ReflexMainState)

        # Update the item_sheet
        item_sheet: ItemSheet
        with await main_state.authenticate_user():
            item_sheet_service = ItemSheetService()
            dto = UpdateItemSheetDTO(
                name=name,
                description=description,
                supplier_id=supplier_id,
                unit_type=unit_type,
            )
            item_sheet = item_sheet_service.update_item_sheet(self._editing_item_sheet.id, dto)

        # Show success toast
        yield rx.toast.success("ItemSheet updated successfully")

        if self._callback_after_close:
            await self._callback_after_close(item_sheet.to_dto())

    async def _clear_form_state(self):
        """Clear all form state after successful operation."""
        self._editing_item_sheet = None
        self.form_name = ""
        self.form_code = ""
        self.form_description = ""
        self.form_supplier_id = self.NO_SUPPLIER_VALUE
        self.form_is_consumable = True
        self.form_unit_type = UnitType.COUNT.value
        self.unit_type_locked = False
        self.is_update_mode = False

    def set_callback_after_close(self, callback: FormDialogCloseCallback | None):
        """Set the callback to invoke after the dialog closes successfully.

        This callback is called after a successful create or update operation,
        typically used to refresh a list or navigate to the created/updated item.

        Args:
            callback: The async callback function to invoke, or None to clear
        """
        self._callback_after_close = callback
