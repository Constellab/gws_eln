"""State management for the concentrate item form dialog."""

from collections.abc import Callable, Coroutine
from decimal import Decimal
from typing import Any

import reflex as rx
from gws_eln.core.unit_type import UnitType
from gws_eln.items.item_dto import ConcentrateItemDTO, ItemDTO
from gws_eln.items.item_service import ItemService
from gws_eln.utils.units_converter import UnitConverter
from gws_reflex_main import FormDialogState, ReflexMainState

from ...notes.note_linkable_dialog_state import NoteLinkableDialogState

FormDialogCloseCallback = Callable[[ItemDTO], Coroutine[Any, Any, None]]

# Sentinel for the "no concentration unit" option.
NO_CONCENTRATION_VALUE = "__none__"


class ConcentrateItemFormDialogState(NoteLinkableDialogState, FormDialogState, rx.State):
    """State for the concentrate item dialog.

    Concentrates a source item into a new, more concentrated item: the source is
    reduced by a drawn amount and a new output item is created on the source's
    own sheet at a user-entered (higher) concentration.
    """

    # Source item being concentrated (required input)
    _item: ItemDTO | None = None

    # Source's unit type (shared by the draw and output unit selectors - same sheet)
    form_unit_type: str = UnitType.COUNT.value
    form_draw_unit: str = UnitConverter.get_default_unit(UnitType.COUNT)
    form_output_unit: str = UnitConverter.get_default_unit(UnitType.COUNT)
    form_concentration_unit: str = NO_CONCENTRATION_VALUE

    _callback_after_close: FormDialogCloseCallback | None = None

    @rx.var
    def code(self) -> str:
        """Get the source item code for display."""
        if self._item:
            return self._item.code
        return ""

    @rx.var
    def current_quantity(self) -> str:
        """Get the source's current quantity for display."""
        if self._item:
            return self._item.pretty_quantity
        return ""

    @rx.var
    def current_concentration(self) -> str:
        """Get the source's current concentration for display."""
        if self._item and self._item.concentration is not None:
            return f"{self._item.concentration} {self._item.concentration_unit or ''}".strip()
        return "—"

    def _best_unit_for_quantity(self, quantity: Decimal, unit_type: UnitType) -> str:
        """Pick the most readable unit for a quantity (value between 1 and 1000)."""
        if quantity == 0:
            return UnitConverter.get_default_unit(unit_type)

        for unit in UnitConverter.UNIT_ORDER.get(unit_type, ["units"]):
            converted = abs(UnitConverter.from_base_unit(quantity, unit, unit_type))
            if Decimal("1") <= converted < Decimal("1000"):
                return unit

        return UnitConverter.get_default_unit(unit_type)

    def open_concentrate_dialog(self, item: ItemDTO):
        """Open the dialog to concentrate the specified item.

        Args:
            item: The source item to concentrate (required)
        """
        self._item = item
        self.form_unit_type = item.unit_type.value
        best_unit = self._best_unit_for_quantity(item.quantity, item.unit_type)
        self.form_draw_unit = best_unit
        self.form_output_unit = best_unit
        self.form_concentration_unit = NO_CONCENTRATION_VALUE

        self.is_update_mode = False
        self.dialog_opened = True

    @rx.event
    def set_draw_unit(self, value: str):
        """Handle the drawn-quantity unit selection change."""
        self.form_draw_unit = value

    @rx.event
    def set_output_unit(self, value: str):
        """Handle the output-quantity unit selection change."""
        self.form_output_unit = value

    @rx.event
    def set_concentration_unit(self, value: str):
        """Handle the output concentration unit selection change."""
        self.form_concentration_unit = value

    @staticmethod
    def _parse_quantity(raw: str, label: str) -> Decimal:
        """Parse a required positive quantity from a form string."""
        value = raw.strip()
        if not value:
            raise Exception(f"{label} is required")
        try:
            quantity = Decimal(value)
        except (ValueError, ArithmeticError):
            raise Exception(f"Invalid {label.lower()} value")
        if quantity <= 0:
            raise Exception(f"{label} must be positive")
        return quantity

    async def _create(self, form_data: dict):
        """Execute the concentrate using the form data.

        Yields:
            Reflex events (rx.toast)
        """
        if not self._item:
            raise Exception("Item is required")

        draw_quantity = self._parse_quantity(form_data.get("draw_quantity", ""), "Drawn quantity")
        output_quantity = self._parse_quantity(
            form_data.get("output_quantity", ""), "Output quantity"
        )

        # Optional output concentration (value + unit)
        output_concentration: Decimal | None = None
        concentration_str = form_data.get("output_concentration", "").strip()
        if concentration_str:
            try:
                output_concentration = Decimal(concentration_str)
            except (ValueError, ArithmeticError):
                raise Exception("Invalid output concentration value")

        concentration_unit = (
            self.form_concentration_unit
            if self.form_concentration_unit != NO_CONCENTRATION_VALUE
            else None
        )
        output_label = form_data.get("output_label", "").strip() or None
        notes = form_data.get("notes", "").strip() or None

        dto = ConcentrateItemDTO(
            quantity_contributed=draw_quantity,
            unit=self.form_draw_unit,
            output_quantity=output_quantity,
            output_unit=self.form_output_unit,
            output_concentration=output_concentration,
            output_concentration_unit=concentration_unit,
            output_label=output_label,
            notes=notes,
        )

        main_state: ReflexMainState
        async with self:
            main_state = await self.get_state(ReflexMainState)

        dto.note_id = self.note_dto_id
        with await main_state.authenticate_user():
            result = ItemService().concentrate_item(self._item.id, dto)
            linked_note = self._link_note_activity(result.activity.id)

        yield rx.toast.success("Item concentrated successfully")
        await self._after_note_link(linked_note)

        if self._callback_after_close:
            await self._callback_after_close(result.inputs[0].to_dto())

    async def _update(self, form_data: dict):
        """Not implemented - this dialog only concentrates (create)."""
        raise NotImplementedError("Update is not supported by this dialog")

    async def _clear_form_state(self):
        """Clear all form state after the dialog closes."""
        self._item = None
        self.form_unit_type = UnitType.COUNT.value
        self.form_draw_unit = UnitConverter.get_default_unit(UnitType.COUNT)
        self.form_output_unit = UnitConverter.get_default_unit(UnitType.COUNT)
        self.form_concentration_unit = NO_CONCENTRATION_VALUE
        self.clear_note_context()
        self.is_update_mode = False

    def set_callback_after_close(self, callback: FormDialogCloseCallback | None):
        """Set the callback invoked after a successful concentrate (e.g. to refresh).

        Args:
            callback: The async callback function to invoke, or None to clear
        """
        self._callback_after_close = callback
