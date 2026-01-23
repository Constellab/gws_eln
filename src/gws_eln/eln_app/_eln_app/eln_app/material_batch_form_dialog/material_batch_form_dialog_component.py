import reflex as rx
from gws_reflex_main import form_dialog_component

from ..common.location.location_select_component import (
    location_select_component,
)
from ..common.supplier.supplier_select_component import (
    supplier_select_component,
)
from ..common.unit.unit_components import quantity_unit_input
from .material_batch_form_dialog_state import MaterialBatchFormDialogState


def _form_content() -> rx.Component:
    """Form content for entering material batch details."""
    return rx.vstack(
        # Material Name (read-only display)
        rx.vstack(
            rx.text("Material", size="2", weight="bold"),
            rx.text(
                MaterialBatchFormDialogState.material_name,
                size="2",
                color="gray",
            ),
            width="100%",
            spacing="1",
        ),
        # Batch Number field
        rx.vstack(
            rx.text("Batch Number*", size="2", weight="bold"),
            rx.input(
                placeholder="Enter batch number (e.g., LOT-2024-001)",
                name="batch_number",
                required=True,
                width="100%",
                default_value=MaterialBatchFormDialogState.form_batch_number,
            ),
            width="100%",
            spacing="1",
        ),
        quantity_unit_input(
            unit_type=MaterialBatchFormDialogState.form_unit_type,
            unit_value=MaterialBatchFormDialogState.form_unit,
            on_unit_change=MaterialBatchFormDialogState.set_unit,
        ),
        # Location field
        rx.vstack(
            rx.text("Location*", size="2", weight="bold"),
            location_select_component(
                placeholder="Select a location",
                value=MaterialBatchFormDialogState.form_location_id,
                on_change=MaterialBatchFormDialogState.set_location_id,
                required=True,
            ),
            width="100%",
            spacing="1",
        ),
        # Supplier field
        rx.vstack(
            rx.text("Supplier", size="2", weight="bold"),
            supplier_select_component(
                placeholder="Select a supplier (optional)",
                additional_option=("No supplier", "__none__"),
                value=MaterialBatchFormDialogState.form_supplier_id,
                on_change=MaterialBatchFormDialogState.set_supplier_id,
            ),
            width="100%",
            spacing="1",
        ),
        # Expiry Date field
        rx.vstack(
            rx.text("Expiry Date", size="2", weight="bold"),
            rx.input(
                placeholder="Select expiry date (optional)",
                name="expiry_date",
                type="date",
                width="100%",
                default_value=MaterialBatchFormDialogState.form_expiry_date,
                on_change=MaterialBatchFormDialogState.set_expiry_date,
            ),
            width="100%",
            spacing="1",
        ),
        # Label field
        rx.vstack(
            rx.text("Label", size="2", weight="bold"),
            rx.input(
                placeholder="Enter custom label (optional)",
                name="label",
                width="100%",
                default_value=MaterialBatchFormDialogState.form_label,
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
                default_value=MaterialBatchFormDialogState.form_notes,
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
        state=MaterialBatchFormDialogState,
        title="Create New Batch",
        description="Fill in the details below to create a new material batch.",
        form_content=_form_content(),
        max_width="550px",
    )


def create_material_batch_dialog() -> rx.Component:
    """Dialog component for creating a new material batch.

    This component provides just the dialog (without a trigger button).
    The dialog is controlled by the MaterialBatchFormDialogState.dialog_opened state.

    To open the dialog, call MaterialBatchFormDialogState.open_create_dialog(material)
    with the material for which to create a batch.

    :return: The create material batch dialog component
    :rtype: rx.Component
    """
    return _dialog()
