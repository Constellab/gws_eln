"""State management for the combine item form dialog."""

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import reflex as rx
from gws_eln.core.unit_type import UnitType
from gws_eln.items.item_dto import CombineInputDTO, CombineItemDTO, ItemDTO
from gws_eln.items.item_service import ItemService
from gws_eln.items.item_sheet_dto import ItemSheetDTO
from gws_eln.utils.units_converter import UnitConverter
from gws_reflex_main import FormDialogState, ReflexMainState
from gws_reflex_main.gws_components import InputSearchResultDTO

from ...notes.note_linkable_dialog_state import NoteLinkableDialogState
from ..core.instrument_picker_mixin import InstrumentPickerMixin

FormDialogCloseCallback = Callable[[ItemDTO], Coroutine[Any, Any, None]]

# Sentinel for the "no concentration unit" option (rx.select cannot use None).
NO_CONCENTRATION_VALUE = "__none__"

# A combine merges several items, so it needs at least this many ingredients.
MIN_INGREDIENTS = 2


def _item_display(item: ItemDTO) -> str:
    """Human-readable label for a selected ingredient item."""
    if item.label:
        return f"{item.code} ({item.label})"
    return item.code


@dataclass
class CombineIngredientRow:
    """One editable ingredient row in the combine form.

    Each ingredient is an existing item, drawn from by `quantity` `unit`.
    Ingredients may be of any dimension, so each row carries its own unit_type.
    Quantities are kept as strings while editing and parsed on submit.
    """

    item_id: str = ""
    item_display: str = ""
    quantity: str = ""
    unit: str = ""
    unit_type: str = UnitType.COUNT.value


