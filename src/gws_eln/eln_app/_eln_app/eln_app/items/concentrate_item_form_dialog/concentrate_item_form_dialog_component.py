"""Concentrate item form dialog component."""

import reflex as rx
from gws_reflex_main import form_dialog_component

from ...common.unit.concentration_unit_components import concentration_unit_select
from ...common.unit.unit_components import quantity_unit_input
from ..core.instrument_picker_component import instrument_picker_component
from .concentrate_item_form_dialog_state import ConcentrateItemFormDialogState


def _form_content() -> rx.Component:
    """Form content for concentrating an item."""
    return rx.vstack(
        # Source item (read-only)
        rx.vstack(
            rx.text("Source Item", size="2", weight="bold"),
            rx.code(ConcentrateItemFormDialogState.code, size="2"),
            width="100%",
            spacing="1",
            align="start",
        ),
        rx.hstack(
            rx.vstack(
                rx.text("Available Quantity", size="2", weight="bold"),
                rx.text(ConcentrateItemFormDialogState.current_quantity, size="2", color="gray"),
                width="50%",
                spacing="1",
            ),
            rx.vstack(
                rx.text("Current Concentration", size="2", weight="bold"),
                rx.text(
                    ConcentrateItemFormDialogState.current_concentration, size="2", color="gray"
                ),
                width="50%",
                spacing="1",
            ),
            width="100%",
        ),
        # Quantity drawn from the source
        quantity_unit_input(
            unit_type=ConcentrateItemFormDialogState.form_unit_type,
            quantity_name="draw_quantity",
            unit_value=ConcentrateItemFormDialogState.form_draw_unit,
            on_unit_change=ConcentrateItemFormDialogState.set_draw_unit,
            quantity_label="Quantity to concentrate",
        ),
        rx.divider(margin_y="0.25rem"),
        # Output item
        rx.text("Output item", size="2", weight="bold"),
        quantity_unit_input(
            unit_type=ConcentrateItemFormDialogState.form_unit_type,
            quantity_name="output_quantity",
            unit_value=ConcentrateItemFormDialogState.form_output_unit,
            on_unit_change=ConcentrateItemFormDialogState.set_output_unit,
            quantity_label="Output quantity",
        ),
        # New concentration (optional)
        rx.hstack(
            rx.vstack(
                rx.text("New concentration", size="1", weight="medium", color="gray"),
                rx.input(
                    placeholder="Optional",
                    name="output_concentration",
                    type="number",
                    min="0",
                    step="any",
                    width="100%",
                ),
                width="60%",
                spacing="1",
            ),
            rx.vstack(
                rx.text("Unit", size="1", weight="medium", color="gray"),
                concentration_unit_select(
                    value=ConcentrateItemFormDialogState.form_concentration_unit,
                    on_change=ConcentrateItemFormDialogState.set_concentration_unit,
                ),
                width="40%",
                spacing="1",
            ),
            width="100%",
            spacing="3",
        ),
        # Label (optional)
        rx.vstack(
            rx.text("Label", size="1", weight="medium", color="gray"),
            rx.input(placeholder="Enter label (optional)", name="output_label", width="100%"),
            width="100%",
            spacing="1",
        ),
        # Optional instruments used
        instrument_picker_component(ConcentrateItemFormDialogState),
        # Notes (optional)
        rx.vstack(
            rx.text("Notes", size="2", weight="bold"),
            rx.text_area(
                placeholder="Enter notes (optional)", name="notes", width="100%", rows="2"
            ),
            width="100%",
            spacing="1",
        ),
        width="100%",
        spacing="3",
    )


def _dialog() -> rx.Component:
    """The base concentrate dialog component without a trigger."""
    return form_dialog_component(
        state=ConcentrateItemFormDialogState,
        title="Concentrate Item",
        description=(
            "Concentrate part of this item into a new, more concentrated item. "
            "The source quantity is reduced by the amount drawn."
        ),
        form_content=_form_content(),
        max_width="520px",
    )


def concentrate_item_dialog() -> rx.Component:
    """Dialog component for concentrating an item.

    The dialog is controlled by ConcentrateItemFormDialogState.dialog_opened.
    Open it via ConcentrateItemFormDialogState.open_concentrate_dialog(item).

    :return: The concentrate item dialog component
    :rtype: rx.Component
    """
    return _dialog()
