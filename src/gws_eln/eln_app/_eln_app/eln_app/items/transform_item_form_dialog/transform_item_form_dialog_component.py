"""Transform item form dialog component (classic variant).

Generic N inputs -> M outputs transform. Inputs (left) are built in place
(existing item/instrument + quantity). Outputs (right) delegate creation to the
existing dialogs: a new ItemSheet via the ItemSheet dialog, and each output
item via the item dialog in collect mode.
"""

import reflex as rx
from gws_reflex_main import dialog_header

from ...common.feedback_components import compact_warning
from .transform_input_dialog_component import transform_input_dialog
from .transform_item_form_dialog_state import TransformItemFormDialogState
from .transform_models import (
    INPUT_ROLE_TARGET,
    TransformInputRow,
    TransformKind,
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


def _description_hint(description: str, hint: str | None = None) -> rx.Component:
    """Gray section description with an optional info tooltip to its right."""
    return rx.hstack(
        rx.text(description, size="1", color="gray"),
        *([rx.tooltip(rx.icon("info", size=14, color="gray"), content=hint)] if hint else []),
        align="center",
        spacing="1",
    )


# On hover, expose the full text as the native browser tooltip only when the
# text is actually truncated (overflowing its box); clear it otherwise.
_TRUNCATION_TITLE_JS = rx.Var(
    "(e) => { const t = e.currentTarget;"
    " t.title = t.scrollWidth > t.clientWidth ? t.textContent : ''; }"
)


def _ellipsis_text(text, **props) -> rx.Component:
    """Single-line text truncated with an ellipsis when it overflows the
    available width, with a native browser tooltip shown only when truncated."""
    return rx.text(
        text,
        width="100%",
        white_space="nowrap",
        overflow="hidden",
        text_overflow="ellipsis",
        custom_attrs={"onMouseEnter": _TRUNCATION_TITLE_JS},
        **props,
    )


def _row_warns_no_concentration(row: TransformInputRow) -> rx.Var:
    """Whether to warn that this input lacks a concentration (concentrate source /
    dilute target only)."""
    return (
        row.is_consumable
        & (row.init_conc == "")
        & (
            _S.kind_is_concentrate
            | (_S.kind_is_dilute & (row.role == INPUT_ROLE_TARGET))
        )
    )


def _row_shows_concentration(row: TransformInputRow) -> rx.Var:
    """Whether to surface this input's concentration on its card.

    The "before" value for concentrate's source / dilute's target, and each
    ingredient's concentration for a combine (shown whenever it exists)."""
    return (
        row.is_consumable
        & (row.init_conc != "")
        & (
            _S.kind_is_concentrate
            | _S.kind_is_combine
            | (_S.kind_is_dilute & (row.role == INPUT_ROLE_TARGET))
        )
    )


def _concentration_badge(value: rx.Var, unit: rx.Var) -> rx.Component:
    """A small chip showing an item's concentration.

    Used on the source and output cards of a concentrate/dilute to display the
    "before" and "after" concentration. Kept visually distinct (iris) from the
    consumed/produced quantity badges so the pair reads across the arrow.
    """
    return rx.badge(
        rx.icon("beaker", size=11),
        rx.cond(unit != "", f"{value} {unit}", value),
        variant="soft",
        color_scheme="iris",
        radius="full",
    )


def _input_row(row: TransformInputRow, editable: bool) -> rx.Component:
    """One input row. Consumable rows (editable=True) are clickable to edit the
    quantity (except the remove button); instruments are not editable. A missing
    concentration is flagged below the row for concentrate/dilute."""
    return rx.vstack(
        rx.hstack(
            rx.box(rx.text(row.code, style=_CODE_BADGE)),
            rx.vstack(
                _ellipsis_text(row.label, size="2", weight="medium"),
                _ellipsis_text(f"{row.sheet_name} · {row.loc}", size="1", color="gray"),
                spacing="0",
                align="start",
                flex="1",
                min_width="0",
            ),
            # Consumed quantity, with the source's concentration ("before") stacked
            # under it for concentrate/dilute.
            rx.vstack(
                rx.cond(
                    row.is_consumable,
                    rx.cond(
                        row.qty != "",
                        rx.badge(f"- {row.consumed}", color_scheme="ruby", variant="soft"),
                        # No quantity set yet: clicking the row (or this badge) opens
                        # the edit dialog to set the consumed quantity.
                        rx.badge(
                            rx.icon("plus", size=12),
                            "Add",
                            variant="soft",
                            style={"cursor": "pointer"},
                        ),
                    ),
                ),
                rx.cond(
                    _row_shows_concentration(row),
                    _concentration_badge(row.init_conc, row.init_conc_unit),
                ),
                spacing="1",
                align="end",
            ),
            rx.icon_button(
                rx.icon("x", size=14),
                type="button",
                variant="ghost",
                color_scheme="gray",
                size="1",
                # Stop propagation so removing a row never triggers the row's edit click.
                on_click=_S.remove_input_by_id(row.id).stop_propagation,
            ),
            align="center",
            spacing="3",
            width="100%",
            padding="11px 12px",
            background="var(--gray-1)",
            border="1px solid var(--gray-5)",
            border_radius="10px",
            on_click=_S.edit_input(row.id) if editable else None,
            cursor="pointer" if editable else "default",
            style={":hover": {"background_color": "var(--gray-3)"}} if editable else None,
        ),
        rx.cond(
            _row_warns_no_concentration(row),
            compact_warning("This item has no recorded concentration."),
        ),
        spacing="1",
        width="100%",
        align="stretch",
    )


def _output_row(row: TransformOutputRow, index: int) -> rx.Component:
    """One output row. Clickable to edit (except the remove button)."""
    return rx.hstack(
        rx.box(rx.text(row.code_preview, style=_CODE_BADGE)),
        rx.vstack(
            _ellipsis_text(row.label, size="2", weight="medium"),
            _ellipsis_text(f"{row.sheet_name} · {row.loc}", size="1", color="gray"),
            spacing="0",
            align="start",
            flex="1",
            min_width="0",
        ),
        # Produced quantity, with the output concentration ("after") stacked
        # under it for concentrate/dilute.
        rx.vstack(
            rx.badge(f"+ {row.produced}", color_scheme="grass", variant="soft"),
            rx.cond(
                _S.needs_concentration & (row.conc != ""),
                _concentration_badge(row.conc, row.conc_unit),
            ),
            spacing="1",
            align="end",
        ),
        rx.icon_button(
            rx.icon("x", size=14),
            type="button",
            variant="ghost",
            color_scheme="gray",
            size="1",
            # Stop propagation so removing a row never triggers the row's edit click.
            on_click=_S.remove_output(index).stop_propagation,
        ),
        align="center",
        spacing="3",
        width="100%",
        padding="11px 12px",
        background="var(--gray-1)",
        border="1px solid var(--gray-5)",
        border_radius="10px",
        on_click=_S.edit_output(row.id),
        cursor="pointer",
        style={":hover": {"background_color": "var(--gray-3)"}},
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


def _input_group(
    title: str | None,
    description: str,
    rows: rx.Var,
    button_label: str,
    on_create,
    editable: bool,
    can_create=True,
    hint: str | None = None,
) -> rx.Component:
    """A persistent input sub-section: (optional subtitle), helper text, its rows,
    a create button.

    The subtitle is omitted when ``title`` is None (e.g. when the enclosing box
    already carries a section header). The helper text is shown only while the
    sub-section has no row yet, with ``hint`` (when given) as an info tooltip to
    its right. Rows are clickable to edit when ``editable`` is True (consumables
    only). The create button is hidden when ``can_create`` is falsy (e.g. split
    allows one source).
    """
    return rx.vstack(
        rx.text(title, size="2", weight="medium") if title is not None else rx.fragment(),
        rx.cond(rows.length() == 0, _description_hint(description, hint)),
        rx.foreach(rows, lambda row: _input_row(row, editable)),
        rx.cond(can_create, _create_button(button_label, on_create)),
        spacing="2",
        width="100%",
        align="stretch",
    )


def _dilute_consumable_groups() -> rx.Component:
    """Dilute splits its two consumables into the Target and Diluent roles."""
    return rx.vstack(
        _input_group(
            "Target",
            "The item being diluted — its quantity is reduced.",
            _S.dilute_target_inputs,
            "Set target",
            _S.open_target_input_dialog,
            editable=True,
            can_create=_S.dilute_target_inputs.length() == 0,
        ),
        _input_group(
            "Diluents",
            "Added to dilute the target — each one's quantity is reduced.",
            _S.dilute_diluent_inputs,
            "Add diluent",
            _S.open_diluent_input_dialog,
            editable=True,
            can_create=True,
        ),
        spacing="4",
        width="100%",
        align="stretch",
    )


def _section_box(*children: rx.Component) -> rx.Component:
    """The rounded, tinted panel shared by the input/output sections."""
    return rx.vstack(
        *children,
        spacing="3",
        align="stretch",
        padding="16px",
        background="var(--gray-2)",
        border="1px solid var(--gray-4)",
        border_radius="14px",
    )


def _consumable_inputs_section() -> rx.Component:
    """Consumable inputs, in their own panel with a dedicated counter."""
    return _section_box(
        _section_label("INPUTS", _S.consumable_inputs.length()),
        rx.cond(
            _S.kind_is_dilute,
            _dilute_consumable_groups(),
            _input_group(
                None,
                "Items consumed by the transform.",
                _S.consumable_inputs,
                "Add input",
                _S.open_consumable_input_dialog,
                editable=True,
                can_create=_S.can_add_consumable_input,
                hint="A quantity is deducted from their stock.",
            ),
        ),
    )


def _instrument_inputs_section() -> rx.Component:
    """Instrument (non-consumable) inputs, in their own panel with a counter."""
    return _section_box(
        _section_label("INSTRUMENTS", _S.instrument_inputs.length()),
        _input_group(
            None,
            "Instruments used during the transform.",
            _S.instrument_inputs,
            "Add instrument",
            _S.open_instrument_input_dialog,
            editable=False,
            hint="No quantity change.",
        ),
    )


def _inputs_section() -> rx.Component:
    """Left column: consumable inputs and instruments as two dissociated panels."""
    return rx.vstack(
        _consumable_inputs_section(),
        _instrument_inputs_section(),
        spacing="4",
        flex="1",
        min_width="0",
        align="stretch",
    )


def _outputs_section() -> rx.Component:
    return rx.vstack(
        _section_label("OUTPUTS", _S.output_count),
        rx.cond(
            _S.outputs_empty_hint,
            _description_hint(
                "New items produced by the transform.",
                "Created when you save.",
            ),
        ),
        rx.foreach(_S.outputs, lambda row, i: _output_row(row, i)),
        rx.cond(
            _S.output_concentration_warning,
            compact_warning(_S.output_concentration_warning),
        ),
        rx.cond(
            _S.quantity_warning,
            compact_warning(_S.quantity_warning),
        ),
        rx.cond(
            _S.can_add_output,
            _create_button("Add output", _S.open_output_wizard),
        ),
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
                align="center",
                spacing="3",
            ),
        ),
        spacing="4",
        width="100%",
    )


