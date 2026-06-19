import reflex as rx
from gws_reflex_main import form_dialog_component

from ...common.unit.concentration_unit_components import concentration_unit_select
from ...common.unit.unit_components import quantity_unit_input
from ...locations.core.location_select_component import (
    location_select_component,
)
from ...suppliers.core.supplier_select_component import (
    supplier_select_component,
)
from .item_form_dialog_state import ItemFormDialogState


def _consumable_quantity_section() -> rx.Component:
    """Quantity + concentration inputs for a consumable item (single item)."""
    return rx.vstack(
        quantity_unit_input(
            unit_type=ItemFormDialogState.form_unit_type,
            unit_value=ItemFormDialogState.form_unit,
            on_unit_change=ItemFormDialogState.set_unit,
        ),
        # Concentration value + unit (optional, recorded verbatim)
        rx.hstack(
            rx.vstack(
                rx.text("Concentration", size="2", weight="bold"),
                rx.input(
                    placeholder="Enter concentration (optional)",
                    name="concentration",
                    type="number",
                    min="0",
                    step="any",
                    width="100%",
                ),
                width="60%",
                spacing="1",
            ),
            rx.vstack(
                rx.text("Unit", size="2", weight="bold"),
                concentration_unit_select(
                    name="concentration_unit",
                    value=ItemFormDialogState.form_concentration_unit,
                    on_change=ItemFormDialogState.set_concentration_unit,
                ),
                width="40%",
                spacing="1",
            ),
            width="100%",
            spacing="3",
        ),
        width="100%",
        spacing="3",
    )


def _bulk_units_section() -> rx.Component:
    """Number of units + one serial input per unit (non-consumable, qty 1 each)."""
    return rx.vstack(
        rx.vstack(
            rx.text("Number of units", size="2", weight="bold"),
            rx.input(
                type="number",
                min="1",
                width="100%",
                value=ItemFormDialogState.form_unit_count.to_string(),
                on_change=ItemFormDialogState.set_unit_count,
            ),
            width="100%",
            spacing="1",
        ),
        rx.text("Serial numbers", size="2", weight="bold"),
        rx.foreach(
            ItemFormDialogState.form_serials,
            lambda serial, index: rx.input(
                placeholder="Serial number (optional)",
                width="100%",
                value=serial,
                on_change=lambda value: ItemFormDialogState.set_serial(index, value),
            ),
        ),
        width="100%",
        spacing="2",
    )


def _form_content() -> rx.Component:
    """Form content for entering item_sheet item details."""
    return rx.vstack(
        # ItemSheet + Code (read-only, side by side, equal width)
        rx.hstack(
            rx.vstack(
                rx.text("ItemSheet", size="2", weight="bold"),
                rx.text(
                    ItemFormDialogState.item_sheet_name,
                    size="2",
                    color="gray",
                ),
                width="50%",
                spacing="1",
            ),
            rx.vstack(
                rx.text("Code", size="2", weight="bold"),
                rx.code(ItemFormDialogState.code_preview, size="2"),
                width="50%",
                spacing="1",
                align="start",
            ),
            width="100%",
            spacing="3",
            align="start",
        ),
        # Label field (human-readable name for the item)
        rx.vstack(
            rx.text("Label", size="2", weight="bold"),
            rx.input(
                placeholder="Enter a label to name this item (optional)",
                name="label",
                width="100%",
                default_value=ItemFormDialogState.form_label,
            ),
            width="100%",
            spacing="1",
        ),
        # Consumable: quantity + concentration. Non-consumable: N units + serials.
        rx.cond(
            ItemFormDialogState.is_consumable,
            _consumable_quantity_section(),
            _bulk_units_section(),
        ),
        # Location + Supplier (side by side, equal width)
        rx.hstack(
            rx.vstack(
                rx.text("Location*", size="2", weight="bold"),
                location_select_component(
                    placeholder="Select a location",
                    value=ItemFormDialogState.form_location_id,
                    on_change=ItemFormDialogState.set_location_id,
                    required=True,
                ),
                width="50%",
                spacing="1",
            ),
            rx.vstack(
                rx.text("Supplier", size="2", weight="bold"),
                supplier_select_component(
                    placeholder="Select a supplier (optional)",
                    additional_option=("No supplier", "__none__"),
                    value=ItemFormDialogState.form_supplier_id,
                    on_change=ItemFormDialogState.set_supplier_id,
                ),
                width="50%",
                spacing="1",
            ),
            width="100%",
            spacing="3",
        ),
        # Expiry Date + Storage conditions (side by side, equal width)
        rx.hstack(
            rx.vstack(
                rx.text("Expiry Date", size="2", weight="bold"),
                rx.input(
                    placeholder="Select expiry date (optional)",
                    name="expiry_date",
                    type="date",
                    width="100%",
                    default_value=ItemFormDialogState.form_expiry_date,
                    on_change=ItemFormDialogState.set_expiry_date,
                ),
                width="50%",
                spacing="1",
            ),
            rx.vstack(
                rx.text("Storage conditions", size="2", weight="bold"),
                rx.input(
                    placeholder="e.g. -20°C (optional)",
                    name="storage_conditions",
                    width="100%",
                    default_value=ItemFormDialogState.form_storage_conditions,
                ),
                width="50%",
                spacing="1",
            ),
            width="100%",
            spacing="3",
            align="start",
        ),
        rx.text(
            "Storage conditions are prefilled from the item sheet's default; "
            "edit to override for this item.",
            size="1",
            color="gray",
        ),
        # Notes field
        rx.vstack(
            rx.text("Notes", size="2", weight="bold"),
            rx.text_area(
                placeholder="Enter notes (optional)",
                name="notes",
                width="100%",
                default_value=ItemFormDialogState.form_notes,
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
        state=ItemFormDialogState,
        title="Create New Item",
        description="Fill in the details below to create a new item_sheet item.",
        form_content=_form_content(),
        max_width="550px",
        dismissable=False,
    )


def create_item_dialog() -> rx.Component:
    """Dialog component for creating a new item_sheet item.

    This component provides just the dialog (without a trigger button).
    The dialog is controlled by the ItemFormDialogState.dialog_opened state.

    To open the dialog, call ItemFormDialogState.open_create_dialog(item_sheet)
    with the item_sheet for which to create a item.

    :return: The create item_sheet item dialog component
    :rtype: rx.Component
    """
    return _dialog()
