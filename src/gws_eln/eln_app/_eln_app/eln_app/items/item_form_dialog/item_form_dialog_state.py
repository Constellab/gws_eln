from collections.abc import Callable, Coroutine
from datetime import date
from decimal import Decimal
from typing import Any

import reflex as rx
from gws_eln.core.unit_type import UnitType
from gws_eln.items.item import Item
from gws_eln.items.item_dto import CreateItemDTO, CreateItemsBulkDTO, ItemDTO
from gws_eln.items.item_service import ItemService
from gws_eln.items.item_sheet_dto import ItemSheetDTO
from gws_eln.items.item_sheet_service import ItemSheetService
from gws_eln.locations.location_dto import LocationDTO
from gws_eln.suppliers.supplier_dto import SupplierDTO
from gws_eln.utils.units_converter import UnitConverter
from gws_reflex_base import ReflexAppException
from gws_reflex_main import FormDialogState, ReflexMainState

from ...locations.core.location_select_state import LocationSelectState
from ...locations.location_form_dialog.location_form_dialog_state import LocationFormDialogState
from ...suppliers.core.supplier_select_state import SupplierSelectState
from ...suppliers.supplier_form_dialog.supplier_form_dialog_state import SupplierFormDialogState

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

    # Best-effort preview of the code the backend will assign at save
    # (computed when the sheet is loaded; indicative, see code_preview).
    _next_code: str = ""

    # Form field default values
    form_unit_type: str = UnitType.COUNT.value
    form_unit: str = UnitConverter.get_default_unit(UnitType.COUNT)
    form_quantity: str = ""
    form_concentration: str = ""
    form_concentration_unit: str = "__none__"
    form_batch_number: str = ""
    form_location_id: str = ""
    form_supplier_id: str = "__none__"
    form_expiry_date: str = ""
    form_label: str = ""
    form_storage_conditions: str = ""
    form_notes: str = ""

    # Non-consumable bulk creation: N units, one serial per unit.
    form_unit_count: int = 1
    form_serials: list[str] = [""]

    # Reusable "justify a divergence" capture: when a reference label is set (by a
    # caller such as the split output wizard), changing the label away from it
    # requires a reason. Empty reference disables the check entirely (plain create).
    _reference_label: str = ""
    form_override_reason: str = ""

    # Bumped to remount the supplier/location selects after an on-the-fly create,
    # so Radix picks up the freshly-added option as the selected value.
    supplier_select_key: int = 0
    location_select_key: int = 0

    _callback_after_close: FormDialogCloseCallback | None = None

    # Collect mode: when set, the dialog does NOT persist on save. Instead it
    # builds a single CreateItemDTO and hands it to this callback (used by the
    # Transform dialog, which creates the output item itself). Always uses the
    # single-item form, even for non-consumable sheets.
    _collect_callback: Callable[[CreateItemDTO], Coroutine[Any, Any, None]] | None = None

    @rx.var
    def collect_mode(self) -> bool:
        """Whether the dialog is collecting an item spec instead of persisting."""
        return self._collect_callback is not None

    @rx.var
    def label_changed(self) -> bool:
        """Whether the label diverges from the reference set by the caller.

        Drives the "justify the change" warning + reason field. Always False when
        no reference label was set (a plain create never asks for a reason).
        """
        if not self._reference_label:
            return False
        return self.form_label.strip() != self._reference_label.strip()

    @rx.var
    def item_sheet_name(self) -> str:
        """Get the name of the item_sheet for display."""
        if self._item_sheet:
            return self._item_sheet.name
        return ""

    @rx.var
    def is_consumable(self) -> bool:
        """Whether the item sheet is consumable.

        Serial numbers only apply to non-consumable (serialized) units, so the
        serial input is shown only when this is False.
        """
        if self._item_sheet:
            return self._item_sheet.is_consumable
        return True

    @rx.var
    def code_preview(self) -> str:
        """Best-effort preview of the auto-generated code (informative only).

        Shows the next code the backend is expected to assign (sheet prefix +
        MAX+1 increment), computed when the sheet is loaded. The authoritative
        code is still assigned at save, so under concurrency (or a split) the
        real value may differ. Falls back to the ``-XXXX`` pattern if the
        increment could not be computed.
        """
        if self._next_code:
            return self._next_code
        if self._item_sheet:
            return f"{self._item_sheet.code}-XXXX"
        return ""

    async def prepare_create_form(self, item_sheet_id: str, code_offset: int = 0):
        """Load the sheet and reset the form for create mode, WITHOUT opening the dialog.

        Split out from :meth:`open_create_dialog` so the form can be reused inside
        another container (e.g. the Transform output wizard) without popping this
        dialog's own modal.

        Args:
            item_sheet_id: The ID of the item_sheet for which to create a item (required)
            code_offset: Items of this sheet already staged by the caller but not yet
                saved, which will take a code before this one (see peek_next_item_code)
        """
        main_state: ReflexMainState
        async with self:
            main_state = await self.get_state(ReflexMainState)

        # Load the item_sheet
        with await main_state.authenticate_user():
            item_sheet_service = ItemSheetService()
            item_sheet = item_sheet_service.get_item_sheet(item_sheet_id)
            self._item_sheet = item_sheet.to_dto()
            # Guess the code the backend will assign, from existing item codes.
            self._next_code = ItemService().peek_next_item_code(item_sheet, offset=code_offset)

        # Normal (persisting) open: clear any leftover collect callback.
        self._collect_callback = None

        # Reset form fields to defaults
        self.form_label = ""
        # Reset the divergence check: a caller (e.g. split wizard) re-arms it after.
        self._reference_label = ""
        self.form_override_reason = ""
        self.form_quantity = ""
        self.form_concentration = ""
        self.form_batch_number = ""
        self.form_unit_count = 1
        self.form_serials = [""]
        # Prefill the storage condition with the sheet's default (editable override)
        self.form_storage_conditions = self._item_sheet.storage_conditions or ""
        self.form_notes = ""
        self.form_expiry_date = ""
        self.form_location_id = ""
        self.form_concentration_unit = self.NO_CONCENTRATION_VALUE

        # Set unit type and default unit from item_sheet
        self.form_unit_type = self._item_sheet.unit_type.value
        self.form_unit = UnitConverter.get_default_unit(self._item_sheet.unit_type)

        # Use item_sheet's default supplier if available
        if self._item_sheet.default_supplier:
            self.form_supplier_id = self._item_sheet.default_supplier.id
        else:
            self.form_supplier_id = self.NO_SUPPLIER_VALUE

        # Set to create mode
        self.is_update_mode = False

        # Refresh the option lists so suppliers/locations created in their own tabs
        # since the last load appear here (the select states cache after first load).
        supplier_select_state = await self.get_state(SupplierSelectState)
        await supplier_select_state.reload()
        location_select_state = await self.get_state(LocationSelectState)
        await location_select_state.reload()

    @rx.event
    async def open_create_dialog(self, item_sheet_id: str):
        """Open the dialog to create a item for the specified item_sheet.

        Args:
            item_sheet_id: The ID of the item_sheet for which to create a item (required)
        """
        await self.prepare_create_form(item_sheet_id)

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
    async def open_create_supplier_dialog(self):
        """Open the create-supplier dialog to add a supplier without leaving this form."""
        dialog_state = await self.get_state(SupplierFormDialogState)
        dialog_state.set_callback_after_close(self._on_supplier_created)
        await dialog_state.open_create_dialog()

    async def _on_supplier_created(self, supplier: SupplierDTO):
        """Refresh the supplier options and select the just-created supplier."""
        supplier_select_state = await self.get_state(SupplierSelectState)
        await supplier_select_state.reload()
        self.form_supplier_id = supplier.id
        self.supplier_select_key += 1

    @rx.event
    async def open_create_location_dialog(self):
        """Open the create-location dialog to add a location without leaving this form."""
        dialog_state = await self.get_state(LocationFormDialogState)
        dialog_state.set_callback_after_close(self._on_location_created)
        await dialog_state.open_create_dialog()

    async def _on_location_created(self, location: LocationDTO):
        """Refresh the location options and select the just-created location."""
        location_select_state = await self.get_state(LocationSelectState)
        await location_select_state.reload()
        self.form_location_id = location.id
        self.location_select_key += 1

    @rx.event
    def set_unit(self, value: str):
        """Handle unit selection change."""
        self.form_unit = value

    @rx.event
    def set_quantity(self, value: str):
        """Handle quantity input change."""
        self.form_quantity = value

    @rx.event
    def set_concentration(self, value: str):
        """Handle concentration input change."""
        self.form_concentration = value

    @rx.event
    def set_concentration_unit(self, value: str):
        """Handle concentration unit selection change."""
        self.form_concentration_unit = value

    @rx.event
    def set_expiry_date(self, value: str):
        """Handle expiry date change."""
        self.form_expiry_date = value

    @rx.event
    def set_label(self, value: str):
        """Track the label as it is typed, so ``label_changed`` reacts live."""
        self.form_label = value

    @rx.event
    def set_notes(self, value: str):
        """Track the notes as they are typed.

        Read from state (not form_data) at submit: an ``rx.text_area`` value is
        not reliably collected by the form's on_submit, so name-based capture
        silently dropped the notes.
        """
        self.form_notes = value

    @rx.event
    def set_override_reason(self, value: str):
        """Set the justification for a divergence flagged by ``label_changed``."""
        self.form_override_reason = value

    @rx.event
    def set_unit_count(self, value: str):
        """Set the number of non-consumable units to create and resize serials."""
        try:
            count = int(value)
        except (ValueError, TypeError):
            count = 1
        count = max(1, min(count, 100))
        self.form_unit_count = count

        serials = list(self.form_serials)
        if count > len(serials):
            serials += [""] * (count - len(serials))
        else:
            serials = serials[:count]
        self.form_serials = serials

    @rx.event
    def set_serial(self, index: int, value: str):
        """Set the serial number of the unit at the given index."""
        serials = list(self.form_serials)
        if 0 <= index < len(serials):
            serials[index] = value
            self.form_serials = serials

    def _parse_expiry_date(self) -> date | None:
        """Parse the expiry date from state (empty -> None)."""
        if not self.form_expiry_date:
            return None
        try:
            return date.fromisoformat(self.form_expiry_date)
        except ValueError as err:
            raise ReflexAppException("Invalid expiry date format") from err

    @staticmethod
    def _parse_quantity(quantity_str: str) -> Decimal:
        """Parse a required, strictly-positive quantity."""
        if not quantity_str:
            raise ReflexAppException("Quantity is required")
        try:
            quantity = Decimal(quantity_str)
        except (ValueError, ArithmeticError) as err:
            raise ReflexAppException("Invalid quantity value") from err
        if quantity <= 0:
            raise ReflexAppException("Quantity must be positive")
        return quantity

    @staticmethod
    def _parse_concentration(concentration_str: str) -> Decimal | None:
        """Parse an optional, strictly-positive concentration (empty -> None)."""
        if not concentration_str:
            return None
        try:
            concentration = Decimal(concentration_str)
        except (ValueError, ArithmeticError) as err:
            raise ReflexAppException("Invalid concentration value") from err
        if concentration <= 0:
            raise ReflexAppException("Concentration must be positive")
        return concentration

    def _validate_form_data(
        self, form_data: dict
    ) -> tuple[
        Decimal,
        str,
        Decimal | None,
        str,
        str | None,
        date | None,
        str,
        str | None,
        str | None,
    ]:
        """Validate and parse form data for a single (consumable) item.

        Returns the parsed (quantity, unit, concentration, location_id,
        supplier_id, expiry_date, label, storage_conditions, notes). Raises a
        ``ReflexAppException`` (surfaced as a toast) on the first invalid field.
        """
        quantity = self._parse_quantity(self.form_quantity.strip())
        concentration = self._parse_concentration(self.form_concentration.strip())
        expiry_date = self._parse_expiry_date()
        label = form_data.get("label", "").strip()
        if not label:
            raise ReflexAppException("Label is required")
        # Keep "" (not None) when cleared: field is pre-filled with the sheet default,
        # so empty means "no condition" and must not fall back to it. None = not provided.
        storage_conditions = form_data.get("storage_conditions", "").strip()
        # Notes come from state (on_change), not form_data: a text_area value is
        # not reliably submitted with the form.
        notes = self.form_notes.strip() or None

        # Values from state (select components)
        location_id = self.form_location_id
        if not location_id:
            raise ReflexAppException("Location is required")

        unit = self.form_unit
        if not unit:
            raise ReflexAppException("Unit is required")

        supplier_id = (
            self.form_supplier_id
            if self.form_supplier_id and self.form_supplier_id != self.NO_SUPPLIER_VALUE
            else None
        )

        return (
            quantity,
            unit,
            concentration,
            location_id,
            supplier_id,
            expiry_date,
            label,
            storage_conditions,
            notes,
        )

    async def _create(self, form_data: dict):
        """Create item(s) from the form.

        Consumable sheets create a single item (with a quantity); non-consumable
        sheets create N serialized units in one action (the bulk path).
        """
        if not self._item_sheet:
            raise ReflexAppException("Item sheet is required")

        # Collect mode: hand the spec to the caller, do not persist.
        if self._collect_callback is not None:
            async for event in self._collect_single(form_data):
                yield event
            return

        if self._item_sheet.is_consumable:
            async for event in self._create_single(form_data):
                yield event
        else:
            async for event in self._create_bulk(form_data):
                yield event

    async def _collect_single(self, form_data: dict):
        """Build a single CreateItemDTO and hand it to the collect callback.

        Used by the Transform dialog: the output item is created by the transform
        itself, so here we only validate + assemble the spec, never persist.
        """
        (
            quantity,
            unit,
            concentration,
            location_id,
            supplier_id,
            expiry_date,
            label,
            storage_conditions,
            notes,
        ) = self._validate_form_data(form_data)

        # A consumable output item must carry an expiry date (same rule as a
        # standalone create); collect mode always uses the consumable form.
        if expiry_date is None:
            raise ReflexAppException("Expiry date is required")

        concentration_unit = (
            self.form_concentration_unit
            if self.form_concentration_unit
            and self.form_concentration_unit != self.NO_CONCENTRATION_VALUE
            else None
        )

        # A label diverging from the caller's reference must carry a justification.
        override_reason = self.form_override_reason.strip()
        if self._reference_label and label != self._reference_label.strip() and not override_reason:
            raise ReflexAppException(
                "The label differs from the original: please give a reason for the change"
            )

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
            storage_conditions=storage_conditions,
            notes=notes,
            override_reason=override_reason or None,
        )

        yield rx.toast.success("Output item defined")

        if self._collect_callback:
            await self._collect_callback(dto)

    async def _create_single(self, form_data: dict):
        """Create one consumable item using the form data.

        Yields:
            Reflex events (rx.toast)
        """
        # Validate and parse form data
        (
            quantity,
            unit,
            concentration,
            location_id,
            supplier_id,
            expiry_date,
            label,
            storage_conditions,
            notes,
        ) = self._validate_form_data(form_data)

        # Expiry date is mandatory for a consumable item (this path is only
        # reached for consumable sheets).
        if expiry_date is None:
            raise ReflexAppException("Expiry date is required")

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

        # Supplier lot number for this delivery (optional, single lot).
        batch_number = form_data.get("batch_number", "").strip() or None

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
                batch_number=batch_number,
                location_id=location_id,
                supplier_id=supplier_id,
                expiry_date=expiry_date,
                label=label,
                storage_conditions=storage_conditions,
                notes=notes,
            )
            item = item_service.create_item(dto)

        # Show success toast
        yield rx.toast.success("Item sheet item created successfully")

        if self._callback_after_close:
            await self._callback_after_close(item.to_dto())

    async def _create_bulk(self, form_data: dict):
        """Create N serialized non-consumable units in one action.

        Yields:
            Reflex events (rx.toast)
        """
        # Shared fields (one value applied to every created unit)
        label = form_data.get("label", "").strip()
        if not label:
            raise ReflexAppException("Label is required")
        # Keep "" (not None) when cleared: field is pre-filled with the sheet default,
        # so empty means "no condition" and must not fall back to it. None = not provided.
        storage_conditions = form_data.get("storage_conditions", "").strip()
        # Notes come from state (on_change), not form_data: a text_area value is
        # not reliably submitted with the form.
        notes = self.form_notes.strip() or None
        expiry_date = self._parse_expiry_date()  # next due date: optional for non-consumables

        location_id = self.form_location_id
        if not location_id:
            raise ReflexAppException("Location is required")

        supplier_id = (
            self.form_supplier_id
            if self.form_supplier_id and self.form_supplier_id != self.NO_SUPPLIER_VALUE
            else None
        )

        # Supplier lot number, shared by every created unit (optional, single lot).
        batch_number = form_data.get("batch_number", "").strip() or None

        # One serial per unit (empty -> None for not-yet-serialized units)
        serial_numbers = [serial.strip() or None for serial in self.form_serials]
        if not serial_numbers:
            raise ReflexAppException("At least one unit is required")

        main_state: ReflexMainState
        async with self:
            main_state = await self.get_state(ReflexMainState)

        with await main_state.authenticate_user():
            item_service = ItemService()
            dto = CreateItemsBulkDTO(
                item_sheet_id=self._item_sheet.id,
                serial_numbers=serial_numbers,
                batch_number=batch_number,
                location_id=location_id,
                supplier_id=supplier_id,
                expiry_date=expiry_date,
                label=label,
                storage_conditions=storage_conditions,
                notes=notes,
            )
            items = item_service.create_items_bulk(dto)

        yield rx.toast.success(f"{len(items)} item(s) created successfully")

        if self._callback_after_close and items:
            await self._callback_after_close(items[0].to_dto())

    async def _update(self, form_data: dict):
        """Not implemented - update is handled by a separate dialog."""
        raise NotImplementedError("Update is not supported by this dialog")

    def set_collect_callback(self, callback):
        """Arm collect mode: on save, hand the CreateItemDTO to ``callback``
        instead of persisting. Call right after ``open_create_dialog``.
        """
        self._collect_callback = callback

    async def _clear_form_state(self):
        """Clear all form state after successful operation."""
        self._collect_callback = None
        self._item_sheet = None
        self._next_code = ""
        self.form_unit_type = UnitType.COUNT.value
        self.form_unit = UnitConverter.get_default_unit(UnitType.COUNT)
        self.form_quantity = ""
        self.form_concentration = ""
        self.form_concentration_unit = self.NO_CONCENTRATION_VALUE
        self.form_batch_number = ""
        self.form_location_id = ""
        self.form_supplier_id = self.NO_SUPPLIER_VALUE
        self.form_expiry_date = ""
        self.form_label = ""
        self.form_unit_count = 1
        self.form_serials = [""]
        self.form_storage_conditions = ""
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
