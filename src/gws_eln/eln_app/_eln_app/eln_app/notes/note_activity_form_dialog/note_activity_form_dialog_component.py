"""Note activity form dialog component.

Two-step dialog for adding a item activity from within a note:
1. Select a item and an activity type
2. Fill in the activity-specific sub-form (reused from existing form sections)
"""

import reflex as rx
from gws_reflex_main import form_dialog_component

from ...activities.activity_form_sections import (
    aliquot_form_section,
    create_item_form_section,
    move_form_section,
    receive_consume_form_section,
    relabel_form_section,
    use_discard_form_section,
)
from ...activities.activity_type_select_component import (
    activity_type_select_component,
)
from ...items.core.item_select_component import item_select_component
from .note_activity_form_dialog_state import NoteActivityFormDialogState

S = NoteActivityFormDialogState


def _item_info_section() -> rx.Component:
    """Read-only display of selected item info, shown when a sub-form is active (except for CREATE)."""
    return rx.cond(
        S.show_item_select & S.item,
        rx.vstack(
            rx.vstack(
                rx.text("Current Quantity", size="2", weight="bold"),
                rx.text(S.item.pretty_quantity, size="2", color="gray"),
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
            S.show_create_form,
            create_item_form_section(
                form_item_sheet=S.form_item_sheet,
                on_item_sheet_change=S.set_item_sheet,
                form_unit_type=S.form_unit_type,
                form_unit=S.form_unit,
                on_unit_change=S.set_unit,
                form_location_id=S.form_location_id,
                on_location_change=S.set_location_id,
                form_supplier_id=S.form_supplier_id,
                on_supplier_change=S.set_supplier_id,
                form_notes=S.form_notes,
            ),
        ),
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
                form_item_number=S.form_item_number,
                form_label=S.form_label,
            ),
        ),
        rx.cond(
            S.show_aliquot_form,
            aliquot_form_section(
                form_unit_type=S.form_unit_type,
                form_source_unit=S.form_source_unit,
                on_source_unit_change=S.set_source_unit,
                form_aliquot_unit_type=S.form_aliquot_unit_type,
                form_aliquot_unit=S.form_aliquot_unit,
                on_aliquot_unit_change=S.set_aliquot_unit,
                form_location_id=S.form_location_id,
                on_location_change=S.set_location_id,
                form_supplier_id=S.form_supplier_id,
                on_supplier_change=S.set_supplier_id,
                form_notes=S.form_notes,
                form_target_item_sheet=S.form_target_item_sheet,
                on_target_item_sheet_change=S.set_target_item_sheet,
                form_parent_item=S.form_item,
                parent_item=S.item,
                on_parent_item_change=S.set_item,
                item_select_disabled=False,
            ),
        ),
    )


def _form_content() -> rx.Component:
    """Full form content: selection step + dynamic sub-form."""
    return rx.vstack(
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
        rx.cond(
            S.show_item_select,
            # For other activities: show item selector
            rx.vstack(
                item_select_component(
                    placeholder="Select a item...",
                    selected_item=S.form_item,
                    item_selected=S.set_item,
                ),
                width="100%",
                spacing="1",
            ),
        ),
        # Item info + sub-form (shown after both selections)
        _item_info_section(),
        _sub_form(),
        width="100%",
        spacing="3",
    )


def _dialog() -> rx.Component:
    """The dialog component."""
    return form_dialog_component(
        state=NoteActivityFormDialogState,
        title="Add Item Activity",
        description="Select a item and an activity to record from this note.",
        form_content=_form_content(),
        max_width="500px",
    )


def note_activity_form_dialog() -> rx.Component:
    """Dialog component for adding a item activity from a note.

    This component provides the dialog (without a trigger button).
    The dialog is controlled by NoteActivityFormDialogState.dialog_opened.

    To open the dialog, call:
        NoteActivityFormDialogState.open_dialog(note_id, note_block_id)

    :return: The note activity form dialog component
    :rtype: rx.Component
    """
    return _dialog()
