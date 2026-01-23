"""Relabel batch form dialog component."""

import reflex as rx
from gws_reflex_main import form_dialog_component

from .relabel_batch_form_dialog_state import RelabelBatchFormDialogState


def _form_content() -> rx.Component:
    """Form content for relabeling a batch."""
    return rx.vstack(
        # Material Name (read-only display)
        rx.vstack(
            rx.text("Material", size="2", weight="bold"),
            rx.text(
                RelabelBatchFormDialogState.material_name,
                size="2",
                color="gray",
            ),
            width="100%",
            spacing="1",
        ),
        # Current Batch Number (read-only display)
        rx.vstack(
            rx.text("Current Batch Number", size="2", weight="bold"),
            rx.text(
                RelabelBatchFormDialogState.current_batch_number,
                size="2",
                color="gray",
            ),
            width="100%",
            spacing="1",
        ),
        # Current Label (read-only display)
        rx.vstack(
            rx.text("Current Label", size="2", weight="bold"),
            rx.text(
                RelabelBatchFormDialogState.current_label,
                size="2",
                color="gray",
            ),
            width="100%",
            spacing="1",
        ),
        rx.divider(margin_y="0.5rem"),
        # New Batch Number field
        rx.vstack(
            rx.text("New Batch Number*", size="2", weight="bold"),
            rx.input(
                placeholder="Enter new batch number",
                name="batch_number",
                required=True,
                width="100%",
                default_value=RelabelBatchFormDialogState.form_batch_number,
            ),
            width="100%",
            spacing="1",
        ),
        # New Label field
        rx.vstack(
            rx.text("New Label", size="2", weight="bold"),
            rx.input(
                placeholder="Enter new label (optional)",
                name="label",
                width="100%",
                default_value=RelabelBatchFormDialogState.form_label,
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
        state=RelabelBatchFormDialogState,
        title="Relabel Batch",
        description="Change the batch number and/or label. This action will be logged in the activity history.",
        form_content=_form_content(),
        max_width="450px",
    )


def relabel_batch_dialog() -> rx.Component:
    """Dialog component for relabeling a batch.

    This component provides just the dialog (without a trigger button).
    The dialog is controlled by the RelabelBatchFormDialogState.dialog_opened state.

    To open the dialog, call RelabelBatchFormDialogState.open_relabel_dialog(batch)
    with the batch to relabel.

    :return: The relabel batch dialog component
    :rtype: rx.Component
    """
    return _dialog()
