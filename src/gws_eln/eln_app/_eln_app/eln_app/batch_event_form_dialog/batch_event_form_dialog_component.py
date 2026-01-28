"""Batch event form dialog component for Receive, Increment, Decrement operations."""

import reflex as rx
from gws_reflex_main import form_dialog_component

from ..common.activity_form_sections import receive_consume_form_section
from .batch_event_form_dialog_state import BatchEventFormDialogState


def _form_content() -> rx.Component:
    """Form content for entering batch event details."""
    return rx.vstack(
        # Batch info (read-only display)
        rx.vstack(
            rx.text("Batch", size="2", weight="bold"),
            rx.text(
                BatchEventFormDialogState.batch_number,
                size="2",
                color="gray",
            ),
            width="100%",
            spacing="1",
        ),
        # Current quantity display
        rx.vstack(
            rx.text("Current Quantity", size="2", weight="bold"),
            rx.text(
                BatchEventFormDialogState.current_quantity,
                size="2",
                color="gray",
            ),
            width="100%",
            spacing="1",
        ),
        # Reusable receive/consume form section
        receive_consume_form_section(
            unit_type=BatchEventFormDialogState.form_unit_type,
            unit_value=BatchEventFormDialogState.form_unit,
            on_unit_change=BatchEventFormDialogState.set_unit,
            quantity_label=BatchEventFormDialogState.quantity_label,
            form_notes=BatchEventFormDialogState.form_notes,
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
        state=BatchEventFormDialogState,
        title=BatchEventFormDialogState.dialog_title,
        description=BatchEventFormDialogState.dialog_description,
        form_content=_form_content(),
        max_width="450px",
    )


def batch_event_form_dialog() -> rx.Component:
    """Dialog component for batch events (Receive, Increment, Decrement).

    This component provides just the dialog (without a trigger button).
    The dialog is controlled by the BatchEventFormDialogState.dialog_opened state.

    To open the dialog, call BatchEventFormDialogState.open_dialog_for_event(batch_id, event_type)
    with the batch ID and event type ('receive', 'increment', 'decrement').

    :return: The batch event form dialog component
    :rtype: rx.Component
    """
    return _dialog()
