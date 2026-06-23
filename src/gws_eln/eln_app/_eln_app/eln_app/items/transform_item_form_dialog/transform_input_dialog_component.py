"""Transform input dialog: search an existing item/instrument and add it as an
input of the Transform.

Consumable items also expose a consumed-quantity field; instruments (non
consumable) carry no quantity. Validating appends a row to the inputs list.
"""

import reflex as rx
from gws_reflex_main import dialog_header

from ...common.unit.unit_components import quantity_unit_input
from ..core.item_select_component import item_select_component
from .transform_item_form_dialog_state import TransformItemFormDialogState

_S = TransformItemFormDialogState


def _body() -> rx.Component:
    return rx.vstack(
        rx.vstack(
            item_select_component(
                placeholder="Search for an item or instrument…",
                item_selected=_S.select_input_item,
            ),
            rx.cond(
                _S.input_is_consumable,
                rx.text(
                    f"Available quantity : {_S.in_item_available}",
                    size="1",
                    color="gray",
                ),
            ),
            spacing="1",
            width="100%",
            align="start",
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
        spacing="3",
        width="100%",
        align="start",
    )


def transform_input_dialog() -> rx.Component:
    """Dialog to add one input to the Transform, controlled by
    ``TransformItemFormDialogState.input_dialog_opened``."""
    return rx.dialog.root(
        rx.dialog.content(
            dialog_header("Add an input", close=_S.close_input_dialog),
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
                    rx.icon("plus", size=16),
                    "Add input",
                    type="button",
                    on_click=_S.commit_input,
                ),
                justify="end",
                spacing="3",
                width="100%",
                margin_top="1rem",
            ),
            max_width="460px",
            on_interact_outside=_S.close_input_dialog,
            on_escape_key_down=_S.close_input_dialog,
        ),
        open=_S.input_dialog_opened,
    )
