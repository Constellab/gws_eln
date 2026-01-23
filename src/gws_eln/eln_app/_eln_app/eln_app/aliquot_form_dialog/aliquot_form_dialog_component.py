"""Aliquot form dialog component for creating aliquots from a parent batch."""

import reflex as rx
from gws_reflex_main import form_dialog_component

from ..common.location.location_select_component import location_select_component
from ..common.supplier.supplier_select_component import supplier_select_component
from ..common.unit.unit_components import quantity_unit_input
from .aliquot_form_dialog_state import AliquotFormDialogState


def _form_content() -> rx.Component:
    """Form content for entering aliquot details."""
    return rx.vstack(
        # Parent batch info (read-only display)
        rx.vstack(
            rx.text("Parent Batch", size="2", weight="bold"),
            rx.text(
                AliquotFormDialogState.batch_number,
                size="2",
                color="gray",
            ),
            width="100%",
            spacing="1",
        ),
        # Current quantity display
        rx.vstack(
            rx.text("Available Quantity", size="2", weight="bold"),
            rx.text(
                AliquotFormDialogState.current_quantity,
                size="2",
                color="gray",
            ),
            width="100%",
            spacing="1",
        ),
        rx.divider(),
        # Source quantity (amount to take from parent)
        quantity_unit_input(
            unit_type=AliquotFormDialogState.form_unit_type,
            quantity_name="source_quantity",
            unit_name="source_unit",
            unit_value=AliquotFormDialogState.form_source_unit,
            on_unit_change=AliquotFormDialogState.set_source_unit,
            quantity_label="Source Quantity",
            unit_label="Unit",
            quantity_placeholder="Amount to take from parent",
        ),
        # Aliquot quantity (amount for the new aliquot)
        quantity_unit_input(
            unit_type=AliquotFormDialogState.form_unit_type,
            quantity_name="aliquot_quantity",
            unit_name="aliquot_unit",
            unit_value=AliquotFormDialogState.form_aliquot_unit,
            on_unit_change=AliquotFormDialogState.set_aliquot_unit,
            quantity_label="Aliquot Quantity",
            unit_label="Unit",
            quantity_placeholder="Amount for new aliquot",
        ),
        rx.divider(),
        # Aliquot batch number (optional)
        rx.vstack(
            rx.text("Batch Number", size="2", weight="bold"),
            rx.input(
                placeholder="Auto-generated if empty",
                name="aliquot_batch_number",
                width="100%",
            ),
            rx.text(
                "Leave empty to auto-generate based on parent batch",
                size="1",
                color="gray",
            ),
            width="100%",
            spacing="1",
        ),
        # Label (optional)
        rx.vstack(
            rx.text("Label", size="2", weight="bold"),
            rx.input(
                placeholder="Optional label",
                name="label",
                width="100%",
            ),
            width="100%",
            spacing="1",
        ),
        # Location
        rx.vstack(
            rx.text("Location", size="2", weight="bold"),
            location_select_component(
                placeholder="Select location...",
                value=AliquotFormDialogState.form_location_id,
                on_change=AliquotFormDialogState.set_location_id,
            ),
            width="100%",
            spacing="1",
        ),
        # Supplier (optional)
        rx.vstack(
            rx.text("Supplier", size="2", weight="bold"),
            supplier_select_component(
                placeholder="Select supplier (optional)...",
                value=AliquotFormDialogState.form_supplier_id,
                on_change=AliquotFormDialogState.set_supplier_id,
                additional_option=("None", "__none__"),
            ),
            width="100%",
            spacing="1",
        ),
        # Notes field
        rx.vstack(
            rx.text("Notes", size="2", weight="bold"),
            rx.text_area(
                placeholder="Enter notes (optional)",
                name="notes",
                width="100%",
                default_value=AliquotFormDialogState.form_notes,
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
