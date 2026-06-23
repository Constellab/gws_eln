"""Transform item form dialog component (classic variant).

Generic N inputs -> M outputs transform. Inputs (left) are built in place
(existing item/instrument + quantity). Outputs (right) delegate creation to the
existing dialogs: a new ItemSheet via the ItemSheet dialog, and each output
item via the item dialog in collect mode.
"""

import reflex as rx
from gws_reflex_main import form_dialog_component

from .transform_input_dialog_component import transform_input_dialog
from .transform_item_form_dialog_state import (
    TransformInputRow,
    TransformItemFormDialogState,
    TransformOutputRow,
)
from .transform_output_wizard_component import transform_output_wizard

_S = TransformItemFormDialogState

_CODE_BADGE = {
    "font_family": "monospace",
    "font_size": "11px",
    "font_weight": "500",
    "color": "var(--accent-11)",
    "background": "var(--accent-3)",
    "padding": "3px 7px",
    "border_radius": "5px",
    "white_space": "nowrap",
}


def _section_label(text: str, count: rx.Var) -> rx.Component:
    return rx.hstack(
        rx.text(text, size="1", weight="bold", letter_spacing="1.4px", color="gray"),
        rx.badge(count, variant="surface", radius="full"),
        align="center",
        spacing="2",
        margin_bottom="2",
    )


def _input_row(row: TransformInputRow, index: int) -> rx.Component:
    return rx.hstack(
        rx.box(rx.text(row.code, style=_CODE_BADGE)),
        rx.vstack(
            rx.text(row.label, size="2", weight="medium", no_of_lines=1),
            rx.text(f"{row.sheet_name} · {row.loc}", size="1", color="gray"),
            spacing="0",
            align="start",
            flex="1",
            min_width="0",
        ),
        rx.badge(f"- {row.consumed}", color_scheme="ruby", variant="soft"),
        rx.icon_button(
            rx.icon("x", size=14),
            type="button",
            variant="ghost",
            color_scheme="gray",
            size="1",
            on_click=lambda: _S.remove_input(index),
        ),
        align="center",
        spacing="3",
        width="100%",
        padding="11px 12px",
        background="var(--gray-1)",
        border="1px solid var(--gray-5)",
        border_radius="10px",
    )


def _output_row(row: TransformOutputRow, index: int) -> rx.Component:
    return rx.hstack(
        rx.box(rx.text(row.code_preview, style=_CODE_BADGE)),
        rx.vstack(
            rx.text(row.label, size="2", weight="medium", no_of_lines=1),
            rx.text(f"{row.sheet_name} · {row.loc}", size="1", color="gray"),
            spacing="0",
            align="start",
            flex="1",
            min_width="0",
        ),
        rx.badge(f"+ {row.produced}", color_scheme="grass", variant="soft"),
        rx.icon_button(
            rx.icon("x", size=14),
            type="button",
            variant="ghost",
            color_scheme="gray",
            size="1",
            on_click=lambda: _S.remove_output(index),
        ),
        align="center",
        spacing="3",
        width="100%",
        padding="11px 12px",
        background="var(--gray-1)",
        border="1px solid var(--gray-5)",
        border_radius="10px",
    )


def _create_button(label: str, handler) -> rx.Component:
    return rx.button(
        rx.icon("plus", size=16),
        label,
        type="button",
        variant="outline",
        width="100%",
        on_click=handler,
    )


def _inputs_section() -> rx.Component:
    return rx.vstack(
        _section_label("INPUTS", _S.input_count),
        rx.foreach(_S.inputs, lambda row, i: _input_row(row, i)),
        rx.cond(
            _S.inputs_empty_hint,
            rx.text(
                "No input yet. Add the consumed items or instruments.",
                size="2",
                color="gray",
                text_align="center",
                padding="3",
            ),
        ),
        _create_button("Create input", _S.open_input_dialog),
        spacing="3",
        flex="1",
        min_width="0",
        align="stretch",
        padding="16px",
        background="var(--gray-2)",
        border="1px solid var(--gray-4)",
        border_radius="14px",
    )


def _outputs_section() -> rx.Component:
    return rx.vstack(
        _section_label("OUTPUTS", _S.output_count),
        rx.foreach(_S.outputs, lambda row, i: _output_row(row, i)),
        rx.cond(
            _S.outputs_empty_hint,
            rx.text(
                "No output yet. Create the items produced by the transform.",
                size="2",
                color="gray",
                text_align="center",
                padding="3",
            ),
        ),
        _create_button("Create output", _S.open_output_wizard),
        spacing="3",
        flex="1",
        min_width="0",
        align="stretch",
        padding="16px",
        background="var(--gray-2)",
        border="1px solid var(--gray-4)",
        border_radius="14px",
    )


def _center_arrow() -> rx.Component:
    return rx.center(
        rx.box(
            rx.icon("arrow-right", size=22, color="var(--accent-11)"),
            width="46px",
            height="46px",
            border_radius="50%",
            background="var(--accent-3)",
            border="1px solid var(--accent-6)",
            display="flex",
            align_items="center",
            justify_content="center",
        ),
        flex="0 0 58px",
    )


def _form_content() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            _inputs_section(),
            _center_arrow(),
            _outputs_section(),
            align="stretch",
            spacing="1",
            width="100%",
        ),
        rx.vstack(
            rx.text("Notes", size="2", weight="bold"),
            rx.text_area(
                placeholder="Enter notes (optional)",
                name="notes",
                width="100%",
                rows="2",
            ),
            spacing="1",
            width="100%",
            align="start",
        ),
        rx.cond(
            _S.has_any,
            rx.hstack(
                rx.text(_S.summary_str, size="2", color="gray"),
                rx.button(
                    "Clear all",
                    type="button",
                    variant="ghost",
                    color_scheme="gray",
                    size="1",
                    on_click=_S.clear_all,
                ),
                align="center",
                spacing="3",
            ),
        ),
        spacing="4",
        width="100%",
    )


def _dialog() -> rx.Component:
    return form_dialog_component(
        state=_S,
        title="Transform",
        description=(
            "Consume input items or instruments to produce new output items."
        ),
        form_content=_form_content(),
        max_width="980px",
        dismissable=False,
    )


def transform_item_dialog() -> rx.Component:
    """Dialog for the generic Transform activity (N inputs -> M outputs).

    Controlled by TransformItemFormDialogState.dialog_opened. Open it via
    TransformItemFormDialogState.open_transform_dialog(item). Bundles the output
    wizard (stacked on top) so every mount site gets it automatically.
    """
    return rx.fragment(_dialog(), transform_input_dialog(), transform_output_wizard())
