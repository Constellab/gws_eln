import reflex as rx
from gws_reflex_main import form_dialog_component

from ...activities.activity_form_sections import move_form_section
from .move_batch_form_dialog_state import MoveBatchFormDialogState


def _form_content() -> rx.Component:
    """Form content for moving a batch to a new location."""
    return rx.vstack(
        # Batch Number (read-only display)
        rx.vstack(
            rx.text("Batch", size="2", weight="bold"),
            rx.text(
                MoveBatchFormDialogState.batch_number,
                size="2",
                color="gray",
            ),
            width="100%",
            spacing="1",
        ),
        # Current Location (read-only display)
        rx.vstack(
            rx.text("Current Location", size="2", weight="bold"),
            rx.text(
                MoveBatchFormDialogState.current_location_name,
                size="2",
                color="gray",
            ),
            width="100%",
            spacing="1",
        ),
        # Reusable move form section
        move_form_section(
            form_location_id=MoveBatchFormDialogState.form_location_id,
            on_location_change=MoveBatchFormDialogState.set_location_id,
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
        state=MoveBatchFormDialogState,
        title="Move Batch",
        description="Select the destination location to move this batch.",
        form_content=_form_content(),
        max_width="450px",
    )


def move_batch_dialog() -> rx.Component:
    """Dialog component for moving a batch to a new location.

    This component provides just the dialog (without a trigger button).
    The dialog is controlled by the MoveBatchFormDialogState.dialog_opened state.

    To open the dialog, call MoveBatchFormDialogState.open_move_dialog(batch)
    with the batch to move.

    :return: The move batch dialog component
    :rtype: rx.Component
    """
    return _dialog()
