"""State management for the generic Transform dialog (N inputs -> M outputs).

Inputs (existing item/instrument + quantity) are built in place. Outputs delegate
to the existing dialogs: the ItemSheet creation dialog for a new sheet, and the
item creation dialog in *collect mode* (it returns a CreateItemDTO instead of
persisting) so the Transform itself creates the output items on save.
"""

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum, IntEnum
from typing import Any

import reflex as rx
from gws_eln.core.concentration_unit import (
    convert_concentration,
    same_concentration_family,
)
from gws_eln.core.unit_type import UnitType
from gws_eln.items.item_dto import (
    CombineInputDTO,
    CombineItemDTO,
    ConcentrateItemDTO,
    CreateItemDTO,
    DiluteItemDTO,
    ItemDTO,
    SplitItemDTO,
    SplitOutputDTO,
    TransformInputDTO,
    TransformItemsDTO,
    TransformOutputDTO,
)
from gws_eln.items.item_service import ItemService
from gws_eln.items.item_sheet_dto import ItemSheetDTO
from gws_eln.locations.location_service import LocationService
from gws_eln.utils.units_converter import UnitConverter
from gws_reflex_base import ReflexAppException
from gws_reflex_main import ConfirmDialogState, FormDialogState, ReflexMainState
from gws_reflex_main.gws_components import InputSearchResultDTO

from ...item_sheets.item_sheet_form_dialog.item_sheet_form_dialog_state import (
    ItemSheetFormDialogState,
)
from ...notes.note_linkable_dialog_state import NoteLinkableDialogState
from ..item_form_dialog.item_form_dialog_state import ItemFormDialogState
from ..update_item_form_dialog.update_item_form_dialog_state import (
    UpdateItemFormDialogState,
)

FormDialogCloseCallback = Callable[[ItemDTO], Coroutine[Any, Any, None]]


class OutputStep(IntEnum):
    """Steps of the output wizard (serializes as int for the frontend)."""

    SHEET = 1  # choose or create the destination ItemSheet
    ITEM = 2  # create the produced item


class TransformKind(Enum):
    """The transformation chosen in the wizard's first step.

    Values match ``ActivityType`` for the specialised kinds; ``CUSTOM`` is the
    generic N->M transform (``ActivityType.TRANSFORM``).
    """

    SPLIT = "split"
    COMBINE = "combine"
    DILUTE = "dilute"
    CONCENTRATE = "concentrate"
    CUSTOM = "transform"


class TransformStep(IntEnum):
    """Steps of the transform wizard (serializes as int for the frontend)."""

    CHOOSE = 1  # pick the transformation kind
    BUILD = 2  # build the inputs/outputs


# A combine needs at least this many consumable ingredients.
COMBINE_MIN_INPUTS = 2

# A split must produce at least this many outputs (1 output would be a move/aliquot).
SPLIT_MIN_OUTPUTS = 2

# Roles for the two consumable inputs of a dilute (target is the item being diluted).
INPUT_ROLE_TARGET = "target"
INPUT_ROLE_DILUENT = "diluent"


@dataclass
class TransformInputRow:
    """One committed input (item or instrument) consumed by the transform."""

    id: str
    item_id: str
    sheet_id: str  # the item's sheet id (used to fix the output sheet for split)
    sheet_code: str  # the item's sheet code (for the output code preview)
    sheet_name: str
    code: str
    label: str
    loc: str
    is_consumable: bool
    qty: str  # raw, for DTO (empty for instruments)
    unit: str  # raw, for DTO
    unit_type: str  # for re-populating the edit form
    available: str  # available quantity (display), for re-populating the edit form
    qty_base: str  # available quantity in base unit, for edit-time validation
    consumed: str  # display, e.g. "4 units" or "instrument"
    role: str = ""  # dilute role: INPUT_ROLE_TARGET / INPUT_ROLE_DILUENT ("" otherwise)
    init_conc: str = ""  # the item's current concentration (for concentrate/dilute checks)
    init_conc_unit: str = ""  # unit of init_conc ("" when none)


@dataclass
class TransformOutputRow:
    """One committed output (new item) produced by the transform."""

    id: str
    sheet_id: str
    sheet_code: str
    sheet_name: str
    label: str
    loc: str
    qty: str  # raw, for DTO
    unit: str  # raw, for DTO
    location_id: str  # raw, for DTO
    conc: str  # raw, for DTO
    conc_unit: str  # raw, for DTO ("" when none)
    code_preview: str
    produced: str  # display
    dilution_factor: str = ""  # raw, for DTO (concentrate/dilute audit; "" when none)


