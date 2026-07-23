"""Transform instrument wizard: a 2-step dialog to create an instrument on the fly.

Step 1 — select an existing non-consumable ItemSheet, or morph into the ItemSheet
creation form.
Step 2 — create (persist) the instrument item for the chosen sheet; the created
item is then appended to the Transform as an instrument input.

Both step bodies REUSE the existing form content of the ItemSheet dialog and the
item dialog (``item_sheet_form_content`` / ``item_form_content``).
"""

import reflex as rx
from gws_reflex_main import dialog_header
from gws_reflex_main.gws_components import input_search_component

from ...item_sheets.item_sheet_form_dialog.item_sheet_form_dialog_component import (
    item_sheet_form_content,
)
from ..item_form_dialog.item_form_dialog_component import item_form_content
from .transform_instrument_sheet_select_state import TransformInstrumentSheetSelectState
from .transform_item_form_dialog_state import TransformItemFormDialogState

_S = TransformItemFormDialogState
_ISS = TransformInstrumentSheetSelectState


def _or_divider() -> rx.Component:
    """A horizontal divider with a centered "or" label."""
    return rx.hstack(
        rx.divider(),
        rx.text("or", size="1", color="gray", flex_shrink="0"),
        rx.divider(),
        align="center",
        spacing="3",
        width="100%",
    )


def _step_pill(number: str, label: str, active: rx.Var) -> rx.Component:
    return rx.hstack(
        rx.center(
            rx.text(number, size="1", weight="bold"),
            width="22px",
            height="22px",
            border_radius="50%",
            background=rx.cond(active, "var(--accent-9)", "var(--gray-4)"),
            color=rx.cond(active, "white", "var(--gray-11)"),
        ),
        rx.text(
            label,
            size="2",
            weight=rx.cond(active, "bold", "regular"),
            color=rx.cond(active, "var(--accent-11)", "gray"),
        ),
        align="center",
        spacing="2",
    )


def _step_indicator() -> rx.Component:
    return rx.hstack(
        _step_pill("1", "Instrument sheet", _S.instrument_step1_active),
        rx.divider(width="24px"),
        _step_pill("2", "Instrument", _S.instrument_step2_active),
        align="center",
        spacing="3",
        justify="center",
        width="100%",
        margin_bottom="0.5rem",
        flex_shrink="0",
    )


def _scroll_box(*children) -> rx.Component:
    return rx.box(
        rx.vstack(*children, width="100%", spacing="3", align="stretch", margin_top="0.5rem"),
        overflow_y="auto",
        flex="1",
        min_height="0",
        width="100%",
        padding="0.5rem",
    )


def _footer(*children) -> rx.Component:
    return rx.hstack(
        *children,
        justify="end",
        spacing="3",
        width="100%",
        flex_shrink="0",
        padding_top="3",
        margin_top="1rem",
    )


def _step1_select() -> rx.Component:
    """Step 1, default mode: pick an existing non-consumable sheet, or switch to create."""
    return rx.box(
        _scroll_box(
            input_search_component(
                search_result=_ISS.results,
                selected_item=None,
                item_selected=_S.select_instrument_sheet,
                search_trigger=_ISS.search,
                placeholder="Search a non-consumable item sheet…",
                min_input_search_length=0,
                init_search_on_focus=True,
            ),
            _or_divider(),
            rx.button(
                rx.icon("plus", size=16),
                "Create a new instrument sheet",
                type="button",
                variant="outline",
                width="100%",
                on_click=_S.instrument_enter_create_sheet,
            ),
        ),
        _footer(
            rx.button(
                "Cancel",
                type="button",
                variant="soft",
                color_scheme="gray",
                on_click=_S.close_instrument_wizard,
            ),
        ),
        width="100%",
        flex="1",
        min_height="0",
        display="flex",
        flex_direction="column",
    )


def _step1_create() -> rx.Component:
    """Step 1, create mode: the reused ItemSheet creation form (non-consumable)."""
    return rx.form(
        _scroll_box(item_sheet_form_content()),
        _footer(
            rx.button(
                rx.icon("arrow-left", size=15),
                "Back",
                type="button",
                variant="soft",
                color_scheme="gray",
                on_click=_S.instrument_back_to_select_sheet,
            ),
            rx.button(
                "Create & continue",
                rx.icon("arrow-right", size=15),
                type="submit",
            ),
        ),
        on_submit=_S.submit_create_instrument_sheet,
        width="100%",
        flex="1",
        min_height="0",
        display="flex",
        flex_direction="column",
    )


def _step1_body() -> rx.Component:
    return rx.cond(_S.instrument_create_sheet_mode, _step1_create(), _step1_select())


def _step2_body() -> rx.Component:
    """Step 2: the reused item creation form (persisted on save)."""
    return rx.form(
        # Keyed on the chosen sheet so the reused form remounts fresh when it changes.
        _scroll_box(
            rx.box(
                item_form_content(),
                key=_S.inst_sheet_id,
                width="100%",
            ),
        ),
        _footer(
            rx.button(
                rx.icon("arrow-left", size=15),
                "Back",
                type="button",
                variant="soft",
                color_scheme="gray",
                on_click=_S.open_instrument_wizard,
            ),
            rx.button(
                rx.icon("plus", size=16),
                "Create instrument",
                type="submit",
            ),
        ),
        on_submit=_S.submit_create_instrument_item,
        width="100%",
        flex="1",
        min_height="0",
        display="flex",
        flex_direction="column",
    )


def transform_instrument_wizard() -> rx.Component:
    """The 2-step instrument wizard dialog, controlled by
    ``TransformItemFormDialogState.instrument_dialog_opened``."""
    return rx.dialog.root(
        rx.dialog.content(
            dialog_header("Create an instrument", close=_S.close_instrument_wizard),
            _step_indicator(),
            rx.cond(_S.instrument_step1_active, _step1_body()),
            rx.cond(_S.instrument_step2_active, _step2_body()),
            max_width="560px",
            max_height="90vh",
            display="flex",
            flex_direction="column",
            on_interact_outside=rx.prevent_default,
            on_escape_key_down=rx.prevent_default,
        ),
        open=_S.instrument_dialog_opened,
    )
