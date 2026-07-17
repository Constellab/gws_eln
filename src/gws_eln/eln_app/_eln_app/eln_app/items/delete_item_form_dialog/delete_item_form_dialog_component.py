"""Delete item form dialog component."""

import reflex as rx
from gws_reflex_main import form_dialog_component

from ...activities.activity_form_sections import use_discard_form_section
from .delete_item_form_dialog_state import DeleteItemFormDialogState


def _form_content() -> rx.Component:
    """Form content for deleting/discarding a item."""
    return rx.vstack(
        # Warning callout: message depends on whether it discards or hard-deletes.
        rx.callout(
            rx.cond(
                DeleteItemFormDialogState.will_discard,
                "This item has activity history, so it will be marked as discarded "
                "(not deleted). A reason is required.",
                "This item has no history and will be permanently deleted. "
                "This action cannot be undone.",
            ),
            icon="triangle_alert",
            color="red",
        ),
        # Item info (read-only display): name and code side by side
        rx.hstack(
            rx.vstack(
                rx.text("Item name", size="2", weight="bold"),
                rx.text(
                    DeleteItemFormDialogState.label,
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
                    DeleteItemFormDialogState.code,
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
        # Current Quantity (read-only display)
        rx.vstack(
            rx.text("Current Quantity", size="2", weight="bold"),
            rx.badge(
                DeleteItemFormDialogState.current_quantity,
                color_scheme="red",
                size="2",
            ),
            width="100%",
            spacing="1",
            align="start",
        ),
        # Reason: only when discarding. A hard-deleted item leaves no trace, so a
        # reason would be visible nowhere - the field is hidden entirely then.
        rx.cond(
            DeleteItemFormDialogState.will_discard,
            use_discard_form_section(
                form_notes=DeleteItemFormDialogState.form_notes,
                notes_label="Reason *",
                notes_placeholder="Enter reason for discarding this item",
                on_notes_change=DeleteItemFormDialogState.set_notes,
            ),
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
