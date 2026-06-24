"""Update item form dialog component."""

import reflex as rx
from gws_reflex_main import form_dialog_component

from ...common.unit.concentration_unit_components import concentration_unit_select
from ...suppliers.core.supplier_select_component import supplier_select_component
from .update_item_form_dialog_state import UpdateItemFormDialogState


def _form_content() -> rx.Component:
    """Form content for updating item metadata."""
    return rx.vstack(
        # Item + ItemSheet (read-only, side by side, equal width)
        rx.hstack(
            rx.vstack(
                rx.text("Item", size="2", weight="bold"),
                rx.text(
                    UpdateItemFormDialogState.code,
                    size="2",
                    color="gray",
                ),
                width="50%",
                spacing="1",
            ),
            rx.vstack(
                rx.text("ItemSheet", size="2", weight="bold"),
                rx.text(
                    UpdateItemFormDialogState.item_sheet_name,
                    size="2",
                    color="gray",
                ),
                width="50%",
                spacing="1",
            ),
            width="100%",
            spacing="3",
            align="start",
        ),
        # Supplier field
        rx.vstack(
            rx.text("Supplier", size="2", weight="bold"),
            supplier_select_component(
                placeholder="Select a supplier (optional)",
                additional_option=("No supplier", "__none__"),
                value=UpdateItemFormDialogState.form_supplier_id,
                on_change=UpdateItemFormDialogState.set_supplier_id,
            ),
            width="100%",
            spacing="1",
        ),
        # Concentration value + unit (optional, recorded verbatim)
        rx.hstack(
            rx.vstack(
                rx.text("Concentration", size="2", weight="bold"),
                rx.input(
                    placeholder="Enter concentration (optional)",
                    name="concentration",
                    type="number",
                    min="0",
                    step="any",
                    width="100%",
                    default_value=UpdateItemFormDialogState.form_concentration,
                ),
                width="60%",
                spacing="1",
            ),
            rx.vstack(
                rx.text("Unit", size="2", weight="bold"),
                concentration_unit_select(
                    name="concentration_unit",
                    value=UpdateItemFormDialogState.form_concentration_unit,
                    on_change=UpdateItemFormDialogState.set_concentration_unit,
                ),
                width="40%",
                spacing="1",
            ),
            width="100%",
            spacing="3",
        ),
        # Expiry Date + Storage conditions (side by side, equal width)
        rx.hstack(
            rx.vstack(
                rx.text("Expiry Date", size="2", weight="bold"),
                rx.input(
                    placeholder="Select expiry date (optional)",
                    name="expiry_date",
                    type="date",
                    width="100%",
                    value=UpdateItemFormDialogState.form_expiry_date,
                    on_change=UpdateItemFormDialogState.set_expiry_date,
                ),
                width="50%",
                spacing="1",
            ),
            rx.vstack(
                rx.text("Storage conditions", size="2", weight="bold"),
                rx.input(
                    placeholder="e.g. -20°C (optional)",
                    name="storage_conditions",
                    width="100%",
                    default_value=UpdateItemFormDialogState.form_storage_conditions,
                ),
                width="50%",
                spacing="1",
            ),
            width="100%",
            spacing="3",
            align="start",
        ),
        # Notes field
        rx.vstack(
            rx.text("Notes", size="2", weight="bold"),
            rx.text_area(
                placeholder="Enter notes (optional)",
                name="notes",
                width="100%",
                default_value=UpdateItemFormDialogState.form_notes,
                rows="3",
            ),
            width="100%",
            spacing="1",
        ),
        width="100%",
        spacing="3",
    )


def _dialog() -> rx.Component:
    """The base dialog component without a trigger.

    :return: The dialog component
    :rtype: rx.Component
    """
    return form_dialog_component(
        state=UpdateItemFormDialogState,
        title="Update Item",
        description="Update item metadata.",
        form_content=_form_content(),
        max_width="450px",
    )


def update_item_dialog() -> rx.Component:
    """Dialog component for updating item metadata.

    This component provides just the dialog (without a trigger button).
    The dialog is controlled by the UpdateItemFormDialogState.dialog_opened state.

    To open the dialog, call UpdateItemFormDialogState.open_update_dialog(item)
    with the item to update.

    :return: The update item dialog component
    :rtype: rx.Component
    """
    return _dialog()
