"""Output side of the Transform dialog: the 2-step output wizard.

A Reflex state mixin (``mixin=True``) merged into ``TransformItemFormDialogState``.
It holds the output-wizard fields, its events, and the wizard-only computed vars.
The wizard delegates item/sheet creation to the reused ``ItemFormDialogState`` and
``ItemSheetFormDialogState`` (in *collect mode*), and appends the produced rows to
the composing state's ``outputs`` list — all resolved at runtime on the merged
leaf state.
"""

from dataclasses import replace

import reflex as rx
from gws_eln.items.item_dto import CreateItemDTO
from gws_eln.items.item_service import ItemService
from gws_eln.items.item_sheet_dto import ItemSheetDTO
from gws_eln.items.item_sheet_service import ItemSheetService
from gws_eln.locations.location_service import LocationService
from gws_eln.utils.units_converter import UnitConverter
from gws_reflex_base import ReflexAppException
from gws_reflex_main import ReflexMainState
from gws_reflex_main.gws_components import InputSearchResultDTO

from ...common.unit.concentration_method_components import NO_CONCENTRATION_METHOD_VALUE
from ...item_sheets.item_sheet_form_dialog.item_sheet_form_dialog_state import (
    ItemSheetFormDialogState,
)
from ..item_form_dialog.item_form_dialog_state import ItemFormDialogState
from .transform_models import (
    OutputStep,
    TransformInputRow,
    TransformKind,
    TransformOutputRow,
)


