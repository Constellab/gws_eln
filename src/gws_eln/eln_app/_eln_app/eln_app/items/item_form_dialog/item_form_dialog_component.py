import reflex as rx
from gws_reflex_main import form_dialog_component

from ...common.unit.unit_components import quantity_unit_input
from ...locations.core.location_select_component import (
    location_select_component,
)
from ...suppliers.core.supplier_select_component import (
    supplier_select_component,
)
from .item_form_dialog_state import ItemFormDialogState


def _form_content() -> rx.Component:
    """Form content for entering item_sheet item details."""
    return rx.vstack(
        # ItemSheet Name (read-only display)
        rx.vstack(
            rx.text("ItemSheet", size="2", weight="bold"),
            rx.text(
                ItemFormDialogState.item_sheet_name,
                size="2",
                color="gray",
            ),
            width="100%",
            spacing="1",
        ),
        # Item Number field
        rx.vstack(
            rx.text("Item Number*", size="2", weight="bold"),
            rx.input(
                placeholder="Enter item number (e.g., LOT-2024-001)",
                name="item_number",
                required=True,
                width="100%",
                default_value=ItemFormDialogState.form_item_number,
            ),
            width="100%",
            spacing="1",
        ),
        quantity_unit_input(
            unit_type=ItemFormDialogState.form_unit_type,
            unit_value=ItemFormDialogState.form_unit,
            on_unit_change=ItemFormDialogState.set_unit,
        ),
        # Location field
        rx.vstack(
            rx.text("Location*", size="2", weight="bold"),
            location_select_component(
                placeholder="Select a location",
                value=ItemFormDialogState.form_location_id,
                on_change=ItemFormDialogState.set_location_id,
                required=True,
            ),
            width="100%",
            spacing="1",
        ),
        # Supplier field
        rx.vstack(
            rx.text("Supplier", size="2", weight="bold"),
            supplier_select_component(
                placeholder="Select a supplier (optional)",
                additional_option=("No supplier", "__none__"),
                value=ItemFormDialogState.form_supplier_id,
                on_change=ItemFormDialogState.set_supplier_id,
            ),
            width="100%",
            spacing="1",
        ),
        # Expiry Date field
        rx.vstack(
            rx.text("Expiry Date", size="2", weight="bold"),
            rx.input(
                placeholder="Select expiry date (optional)",
                name="expiry_date",
                type="date",
                width="100%",
                default_value=ItemFormDialogState.form_expiry_date,
                on_change=ItemFormDialogState.set_expiry_date,
            ),
            width="100%",
            spacing="1",
        ),
        # Label field
        rx.vstack(
            rx.text("Label", size="2", weight="bold"),
            rx.input(
                placeholder="Enter custom label (optional)",
                name="label",
                width="100%",
                default_value=ItemFormDialogState.form_label,
            ),
            rx.text(
                "Additional label to complement the item number. Useful to provide extra information.",
                size="1",
                color="gray",
            ),
            width="100%",
            spacing="1",
        ),
        # Notes field
        rx.vstack(
            rx.text("Notes", size="2", weight="bold"),
            rx.text_area(
                placeholder="Enter notes (optional)",
                name="notes",
                width="100%",
                default_value=ItemFormDialogState.form_notes,
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

    This can be reused in different contexts with different triggers.

    :return: The dialog component
    :rtype: rx.Component
    """
    return form_dialog_component(
        state=ItemFormDialogState,
        title="Create New Item",
        description="Fill in the details below to create a new item_sheet item.",
        form_content=_form_content(),
        max_width="550px",
    )


def create_item_dialog() -> rx.Component:
    """Dialog component for creating a new item_sheet item.

    This component provides just the dialog (without a trigger button).
    The dialog is controlled by the ItemFormDialogState.dialog_opened state.

    To open the dialog, call ItemFormDialogState.open_create_dialog(item_sheet)
    with the item_sheet for which to create a item.

    :return: The create item_sheet item dialog component
    :rtype: rx.Component
    """
    return _dialog()
