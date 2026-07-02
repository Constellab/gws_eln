"""Input side of the Transform dialog: the "add / edit an input" modal.

A Reflex state mixin (``mixin=True``) merged into ``TransformItemFormDialogState``.
It holds the input-draft fields, the input-dialog events, and the draft-only
computed vars. It reads the committed ``inputs`` list and the chosen
``transform_kind`` from the composing state — both resolved at runtime on the
single merged leaf state.
"""

from decimal import Decimal

import reflex as rx
from gws_eln.core.unit_type import UnitType
from gws_eln.items.item_dto import ItemDTO
from gws_eln.items.item_service import ItemService
from gws_eln.utils.units_converter import UnitConverter
from gws_reflex_base import ReflexAppException
from gws_reflex_main import ReflexMainState
from gws_reflex_main.gws_components import InputSearchResultDTO

from ..update_item_form_dialog.update_item_form_dialog_state import (
    UpdateItemFormDialogState,
)
from . import transform_builders
from .transform_models import (
    INPUT_ROLE_DILUENT,
    INPUT_ROLE_TARGET,
    TransformInputRow,
    TransformKind,
)


class TransformInputDialogMixin(rx.State, mixin=True):
    """Input-draft state and the "add / edit an input" dialog behavior."""

    # ---- input dialog (search for an existing item/instrument + quantity) ----
    input_dialog_opened: bool = False
    input_dialog_is_consumable: bool = True
    _editing_input_id: str = ""
    # Role assigned to the input being added/edited (dilute target/diluent; "" else).
    _pending_input_role: str = ""
    in_item_id: str = ""
    in_item_code: str = ""
    in_item_label: str = ""
    in_item_sheet_id: str = ""  # sheet id of the selected item (to fix split output sheet)
    in_item_sheet_code: str = ""  # sheet code of the selected item (output code preview)
    in_item_sheet_name: str = ""  # sheet name of the selected item (display)
    in_item_loc: str = ""  # location name of the selected item (display)
    in_item_available: str = ""  # available quantity of the selected item (display)
    in_item_qty_base: str = ""  # available quantity in base unit (raw, for validation)
    in_item_consumable: bool = True
    in_item_conc: str = ""  # the selected item's current concentration (raw)
    in_item_conc_unit: str = ""  # unit of in_item_conc ("" when none)
    in_unit_type: str = UnitType.COUNT.value
    in_qty: str = ""
    in_unit: str = UnitConverter.get_default_unit(UnitType.COUNT)

    # ------------------------------------------------------------------ vars

    @rx.var
    def input_has_sel(self) -> bool:
        return bool(self.in_item_id)

    @rx.var
    def input_is_instrument(self) -> bool:
        return bool(self.in_item_id) and not self.in_item_consumable

    @rx.var
    def input_is_consumable(self) -> bool:
        return bool(self.in_item_id) and self.in_item_consumable

    @rx.var
    def input_is_editing(self) -> bool:
        return bool(self._editing_input_id)

    @rx.var
    def input_has_concentration(self) -> bool:
        """Whether the selected input carries a concentration (for info display)."""
        return bool(self.in_item_id) and bool(self.in_item_conc)

    @rx.var
    def input_warn_no_concentration(self) -> bool:
        """Warn that the selected input has no concentration, when it matters.

        Concentrate's source and dilute's target are expected to carry a
        concentration (it drives the dilution audit). A missing concentration is
        allowed, but surfaced as a warning once the item is selected.
        """
        if not self.input_is_consumable or self.in_item_conc:
            return False
        if self.transform_kind == TransformKind.CONCENTRATE.value:
            return True
        if self.transform_kind == TransformKind.DILUTE.value:
            return self._pending_input_role == INPUT_ROLE_TARGET
        return False

    # ------------------------------------------------------------------ draft helpers

    def _reset_input_draft(self):
        """Fully reset the input draft: fields + editing/role state."""
        self._reset_input_fields()
        self._editing_input_id = ""
        self._pending_input_role = ""

    def _reset_input_fields(self):
        """Reset the input draft fields to their defaults (no item selected)."""
        self.in_item_id = ""
        self.in_item_code = ""
        self.in_item_label = ""
        self.in_item_sheet_id = ""
        self.in_item_sheet_code = ""
        self.in_item_sheet_name = ""
        self.in_item_loc = ""
        self.in_item_available = ""
        self.in_item_qty_base = ""
        self.in_item_consumable = True
        self.in_item_conc = ""
        self.in_item_conc_unit = ""
        self.in_unit_type = UnitType.COUNT.value
        self.in_qty = ""
        self.in_unit = UnitConverter.get_default_unit(UnitType.COUNT)

    def _set_input_from_item(self, item: ItemDTO):
        """Fill the input draft fields from a selected item."""
        self.in_item_id = item.id
        self.in_item_code = item.code
        self.in_item_label = item.label
        self.in_item_sheet_id = item.item_sheet.id
        self.in_item_sheet_code = item.item_sheet.code
        self.in_item_sheet_name = item.item_sheet.name
        self.in_item_loc = item.location.name
        self.in_item_available = item.pretty_quantity
        self.in_item_qty_base = str(item.quantity)
        self.in_item_consumable = item.item_sheet.is_consumable
        self.in_item_conc = (
            UnitConverter.format_number(item.concentration)
            if item.concentration is not None
            else ""
        )
        self.in_item_conc_unit = item.concentration_unit or ""
        self.in_unit_type = item.unit_type.value
        self.in_unit = UnitConverter.get_default_unit(item.unit_type)

    # ------------------------------------------------------------------ events

    @rx.event
    def open_consumable_input_dialog(self):
        """Open the dialog to add a consumable input."""
        self._reset_input_draft()
        self.input_dialog_is_consumable = True
        self.input_dialog_opened = True

    @rx.event
    def open_target_input_dialog(self):
        """Open the dialog to set the dilute target (the item being diluted)."""
        self._reset_input_draft()
        self._pending_input_role = INPUT_ROLE_TARGET
        self.input_dialog_is_consumable = True
        self.input_dialog_opened = True

    @rx.event
    def open_diluent_input_dialog(self):
        """Open the dialog to set the dilute diluent."""
        self._reset_input_draft()
        self._pending_input_role = INPUT_ROLE_DILUENT
        self.input_dialog_is_consumable = True
        self.input_dialog_opened = True

    @rx.event
    def edit_input(self, row_id: str):
        """Open the input dialog pre-filled to edit an existing input row."""
        row = next((r for r in self.inputs if r.id == row_id), None)
        if row is None:
            return
        self._editing_input_id = row_id
        self._pending_input_role = row.role
        self.in_item_id = row.item_id
        self.in_item_code = row.code
        self.in_item_label = row.label
        self.in_item_sheet_id = row.sheet_id
        self.in_item_sheet_code = row.sheet_code
        self.in_item_sheet_name = row.sheet_name
        self.in_item_loc = row.loc
        self.in_item_available = row.available
        self.in_item_qty_base = row.qty_base
        self.in_item_consumable = row.is_consumable
        self.in_item_conc = row.init_conc
        self.in_item_conc_unit = row.init_conc_unit
        self.in_unit_type = row.unit_type
        self.in_qty = row.qty
        self.in_unit = row.unit
        self.input_dialog_is_consumable = row.is_consumable
        self.input_dialog_opened = True

    @rx.event
    def open_instrument_input_dialog(self):
        """Open the dialog to add an instrument (non-consumable) input."""
        self._reset_input_draft()
        self.input_dialog_is_consumable = False
        self.input_dialog_opened = True

    @rx.event
    def select_input_item(self, event_data: dict):
        """Set the selected input item from the search component."""
        result = InputSearchResultDTO.from_json_object(event_data, ItemDTO)
        self._set_input_from_item(result.object)

    @rx.event
    def set_input_qty(self, value: str):
        self.in_qty = value

    @rx.event
    def set_input_unit(self, value: str):
        self.in_unit = value

    @rx.event
    async def add_concentration_to_input(self):
        """Open the update-item dialog to add a concentration to the selected input.

        Used when the source/target of a concentrate/dilute has no concentration:
        the user can set one on the fly without leaving the transform.
        """
        if not self.in_item_id:
            return
        main_state = await self.get_state(ReflexMainState)
        with await main_state.authenticate_user():
            item = ItemService().get_item(self.in_item_id).to_dto()
        update_state = await self.get_state(UpdateItemFormDialogState)
        update_state.set_callback_after_close(self._on_input_item_updated)
        await update_state.open_update_dialog(item)

    async def _on_input_item_updated(self, item: ItemDTO):
        """Refresh the selected input's concentration after an on-the-fly update."""
        if item.id != self.in_item_id:
            return
        self.in_item_conc = (
            UnitConverter.format_number(item.concentration)
            if item.concentration is not None
            else ""
        )
        self.in_item_conc_unit = item.concentration_unit or ""

    @rx.event
    def close_input_dialog(self):
        self.input_dialog_opened = False

    @rx.event
    def commit_input(self):
        """Validate the draft and add it (or update the edited row) in the list.

        The row id is the item id, so an item can only appear once as an input.
        """
        if not self.in_item_id:
            raise ReflexAppException("Please select an item first")
        if self.in_item_consumable and not self.in_qty.strip():
            raise ReflexAppException("Consumed quantity is required")
        if self.in_item_consumable:
            transform_builders.validate_consumed_quantity(
                self.in_qty,
                self.in_unit,
                self.in_unit_type,
                self.in_item_qty_base,
                self.in_item_available,
            )
        qty = self.in_qty.strip()
        if self.in_item_consumable:
            qty = UnitConverter.format_number(Decimal(qty))
        consumed = "instrument" if not self.in_item_consumable else f"{qty} {self.in_unit}"
        row = TransformInputRow(
            id=self.in_item_id,
            item_id=self.in_item_id,
            sheet_id=self.in_item_sheet_id,
            sheet_code=self.in_item_sheet_code,
            sheet_name=self.in_item_sheet_name,
            code=self.in_item_code,
            label=self.in_item_label,
            loc=self.in_item_loc,
            is_consumable=self.in_item_consumable,
            qty=qty,
            unit=self.in_unit,
            unit_type=self.in_unit_type,
            available=self.in_item_available,
            qty_base=self.in_item_qty_base,
            consumed=consumed,
            role=self._pending_input_role,
            init_conc=self.in_item_conc,
            init_conc_unit=self.in_item_conc_unit,
        )
        if self._editing_input_id:
            self.inputs = [row if r.id == self._editing_input_id else r for r in self.inputs]
        else:
            self.inputs = self.inputs + [row]
        self.input_dialog_opened = False
        self._reset_input_draft()

    @rx.event
    def remove_input_by_id(self, row_id: str):
        self.inputs = [row for row in self.inputs if row.id != row_id]
