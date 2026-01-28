"""Note activity form dialog component.

Two-step dialog for adding a batch activity from within a note:
1. Select a batch and an activity type
2. Fill in the activity-specific sub-form (reused from existing form sections)
"""

import reflex as rx
from gws_reflex_main import form_dialog_component

from ..common.activity.activity_type_select_component import (
    activity_type_select_component,
)
from ..common.activity_form_sections import (
    aliquot_form_section,
    move_form_section,
    receive_consume_form_section,
    relabel_form_section,
    use_discard_form_section,
)
from ..common.batch.batch_select_component import batch_select_component
from .note_activity_form_dialog_state import NoteActivityFormDialogState

S = NoteActivityFormDialogState


def _batch_info_section() -> rx.Component:
    """Read-only display of selected batch info, shown when a sub-form is active."""
    return rx.cond(
        S.show_sub_form,
        rx.vstack(
            rx.vstack(
                rx.text("Current Quantity", size="2", weight="bold"),
                rx.text(S.current_quantity, size="2", color="gray"),
                width="100%",
                spacing="1",
            ),
            rx.divider(),
            width="100%",
            spacing="3",
        ),
    )


def _sub_form() -> rx.Component:
    """Conditionally render the activity-specific sub-form."""
    return rx.fragment(
        rx.cond(
            S.show_receive_consume_form,
            receive_consume_form_section(
                unit_type=S.form_unit_type,
                unit_value=S.form_unit,
                on_unit_change=S.set_unit,
                quantity_label=S.quantity_label,
                form_notes=S.form_notes,
            ),
        ),
        rx.cond(
            S.show_move_form,
            rx.fragment(
                rx.vstack(
                    rx.text("Current Location", size="2", weight="bold"),
                    rx.text(S.current_location_name, size="2", color="gray"),
                    width="100%",
                    spacing="1",
                ),
                move_form_section(
                    form_location_id=S.form_location_id,
                    on_location_change=S.set_location_id,
                ),
            ),
        ),
        rx.cond(
            S.show_use_discard_form,
            use_discard_form_section(
                form_notes=S.form_notes,
            ),
        ),
        rx.cond(
            S.show_relabel_form,
            relabel_form_section(
                form_batch_number=S.form_batch_number,
                form_label=S.form_label,
            ),
        ),
        rx.cond(
            S.show_aliquot_form,
            aliquot_form_section(
                form_unit_type=S.form_unit_type,
                form_source_unit=S.form_source_unit,
                on_source_unit_change=S.set_source_unit,
                form_aliquot_unit=S.form_aliquot_unit,
                on_aliquot_unit_change=S.set_aliquot_unit,
                form_location_id=S.form_location_id,
                on_location_change=S.set_location_id,
                form_supplier_id=S.form_supplier_id,
                on_supplier_change=S.set_supplier_id,
                form_notes=S.form_notes,
            ),
        ),
    )


def _form_content() -> rx.Component:
    """Full form content: selection step + dynamic sub-form."""
    return rx.vstack(
        # Step 1: Batch selection
        rx.vstack(
            rx.text("Batch*", size="2", weight="bold"),
            batch_select_component(
                placeholder="Select a batch...",
                value=S.form_batch_id,
                on_change=S.set_batch_id,
            ),
            width="100%",
            spacing="1",
        ),
        # Step 1: Activity type selection
        rx.vstack(
            rx.text("Activity Type*", size="2", weight="bold"),
            activity_type_select_component(
                value=S.form_activity_type,
                on_change=S.set_activity_type,
            ),
            width="100%",
            spacing="1",
        ),
        # Batch info + sub-form (shown after both selections)
        _batch_info_section(),
        _sub_form(),
        width="100%",
        spacing="3",
    )


def _dialog() -> rx.Component:
    """The dialog component."""
    return form_dialog_component(
        state=NoteActivityFormDialogState,
        title="Add Batch Activity",
        description="Select a batch and an activity to record from this note.",
        form_content=_form_content(),
        max_width="500px",
    )


def note_activity_form_dialog() -> rx.Component:
    """Dialog component for adding a batch activity from a note.

    This component provides the dialog (without a trigger button).
    The dialog is controlled by NoteActivityFormDialogState.dialog_opened.

    To open the dialog, call:
        NoteActivityFormDialogState.open_dialog(note_id, note_block_id)

    :return: The note activity form dialog component
    :rtype: rx.Component
    """
    return _dialog()
