"""State for the generic Transform dialog (N inputs -> M outputs).

This leaf state composes two mixins that hold the two sub-dialogs:
- :class:`TransformInputDialogMixin` — the "add / edit an input" modal.
- :class:`TransformOutputWizardMixin` — the 2-step output wizard.

They are merged into this single state, so the input/output events read the
committed ``inputs``/``outputs`` and the chosen ``transform_kind`` directly. This
state keeps the committed rows, the kind/step wizard, the shared computed vars,
and the save flow (which builds the per-kind DTOs via :mod:`transform_builders`).
"""

from collections.abc import Callable, Coroutine
from decimal import Decimal
from typing import Any

import reflex as rx
from gws_eln.core.concentration_unit import (
    convert_concentration,
    same_concentration_family,
)
from gws_eln.core.unit_type import UnitType
from gws_eln.items.item_dto import ItemDTO
from gws_eln.items.item_service import ItemService
from gws_eln.utils.units_converter import UnitConverter
from gws_reflex_base import ReflexAppException
from gws_reflex_main import ConfirmDialogState, FormDialogState, ReflexMainState

from ...notes.note_linkable_dialog_state import NoteLinkableDialogState
from . import transform_builders
from .transform_input_dialog_mixin import TransformInputDialogMixin
from .transform_models import (
    INPUT_ROLE_DILUENT,
    INPUT_ROLE_TARGET,
    OutputStep,
    TransformInputRow,
    TransformKind,
    TransformOutputRow,
    TransformStep,
)
from .transform_output_wizard_mixin import TransformOutputWizardMixin

FormDialogCloseCallback = Callable[[ItemDTO], Coroutine[Any, Any, None]]


