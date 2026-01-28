"""Aliquot form dialog component for creating aliquots from a parent batch."""

import reflex as rx
from gws_reflex_main import form_dialog_component

from ..common.activity_form_sections import aliquot_form_section
from .aliquot_form_dialog_state import AliquotFormDialogState


def _form_content() -> rx.Component:
    """Form content for entering aliquot details."""
    return aliquot_form_section(
        form_unit_type=AliquotFormDialogState.form_unit_type,
        form_source_unit=AliquotFormDialogState.form_source_unit,
        on_source_unit_change=AliquotFormDialogState.set_source_unit,
        form_aliquot_unit_type=AliquotFormDialogState.form_aliquot_unit_type,
        form_aliquot_unit=AliquotFormDialogState.form_aliquot_unit,
        on_aliquot_unit_change=AliquotFormDialogState.set_aliquot_unit,
        form_location_id=AliquotFormDialogState.form_location_id,
        on_location_change=AliquotFormDialogState.set_location_id,
        form_supplier_id=AliquotFormDialogState.form_supplier_id,
        on_supplier_change=AliquotFormDialogState.set_supplier_id,
        form_notes=AliquotFormDialogState.form_notes,
        form_target_material_id=AliquotFormDialogState.form_target_material_id,
        on_target_material_change=AliquotFormDialogState.set_target_material_id,
        parent_batch_number=AliquotFormDialogState.batch_number,
        parent_available_quantity=AliquotFormDialogState.current_quantity,
    )


def _dialog() -> rx.Component:
    """The base dialog component without a trigger.

    This can be reused in different contexts with different triggers.

    :return: The dialog component
    :rtype: rx.Component
    """
    return form_dialog_component(
        state=AliquotFormDialogState,
        title=AliquotFormDialogState.dialog_title,
        description=AliquotFormDialogState.dialog_description,
        form_content=_form_content(),
        max_width="500px",
    )


def aliquot_form_dialog() -> rx.Component:
    """Dialog component for creating aliquots from a parent batch.

    This component provides just the dialog (without a trigger button).
    The dialog is controlled by the AliquotFormDialogState.dialog_opened state.

    To open the dialog, call AliquotFormDialogState.open_dialog(batch)
    with the parent batch DTO.

    :return: The aliquot form dialog component
    :rtype: rx.Component
    """
    return _dialog()
