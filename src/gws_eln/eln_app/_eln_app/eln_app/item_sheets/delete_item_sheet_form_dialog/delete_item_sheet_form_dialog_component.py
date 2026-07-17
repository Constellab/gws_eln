"""Delete/discard item sheet form dialog component."""

import reflex as rx
from gws_reflex_main import form_dialog_component

from ...activities.activity_form_sections import use_discard_form_section
from .delete_item_sheet_form_dialog_state import DeleteItemSheetFormDialogState


def _form_content() -> rx.Component:
    """Form content for deleting/discarding an item sheet."""
    return rx.vstack(
        # Context-dependent callout: discard (still holds discarded items) vs hard
        # delete (no items). A blocked sheet never reaches this dialog - it is
        # refused with a toast instead.
        rx.cond(
            DeleteItemSheetFormDialogState.is_discard,
            rx.callout(
                "This item sheet still holds discarded items, so it will be "
                "marked as discarded (not deleted). A reason is required.",
                icon="triangle_alert",
                color="red",
            ),
            rx.callout(
                "This item sheet has no items and will be permanently deleted. "
                "This action cannot be undone.",
                icon="triangle_alert",
                color="red",
            ),
        ),
        # Sheet name (read-only)
        rx.vstack(
            rx.text("Item sheet", size="2", weight="bold"),
            rx.text(DeleteItemSheetFormDialogState.name, size="2", color="gray"),
            width="100%",
            spacing="1",
            align="start",
        ),
        # Reason: only when discarding (required).
        rx.cond(
            DeleteItemSheetFormDialogState.is_discard,
            use_discard_form_section(
                form_notes=DeleteItemSheetFormDialogState.form_reason,
                notes_label="Reason *",
                notes_placeholder="Enter reason for discarding this item sheet",
                on_notes_change=DeleteItemSheetFormDialogState.set_reason,
            ),
        ),
        width="100%",
        spacing="3",
    )


def delete_item_sheet_dialog() -> rx.Component:
    """Dialog for deleting/discarding an item sheet (no trigger).

    Open it with ``DeleteItemSheetFormDialogState.open_delete_dialog(item_sheet)``.

    :return: The delete item sheet dialog component.
    :rtype: rx.Component
    """
    return form_dialog_component(
        state=DeleteItemSheetFormDialogState,
        title="Delete item sheet",
        description="Are you sure you want to delete this item sheet?",
        form_content=_form_content(),
        max_width="450px",
    )
