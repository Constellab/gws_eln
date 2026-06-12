"""State management for the split item form dialog."""

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import reflex as rx
from gws_eln.core.unit_type import UnitType
from gws_eln.items.item_dto import ItemDTO, SplitItemDTO, SplitOutputDTO
from gws_eln.items.item_service import ItemService
from gws_eln.utils.units_converter import UnitConverter
from gws_reflex_main import FormDialogState, ReflexMainState

FormDialogCloseCallback = Callable[[ItemDTO], Coroutine[Any, Any, None]]


@dataclass
class SplitOutputRow:
    """One editable output row in the split form.

    The output inherits the source item's sheet/unit_type/concentration; only
    these fields are user-entered per output. Quantities are kept as strings
    while editing and parsed/validated on submit.
    """

    item_number: str = ""
    quantity: str = ""
    unit: str = ""
    label: str = ""


class SplitItemFormDialogState(FormDialogState, rx.State):
    """State for the split item dialog.

    Splits one source item into 1..N new output items. The source quantity is
    reduced in place by the sum of the output quantities; each output is a new
    item inheriting the source's sheet/unit_type/concentration. The dialog
    manages a dynamic, editable list of output rows.
    """

    # Source item being split (required input)
    _item: ItemDTO | None = None

    # Source's unit type value (shared by every output row's unit selector)
    form_unit_type: str = UnitType.COUNT.value

    # Default unit pre-filled for each new output row (best scale for the source)
    form_default_unit: str = UnitConverter.get_default_unit(UnitType.COUNT)

    # Editable list of output rows
    outputs: list[SplitOutputRow] = []

    _callback_after_close: FormDialogCloseCallback | None = None

    @rx.var
    def item_number(self) -> str:
        """Get the source item number for display."""
        if self._item:
            return self._item.item_number
        return ""

    @rx.var
    def current_quantity(self) -> str:
        """Get the source's current quantity for display."""
        if self._item:
            return self._item.pretty_quantity
        return ""

    @rx.var
    def can_remove_row(self) -> bool:
        """Whether output rows can be removed (a split needs at least one)."""
        return len(self.outputs) > 1

    def _best_unit_for_quantity(self, quantity: Decimal, unit_type: UnitType) -> str:
        """Pick the most readable unit for a quantity (value between 1 and 1000)."""
        if quantity == 0:
            return UnitConverter.get_default_unit(unit_type)

        for unit in UnitConverter.UNIT_ORDER.get(unit_type, ["units"]):
            converted = abs(UnitConverter.from_base_unit(quantity, unit, unit_type))
            if Decimal("1") <= converted < Decimal("1000"):
                return unit

        return UnitConverter.get_default_unit(unit_type)

    def open_split_dialog(self, item: ItemDTO):
        """Open the dialog to split the specified item.

        Args:
            item: The source item to split (required)
        """
        self._item = item
        self.form_unit_type = item.unit_type.value
        self.form_default_unit = self._best_unit_for_quantity(item.quantity, item.unit_type)

        # Start with a single empty output row
        self.outputs = [SplitOutputRow(unit=self.form_default_unit)]

        self.is_update_mode = False
        self.dialog_opened = True

    @rx.event
    def add_row(self):
        """Add a new empty output row."""
        self.outputs.append(SplitOutputRow(unit=self.form_default_unit))

    @rx.event
    def remove_row(self, index: int):
        """Remove the output row at the given index (keeps at least one)."""
        if len(self.outputs) > 1:
            del self.outputs[index]

    @rx.event
    def set_row_item_number(self, index: int, value: str):
        """Update the item number of the output row at the given index."""
        self.outputs[index].item_number = value

    @rx.event
    def set_row_quantity(self, index: int, value: str):
        """Update the quantity of the output row at the given index."""
        self.outputs[index].quantity = value

    @rx.event
    def set_row_unit(self, index: int, value: str):
        """Update the unit of the output row at the given index."""
        self.outputs[index].unit = value

    @rx.event
    def set_row_label(self, index: int, value: str):
        """Update the label of the output row at the given index."""
        self.outputs[index].label = value

    def _build_outputs_dto(self) -> list[SplitOutputDTO]:
        """Validate the output rows and build the SplitOutputDTO list.

        Raises:
            Exception: If any row is missing a required field or has a bad value.
        """
        outputs: list[SplitOutputDTO] = []
        for position, row in enumerate(self.outputs, start=1):
            item_number = row.item_number.strip()
            if not item_number:
                raise Exception(f"Output #{position}: an item number is required")

            quantity_str = row.quantity.strip()
            if not quantity_str:
                raise Exception(f"Output #{position}: a quantity is required")
            try:
                quantity = Decimal(quantity_str)
            except (ValueError, ArithmeticError):
                raise Exception(f"Output #{position}: invalid quantity value")
            if quantity <= 0:
                raise Exception(f"Output #{position}: quantity must be positive")

            if not row.unit:
                raise Exception(f"Output #{position}: a unit is required")

            outputs.append(
                SplitOutputDTO(
                    item_number=item_number,
                    quantity=quantity,
                    unit=row.unit,
                    label=row.label.strip() or None,
                )
            )
        return outputs

    async def _create(self, form_data: dict):
        """Execute the split using the current output rows.

        Args:
            form_data: Form fields (only `notes` is read from the HTML form)

        Yields:
            Reflex events (rx.toast)
        """
        if not self._item:
            raise Exception("Item is required")

        outputs_dto = self._build_outputs_dto()
        notes = form_data.get("notes", "").strip() or None
        dto = SplitItemDTO(outputs=outputs_dto, notes=notes)

        main_state: ReflexMainState
        async with self:
            main_state = await self.get_state(ReflexMainState)

        with await main_state.authenticate_user():
            result = ItemService().split_item(self._item.id, dto)

        yield rx.toast.success(f"Item split into {len(outputs_dto)} new item(s)")

        if self._callback_after_close:
            # The mutated source item (reduced quantity) drives the detail refresh
            await self._callback_after_close(result.inputs[0].to_dto())

    async def _update(self, form_data: dict):
        """Not implemented - this dialog only splits (create)."""
        raise NotImplementedError("Update is not supported by this dialog")

    async def _clear_form_state(self):
        """Clear all form state after the dialog closes."""
        self._item = None
        self.form_unit_type = UnitType.COUNT.value
        self.form_default_unit = UnitConverter.get_default_unit(UnitType.COUNT)
        self.outputs = []
        self.is_update_mode = False

    def set_callback_after_close(self, callback: FormDialogCloseCallback | None):
        """Set the callback invoked after a successful split (e.g. to refresh).

        Args:
            callback: The async callback function to invoke, or None to clear
        """
        self._callback_after_close = callback
