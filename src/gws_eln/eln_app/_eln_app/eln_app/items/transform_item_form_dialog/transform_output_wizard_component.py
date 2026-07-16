"""Transform output wizard: a 2-step dialog to add one output to a Transform.

Step 1 — select an existing ItemSheet, or morph into the ItemSheet creation form.
Step 2 — create the produced item for the chosen sheet (collect mode: the row is
appended to the Transform, the item is persisted only when the Transform is saved).

The two step bodies REUSE the existing form content of the ItemSheet dialog and the
item dialog (`item_sheet_form_content` / `item_form_content`).
"""

import reflex as rx
from gws_reflex_main import dialog_header
from gws_reflex_main.gws_components import input_search_component

from ...common.unit.concentration_method_components import concentration_method_select
from ...item_sheets.item_sheet_form_dialog.item_sheet_form_dialog_component import (
    item_sheet_form_content,
)
from ..item_form_dialog.item_form_dialog_component import item_form_content
from .transform_item_form_dialog_state import TransformItemFormDialogState
from .transform_output_sheet_select_state import TransformOutputSheetSelectState

_S = TransformItemFormDialogState
_OSS = TransformOutputSheetSelectState


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
        _step_pill("1", "Item sheet", _S.output_step1_active),
        rx.divider(width="24px"),
        _step_pill("2", "Item", _S.output_step2_active),
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
        padding_right="0.5rem",
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
    """Step 1, default mode: pick an existing ItemSheet, or switch to create mode."""
    return rx.box(
        _scroll_box(
            input_search_component(
                search_result=_OSS.results,
                selected_item=None,
                item_selected=_S.select_output_sheet,
                search_trigger=_OSS.search,
                placeholder="Search a consumable item sheet…",
                min_input_search_length=0,
                init_search_on_focus=True,
            ),
            _or_divider(),
            rx.button(
                rx.icon("plus", size=16),
                "Create a new item sheet",
                type="button",
                variant="outline",
                width="100%",
                on_click=_S.output_enter_create_sheet,
            ),
        ),
        _footer(
            rx.button(
                "Cancel",
                type="button",
                variant="soft",
                color_scheme="gray",
                on_click=_S.close_output_wizard,
            ),
        ),
        width="100%",
        flex="1",
        min_height="0",
        display="flex",
        flex_direction="column",
    )


def _step1_create() -> rx.Component:
    """Step 1, create mode: the reused ItemSheet creation form."""
    return rx.form(
        _scroll_box(item_sheet_form_content()),
        _footer(
            rx.button(
                rx.icon("arrow-left", size=15),
                "Back",
                type="button",
                variant="soft",
                color_scheme="gray",
                on_click=_S.output_back_to_select_sheet,
            ),
            rx.button(
                "Create & continue",
                rx.icon("arrow-right", size=15),
                type="submit",
            ),
        ),
        on_submit=_S.submit_create_sheet,
        width="100%",
        flex="1",
        min_height="0",
        display="flex",
        flex_direction="column",
    )


def _step1_body() -> rx.Component:
    return rx.cond(_S.output_create_sheet_mode, _step1_create(), _step1_select())


def _dilution_factor_field() -> rx.Component:
    """Factor audit input (store-only, optional).

    Labelled "Concentration factor" for a concentrate and "Dilution factor" for a
    dilute; the form field name stays ``dilution_factor`` (shared backend audit).
    """
    return rx.vstack(
        rx.text(
            rx.cond(_S.kind_is_concentrate, "Concentration factor", "Dilution factor"),
            size="2",
            weight="bold",
        ),
        rx.input(
            placeholder=rx.cond(
                _S.kind_is_concentrate,
                "Enter concentration factor (optional, audit only)",
                "Enter dilution factor (optional, audit only)",
            ),
            name="dilution_factor",
            type="number",
            min="0",
            step="any",
            width="100%",
        ),
        spacing="1",
        width="100%",
        align="start",
    )


