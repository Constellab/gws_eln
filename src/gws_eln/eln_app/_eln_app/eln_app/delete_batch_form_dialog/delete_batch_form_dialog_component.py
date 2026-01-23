"""Delete batch form dialog component."""

import reflex as rx
from gws_reflex_main import form_dialog_component

from .delete_batch_form_dialog_state import DeleteBatchFormDialogState


def _form_content() -> rx.Component:
    """Form content for deleting/discarding a batch."""
    return rx.vstack(
        # Warning callout
        rx.callout(
            "This action cannot be undone. If the batch has activity history, "
            "it will be marked as discarded instead of deleted.",
            icon="triangle_alert",
            color="red",
        ),
        # Batch Number (read-only display)
        rx.vstack(
            rx.text("Batch", size="2", weight="bold"),
            rx.text(
                DeleteBatchFormDialogState.batch_number,
                size="2",
                color="gray",
            ),
            width="100%",
            spacing="1",
        ),
        # Material Name (read-only display)
        rx.vstack(
            rx.text("Material", size="2", weight="bold"),
            rx.text(
                DeleteBatchFormDialogState.material_name,
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
                DeleteBatchFormDialogState.current_quantity,
                size="2",
                color="gray",
            ),
            width="100%",
            spacing="1",
        ),
        # Notes field (for discard reason)
        rx.vstack(
            rx.text("Reason (optional)", size="2", weight="bold"),
            rx.text_area(
                placeholder="Enter reason for deleting/discarding this batch",
                name="notes",
                width="100%",
                default_value=DeleteBatchFormDialogState.form_notes,
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
        state=DeleteBatchFormDialogState,
        title="Delete Batch",
        description="Are you sure you want to delete this batch?",
        form_content=_form_content(),
        max_width="450px",
    )


def delete_batch_dialog() -> rx.Component:
    """Dialog component for deleting/discarding a batch.

    This component provides just the dialog (without a trigger button).
    The dialog is controlled by the DeleteBatchFormDialogState.dialog_opened state.

    To open the dialog, call DeleteBatchFormDialogState.open_delete_dialog(batch)
    with the batch to delete.

    :return: The delete batch dialog component
    :rtype: rx.Component
    """
    return _dialog()