class TransformOutputWizardMixin(rx.State, mixin=True):
    """Output-wizard state and its 2-step (select/create sheet -> create item) behavior."""

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
    # Concentration method selected on the output step (concentrate audit). Held
    # as a controlled select value; the sentinel means "no method".
    concentration_method: str = NO_CONCENTRATION_METHOD_VALUE

    @rx.event
    def set_concentration_method(self, value: str):
        self.concentration_method = value

    # id (str) -> name, to display the location on committed output rows
    _loc_names: dict[str, str] = {}

    # ------------------------------------------------------------------ vars

    @rx.var
    def output_is_editing(self) -> bool:
        return bool(self._editing_output_id)

    @rx.var
    def output_step1_active(self) -> bool:
        return self.output_step == OutputStep.SHEET

    @rx.var
    def output_step2_active(self) -> bool:
        return self.output_step == OutputStep.ITEM

    # ------------------------------------------------------------------ events

    async def _load_locations(self):
        """Load locations (id -> name) for displaying committed output rows."""
        main_state = await self.get_state(ReflexMainState)
        with await main_state.authenticate_user():
            self._loc_names = {loc.id: loc.name for loc in LocationService().list_locations()}

    @rx.event
    async def open_output_wizard(self):
        """Open the output wizard.

        When the output sheet is fixed (split: children inherit the source's
        sheet), skip sheet selection and go straight to the item step. Otherwise
        start at step 1 (sheet selection).
        """
        self.output_create_sheet_mode = False
        self._editing_output_id = ""
        self.concentration_method = NO_CONCENTRATION_METHOD_VALUE
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
        self.concentration_method = row.concentration_method or NO_CONCENTRATION_METHOD_VALUE

        # Prepare the item form for the row's sheet, then prefill its fields and
        # arm collect mode (order matters: prepare clears the collect callback).
        item_state = await self.get_state(ItemFormDialogState)
        await item_state.prepare_create_form(
            row.sheet_id, code_offset=self._pending_code_offset(row.sheet_id)
        )
        item_state.form_label = row.label
        item_state.form_quantity = row.qty
        item_state.form_unit = row.unit
        item_state.form_concentration = row.conc
        item_state.form_concentration_unit = row.conc_unit or item_state.NO_CONCENTRATION_VALUE
        item_state.form_location_id = row.location_id
        item_state.form_override_reason = row.override_reason
        # Re-arm the split relabel check against the source's label.
        if self.transform_kind == TransformKind.SPLIT.value:
            source = self._fixed_output_source()
            if source is not None:
                item_state._reference_label = source.label
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

    def _output_source_input(self) -> TransformInputRow | None:
        """The committed input whose sheet the output shares (fixed source first).

        Used to suggest the output's label and unit when a transform consumes and
        produces the same item sheet (e.g. split, concentrate). Returns None when
        no input matches the output sheet.
        """
        source = self._fixed_output_source()
        if source is not None and source.sheet_id == self.out_sheet_id:
            return source
        return next((row for row in self.inputs if row.sheet_id == self.out_sheet_id), None)

    def _pending_code_offset(self, sheet_id: str) -> int:
        """How many staged outputs take a code on this sheet before the one being edited.

        The outputs are only saved when the transform is submitted, so the item form's
        peek must skip the codes the already-staged outputs of the same sheet will take.
        """
        offset = 0
        for row in self.outputs:
            if row.id and row.id == self._editing_output_id:
                break
            if row.sheet_id == sheet_id:
                offset += 1
        return offset

    async def _refresh_output_code_previews(self):
        """Renumber the staged outputs' code previews (base MAX+1 + rank within the sheet).

        Called after the output list changes so a removal or an edit doesn't leave the
        remaining rows on codes that shifted.
        """
        main_state = await self.get_state(ReflexMainState)
        with await main_state.authenticate_user():
            sheet_service = ItemSheetService()
            item_service = ItemService()
            sheets = {}
            ranks: dict[str, int] = {}
            rows = []
            for row in self.outputs:
                if row.sheet_id not in sheets:
                    sheets[row.sheet_id] = sheet_service.get_item_sheet(row.sheet_id)
                rank = ranks.get(row.sheet_id, 0)
                ranks[row.sheet_id] = rank + 1
                code = item_service.peek_next_item_code(sheets[row.sheet_id], offset=rank)
                rows.append(replace(row, code_preview=code))
            self.outputs = rows

    async def _advance_to_item_step(self):
        """Prepare the item form (collect mode) for the chosen sheet and go to step 2.

        Calls ItemFormDialogState.prepare_create_form (load + reset, no modal) THEN
        arms collect mode (order matters: prepare clears the collect callback).
        """
        item_state = await self.get_state(ItemFormDialogState)
        await item_state.prepare_create_form(
            self.out_sheet_id, code_offset=self._pending_code_offset(self.out_sheet_id)
        )
        # When the output shares an input's sheet (e.g. split, concentrate), prefill
        # the label and unit from that input as editable suggestions.
        source_input = self._output_source_input()
        if source_input is not None:
            item_state.form_label = source_input.label
            item_state.form_unit = source_input.unit
            # A split child that is relabelled away from its source must be justified.
            if self.transform_kind == TransformKind.SPLIT.value:
                item_state._reference_label = source_input.label
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
        # Output concentration (value + unit) is mandatory for concentrate/dilute.
        if self.needs_concentration and (
            not item_state.form_concentration.strip()
            or item_state.form_concentration_unit == item_state.NO_CONCENTRATION_VALUE
        ):
            raise ReflexAppException(
                f"{self.kind_title} requires an output concentration (value and unit)"
            )
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
        # Reuse the code the item form previewed, so the card shows the same value.
        item_state = await self.get_state(ItemFormDialogState)
        code_preview = item_state.code_preview
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
            conc=UnitConverter.format_number(dto.concentration)
            if dto.concentration is not None
            else "",
            conc_unit=dto.concentration_unit or "",
            code_preview=code_preview,
            produced=f"{UnitConverter.format_number(dto.quantity)} {dto.unit}",
            dilution_factor=self._pending_dilution_factor,
            concentration_method=(
                ""
                if self.concentration_method == NO_CONCENTRATION_METHOD_VALUE
                else self.concentration_method
            ),
            override_reason=dto.override_reason or "",
        )
        if self._editing_output_id:
            self.outputs = [row if r.id == self._editing_output_id else r for r in self.outputs]
        else:
            self.outputs = self.outputs + [row]
        self._editing_output_id = ""
        self._pending_dilution_factor = ""
        self.concentration_method = NO_CONCENTRATION_METHOD_VALUE
        self.output_dialog_opened = False
        self.output_step = OutputStep.SHEET
        await self._refresh_output_code_previews()

    @rx.event
    async def remove_output(self, index: int):
        if 0 <= index < len(self.outputs):
            del self.outputs[index]
            await self._refresh_output_code_previews()
