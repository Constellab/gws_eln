"""Transform input dialog: search an existing item/instrument and add it as an
input of the Transform.

Consumable items also expose a consumed-quantity field; instruments (non
consumable) carry no quantity. Validating appends a row to the inputs list.
"""

import reflex as rx
from gws_reflex_main import dialog_header
from gws_reflex_main.gws_components import input_search_component

from ...common.unit.unit_components import quantity_unit_input
from .transform_input_select_state import TransformInputSelectState
from .transform_item_form_dialog_state import TransformItemFormDialogState

_S = TransformItemFormDialogState
_SS = TransformInputSelectState


def _search() -> rx.Component:
    """A single filtered search, picked by the dialog mode (consumable / instrument)."""
    return rx.cond(
        _S.input_dialog_is_consumable,
        input_search_component(
            search_result=_SS.consumable_results,
            selected_item=None,
            item_selected=_S.select_input_item,
            search_trigger=_SS.search_consumables,
            placeholder="Search a consumable item…",
            min_input_search_length=0,
            init_search_on_focus=True,
        ),
        input_search_component(
            search_result=_SS.instrument_results,
            selected_item=None,
            item_selected=_S.select_input_item,
            search_trigger=_SS.search_instruments,
            placeholder="Search an instrument…",
            min_input_search_length=0,
            init_search_on_focus=True,
        ),
    )


def _selected_item() -> rx.Component:
    """Read-only summary of the currently selected item + quantity + change action."""
    return rx.vstack(
        rx.hstack(
            rx.code(_S.in_item_code, size="2"),
            rx.text(_S.in_item_label, size="2", weight="medium", no_of_lines=1),
            rx.spacer(),
            rx.button(
                "Change",
                type="button",
                variant="ghost",
                color_scheme="gray",
                size="1",
                on_click=_S.clear_input_selection,
            ),
            align="center",
            spacing="2",
            width="100%",
        ),
        rx.text(f"{_S.in_item_sheet_name} · {_S.in_item_loc}", size="1", color="gray"),
        rx.cond(
            _S.input_is_consumable,
            rx.text(f"Available quantity : {_S.in_item_available}", size="1", color="gray"),
        ),
        rx.cond(
            _S.input_is_consumable,
            quantity_unit_input(
                unit_type=_S.in_unit_type,
                quantity_value=_S.in_qty,
                unit_value=_S.in_unit,
                on_quantity_change=_S.set_input_qty,
                on_unit_change=_S.set_input_unit,
                quantity_label="Consumed quantity",
                quantity_required=False,
            ),
        ),
        spacing="2",
        width="100%",
        align="start",
    )


def _body() -> rx.Component:
    return rx.cond(_S.input_has_sel, _selected_item(), _search())


def transform_input_dialog() -> rx.Component:
    """Dialog to add one input to the Transform, controlled by
    ``TransformItemFormDialogState.input_dialog_opened``."""
    return rx.dialog.root(
        rx.dialog.content(
            dialog_header(
                rx.cond(
                    _S.input_is_editing,
                    "Edit input",
                    rx.cond(
                        _S.input_dialog_is_consumable,
                        "Add a consumable input",
                        "Add an instrument input",
                    ),
                ),
                close=_S.close_input_dialog,
            ),
            _body(),
            rx.hstack(
                rx.button(
                    "Cancel",
                    type="button",
                    variant="soft",
                    color_scheme="gray",
                    on_click=_S.close_input_dialog,
                ),
                rx.button(
                    rx.cond(_S.input_is_editing, rx.icon("check", size=16), rx.icon("plus", size=16)),
                    rx.cond(_S.input_is_editing, "Save", "Add input"),
                    type="button",
                    on_click=_S.commit_input,
                ),
                justify="end",
                spacing="3",
                width="100%",
                margin_top="1rem",
            ),
            max_width="460px",
            on_interact_outside=rx.prevent_default,
            on_escape_key_down=rx.prevent_default,
        ),
        open=_S.input_dialog_opened,
    )
