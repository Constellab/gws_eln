"""Relabel item form dialog component."""

import reflex as rx
from gws_reflex_main import form_dialog_component

from ...activities.activity_form_sections import relabel_form_section
from .relabel_item_form_dialog_state import RelabelItemFormDialogState


def _form_content() -> rx.Component:
    """Form content for relabeling a item."""
    return rx.vstack(
        # ItemSheet Name (read-only display)
        rx.vstack(
            rx.text("Item sheet", size="2", weight="bold"),
            rx.text(
                RelabelItemFormDialogState.item_sheet_name,
                size="2",
                color="gray",
            ),
            width="100%",
            spacing="1",
        ),
        # Current Code (read-only display)
        rx.vstack(
            rx.text("Code", size="2", weight="bold"),
            rx.code(
                RelabelItemFormDialogState.current_code,
                size="2",
            ),
            width="100%",
            spacing="1",
            align="start",
        ),
        # Current Label (read-only display)
        rx.vstack(
            rx.text("Current Label", size="2", weight="bold"),
            rx.text(
                RelabelItemFormDialogState.current_label,
                size="2",
                color="gray",
            ),
            width="100%",
            spacing="1",
        ),
        rx.divider(margin_y="0.5rem"),
        # Reusable relabel form section
        relabel_form_section(
            form_label=RelabelItemFormDialogState.form_label,
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
        state=RelabelItemFormDialogState,
        title="Relabel Item",
        description="Change the item's label. This action will be logged in the activity history.",
        form_content=_form_content(),
        max_width="450px",
    )


def relabel_item_dialog() -> rx.Component:
    """Dialog component for relabeling a item.

    This component provides just the dialog (without a trigger button).
    The dialog is controlled by the RelabelItemFormDialogState.dialog_opened state.

    To open the dialog, call RelabelItemFormDialogState.open_relabel_dialog(item)
    with the item to relabel.

    :return: The relabel item dialog component
    :rtype: rx.Component
    """
    return _dialog()