def _kind_card(icon: str, title: str, description: str, kind: str) -> rx.Component:
    """One selectable transformation card in the wizard's first step."""
    return rx.card(
        rx.hstack(
            rx.icon(icon, size=24, color="var(--accent-11)", flex_shrink="0"),
            rx.vstack(
                rx.text(title, size="2", weight="bold"),
                rx.text(description, size="1", color="gray"),
                spacing="1",
                align="start",
                flex="1",
                min_width="0",
            ),
            spacing="3",
            align="center",
            width="100%",
        ),
        on_click=lambda: _S.select_transform_kind(kind),
        cursor="pointer",
        width="100%",
        style={":hover": {"background_color": "var(--gray-3)"}},
    )


def _chooser() -> rx.Component:
    """Wizard step 1: pick the transformation to perform."""
    return rx.vstack(
        dialog_header("Choose a transformation", close=_S.close_dialog),
        rx.grid(
            _kind_card(
                "git-fork",
                "Split",
                "One source item → several new items.",
                TransformKind.SPLIT.value,
            ),
            _kind_card(
                "git-merge",
                "Combine",
                "Several items → one new item.",
                TransformKind.COMBINE.value,
            ),
            # Dilute/concentrate only apply to solutions with a volume unit.
            rx.cond(
                _S.seed_is_volume,
                _kind_card(
                    "droplets",
                    "Dilute",
                    "Target + diluent → one diluted item.",
                    TransformKind.DILUTE.value,
                ),
            ),
            rx.cond(
                _S.seed_is_volume,
                _kind_card(
                    "filter",
                    "Concentrate",
                    "One item → one more concentrated item.",
                    TransformKind.CONCENTRATE.value,
                ),
            ),
            _kind_card(
                "shuffle",
                "Custom transform",
                "Any number of inputs → any number of outputs.",
                TransformKind.CUSTOM.value,
            ),
            columns="1",
            spacing="3",
            width="100%",
        ),
        rx.hstack(
            rx.button(
                "Cancel",
                type="button",
                variant="soft",
                color_scheme="gray",
                on_click=_S.close_dialog,
            ),
            justify="end",
            width="100%",
            margin_top="1rem",
        ),
        width="100%",
        min_width="0",
        spacing="3",
    )


