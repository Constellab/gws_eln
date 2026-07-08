import reflex as rx
from gws_reflex_main import form_dialog_component

from ...activities.activity_form_sections import move_form_section
from .move_item_form_dialog_state import MoveItemFormDialogState


def _form_content() -> rx.Component:
    """Form content for moving a item to a new location."""
    return rx.vstack(
        # Item info (read-only display): name and code side by side
        rx.hstack(
            rx.vstack(
                rx.text("Item name", size="2", weight="bold"),
                rx.text(
                    MoveItemFormDialogState.label,
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
                    MoveItemFormDialogState.code,
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
        # Current Location (read-only display)
        rx.vstack(
            rx.text("Current Location", size="2", weight="bold"),
            rx.text(
                MoveItemFormDialogState.current_location_name,
                size="2",
                color="gray",
            ),
            width="100%",
            spacing="1",
        ),
        # Reusable move form section
        move_form_section(
            form_location_id=MoveItemFormDialogState.form_location_id,
            on_location_change=MoveItemFormDialogState.set_location_id,
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
        state=MoveItemFormDialogState,
        title="Move Item",
        subtitle="Select the destination location to move this item.",
        form_content=_form_content(),
        max_width="450px",
    )


def move_item_dialog() -> rx.Component:
    """Dialog component for moving a item to a new location.

    This component provides just the dialog (without a trigger button).
    The dialog is controlled by the MoveItemFormDialogState.dialog_opened state.

    To open the dialog, call MoveItemFormDialogState.open_move_dialog(item)
    with the item to move.

    :return: The move item dialog component
    :rtype: rx.Component
    """
    return _dialog()