def _concentration_method_field() -> rx.Component:
    """Concentration-method audit select (concentrate only); store-only, optional."""
    return rx.vstack(
        rx.text("Concentration method", size="2", weight="bold"),
        concentration_method_select(
            value=_S.concentration_method,
            on_change=_S.set_concentration_method,
        ),
        spacing="1",
        width="100%",
        align="start",
    )


def _extra_concentration_content() -> rx.Component:
    """Audit fields slotted after the concentration row: dilution factor
    (concentrate/dilute) and, for concentrate only, the concentration method —
    laid out side by side on the same row for concentrate."""
    return rx.cond(
        _S.kind_is_concentrate,
        rx.hstack(
            _dilution_factor_field(),
            _concentration_method_field(),
            width="100%",
            spacing="3",
            align="start",
        ),
        rx.cond(_S.needs_concentration, _dilution_factor_field(), rx.fragment()),
    )


def _split_remaining_hint() -> rx.Component:
    """Info banner showing the source quantity still available to allocate (split)."""
    return rx.cond(
        _S.split_remaining_display != "",
        rx.hstack(
            rx.icon("info", size=14, color="var(--accent-11)", flex_shrink="0"),
            rx.text(
                f"Remaining from source: {_S.split_remaining_display}",
                size="1",
                color="var(--accent-11)",
            ),
            spacing="2",
            align="center",
            width="100%",
            background="var(--accent-3)",
            border="1px solid var(--accent-6)",
            padding="0.375rem 0.5rem",
            border_radius="0.5rem",
        ),
    )


def _step2_body() -> rx.Component:
    """Step 2: the reused item creation form (collect mode)."""
    return rx.form(
        # Keyed on the chosen sheet so the reused form (default_value inputs)
        # remounts fresh whenever the destination sheet changes. The
        # dilution-factor audit field is slotted right after the concentration
        # row, and only for concentrate/dilute. Only this scroll box scrolls;
        # the footer below stays fixed with the dialog's padding.
        _scroll_box(
            _split_remaining_hint(),
            rx.box(
                item_form_content(
                    extra_concentration_content=_extra_concentration_content(),
                ),
                key=_S.out_sheet_id,
                width="100%",
            ),
        ),
        _footer(
            # When the sheet is fixed (split) there is no sheet step to go
            # back to, so offer Cancel instead of Back.
            rx.cond(
                _S.output_sheet_is_fixed,
                rx.button(
                    "Cancel",
                    type="button",
                    variant="soft",
                    color_scheme="gray",
                    on_click=_S.close_output_wizard,
                ),
                rx.button(
                    rx.icon("arrow-left", size=15),
                    "Back",
                    type="button",
                    variant="soft",
                    color_scheme="gray",
                    on_click=_S.output_back_to_sheet_step,
                ),
            ),
            rx.button(
                rx.cond(_S.output_is_editing, rx.icon("check", size=16), rx.icon("plus", size=16)),
                rx.cond(_S.output_is_editing, "Save", "Add output"),
                type="submit",
            ),
        ),
        on_submit=_S.submit_collect_item,
        width="100%",
        flex="1",
        min_height="0",
        display="flex",
        flex_direction="column",
    )


def transform_output_wizard() -> rx.Component:
    """The 2-step output wizard dialog, controlled by
    ``TransformItemFormDialogState.output_dialog_opened``."""
    return rx.dialog.root(
        rx.dialog.content(
            # Header stays fixed at the top.
            dialog_header(
                rx.cond(_S.output_is_editing, "Edit output", "Create an output"),
                close=_S.close_output_wizard,
            ),
            # Split fixes the output sheet to the source's, so there is no
            # sheet step — hide the 2-step indicator in that case.
            rx.cond(_S.output_sheet_is_fixed, rx.fragment(), _step_indicator()),
            # The active step's form is the single flex child that fills the
            # remaining height; its inner scroll box scrolls, footer stays fixed.
            rx.cond(_S.output_step1_active, _step1_body()),
            rx.cond(_S.output_step2_active, _step2_body()),
            max_width="560px",
            max_height="90vh",
            display="flex",
            flex_direction="column",
            on_interact_outside=rx.prevent_default,
            on_escape_key_down=rx.prevent_default,
        ),
        open=_S.output_dialog_opened,
    )
