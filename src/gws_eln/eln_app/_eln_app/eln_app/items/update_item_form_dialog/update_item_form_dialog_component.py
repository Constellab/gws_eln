"""Update item form dialog component."""

import reflex as rx
from gws_reflex_main import form_dialog_component

from ...suppliers.core.supplier_select_component import supplier_select_component
from .update_item_form_dialog_state import UpdateItemFormDialogState


def _form_content() -> rx.Component:
    """Form content for updating item metadata."""
    return rx.vstack(
        # Item info (read-only display): name and code side by side
        rx.hstack(
            rx.vstack(
                rx.text("Item name", size="2", weight="bold"),
                rx.text(
                    UpdateItemFormDialogState.label,
                    size="2",
                    color="gray",
                ),
                width="50%",
                spacing="1",
            ),
            rx.vstack(
                rx.hstack(
                    rx.text("Item code", size="2", weight="bold"),
                    rx.tooltip(
                        rx.icon("info", size=14, color="gray"),
                        content=(
                            "Auto-generated identifier: the sheet's code followed by an "
                            "incrementing number."
                        ),
                    ),
                    align="center",
                    spacing="1",
                ),
                rx.text(
                    UpdateItemFormDialogState.code,
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
            rx.hstack(
                rx.text("Supplier", size="2", weight="bold"),
                rx.tooltip(
                    rx.icon("info", size=14, color="gray"),
                    content=(
                        "Who supplied this item (optional); prefilled from the sheet's "
                        "default supplier when it has one."
                    ),
                ),
                align="center",
                spacing="1",
            ),
            supplier_select_component(
                placeholder="Select a supplier (optional)",
                additional_option=("No supplier", "__none__"),
                value=UpdateItemFormDialogState.form_supplier_id,
                on_change=UpdateItemFormDialogState.set_supplier_id,
            ),
            width="100%",
            spacing="1",
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
                rx.hstack(
                    rx.text("Storage conditions", size="2", weight="bold"),
                    rx.tooltip(
                        rx.icon("info", size=14, color="gray"),
                        content=(
                            "Storage conditions are prefilled from the item sheet's "
                            "default; edit to override for this item."
                        ),
                    ),
                    align="center",
                    spacing="1",
                ),
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
        subtitle="Update item metadata.",
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
