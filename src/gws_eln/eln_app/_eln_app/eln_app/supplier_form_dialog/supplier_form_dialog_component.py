import reflex as rx
from gws_reflex_main import form_dialog_component

from .supplier_form_dialog_state import SupplierFormDialogState


def _form_content() -> rx.Component:
    """Form content for entering supplier details."""
    return rx.vstack(
        # Supplier Name field
        rx.vstack(
            rx.text("Supplier Name*", size="2", weight="bold"),
            rx.input(
                placeholder="Enter supplier name",
                name="name",
                required=True,
                width="100%",
                default_value=SupplierFormDialogState.form_name,
            ),
            width="100%",
            spacing="1",
        ),
        # Contact Info field
        rx.vstack(
            rx.text("Contact Info", size="2", weight="bold"),
            rx.text_area(
                placeholder="Enter contact information (optional)",
                name="description",
                width="100%",
                default_value=SupplierFormDialogState.form_description,
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
        state=SupplierFormDialogState,
        title=rx.cond(
            SupplierFormDialogState.is_update_mode, "Update Supplier", "Create New Supplier"
        ),
        description=rx.cond(
            SupplierFormDialogState.is_update_mode,
            "Update the supplier details below.",
            "Fill in the details below to create a new supplier.",
        ),
        form_content=_form_content(),
        max_width="450px",
    )


def create_supplier_dialog() -> rx.Component:
    """Dialog component for creating a new supplier with a trigger button.

    Displays a form for entering supplier details. Success and error messages
    are displayed as toast notifications.

    :return: The create supplier dialog component with trigger button
    :rtype: rx.Component
    """
    return rx.fragment(
        rx.button(
            rx.icon("plus", size=18),
            "Create New Supplier",
            size="3",
            on_click=SupplierFormDialogState.open_create_dialog,
        ),
        _dialog(),
    )


def supplier_update_dialog() -> rx.Component:
    """Dialog component for updating an existing supplier.

    This component provides just the dialog (without a trigger button).
    The dialog is controlled by the SupplierFormDialogState.dialog_opened state.

    :return: The update supplier dialog component
    :rtype: rx.Component
    """
    return _dialog()