def _builder() -> rx.Component:
    """Wizard step 2: build the inputs/outputs for the chosen transformation."""
    return rx.vstack(
        dialog_header(_S.kind_title, _S.kind_subtitle, close=_S.close_dialog),
        rx.form(
            rx.box(
                _form_content(),
                overflow_y="auto",
                # basis auto (not 0) so the content height counts toward the dialog's
                # auto height: the box only scrolls once the dialog hits max height.
                flex="1 1 auto",
                min_height="0",
                width="100%",
                padding_right="0.5rem",
            ),
            rx.hstack(
                rx.button(
                    rx.icon("arrow-left", size=15),
                    "Back",
                    type="button",
                    variant="soft",
                    color_scheme="gray",
                    on_click=_S.back_to_chooser,
                    disabled=_S.is_loading,
                ),
                rx.spacer(),
                rx.button(
                    "Cancel",
                    type="button",
                    variant="soft",
                    color_scheme="gray",
                    on_click=_S.close_dialog,
                    disabled=_S.is_loading,
                ),
                rx.button(
                    rx.spinner(loading=_S.is_loading),
                    "Save",
                    type="submit",
                    disabled=_S.is_loading,
                ),
                margin_top="1rem",
                flex_shrink="0",
                width="100%",
            ),
            on_submit=_S.submit_form,
            display="flex",
            flex_direction="column",
            flex="1 1 auto",
            min_height="0",
            width="100%",
        ),
        width="100%",
        flex="1 1 auto",
        min_height="0",
    )


def _dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.cond(_S.step_is_choose, _chooser(), _builder()),
            # Narrow for the kind chooser, wide for the inputs/outputs builder.
            max_width=rx.cond(_S.step_is_choose, "480px", "1024px"),
            max_height="90vh",
            display="flex",
            flex_direction="column",
            on_interact_outside=rx.prevent_default,
            on_escape_key_down=rx.prevent_default,
        ),
        open=_S.dialog_opened,
    )


def transform_item_dialog() -> rx.Component:
    """Dialog for the generic Transform activity (N inputs -> M outputs).

    Controlled by TransformItemFormDialogState.dialog_opened. Open it via
    TransformItemFormDialogState.open_transform_dialog(item). Bundles the output
    wizard (stacked on top) so every mount site gets it automatically.
    """
    return rx.fragment(_dialog(), transform_input_dialog(), transform_output_wizard())
