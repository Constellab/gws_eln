"""Instrument side of the Transform dialog: create an instrument on the fly.

A Reflex state mixin (``mixin=True``) merged into ``TransformItemFormDialogState``.
Mirrors the output wizard, but for instrument (non-consumable) inputs: a 2-step
flow — select or create a non-consumable ItemSheet, then create the instrument
item. Unlike an output, the instrument is PERSISTED immediately (it must exist to
be referenced), then appended to the Transform's inputs as an instrument row.
"""

import reflex as rx
from gws_eln.items.item_dto import ItemDTO
from gws_eln.items.item_sheet_dto import ItemSheetDTO
from gws_reflex_main.gws_components import InputSearchResultDTO

from ...item_sheets.item_sheet_form_dialog.item_sheet_form_dialog_state import (
    ItemSheetFormDialogState,
)
from ..item_form_dialog.item_form_dialog_state import ItemFormDialogState
from .transform_models import OutputStep


class TransformInstrumentWizardMixin(rx.State, mixin=True):
    """Instrument-creation wizard: select/create a non-consumable sheet, create the item."""

    instrument_dialog_opened: bool = False
    instrument_step: OutputStep = OutputStep.SHEET
    instrument_create_sheet_mode: bool = False  # step 1 morphed into sheet creation
    inst_sheet_id: str = ""
    inst_sheet_code: str = ""
    inst_sheet_name: str = ""

    # ------------------------------------------------------------------ vars

    @rx.var
    def instrument_step1_active(self) -> bool:
        return self.instrument_step == OutputStep.SHEET

    @rx.var
    def instrument_step2_active(self) -> bool:
        return self.instrument_step == OutputStep.ITEM

    # ------------------------------------------------------------------ events

    @rx.event
    async def open_instrument_wizard(self):
        """Open the wizard at step 1 (sheet selection), closing the input search dialog."""
        self.instrument_create_sheet_mode = False
        self.inst_sheet_id = ""
        self.inst_sheet_code = ""
        self.inst_sheet_name = ""
        self.instrument_step = OutputStep.SHEET
        self.input_dialog_opened = False
        self.instrument_dialog_opened = True

    @rx.event
    def close_instrument_wizard(self):
        """Close the wizard and reset its step/mode."""
        self.instrument_dialog_opened = False
        self.instrument_step = OutputStep.SHEET
        self.instrument_create_sheet_mode = False

    @rx.event
    async def select_instrument_sheet(self, event_data: dict):
        """Select an existing non-consumable sheet (step 1) and go to the item step."""
        result = InputSearchResultDTO.from_json_object(event_data, ItemSheetDTO)
        sheet = result.object
        self.inst_sheet_id = sheet.id
        self.inst_sheet_code = sheet.code
        self.inst_sheet_name = sheet.name
        await self._advance_to_instrument_item_step()

    @rx.event
    async def instrument_enter_create_sheet(self):
        """Step 1 morphs into the ItemSheet creation form (forced non-consumable)."""
        self.instrument_create_sheet_mode = True
        sheet_state = await self.get_state(ItemSheetFormDialogState)
        await sheet_state.prepare_create_form(force_consumable=False)
        sheet_state.set_callback_after_close(self._on_instrument_sheet_created)

    @rx.event
    def instrument_back_to_select_sheet(self):
        """Back from the create-sheet form to plain sheet selection (still step 1)."""
        self.instrument_create_sheet_mode = False

    @rx.event
    async def submit_create_instrument_sheet(self, form_data: dict):
        """Step 1 (create mode): create the non-consumable sheet via the reused form.

        On success ``_on_instrument_sheet_created`` selects it and advances to step 2.
        """
        sheet_state = await self.get_state(ItemSheetFormDialogState)
        async for event in sheet_state._create(form_data):
            yield event

    @rx.event
    async def submit_create_instrument_item(self, form_data: dict):
        """Step 2: create (and persist) the instrument item via the reused item form.

        Non-consumable sheet → ItemFormDialogState routes to the bulk create path,
        which persists the unit(s) and fires ``_on_instrument_created``.
        """
        item_state = await self.get_state(ItemFormDialogState)
        async for event in item_state._create(form_data):
            yield event

    async def _on_instrument_sheet_created(self, sheet: ItemSheetDTO):
        """Callback after a new non-consumable sheet is created: select + advance."""
        self.inst_sheet_id = sheet.id
        self.inst_sheet_code = sheet.code
        self.inst_sheet_name = sheet.name
        await self._advance_to_instrument_item_step()

    async def _advance_to_instrument_item_step(self):
        """Prepare the item form (persist mode) for the chosen sheet and go to step 2."""
        item_state = await self.get_state(ItemFormDialogState)
        await item_state.prepare_create_form(self.inst_sheet_id)
        # Persist on save (NOT collect mode), then add the created item as an input.
        item_state.set_callback_after_close(self._on_instrument_created)
        self.instrument_create_sheet_mode = False
        self.instrument_step = OutputStep.ITEM

    async def _on_instrument_created(self, item: ItemDTO):
        """Callback from the item form: append the new instrument as an input, close."""
        # An instrument is non-consumable: seeded as an input with no quantity.
        self._append_seed_input(item, "")
        self.instrument_dialog_opened = False
        self.instrument_step = OutputStep.SHEET
