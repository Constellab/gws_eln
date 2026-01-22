import reflex as rx
from gws_eln.suppliers.supplier_dto import SupplierDTO
from gws_reflex_main import form_dialog_component

from .material_form_dialog_state import MaterialFormDialogState


def _supplier_option(supplier: SupplierDTO) -> rx.Component:
    """Create a select option for a supplier."""
    return rx.select.item(supplier.name, value=supplier.id)


def _form_content() -> rx.Component:
    """Form content for entering material details."""
    return rx.vstack(
        # Material Name field
        rx.vstack(
            rx.text("Material Name*", size="2", weight="bold"),
            rx.input(
                placeholder="Enter material name",
                name="name",
                required=True,
                width="100%",
                default_value=MaterialFormDialogState.form_name,
            ),
            width="100%",
            spacing="1",
        ),
        # Description field
        rx.vstack(
            rx.text("Description", size="2", weight="bold"),
            rx.text_area(
                placeholder="Enter material description (optional)",
                name="description",
                width="100%",
                default_value=MaterialFormDialogState.form_description,
                rows="3",
            ),
            width="100%",
            spacing="1",
        ),
        # Default Supplier field
        rx.vstack(
            rx.text("Default Supplier", size="2", weight="bold"),
            rx.select.root(
                rx.select.trigger(placeholder="Select a supplier (optional)", width="100%"),
                rx.select.content(
                    rx.select.item("No supplier", value="__none__"),
                    rx.foreach(MaterialFormDialogState.available_suppliers, _supplier_option),
                ),
                value=MaterialFormDialogState.form_supplier_id,
                on_change=MaterialFormDialogState.set_supplier_id,
                width="100%",
            ),
            width="100%",
            spacing="1",
        ),
        # Unit Type field
        rx.vstack(
            rx.text("Default Unit Type", size="2", weight="bold"),
            rx.select.root(
                rx.select.trigger(placeholder="Select unit type", width="100%"),
                rx.select.content(
                    rx.foreach(
                        MaterialFormDialogState.unit_type_options,
                        lambda opt: rx.select.item(opt["label"], value=opt["value"]),
                    ),
                ),
                value=MaterialFormDialogState.form_unit_type,
                on_change=MaterialFormDialogState.set_unit_type,
                width="100%",
            ),
            width="100%",
            spacing="1",
        ),
        # Consumable checkbox
        rx.hstack(
            rx.checkbox(
                checked=MaterialFormDialogState.form_is_consumable,
                on_change=MaterialFormDialogState.set_is_consumable,
            ),
            rx.text("Consumable material", size="2"),
            rx.tooltip(
                rx.icon("info", size=14, color="gray"),
                content="Consumable materials (chemicals, reagents) have quantity that decreases with use. Non-consumables (instruments, equipment) are tracked by reference only.",
            ),
            spacing="2",
            align="center",
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
        state=MaterialFormDialogState,
        title=rx.cond(MaterialFormDialogState.is_update_mode, "Update Material", "Create New Material"),
        description=rx.cond(
            MaterialFormDialogState.is_update_mode,
            "Update the material details below.",
            "Fill in the details below to create a new material.",
        ),
        form_content=_form_content(),
        max_width="500px",
    )


def create_material_dialog() -> rx.Component:
    """Dialog component for creating a new material with a trigger button.

    Displays a form for entering material details. Success and error messages
    are displayed as toast notifications.

    :return: The create material dialog component with trigger button
    :rtype: rx.Component
    """
    return rx.fragment(
        rx.button(
            rx.icon("plus", size=18), "Create New Material", size="3", on_click=MaterialFormDialogState.open_create_dialog
        ),
        _dialog(),
    )


def material_update_dialog() -> rx.Component:
    """Dialog component for updating an existing material.

    This component provides just the dialog (without a trigger button).
    The dialog is controlled by the MaterialFormDialogState.dialog_opened state.

    :return: The update material dialog component
    :rtype: rx.Component
    """
    return _dialog()
