import reflex as rx
from gws_eln.locations.location_dto import LocationDTO
from gws_eln.suppliers.supplier_dto import SupplierDTO
from gws_reflex_main import form_dialog_component

from .material_batch_form_dialog_state import MaterialBatchFormDialogState


def _location_option(location: LocationDTO) -> rx.Component:
    """Create a select option for a location."""
    return rx.select.item(location.name, value=location.id)


def _supplier_option(supplier: SupplierDTO) -> rx.Component:
    """Create a select option for a supplier."""
    return rx.select.item(supplier.name, value=supplier.id)


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
        # Quantity and Unit Type fields (side by side)
        rx.hstack(
            rx.vstack(
                rx.text("Quantity*", size="2", weight="bold"),
                rx.input(
                    placeholder="Enter quantity",
                    name="quantity",
                    type="number",
                    min="0",
                    step="any",
                    required=True,
                    width="100%",
                    default_value=MaterialBatchFormDialogState.form_quantity,
                ),
                width="60%",
                spacing="1",
            ),
            rx.vstack(
                rx.text("Unit Type*", size="2", weight="bold"),
                rx.select.root(
                    rx.select.trigger(placeholder="Select unit type", width="100%"),
                    rx.select.content(
                        rx.foreach(
                            MaterialBatchFormDialogState.unit_type_options,
                            lambda opt: rx.select.item(opt["label"], value=opt["value"]),
                        ),
                    ),
                    value=MaterialBatchFormDialogState.form_unit_type,
                    on_change=MaterialBatchFormDialogState.set_unit_type,
                    width="100%",
                ),
                width="40%",
                spacing="1",
            ),
            width="100%",
            spacing="3",
        ),
        # Location field
        rx.vstack(
            rx.text("Location*", size="2", weight="bold"),
            rx.select.root(
                rx.select.trigger(placeholder="Select a location", width="100%"),
                rx.select.content(
                    rx.foreach(MaterialBatchFormDialogState.available_locations, _location_option),
                ),
                value=MaterialBatchFormDialogState.form_location_id,
                on_change=MaterialBatchFormDialogState.set_location_id,
                width="100%",
            ),
            width="100%",
            spacing="1",
        ),
        # Supplier field
        rx.vstack(
            rx.text("Supplier", size="2", weight="bold"),
            rx.select.root(
                rx.select.trigger(placeholder="Select a supplier (optional)", width="100%"),
                rx.select.content(
                    rx.select.item("No supplier", value="__none__"),
                    rx.foreach(MaterialBatchFormDialogState.available_suppliers, _supplier_option),
                ),
                value=MaterialBatchFormDialogState.form_supplier_id,
                on_change=MaterialBatchFormDialogState.set_supplier_id,
                width="100%",
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
