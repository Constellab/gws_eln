"""Delete item form dialog component."""

import reflex as rx
from gws_reflex_main import form_dialog_component

from ...activities.activity_form_sections import use_discard_form_section
from .delete_item_form_dialog_state import DeleteItemFormDialogState


def _form_content() -> rx.Component:
    """Form content for deleting/discarding a item."""
    return rx.vstack(
        # Warning callout
        rx.callout(
            "This action cannot be undone. If the item has activity history, "
            "it will be marked as discarded instead of deleted.",
            icon="triangle_alert",
            color="red",
        ),
        # Item Number (read-only display)
        rx.vstack(
            rx.text("Item", size="2", weight="bold"),
            rx.text(
                DeleteItemFormDialogState.code,
                size="2",
                color="gray",
            ),
            width="100%",
            spacing="1",
        ),
        # ItemSheet Name (read-only display)
        rx.vstack(
            rx.text("Item sheet", size="2", weight="bold"),
            rx.text(
                DeleteItemFormDialogState.item_sheet_name,
                size="2",
                color="gray",
            ),
            width="100%",
            spacing="1",
        ),
        # Current Quantity (read-only display)
        rx.vstack(
            rx.text("Current Quantity", size="2", weight="bold"),
            rx.text(
                DeleteItemFormDialogState.current_quantity,
                size="2",
                color="gray",
            ),
            width="100%",
            spacing="1",
        ),
        # Reusable notes form section
        use_discard_form_section(
            form_notes=DeleteItemFormDialogState.form_notes,
            notes_label="Reason (optional)",
            notes_placeholder="Enter reason for deleting/discarding this item",
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
        state=DeleteItemFormDialogState,
        title="Delete Item",
        description="Are you sure you want to delete this item?",
        form_content=_form_content(),
        max_width="450px",
    )


def delete_item_dialog() -> rx.Component:
    """Dialog component for deleting/discarding a item.

    This component provides just the dialog (without a trigger button).
    The dialog is controlled by the DeleteItemFormDialogState.dialog_opened state.

    To open the dialog, call DeleteItemFormDialogState.open_delete_dialog(item)
    with the item to delete.

    :return: The delete item dialog component
    :rtype: rx.Component
    """
    return _dialog()
