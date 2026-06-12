"""Combine item form dialog component."""

import reflex as rx
from gws_reflex_main import form_dialog_component

from ...common.unit.concentration_unit_components import concentration_unit_select
from ...common.unit.unit_components import quantity_unit_input
from ...item_sheets.core.item_sheet_select_component import item_sheet_select_component
from ..core.item_select_component import item_select_component
from .combine_item_form_dialog_state import (
    CombineIngredientRow,
    CombineItemFormDialogState,
)


def _ingredient_row(row: CombineIngredientRow, index: int) -> rx.Component:
    """Render one editable ingredient row.

    :param row: The ingredient row data (from the state's ingredients list)
    :param index: The row index within the ingredients list
    :return: The ingredient row component
    """
    return rx.vstack(
        # Header: ingredient number + remove button
        rx.hstack(
            rx.text(f"Ingredient #{index + 1}", size="2", weight="bold"),
            rx.spacer(),
            rx.icon_button(
                rx.icon("trash-2", size=14),
                type="button",
                variant="soft",
                color_scheme="gray",
                size="1",
                disabled=~CombineItemFormDialogState.can_remove_ingredient,
                on_click=lambda: CombineItemFormDialogState.remove_ingredient_row(index),
            ),
            width="100%",
            align="center",
        ),
        # Item search/select
        item_select_component(
            placeholder="Search an item...",
            item_selected=lambda e: CombineItemFormDialogState.select_ingredient_item(index, e),
        ),
        # Currently selected item (shown once chosen)
        rx.cond(
            row.item_display,
            rx.text(row.item_display, size="1", color="gray"),
        ),
        # Quantity + unit (each ingredient keeps its own unit type)
        quantity_unit_input(
            unit_type=row.unit_type,
            quantity_value=row.quantity,
            unit_value=row.unit,
            on_quantity_change=lambda v: CombineItemFormDialogState.set_ingredient_quantity(
                index, v
            ),
            on_unit_change=lambda v: CombineItemFormDialogState.set_ingredient_unit(index, v),
            quantity_required=False,
        ),
        width="100%",
        spacing="2",
        padding="0.75rem",
        border="1px solid var(--gray-5)",
        border_radius="0.5rem",
    )


def _output_section() -> rx.Component:
    """Render the output item definition section."""
    return rx.vstack(
        rx.text("Output item", size="2", weight="bold"),
        # Output item sheet select
        item_sheet_select_component(
            placeholder="Search an item sheet for the output...",
            item_selected=CombineItemFormDialogState.select_output_sheet,
        ),
        rx.cond(
            CombineItemFormDialogState.has_output_sheet,
            rx.vstack(
                rx.text(
                    CombineItemFormDialogState.output_sheet_name,
                    size="1",
                    color="gray",
                ),
                # Item number
                rx.vstack(
                    rx.text("Item Number*", size="1", weight="medium", color="gray"),
                    rx.input(
                        placeholder="Enter item number",
                        name="output_item_number",
                        required=True,
                        width="100%",
                    ),
                    width="100%",
                    spacing="1",
                ),
                # Quantity + unit (unit type from the output sheet)
                quantity_unit_input(
                    unit_type=CombineItemFormDialogState.output_unit_type,
                    quantity_name="output_quantity",
                    unit_value=CombineItemFormDialogState.output_unit,
                    on_unit_change=CombineItemFormDialogState.set_output_unit,
                ),
                # Concentration value + unit (optional, recorded verbatim)
                rx.hstack(
                    rx.vstack(
                        rx.text("Concentration", size="1", weight="medium", color="gray"),
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
                            value=CombineItemFormDialogState.output_concentration_unit,
                            on_change=CombineItemFormDialogState.set_output_concentration_unit,
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
                    rx.input(
                        placeholder="Enter label (optional)",
                        name="output_label",
                        width="100%",
                    ),
                    width="100%",
                    spacing="1",
                ),
                width="100%",
                spacing="3",
            ),
        ),
        width="100%",
        spacing="2",
        padding="0.75rem",
        border="1px solid var(--accent-6)",
        border_radius="0.5rem",
    )


def _form_content() -> rx.Component:
    """Form content for combining items."""
    return rx.vstack(
        # Ingredients
        rx.text("Ingredients", size="2", weight="bold"),
        rx.foreach(CombineItemFormDialogState.ingredients, _ingredient_row),
        rx.button(
            rx.icon("plus", size=16),
            "Add ingredient",
            type="button",
            variant="soft",
            color_scheme="gray",
            on_click=CombineItemFormDialogState.add_ingredient_row,
            width="100%",
        ),
        rx.divider(margin_y="0.25rem"),
        # Output
        _output_section(),
        # Notes (optional)
        rx.vstack(
            rx.text("Notes", size="2", weight="bold"),
            rx.text_area(
                placeholder="Enter notes (optional)",
                name="notes",
                width="100%",
                rows="2",
            ),
            width="100%",
            spacing="1",
        ),
        width="100%",
        spacing="3",
    )


def _dialog() -> rx.Component:
    """The base combine dialog component without a trigger.

    :return: The dialog component
    :rtype: rx.Component
    """
    return form_dialog_component(
        state=CombineItemFormDialogState,
        title="Combine Items",
        description=(
            "Combine two or more items into a new item. Each ingredient is "
            "reduced by its contribution; the new item is created on its own sheet."
        ),
        form_content=_form_content(),
        max_width="560px",
    )


def combine_item_dialog() -> rx.Component:
    """Dialog component for combining items.

    This component provides just the dialog (without a trigger button).
    The dialog is controlled by CombineItemFormDialogState.dialog_opened.

    To open the dialog, call CombineItemFormDialogState.open_combine_dialog(item)
    with the source item to seed as the first ingredient.

    :return: The combine item dialog component
    :rtype: rx.Component
    """
    return _dialog()
