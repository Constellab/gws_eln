"""Relabel item form dialog component."""

import reflex as rx
from gws_reflex_main import form_dialog_component

from ...activities.activity_form_sections import relabel_form_section
from .relabel_item_form_dialog_state import RelabelItemFormDialogState


def _form_content() -> rx.Component:
    """Form content for relabeling a item."""
    return rx.vstack(
        # Item info (read-only display): current name and code side by side
        rx.hstack(
            rx.vstack(
                rx.text("Current name", size="2", weight="bold"),
                rx.text(
                    RelabelItemFormDialogState.current_label,
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
                    RelabelItemFormDialogState.current_code,
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
        subtitle="Change the item's label. This action will be logged in the activity history.",
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
