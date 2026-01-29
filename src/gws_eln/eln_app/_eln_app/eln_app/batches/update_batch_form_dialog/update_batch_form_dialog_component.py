"""Update batch form dialog component."""

import reflex as rx
from gws_reflex_main import form_dialog_component

from ...suppliers.core.supplier_select_component import supplier_select_component
from .update_batch_form_dialog_state import UpdateBatchFormDialogState


def _form_content() -> rx.Component:
    """Form content for updating batch metadata."""
    return rx.vstack(
        # Batch Number (read-only display)
        rx.vstack(
            rx.text("Batch", size="2", weight="bold"),
            rx.text(
                UpdateBatchFormDialogState.batch_number,
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
                UpdateBatchFormDialogState.material_name,
                size="2",
                color="gray",
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
                value=UpdateBatchFormDialogState.form_supplier_id,
                on_change=UpdateBatchFormDialogState.set_supplier_id,
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
                value=UpdateBatchFormDialogState.form_expiry_date,
                on_change=UpdateBatchFormDialogState.set_expiry_date,
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
                default_value=UpdateBatchFormDialogState.form_notes,
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
        state=UpdateBatchFormDialogState,
        title="Update Batch",
        description="Update batch metadata (supplier, expiry date, notes).",
        form_content=_form_content(),
        max_width="450px",
    )


def update_batch_dialog() -> rx.Component:
    """Dialog component for updating batch metadata.

    This component provides just the dialog (without a trigger button).
    The dialog is controlled by the UpdateBatchFormDialogState.dialog_opened state.

    To open the dialog, call UpdateBatchFormDialogState.open_update_dialog(batch)
    with the batch to update.

    :return: The update batch dialog component
    :rtype: rx.Component
    """
    return _dialog()
