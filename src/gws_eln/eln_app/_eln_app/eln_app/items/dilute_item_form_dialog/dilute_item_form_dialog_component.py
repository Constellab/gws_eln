"""Dilute item form dialog component."""

import reflex as rx
from gws_reflex_main import form_dialog_component

from ...common.unit.concentration_unit_components import concentration_unit_select
from ...common.unit.unit_components import quantity_unit_input
from ..core.instrument_picker_component import instrument_picker_component
from ..core.item_select_component import item_select_component
from .dilute_item_form_dialog_state import DiluteItemFormDialogState


def _form_content() -> rx.Component:
    """Form content for diluting an item."""
    return rx.vstack(
        # Target item (read-only)
        rx.vstack(
            rx.text("Target Item", size="2", weight="bold"),
            rx.code(DiluteItemFormDialogState.code, size="2"),
            width="100%",
            spacing="1",
            align="start",
        ),
        rx.hstack(
            rx.vstack(
                rx.text("Available Quantity", size="2", weight="bold"),
                rx.text(DiluteItemFormDialogState.current_quantity, size="2", color="gray"),
                width="50%",
                spacing="1",
            ),
            rx.vstack(
                rx.text("Current Concentration", size="2", weight="bold"),
                rx.text(DiluteItemFormDialogState.current_concentration, size="2", color="gray"),
                width="50%",
                spacing="1",
            ),
            width="100%",
        ),
        # Quantity drawn from the target
        quantity_unit_input(
            unit_type=DiluteItemFormDialogState.form_unit_type,
            quantity_name="draw_quantity",
            unit_value=DiluteItemFormDialogState.form_draw_unit,
            on_unit_change=DiluteItemFormDialogState.set_draw_unit,
            quantity_label="Quantity from target",
        ),
        rx.divider(margin_y="0.25rem"),
        # Diluent
        rx.text("Diluent", size="2", weight="bold"),
        item_select_component(
            placeholder="Search a diluent item...",
            item_selected=DiluteItemFormDialogState.select_diluent_item,
        ),
        rx.cond(
            DiluteItemFormDialogState.diluent_display,
            rx.text(DiluteItemFormDialogState.diluent_display, size="1", color="gray"),
        ),
        rx.cond(
            DiluteItemFormDialogState.has_diluent,
            quantity_unit_input(
                unit_type=DiluteItemFormDialogState.diluent_unit_type,
                quantity_name="diluent_quantity",
                unit_value=DiluteItemFormDialogState.form_diluent_unit,
                on_unit_change=DiluteItemFormDialogState.set_diluent_unit,
                quantity_label="Quantity of diluent",
            ),
        ),
        rx.divider(margin_y="0.25rem"),
        # Output item
        rx.text("Output item", size="2", weight="bold"),
        quantity_unit_input(
            unit_type=DiluteItemFormDialogState.form_unit_type,
            quantity_name="output_quantity",
            unit_value=DiluteItemFormDialogState.form_output_unit,
            on_unit_change=DiluteItemFormDialogState.set_output_unit,
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
                    value=DiluteItemFormDialogState.form_concentration_unit,
                    on_change=DiluteItemFormDialogState.set_concentration_unit,
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
        instrument_picker_component(DiluteItemFormDialogState),
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
    """The base dilute dialog component without a trigger."""
    return form_dialog_component(
        state=DiluteItemFormDialogState,
        title="Dilute Item",
        description=(
            "Dilute part of this item with a diluent into a new, less "
            "concentrated item. The target and diluent quantities are reduced."
        ),
        form_content=_form_content(),
        max_width="540px",
    )


def dilute_item_dialog() -> rx.Component:
    """Dialog component for diluting an item.

    The dialog is controlled by DiluteItemFormDialogState.dialog_opened.
    Open it via DiluteItemFormDialogState.open_dilute_dialog(item).

    :return: The dilute item dialog component
    :rtype: rx.Component
    """
    return _dialog()