class TransformItemFormDialogState(NoteLinkableDialogState, FormDialogState, rx.State):
    """State for the generic Transform dialog (N inputs -> M outputs)."""

    # Committed rows
    inputs: list[TransformInputRow] = []
    outputs: list[TransformOutputRow] = []

    # ---- wizard: choose a transformation kind, then build it ----
    transform_kind: str = ""  # TransformKind value once picked
    transform_step: TransformStep = TransformStep.CHOOSE
    # Launching item, seeded as the first input only after the kind is picked.
    _seed_item: ItemDTO | None = None

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

    # ---- output wizard (2-step dialog: select/create sheet -> create item) ----
    # The selected (or freshly created) destination sheet for the current output.
    out_sheet_id: str = ""
    out_sheet_code: str = ""
    out_sheet_name: str = ""
    output_dialog_opened: bool = False
    output_step: OutputStep = OutputStep.SHEET
    output_create_sheet_mode: bool = False  # step 1 morphed into the sheet creation form
    _editing_output_id: str = ""  # set when editing an existing output row
    # Dilution factor entered on the output step (concentrate/dilute audit), read
    # back when the output item is collected.
    _pending_dilution_factor: str = ""

    # id (str) -> name, to display the location on committed output rows
    _loc_names: dict[str, str] = {}

    _callback_after_close: FormDialogCloseCallback | None = None

    # ------------------------------------------------------------------ vars

    @rx.var
    def step_is_choose(self) -> bool:
        return self.transform_step == TransformStep.CHOOSE

    @rx.var
    def step_is_build(self) -> bool:
        return self.transform_step == TransformStep.BUILD

    @rx.var
    def kind_is_custom(self) -> bool:
        return self.transform_kind == TransformKind.CUSTOM.value

    @rx.var
    def kind_is_dilute(self) -> bool:
        return self.transform_kind == TransformKind.DILUTE.value

    @rx.var
    def kind_is_concentrate(self) -> bool:
        return self.transform_kind == TransformKind.CONCENTRATE.value

    @rx.var
    def dilute_target_inputs(self) -> list[TransformInputRow]:
        return [row for row in self.inputs if row.role == INPUT_ROLE_TARGET]

    @rx.var
    def dilute_diluent_inputs(self) -> list[TransformInputRow]:
        return [row for row in self.inputs if row.role == INPUT_ROLE_DILUENT]

    @rx.var
    def kind_title(self) -> str:
        return {
            TransformKind.SPLIT.value: "Split",
            TransformKind.COMBINE.value: "Combine",
            TransformKind.DILUTE.value: "Dilute",
            TransformKind.CONCENTRATE.value: "Concentrate",
            TransformKind.CUSTOM.value: "Custom transform",
        }.get(self.transform_kind, "Transform")

    @rx.var
    def can_add_consumable_input(self) -> bool:
        """Whether another consumable input may be added for the current kind.

        Split and concentrate take exactly one consumable input (the source);
        other kinds are unconstrained for now.
        """
        if self.transform_kind in (
            TransformKind.SPLIT.value,
            TransformKind.CONCENTRATE.value,
        ):
            return len(self.consumable_inputs) < 1
        return True

    @rx.var
    def output_sheet_is_fixed(self) -> bool:
        """Whether outputs are forced onto the source's sheet (no sheet picker).

        True for split/concentrate (source's sheet) and dilute (target's sheet).
        """
        return self.transform_kind in (
            TransformKind.SPLIT.value,
            TransformKind.CONCENTRATE.value,
            TransformKind.DILUTE.value,
        )

    @rx.var
    def needs_concentration(self) -> bool:
        """Whether the output step should expose the dilution-factor audit field.

        True for concentrate and dilute (store-only concentration audit).
        """
        return self.transform_kind in (
            TransformKind.CONCENTRATE.value,
            TransformKind.DILUTE.value,
        )

    @rx.var
    def output_concentration_warning(self) -> str:
        """Live warning when the committed output concentration goes the wrong way.

        Concentrate should raise the concentration, dilute should lower it. Surfaced
        in the builder so the user notices before saving (the save-time check still
        enforces it). Empty string when there is nothing to warn about.
        """
        if not self.needs_concentration or not self.outputs:
            return ""
        output = self.outputs[0]
        # Missing output concentration (value + unit) is required for concentrate/dilute.
        if not output.conc or not output.conc_unit:
            return f"{self.kind_title} requires an output concentration (value and unit)."
        source = self._fixed_output_source()
        # No source concentration, or different families → can't compare the
        # direction; accept it and leave it to the user (no warning).
        if (
            source is None
            or not source.init_conc
            or not source.init_conc_unit
            or not same_concentration_family(source.init_conc_unit, output.conc_unit)
        ):
            return ""
        initial = convert_concentration(source.init_conc, source.init_conc_unit, output.conc_unit)
        final = Decimal(output.conc)
        direction_wrong = (
            self.transform_kind == TransformKind.CONCENTRATE.value and final <= initial
        ) or (self.transform_kind == TransformKind.DILUTE.value and final >= initial)
        if direction_wrong:
            return (
                "Concentrate should increase the concentration "
                "(output is not higher than the source's)."
                if self.transform_kind == TransformKind.CONCENTRATE.value
                else "Dilute should decrease the concentration "
                "(output is not lower than the target's)."
            )
        return ""

    @rx.var
    def split_quantity_warning(self) -> str:
        """Live warning when a split's total output quantity exceeds the source's.

        Non-blocking: the user can still save (a confirmation is asked at save
        time). Empty when it does not apply (not a split, no source or no outputs
        yet, or the quantities are consistent / not parseable).
        """
        is_split = self.transform_kind == TransformKind.SPLIT.value
        source = next((row for row in self.inputs if row.is_consumable), None)
        if not is_split or not source or not self.outputs:
            return ""

        unit_type = UnitType(source.unit_type)
        try:
            source_base = UnitConverter.to_base_unit(Decimal(source.qty), source.unit, unit_type)
            total_base = Decimal(0)
            for row in self.outputs:
                total_base += UnitConverter.to_base_unit(Decimal(row.qty), row.unit, unit_type)
        except Exception:  # noqa: BLE001 - a computed var must never raise
            return ""
        if total_base <= source_base:
            return ""
        return (
            f"The total output quantity "
            f"({UnitConverter.format_value(total_base, unit_type)}) exceeds the "
            f"source quantity ({UnitConverter.format_value(source_base, unit_type)})."
        )

    @rx.var
    def can_add_output(self) -> bool:
        """Whether another output may be added for the current kind.

        Split needs a source consumable before producing children (outputs are
        otherwise unbounded); combine and concentrate produce exactly one output
        (concentrate also needs its source first); other kinds are unconstrained.
        """
        if self.transform_kind == TransformKind.SPLIT.value:
            return len(self.consumable_inputs) >= 1
        if self.transform_kind == TransformKind.COMBINE.value:
            return len(self.outputs) < 1
        if self.transform_kind == TransformKind.CONCENTRATE.value:
            return len(self.consumable_inputs) >= 1 and len(self.outputs) < 1
        if self.transform_kind == TransformKind.DILUTE.value:
            # Need the target (it fixes the output sheet); exactly one output.
            has_target = any(row.role == INPUT_ROLE_TARGET for row in self.inputs)
            return has_target and len(self.outputs) < 1
        return True

    @rx.var
    def input_count(self) -> int:
        return len(self.inputs)

    @rx.var
    def consumable_inputs(self) -> list[TransformInputRow]:
        return [row for row in self.inputs if row.is_consumable]

    @rx.var
    def instrument_inputs(self) -> list[TransformInputRow]:
        return [row for row in self.inputs if not row.is_consumable]

    @rx.var
    def output_count(self) -> int:
        return len(self.outputs)

    @rx.var
    def outputs_empty_hint(self) -> bool:
        return len(self.outputs) == 0

    @rx.var
    def output_is_editing(self) -> bool:
        return bool(self._editing_output_id)

    @rx.var
    def output_step1_active(self) -> bool:
        return self.output_step == OutputStep.SHEET

    @rx.var
    def output_step2_active(self) -> bool:
        return self.output_step == OutputStep.ITEM

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

    @rx.var
    def has_any(self) -> bool:
        return len(self.inputs) > 0 or len(self.outputs) > 0

    @rx.var
    def summary_str(self) -> str:
        return f"{len(self.inputs)} input(s) · {len(self.outputs)} output(s)"

    # ------------------------------------------------------------------ open

    async def _load_locations(self):
        """Load locations (id -> name) for displaying committed output rows."""
        main_state = await self.get_state(ReflexMainState)
        with await main_state.authenticate_user():
            self._loc_names = {loc.id: loc.name for loc in LocationService().list_locations()}

    @rx.event
    async def open_transform_dialog(self, item: ItemDTO):
        """Open the wizard at the kind-selection step.

        The launching item is stashed and only seeded as the first input once the
        user picks a transformation kind (see :meth:`select_transform_kind`).

        :param item: The item the transform was launched from
        :type item: ItemDTO
        """
        self._reset_state()
        await self._load_locations()
        self.is_update_mode = False
        self._seed_item = item
        self.transform_step = TransformStep.CHOOSE
        self.dialog_opened = True

    @rx.event
    def select_transform_kind(self, kind: str):
        """Pick the transformation kind and move to the build step.

        If the dialog was launched from an item, seed it as the first input and
        open the quantity modal straight away.
        """
        self.transform_kind = kind
        self.transform_step = TransformStep.BUILD
        if self._seed_item is not None:
            item = self._seed_item
            self._set_input_from_item(item)
            self.input_dialog_is_consumable = item.item_sheet.is_consumable
            self._editing_input_id = ""
            # For dilute the launching item is the target being diluted.
            self._pending_input_role = (
                INPUT_ROLE_TARGET if kind == TransformKind.DILUTE.value else ""
            )
            self.input_dialog_opened = True
            self._seed_item = None

    @rx.event
    def back_to_chooser(self):
        """Return to the kind-selection step."""
        self.transform_step = TransformStep.CHOOSE

    # ------------------------------------------------------------------ inputs

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
        self.in_item_conc = str(item.concentration) if item.concentration is not None else ""
        self.in_item_conc_unit = item.concentration_unit or ""
        self.in_unit_type = item.unit_type.value
        self.in_unit = UnitConverter.get_default_unit(item.unit_type)

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
        self.in_item_conc = str(item.concentration) if item.concentration is not None else ""
        self.in_item_conc_unit = item.concentration_unit or ""

    @rx.event
    def close_input_dialog(self):
        self.input_dialog_opened = False

    def _validate_input_quantity(self):
        """Validate the draft consumed quantity against the item's availability.

        :raises Exception: if the quantity is invalid, non-positive, or exceeds
            the available quantity of the selected item.
        """
        try:
            qty = Decimal(self.in_qty.strip())
        except (ArithmeticError, ValueError):
            raise ReflexAppException("Invalid quantity") from None
        if qty <= 0:
            raise ReflexAppException("Quantity must be positive")
        base_qty = UnitConverter.to_base_unit(qty, self.in_unit, UnitType(self.in_unit_type))
        if base_qty > Decimal(self.in_item_qty_base):
            raise ReflexAppException(
                f"Consumed quantity ({self.in_qty.strip()} {self.in_unit}) "
                f"exceeds the available quantity ({self.in_item_available})"
            )

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
            self._validate_input_quantity()
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

    # ------------------------------------------------------------------ outputs

    def _fixed_output_source(self) -> TransformInputRow | None:
        """The input whose sheet the output inherits when the sheet is fixed.

        Dilute uses the target; split/concentrate use the (single) consumable.
        """
        if self.transform_kind == TransformKind.DILUTE.value:
            return next((r for r in self.inputs if r.role == INPUT_ROLE_TARGET), None)
        return next((r for r in self.inputs if r.is_consumable), None)

    @rx.event
    async def open_output_wizard(self):
        """Open the output wizard.

        When the output sheet is fixed (split: children inherit the source's
        sheet), skip sheet selection and go straight to the item step. Otherwise
        start at step 1 (sheet selection).
        """
        self.output_create_sheet_mode = False
        self._editing_output_id = ""
        if self.output_sheet_is_fixed:
            source = self._fixed_output_source()
            if source is None:
                return
            self.out_sheet_id = source.sheet_id
            self.out_sheet_code = source.sheet_code
            self.out_sheet_name = source.sheet_name
            self.output_dialog_opened = True
            await self._advance_to_item_step()
            return
        self.out_sheet_id = ""
        self.out_sheet_code = ""
        self.out_sheet_name = ""
        self.output_step = OutputStep.SHEET
        self.output_dialog_opened = True

    @rx.event
    async def edit_output(self, row_id: str):
        """Open the output wizard pre-filled to edit an existing output row."""
        row = next((r for r in self.outputs if r.id == row_id), None)
        if row is None:
            return
        self._editing_output_id = row_id
        self.out_sheet_id = row.sheet_id
        self.out_sheet_code = row.sheet_code
        self.out_sheet_name = row.sheet_name
        self._pending_dilution_factor = row.dilution_factor

        # Prepare the item form for the row's sheet, then prefill its fields and
        # arm collect mode (order matters: prepare clears the collect callback).
        item_state = await self.get_state(ItemFormDialogState)
        await item_state.prepare_create_form(row.sheet_id)
        item_state.form_label = row.label
        item_state.form_quantity = row.qty
        item_state.form_unit = row.unit
        item_state.form_concentration = row.conc
        item_state.form_concentration_unit = row.conc_unit or item_state.NO_CONCENTRATION_VALUE
        item_state.form_location_id = row.location_id
        item_state.set_collect_callback(self._on_output_item_collected)

        self.output_create_sheet_mode = False
        self.output_step = OutputStep.ITEM
        self.output_dialog_opened = True

    @rx.event
    def close_output_wizard(self):
        """Close the output wizard and reset its step/mode."""
        self.output_dialog_opened = False
        self.output_step = OutputStep.SHEET
        self.output_create_sheet_mode = False
        self._editing_output_id = ""

    @rx.event
    async def select_output_sheet(self, event_data: dict):
        """Select an existing sheet (step 1) and jump straight to item creation."""
        result = InputSearchResultDTO.from_json_object(event_data, ItemSheetDTO)
        sheet = result.object
        self.out_sheet_id = sheet.id
        self.out_sheet_code = sheet.code
        self.out_sheet_name = sheet.name
        await self._advance_to_item_step()

    @rx.event
    async def output_enter_create_sheet(self):
        """Step 1 morphs into the ItemSheet creation form (still step 1).

        Prepares the ItemSheet form (load + reset) WITHOUT opening its own modal.
        """
        self.output_create_sheet_mode = True
        sheet_state = await self.get_state(ItemSheetFormDialogState)
        await sheet_state.prepare_create_form(force_consumable=True)
        sheet_state.set_callback_after_close(self._on_sheet_created)

    @rx.event
    def output_back_to_select_sheet(self):
        """Back from the create-sheet form to plain sheet selection (still step 1)."""
        self.output_create_sheet_mode = False

    @rx.event
    def output_back_to_sheet_step(self):
        """Back from step 2 to step 1 (sheet selection)."""
        self.output_step = OutputStep.SHEET

    async def _advance_to_item_step(self):
        """Prepare the item form (collect mode) for the chosen sheet and go to step 2.

        Calls ItemFormDialogState.prepare_create_form (load + reset, no modal) THEN
        arms collect mode (order matters: prepare clears the collect callback).
        """
        item_state = await self.get_state(ItemFormDialogState)
        await item_state.prepare_create_form(self.out_sheet_id)
        item_state.set_collect_callback(self._on_output_item_collected)
        self.output_create_sheet_mode = False
        self.output_step = OutputStep.ITEM

    @rx.event
    async def submit_create_sheet(self, form_data: dict):
        """Step 1 (create mode): create the sheet via the reused ItemSheet form.

        On success ItemSheetFormDialogState._create fires `_on_sheet_created`, which
        selects the new sheet and auto-advances to step 2.
        """
        sheet_state = await self.get_state(ItemSheetFormDialogState)
        async for event in sheet_state._create(form_data):
            yield event

    @rx.event
    async def submit_collect_item(self, form_data: dict):
        """Step 2: build the output item via the reused item form (collect mode).

        ItemFormDialogState._create routes to `_collect_single` (collect mode), which
        fires `_on_output_item_collected` to append the output row and close the wizard.
        """
        # Stash the (optional) dilution factor before collecting: the item form's
        # CreateItemDTO does not carry it, so the callback reads it back from here.
        self._pending_dilution_factor = form_data.get("dilution_factor", "").strip()
        item_state = await self.get_state(ItemFormDialogState)
        async for event in item_state._create(form_data):
            yield event

    async def _on_sheet_created(self, sheet: ItemSheetDTO):
        """Callback after a new ItemSheet is created: select it and advance to step 2."""
        self.out_sheet_id = sheet.id
        self.out_sheet_code = sheet.code
        self.out_sheet_name = sheet.name
        await self._advance_to_item_step()

    async def _on_output_item_collected(self, dto: CreateItemDTO):
        """Callback from the item form (collect mode): add/replace the output row, close wizard."""
        loc_name = self._loc_names.get(dto.location_id, "—") if dto.location_id else "—"
        row_id = self._editing_output_id or f"out{len(self.outputs)}_{self.out_sheet_code}"
        row = TransformOutputRow(
            id=row_id,
            sheet_id=dto.item_sheet_id,
            sheet_code=self.out_sheet_code,
            sheet_name=self.out_sheet_name,
            label=dto.label,
            loc=loc_name,
            qty=UnitConverter.format_number(dto.quantity),
            unit=dto.unit,
            location_id=dto.location_id or "",
            conc=str(dto.concentration) if dto.concentration is not None else "",
            conc_unit=dto.concentration_unit or "",
            code_preview=f"{self.out_sheet_code}-{date.today().year}-XXXX",
            produced=f"{UnitConverter.format_number(dto.quantity)} {dto.unit}",
            dilution_factor=self._pending_dilution_factor,
        )
        if self._editing_output_id:
            self.outputs = [row if r.id == self._editing_output_id else r for r in self.outputs]
        else:
            self.outputs = self.outputs + [row]
        self._editing_output_id = ""
        self._pending_dilution_factor = ""
        self.output_dialog_opened = False
        self.output_step = OutputStep.SHEET

    @rx.event
    def remove_output(self, index: int):
        if 0 <= index < len(self.outputs):
            del self.outputs[index]

    # ------------------------------------------------------------------ global

    @rx.event
    def clear_all(self):
        self.inputs = []
        self.outputs = []
        self.input_dialog_opened = False

    @rx.event(background=True)  # type: ignore
    async def submit_form(self, form_data: dict):
        """Save the transform.

        For a split, if the total output quantity exceeds the source quantity
        (a non-blocking condition), ask the user to confirm before saving instead
        of submitting directly.
        """
        async with self:
            over_quantity = bool(self.split_quantity_warning)
            if over_quantity:
                confirm_state = await self.get_state(ConfirmDialogState)
                confirm_state.open_dialog(
                    title="Output quantity exceeds input",
                    content=f"{self.split_quantity_warning} Do you want to save anyway?",
                    action=lambda: self._run_submit(form_data),
                )
        if over_quantity:
            return
        async for event in self._run_submit(form_data):
            yield event

    async def _run_submit(self, form_data: dict):
        """Run the create/update flow (loading + persist + close on success).

        Shared by the direct save and the over-quantity confirmation path.
        """
        async with self:
            self.is_loading = True
            is_update = self.is_update_mode
        try:
            if is_update:
                async for event in self._update(form_data):
                    yield event
            else:
                async for event in self._create(form_data):
                    yield event
            async with self:
                await self.close_dialog()
        finally:
            async with self:
                self.is_loading = False

    async def _create(self, form_data: dict):
        """Route to the dedicated service for the chosen transformation kind."""
        if self.transform_kind == TransformKind.SPLIT.value:
            async for event in self._create_split(form_data):
                yield event
            return
        if self.transform_kind == TransformKind.COMBINE.value:
            async for event in self._create_combine(form_data):
                yield event
            return
        if self.transform_kind == TransformKind.CONCENTRATE.value:
            async for event in self._create_concentrate(form_data):
                yield event
            return
        if self.transform_kind == TransformKind.DILUTE.value:
            async for event in self._create_dilute(form_data):
                yield event
            return
        async for event in self._create_custom(form_data):
            yield event

    async def _create_split(self, form_data: dict):
        """Split the single source item into the listed output items.

        Children inherit the source's sheet/unit/concentration; only quantity,
        unit, location and label are user-entered per output.
        """
        source = next((row for row in self.inputs if row.is_consumable), None)
        if source is None:
            raise ReflexAppException("Split needs a source consumable item")
        if len(self.outputs) < SPLIT_MIN_OUTPUTS:
            raise ReflexAppException(f"Split needs at least {SPLIT_MIN_OUTPUTS} outputs")

        outputs = [
            SplitOutputDTO(
                quantity=Decimal(row.qty),
                unit=row.unit,
                location_id=row.location_id or None,
                label=row.label or None,
            )
            for row in self.outputs
        ]
        instrument_ids = [row.item_id for row in self.inputs if not row.is_consumable]
        notes = form_data.get("notes", "").strip() or None
        dto = SplitItemDTO(
            outputs=outputs,
            instrument_item_ids=instrument_ids,
            notes=notes,
            note_id=self.note_dto_id,
        )

        main_state: ReflexMainState
        async with self:
            main_state = await self.get_state(ReflexMainState)

        with await main_state.authenticate_user():
            result = ItemService().split_item(source.item_id, dto)
            linked_note = self._link_note_activity(result.activity.id)

        yield rx.toast.success(f"Split saved — {len(outputs)} item(s) created")
        await self._after_note_link(linked_note)

        if self._callback_after_close and result.inputs:
            await self._callback_after_close(result.inputs[0].to_dto())

    async def _create_combine(self, form_data: dict):
        """Combine 2..N consumable ingredients into the single output item.

        Each ingredient is reduced in place by its contribution; the output is a
        new item on its chosen sheet (concentration user-entered or null).
        """
        consumables = [row for row in self.inputs if row.is_consumable]
        if len(consumables) < COMBINE_MIN_INPUTS:
            raise ReflexAppException(f"Combine needs at least {COMBINE_MIN_INPUTS} consumable inputs")
        if len(self.outputs) != 1:
            raise ReflexAppException("Combine produces exactly one output")
        output = self.outputs[0]

        inputs = [
            CombineInputDTO(item_id=row.item_id, quantity=Decimal(row.qty), unit=row.unit)
            for row in consumables
        ]
        instrument_ids = [row.item_id for row in self.inputs if not row.is_consumable]
        notes = form_data.get("notes", "").strip() or None
        dto = CombineItemDTO(
            inputs=inputs,
            output_item_sheet_id=output.sheet_id,
            output_quantity=Decimal(output.qty),
            output_unit=output.unit,
            instrument_item_ids=instrument_ids,
            output_location_id=output.location_id or None,
            output_label=output.label or None,
            output_concentration=Decimal(output.conc) if output.conc else None,
            output_concentration_unit=output.conc_unit or None,
            notes=notes,
            note_id=self.note_dto_id,
        )

        main_state: ReflexMainState
        async with self:
            main_state = await self.get_state(ReflexMainState)

        with await main_state.authenticate_user():
            result = ItemService().combine_items(dto)
            linked_note = self._link_note_activity(result.activity.id)

        yield rx.toast.success(f"Combine saved — {len(inputs)} input(s) → 1 item")
        await self._after_note_link(linked_note)

        if self._callback_after_close and result.inputs:
            await self._callback_after_close(result.inputs[0].to_dto())

    def _validate_concentration_change(
        self,
        init_conc: str,
        init_unit: str,
        out_conc: str,
        out_unit: str,
        must_increase: bool,
        kind_label: str,
    ):
        """Enforce the output concentration and its direction for concentrate/dilute.

        The output concentration (value + unit) is mandatory. The direction is
        checked only when it can be compared meaningfully: the source/target
        already carries a concentration AND both values are in the **same family**
        (converted via :func:`convert_concentration`) — then concentrate must raise
        it and dilute must lower it. A cross-family output unit is accepted as-is:
        the direction can't be inferred across families, so it is left to the user.

        :raises Exception: if the output concentration is missing, or if it changes
            in the wrong direction while in the same family as the source's.
        """
        # Output concentration is mandatory for concentrate/dilute.
        if not out_conc or not out_unit:
            raise ReflexAppException(f"{kind_label} requires an output concentration (value and unit)")
        # Without a source concentration, or across different families, the
        # direction can't be compared — accept it and leave it to the user.
        if not init_conc or not init_unit:
            return
        if not same_concentration_family(init_unit, out_unit):
            return
        # Compare in the output's unit (same family → lossless conversion).
        initial = convert_concentration(init_conc, init_unit, out_unit)
        final = Decimal(out_conc)
        if must_increase and final <= initial:
            raise ReflexAppException(
                "Concentrate must increase the concentration "
                "(output concentration must be higher than the source's)"
            )
        if not must_increase and final >= initial:
            raise ReflexAppException(
                "Dilute must decrease the concentration "
                "(output concentration must be lower than the target's)"
            )

    async def _create_concentrate(self, form_data: dict):
        """Concentrate the single source item into one more concentrated item.

        The source is reduced in place by its contributed quantity; the output is
        a new item on the source's own sheet at the user-entered concentration.
        """
        source = next((row for row in self.inputs if row.is_consumable), None)
        if source is None or not source.qty:
            raise ReflexAppException("Concentrate needs a source consumable item with a quantity")
        if len(self.outputs) != 1:
            raise ReflexAppException("Concentrate produces exactly one output")
        output = self.outputs[0]
        self._validate_concentration_change(
            source.init_conc,
            source.init_conc_unit,
            output.conc,
            output.conc_unit,
            must_increase=True,
            kind_label="Concentrate",
        )

        instrument_ids = [row.item_id for row in self.inputs if not row.is_consumable]
        notes = form_data.get("notes", "").strip() or None
        dto = ConcentrateItemDTO(
            quantity_contributed=Decimal(source.qty),
            unit=source.unit,
            output_quantity=Decimal(output.qty),
            output_unit=output.unit,
            output_concentration=Decimal(output.conc) if output.conc else None,
            output_concentration_unit=output.conc_unit or None,
            dilution_factor=Decimal(output.dilution_factor) if output.dilution_factor else None,
            instrument_item_ids=instrument_ids,
            output_location_id=output.location_id or None,
            output_label=output.label or None,
            notes=notes,
            note_id=self.note_dto_id,
        )

        main_state: ReflexMainState
        async with self:
            main_state = await self.get_state(ReflexMainState)

        with await main_state.authenticate_user():
            result = ItemService().concentrate_item(source.item_id, dto)
            linked_note = self._link_note_activity(result.activity.id)

        yield rx.toast.success("Concentrate saved — 1 item created")
        await self._after_note_link(linked_note)

        if self._callback_after_close and result.inputs:
            await self._callback_after_close(result.inputs[0].to_dto())

    async def _create_dilute(self, form_data: dict):
        """Dilute the target with the diluent into one less-concentrated item.

        BOTH the target and the diluent are reduced in place; the output is a new
        item on the target's own sheet at the user-entered concentration.
        """
        target = next((row for row in self.inputs if row.role == INPUT_ROLE_TARGET), None)
        diluent = next((row for row in self.inputs if row.role == INPUT_ROLE_DILUENT), None)
        if target is None or not target.qty:
            raise ReflexAppException("Dilute needs a target consumable item with a quantity")
        if diluent is None or not diluent.qty:
            raise ReflexAppException("Dilute needs a diluent consumable item with a quantity")
        if len(self.outputs) != 1:
            raise ReflexAppException("Dilute produces exactly one output")
        output = self.outputs[0]
        self._validate_concentration_change(
            target.init_conc,
            target.init_conc_unit,
            output.conc,
            output.conc_unit,
            must_increase=False,
            kind_label="Dilute",
        )

        instrument_ids = [row.item_id for row in self.inputs if not row.is_consumable]
        notes = form_data.get("notes", "").strip() or None
        dto = DiluteItemDTO(
            quantity_contributed=Decimal(target.qty),
            unit=target.unit,
            diluent_item_id=diluent.item_id,
            diluent_quantity_contributed=Decimal(diluent.qty),
            diluent_unit=diluent.unit,
            output_quantity=Decimal(output.qty),
            output_unit=output.unit,
            output_concentration=Decimal(output.conc) if output.conc else None,
            output_concentration_unit=output.conc_unit or None,
            dilution_factor=Decimal(output.dilution_factor) if output.dilution_factor else None,
            instrument_item_ids=instrument_ids,
            output_location_id=output.location_id or None,
            output_label=output.label or None,
            notes=notes,
            note_id=self.note_dto_id,
        )

        main_state: ReflexMainState
        async with self:
            main_state = await self.get_state(ReflexMainState)

        with await main_state.authenticate_user():
            result = ItemService().dilute_item(target.item_id, dto)
            linked_note = self._link_note_activity(result.activity.id)

        yield rx.toast.success("Dilute saved — 1 item created")
        await self._after_note_link(linked_note)

        if self._callback_after_close and result.inputs:
            await self._callback_after_close(result.inputs[0].to_dto())

    async def _create_custom(self, form_data: dict):
        """Build the TransformItemsDTO and call the generic transform service."""
        if not self.inputs or not self.outputs:
            return

        input_dtos = [
            TransformInputDTO(
                item_id=row.item_id,
                quantity=Decimal(row.qty) if (row.is_consumable and row.qty) else None,
                unit=row.unit if row.is_consumable else None,
            )
            for row in self.inputs
        ]
        output_dtos = [
            TransformOutputDTO(
                output_item_sheet_id=row.sheet_id,
                quantity=Decimal(row.qty),
                unit=row.unit,
                location_id=row.location_id or None,
                label=row.label,
                concentration=Decimal(row.conc) if row.conc else None,
                concentration_unit=row.conc_unit or None,
            )
            for row in self.outputs
        ]
        notes = form_data.get("notes", "").strip() or None
        dto = TransformItemsDTO(
            inputs=input_dtos, outputs=output_dtos, notes=notes, note_id=self.note_dto_id
        )

        main_state: ReflexMainState
        async with self:
            main_state = await self.get_state(ReflexMainState)

        with await main_state.authenticate_user():
            result = ItemService().transform_items(dto)
            linked_note = self._link_note_activity(result.activity.id)

        yield rx.toast.success(
            f"Transform saved — {len(input_dtos)} input(s) → {len(output_dtos)} output(s)"
        )
        await self._after_note_link(linked_note)

        if self._callback_after_close and result.inputs:
            await self._callback_after_close(result.inputs[0].to_dto())

    async def _update(self, form_data: dict):
        """Not implemented - this dialog only creates transforms."""
        raise NotImplementedError("Update is not supported by this dialog")

    def _reset_state(self):
        self.inputs = []
        self.outputs = []
        self.transform_kind = ""
        self.transform_step = TransformStep.CHOOSE
        self._seed_item = None
        self._editing_input_id = ""
        self.input_dialog_opened = False
        self.out_sheet_id = ""
        self.out_sheet_code = ""
        self.out_sheet_name = ""
        self.output_dialog_opened = False
        self.output_step = OutputStep.SHEET
        self.output_create_sheet_mode = False
        self._editing_output_id = ""

    async def _clear_form_state(self):
        self._reset_state()
        self.clear_note_context()
        self.is_update_mode = False

    def set_callback_after_close(self, callback: FormDialogCloseCallback | None):
        """Set the callback invoked after a successful transform (e.g. to refresh)."""
        self._callback_after_close = callback