class CombineItemFormDialogState(
    InstrumentPickerMixin, NoteLinkableDialogState, FormDialogState, rx.State
):
    """State for the combine item dialog.

    Combines 2..N ingredient items into one new output item. Each ingredient is
    reduced in place by its contribution; a brand new output item is created on
    the chosen output item sheet. The dialog is launched from a source item,
    which is pre-filled as the first ingredient.
    """

    # Item the dialog was launched from (pre-filled as the first ingredient)
    _seed_item: ItemDTO | None = None

    # Editable list of ingredient rows
    ingredients: list[CombineIngredientRow] = []

    # Output item definition
    output_sheet_id: str = ""
    output_sheet_name: str = ""
    output_unit_type: str = UnitType.COUNT.value
    output_unit: str = UnitConverter.get_default_unit(UnitType.COUNT)
    output_concentration_unit: str = NO_CONCENTRATION_VALUE

    _callback_after_close: FormDialogCloseCallback | None = None

    @rx.var
    def has_output_sheet(self) -> bool:
        """Whether an output item sheet has been selected."""
        return bool(self.output_sheet_id)

    @rx.var
    def can_remove_ingredient(self) -> bool:
        """Whether ingredient rows can be removed (a combine needs at least two)."""
        return len(self.ingredients) > MIN_INGREDIENTS

    def _best_unit_for_quantity(self, quantity: Decimal, unit_type: UnitType) -> str:
        """Pick the most readable unit for a quantity (value between 1 and 1000)."""
        if quantity == 0:
            return UnitConverter.get_default_unit(unit_type)

        for unit in UnitConverter.UNIT_ORDER.get(unit_type, ["units"]):
            converted = abs(UnitConverter.from_base_unit(quantity, unit, unit_type))
            if Decimal("1") <= converted < Decimal("1000"):
                return unit

        return UnitConverter.get_default_unit(unit_type)

    def open_combine_dialog(self, item: ItemDTO):
        """Open the dialog to combine, seeded with `item` as the first ingredient.

        Args:
            item: The source item the combine was launched from (required)
        """
        self._seed_item = item

        seed_row = CombineIngredientRow(
            item_id=item.id,
            item_display=_item_display(item),
            unit=self._best_unit_for_quantity(item.quantity, item.unit_type),
            unit_type=item.unit_type.value,
        )
        # Start with the seed + one empty row (a combine needs at least two)
        self.ingredients = [seed_row, CombineIngredientRow()]

        # Reset the output definition
        self.output_sheet_id = ""
        self.output_sheet_name = ""
        self.output_unit_type = UnitType.COUNT.value
        self.output_unit = UnitConverter.get_default_unit(UnitType.COUNT)
        self.output_concentration_unit = NO_CONCENTRATION_VALUE

        self.is_update_mode = False
        self.dialog_opened = True

    # ----- ingredient row handlers -----

    @rx.event
    def add_ingredient_row(self):
        """Add a new empty ingredient row."""
        self.ingredients.append(CombineIngredientRow())

    @rx.event
    def remove_ingredient_row(self, index: int):
        """Remove the ingredient row at the given index (keeps at least two)."""
        if len(self.ingredients) > MIN_INGREDIENTS:
            del self.ingredients[index]

    @rx.event
    def select_ingredient_item(self, index: int, event_data: dict):
        """Set the selected item for the ingredient row at the given index."""
        result = InputSearchResultDTO.from_json_object(event_data, ItemDTO)
        item = result.object
        row = self.ingredients[index]
        row.item_id = item.id
        row.item_display = _item_display(item)
        row.unit_type = item.unit_type.value
        row.unit = self._best_unit_for_quantity(item.quantity, item.unit_type)

    @rx.event
    def set_ingredient_quantity(self, index: int, value: str):
        """Update the quantity of the ingredient row at the given index."""
        self.ingredients[index].quantity = value

    @rx.event
    def set_ingredient_unit(self, index: int, value: str):
        """Update the unit of the ingredient row at the given index."""
        self.ingredients[index].unit = value

    # ----- output handlers -----

    @rx.event
    def select_output_sheet(self, event_data: dict):
        """Set the output item sheet (and derive its unit type/default unit)."""
        result = InputSearchResultDTO.from_json_object(event_data, ItemSheetDTO)
        sheet = result.object
        self.output_sheet_id = sheet.id
        self.output_sheet_name = sheet.name
        self.output_unit_type = sheet.unit_type.value
        self.output_unit = UnitConverter.get_default_unit(sheet.unit_type)

    @rx.event
    def set_output_unit(self, value: str):
        """Handle the output unit selection change."""
        self.output_unit = value

    @rx.event
    def set_output_concentration_unit(self, value: str):
        """Handle the output concentration unit selection change."""
        self.output_concentration_unit = value

    # ----- submit -----

    def _build_dto(self, form_data: dict) -> CombineItemDTO:
        """Validate the ingredient rows + output fields and build the DTO.

        Raises:
            Exception: If a required field is missing or a value is invalid.
        """
        # Collect the filled ingredient rows (rows with no item selected are skipped)
        inputs: list[CombineInputDTO] = []
        for position, row in enumerate(self.ingredients, start=1):
            if not row.item_id:
                continue

            quantity_str = row.quantity.strip()
            if not quantity_str:
                raise Exception(f"Ingredient #{position}: a quantity is required")
            try:
                quantity = Decimal(quantity_str)
            except (ValueError, ArithmeticError):
                raise Exception(f"Ingredient #{position}: invalid quantity value")
            if quantity <= 0:
                raise Exception(f"Ingredient #{position}: quantity must be positive")
            if not row.unit:
                raise Exception(f"Ingredient #{position}: a unit is required")

            inputs.append(CombineInputDTO(item_id=row.item_id, quantity=quantity, unit=row.unit))

        if len(inputs) < MIN_INGREDIENTS:
            raise Exception(f"A combine requires at least {MIN_INGREDIENTS} ingredients")

        # Output definition
        if not self.output_sheet_id:
            raise Exception("An output item sheet is required")

        output_quantity_str = form_data.get("output_quantity", "").strip()
        if not output_quantity_str:
            raise Exception("An output quantity is required")
        try:
            output_quantity = Decimal(output_quantity_str)
        except (ValueError, ArithmeticError):
            raise Exception("Invalid output quantity value")
        if output_quantity <= 0:
            raise Exception("Output quantity must be positive")

        if not self.output_unit:
            raise Exception("An output unit is required")

        # Optional output concentration (value + unit go together)
        output_concentration: Decimal | None = None
        concentration_str = form_data.get("output_concentration", "").strip()
        if concentration_str:
            try:
                output_concentration = Decimal(concentration_str)
            except (ValueError, ArithmeticError):
                raise Exception("Invalid output concentration value")
            if output_concentration <= 0:
                raise Exception("Output concentration must be positive")

        concentration_unit = (
            self.output_concentration_unit
            if self.output_concentration_unit != NO_CONCENTRATION_VALUE
            else None
        )

        output_label = form_data.get("output_label", "").strip() or None
        notes = form_data.get("notes", "").strip() or None

        return CombineItemDTO(
            inputs=inputs,
            output_item_sheet_id=self.output_sheet_id,
            output_quantity=output_quantity,
            output_unit=self.output_unit,
            output_concentration=output_concentration,
            output_concentration_unit=concentration_unit,
            instrument_item_ids=self.selected_instrument_ids,
            output_label=output_label,
            notes=notes,
        )

    async def _create(self, form_data: dict):
        """Execute the combine using the current ingredient rows and output fields.

        Yields:
            Reflex events (rx.toast)
        """
        dto = self._build_dto(form_data)
        dto.note_id = self.note_dto_id

        main_state: ReflexMainState
        async with self:
            main_state = await self.get_state(ReflexMainState)

        with await main_state.authenticate_user():
            result = ItemService().combine_items(dto)
            linked_note = self._link_note_activity(result.activity.id)

        yield rx.toast.success("Items combined successfully")
        await self._after_note_link(linked_note)

        if self._callback_after_close:
            # The first (seed) mutated ingredient drives the source-detail refresh
            await self._callback_after_close(result.inputs[0].to_dto())

    async def _update(self, form_data: dict):
        """Not implemented - this dialog only combines (create)."""
        raise NotImplementedError("Update is not supported by this dialog")

    async def _clear_form_state(self):
        """Clear all form state after the dialog closes."""
        self._seed_item = None
        self.ingredients = []
        self.output_sheet_id = ""
        self.output_sheet_name = ""
        self.output_unit_type = UnitType.COUNT.value
        self.output_unit = UnitConverter.get_default_unit(UnitType.COUNT)
        self.output_concentration_unit = NO_CONCENTRATION_VALUE
        self.clear_instruments()
        self.clear_note_context()
        self.is_update_mode = False

    def set_callback_after_close(self, callback: FormDialogCloseCallback | None):
        """Set the callback invoked after a successful combine (e.g. to refresh).

        Args:
            callback: The async callback function to invoke, or None to clear
        """
        self._callback_after_close = callback
