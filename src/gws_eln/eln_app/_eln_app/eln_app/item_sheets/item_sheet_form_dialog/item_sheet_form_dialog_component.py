import reflex as rx
from gws_eln.suppliers.supplier_dto import SupplierDTO
from gws_reflex_main import form_dialog_component

from .item_sheet_form_dialog_state import ItemSheetFormDialogState


def _supplier_option(supplier: SupplierDTO) -> rx.Component:
    """Create a select option for a supplier."""
    return rx.select.item(supplier.name, value=supplier.id)


def _form_content() -> rx.Component:
    """Form content for entering item_sheet details."""
    return rx.vstack(
        # ItemSheet Name field
        rx.vstack(
            rx.text("ItemSheet Name*", size="2", weight="bold"),
            rx.input(
                placeholder="Enter item_sheet name",
                name="name",
                required=True,
                width="100%",
                value=ItemSheetFormDialogState.form_name,
                on_change=ItemSheetFormDialogState.set_form_name,
                on_blur=ItemSheetFormDialogState.suggest_code_from_name,
            ),
            width="100%",
            spacing="1",
        ),
        # Code field (create only - the code is immutable once the sheet exists)
        rx.cond(
            ItemSheetFormDialogState.is_update_mode,
            rx.fragment(),
            rx.vstack(
                rx.text("Code* (4 characters, A-Z / 0-9)", size="2", weight="bold"),
                rx.input(
                    placeholder="e.g. ETHA",
                    name="code",
                    required=True,
                    max_length=4,
                    width="100%",
                    value=ItemSheetFormDialogState.form_code,
                    on_change=ItemSheetFormDialogState.set_form_code,
                ),
                width="100%",
                spacing="1",
            ),
        ),
        # Description field
        rx.vstack(
            rx.text("Description", size="2", weight="bold"),
            rx.text_area(
                placeholder="Enter item_sheet description (optional)",
                name="description",
                width="100%",
                default_value=ItemSheetFormDialogState.form_description,
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
                    rx.foreach(ItemSheetFormDialogState.available_suppliers, _supplier_option),
                ),
                value=ItemSheetFormDialogState.form_supplier_id,
                on_change=ItemSheetFormDialogState.set_supplier_id,
                width="100%",
            ),
            width="100%",
            spacing="1",
        ),
        # Unit Type field
        rx.vstack(
            rx.text("Default unit type to use for quantity", size="2", weight="bold"),
            rx.select.root(
                rx.select.trigger(placeholder="Select unit type", width="100%"),
                rx.select.content(
                    rx.foreach(
                        ItemSheetFormDialogState.unit_type_options,
                        lambda opt: rx.select.item(opt["label"], value=opt["value"]),
                    ),
                ),
                value=ItemSheetFormDialogState.form_unit_type,
                on_change=ItemSheetFormDialogState.set_unit_type,
                width="100%",
            ),
            width="100%",
            spacing="1",
        ),
        # Consumable checkbox (only shown in create mode)
        rx.cond(
            ItemSheetFormDialogState.is_update_mode,
            rx.fragment(),
            rx.hstack(
                rx.checkbox(
                    checked=ItemSheetFormDialogState.form_is_consumable,
                    on_change=ItemSheetFormDialogState.set_is_consumable,
                ),
                rx.text("Consumable item_sheet", size="2"),
                rx.tooltip(
                    rx.icon("info", size=14, color="gray"),
                    content="Consumable item_sheets (chemicals, reagents) have quantity that decreases with use. Non-consumables (instruments, equipment) are tracked by reference only.",
                ),
                spacing="2",
                align="center",
            ),
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
        state=ItemSheetFormDialogState,
        title=rx.cond(
            ItemSheetFormDialogState.is_update_mode, "Update ItemSheet", "Create New ItemSheet"
        ),
        description=rx.cond(
            ItemSheetFormDialogState.is_update_mode,
            "Update the item_sheet details below.",
            "Fill in the details below to create a new item_sheet.",
        ),
        form_content=_form_content(),
        max_width="500px",
    )


def item_sheet_update_dialog() -> rx.Component:
    """Dialog component for updating an existing item_sheet.

    This component provides just the dialog (without a trigger button).
    The dialog is controlled by the ItemSheetFormDialogState.dialog_opened state.

    :return: The update item_sheet dialog component
    :rtype: rx.Component
    """
    return _dialog()
