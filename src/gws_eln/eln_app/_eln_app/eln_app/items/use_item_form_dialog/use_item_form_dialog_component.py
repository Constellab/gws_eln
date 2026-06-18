"""Use item form dialog component."""

import reflex as rx
from gws_reflex_main import form_dialog_component

from .use_item_form_dialog_state import UseItemFormDialogState


def _form_content() -> rx.Component:
    """Form content for recording a use of an instrument item."""
    return rx.vstack(
        # ItemSheet Name (read-only display)
        rx.vstack(
            rx.text("ItemSheet", size="2", weight="bold"),
            rx.text(
                UseItemFormDialogState.item_sheet_name,
                size="2",
                color="gray",
            ),
            width="100%",
            spacing="1",
        ),
        # Code (read-only display)
        rx.vstack(
            rx.text("Code", size="2", weight="bold"),
            rx.code(
                UseItemFormDialogState.current_code,
                size="2",
            ),
            width="100%",
            spacing="1",
            align="start",
        ),
        rx.divider(margin_y="0.5rem"),
        # Notes field (optional)
        rx.vstack(
            rx.text("Notes", size="2", weight="bold"),
            rx.text_area(
                placeholder="What was this instrument used for? (optional)",
                name="notes",
                width="100%",
                default_value=UseItemFormDialogState.form_notes,
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
        state=UseItemFormDialogState,
        title="Use Item",
        description="Record that this instrument was used. Logged in the activity history.",
        form_content=_form_content(),
        max_width="450px",
    )


def use_item_dialog() -> rx.Component:
    """Dialog component for recording a use of an instrument item.

    This component provides just the dialog (without a trigger button).
    The dialog is controlled by the UseItemFormDialogState.dialog_opened state.

    To open the dialog, call UseItemFormDialogState.open_use_dialog(item)
    with the item to use.

    :return: The use item dialog component
    :rtype: rx.Component
    """
    return _dialog()