class TransformItemFormDialogState(
    TransformInputDialogMixin,
    TransformOutputWizardMixin,
    NoteLinkableDialogState,
    FormDialogState,
    rx.State,
):
    """State for the generic Transform dialog (N inputs -> M outputs)."""

    # Committed rows
    inputs: list[TransformInputRow] = []
    outputs: list[TransformOutputRow] = []

    # ---- wizard: choose a transformation kind, then build it ----
    transform_kind: str = ""  # TransformKind value once picked
    transform_step: TransformStep = TransformStep.CHOOSE
    # Launching item, seeded as the first input only after the kind is picked.
    _seed_item: ItemDTO | None = None
    # Launching item's unit type, kept for the whole dialog (unlike _seed_item,
    # which is cleared once seeded) so the chooser can gate volume-only kinds.
    _launch_unit_type: str = ""

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
    def seed_is_volume(self) -> bool:
        """Whether the launching item is measured in a volume unit.

        Dilute and concentrate only make sense for solutions with a volume unit,
        so those two activities are hidden in the chooser for any other unit type.
        """
        # Empty until a launching item is set
        if not self._launch_unit_type:
            return False
        return UnitType(self._launch_unit_type).is_volume()

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
    def kind_subtitle(self) -> str:
        """One-line description of the chosen kind, shown as the dialog subtitle
        (same text as the chooser cards)."""
        return {
            TransformKind.SPLIT.value: "One source item → several new items.",
            TransformKind.COMBINE.value: "Several items → one new item.",
            TransformKind.DILUTE.value: "Target + diluent → one diluted item.",
            TransformKind.CONCENTRATE.value: "One item → one more concentrated item.",
            TransformKind.CUSTOM.value: "Any number of inputs → any number of outputs.",
        }.get(self.transform_kind, "")

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
    def quantity_warning(self) -> str:
        """Live warning when a total output quantity exceeds the total input quantity.

        Non-blocking: the user can still save (a confirmation is asked at save
        time). Empty when it does not apply (no inputs or no outputs
        yet, or the quantities are consistent / not parseable).
        """
        consumable_inputs = [row for row in self.inputs if row.is_consumable]
        if not consumable_inputs or not self.outputs:
            return ""

        try:
            unit_type = UnitType(consumable_inputs[0].unit_type)
            total_input_quantity = transform_builders.sum_base_quantity(
                consumable_inputs, unit_type
            )
            total_output_quantity = transform_builders.sum_base_quantity(self.outputs, unit_type)
        except Exception:  # noqa: BLE001 - a computed var must never raise
            return ""

        if total_output_quantity <= total_input_quantity:
            return ""
        return (
            f"The total output quantity "
            f"({UnitConverter.format_value(total_output_quantity, unit_type)}) exceeds the "
            f"total input quantity ({UnitConverter.format_value(total_input_quantity, unit_type)})."
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
    def has_any(self) -> bool:
        return len(self.inputs) > 0 or len(self.outputs) > 0

    @rx.var
    def summary_str(self) -> str:
        return f"{len(self.inputs)} input(s) · {len(self.outputs)} output(s)"

    # ------------------------------------------------------------------ open / kind

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
        self._launch_unit_type = item.unit_type.value
        self.transform_step = TransformStep.CHOOSE
        self.dialog_opened = True

    @rx.event
    def select_transform_kind(self, kind: str):
        """Pick the transformation kind and move to the build step.

        If the dialog was launched from an item, seed it as the first input
        already selected but without a quantity: the row shows an "Add"
        affordance so the user sets the consumed quantity when they choose to,
        rather than being forced through a quantity modal up front.
        """
        # Dilute/concentrate are solution-only: guard against a non-volume seed
        # (the chooser already hides these cards, this is defense in depth).
        if (
            kind in (TransformKind.DILUTE.value, TransformKind.CONCENTRATE.value)
            and not self.seed_is_volume
        ):
            raise ReflexAppException(
                "Dilute and concentrate are only available for items measured in a volume unit"
            )
        self.transform_kind = kind
        self.transform_step = TransformStep.BUILD
        if self._seed_item is not None:
            # For dilute the launching item is the target being diluted.
            role = INPUT_ROLE_TARGET if kind == TransformKind.DILUTE.value else ""
            self._append_seed_input(self._seed_item, role)
            self._seed_item = None

    @rx.event
    def back_to_chooser(self):
        """Return to the kind-selection step."""
        self.transform_step = TransformStep.CHOOSE

    def _fixed_output_source(self) -> TransformInputRow | None:
        """The input whose sheet the output inherits when the sheet is fixed.

        Dilute uses the target; split/concentrate use the (single) consumable.
        Used by both the output wizard and ``output_concentration_warning``.
        """
        if self.transform_kind == TransformKind.DILUTE.value:
            return next((r for r in self.inputs if r.role == INPUT_ROLE_TARGET), None)
        return next((r for r in self.inputs if r.is_consumable), None)

    # ------------------------------------------------------------------ save / global

    @rx.event
    def clear_all(self):
        self.inputs = []
        self.outputs = []
        self.input_dialog_opened = False

    @rx.event(background=True)  # type: ignore
    async def submit_form(self, form_data: dict):
        """Save the transform.

        If the total output quantity exceeds the total input quantity (a
        non-blocking condition), ask the user to confirm before saving instead
        of submitting directly.
        """
        async with self:
            over_quantity = bool(self.quantity_warning)
            # A split may not produce more total quantity than its source: hard block
            # (other kinds only warn and let the user confirm).
            if over_quantity and self.transform_kind == TransformKind.SPLIT.value:
                raise ReflexAppException(
                    "A split cannot produce more total quantity than its source. "
                    "Reduce the output quantities."
                )
            if over_quantity:
                confirm_state = await self.get_state(ConfirmDialogState)
                confirm_state.open_dialog(
                    title="Output quantity exceeds input",
                    content=f"{self.quantity_warning} Do you want to save anyway?",
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

    async def _persist_and_finish(self, service_call: Callable[[], Any], success_msg: str):
        """Shared orchestration tail of every ``_create_*`` kind.

        Authenticate, run the (kind-specific) service call, link the note,
        toast, and fire the post-close callback with the first affected item.
        """
        main_state: ReflexMainState
        async with self:
            main_state = await self.get_state(ReflexMainState)

        with await main_state.authenticate_user():
            result = service_call()
            linked_note = self._link_note_activity(result.activity.id)

        yield rx.toast.success(success_msg)
        await self._after_note_link(linked_note)

        if self._callback_after_close and result.inputs:
            await self._callback_after_close(result.inputs[0].to_dto())

    async def _create_split(self, form_data: dict):
        """Split the single source item into the listed output items."""
        notes = form_data.get("notes", "").strip() or None
        source_id, dto = transform_builders.build_split(
            self.inputs, self.outputs, notes, self.note_dto_id
        )
        async for event in self._persist_and_finish(
            lambda: ItemService().split_item(source_id, dto),
            f"Split saved — {len(dto.outputs)} item(s) created",
        ):
            yield event

    async def _create_combine(self, form_data: dict):
        """Combine 2..N consumable ingredients into the single output item."""
        notes = form_data.get("notes", "").strip() or None
        dto = transform_builders.build_combine(self.inputs, self.outputs, notes, self.note_dto_id)
        async for event in self._persist_and_finish(
            lambda: ItemService().combine_items(dto),
            f"Combine saved — {len(dto.inputs)} input(s) → 1 item",
        ):
            yield event

    async def _create_concentrate(self, form_data: dict):
        """Concentrate the single source item into one more concentrated item."""
        notes = form_data.get("notes", "").strip() or None
        source_id, dto = transform_builders.build_concentrate(
            self.inputs, self.outputs, notes, self.note_dto_id
        )
        async for event in self._persist_and_finish(
            lambda: ItemService().concentrate_item(source_id, dto),
            "Concentrate saved — 1 item created",
        ):
            yield event

    async def _create_dilute(self, form_data: dict):
        """Dilute the target with the diluent into one less-concentrated item."""
        notes = form_data.get("notes", "").strip() or None
        target_id, dto = transform_builders.build_dilute(
            self.inputs, self.outputs, notes, self.note_dto_id
        )
        async for event in self._persist_and_finish(
            lambda: ItemService().dilute_item(target_id, dto),
            "Dilute saved — 1 item created",
        ):
            yield event

    async def _create_custom(self, form_data: dict):
        """Build the TransformItemsDTO and call the generic transform service."""
        notes = form_data.get("notes", "").strip() or None
        dto = transform_builders.build_custom(self.inputs, self.outputs, notes, self.note_dto_id)
        if dto is None:
            return
        async for event in self._persist_and_finish(
            lambda: ItemService().transform_items(dto),
            f"Transform saved — {len(dto.inputs)} input(s) → {len(dto.outputs)} output(s)",
        ):
            yield event

    async def _update(self, form_data: dict):
        """Not implemented - this dialog only creates transforms."""
        raise NotImplementedError("Update is not supported by this dialog")

    def _reset_state(self):
        self.inputs = []
        self.outputs = []
        self.transform_kind = ""
        self.transform_step = TransformStep.CHOOSE
        self._seed_item = None
        self._launch_unit_type = ""
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
