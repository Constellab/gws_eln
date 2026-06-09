"""Reusable form sections for item activity dialogs.

Each function returns the editable form fields for a specific activity type.
These are used by both the standalone form dialogs and the note activity dialog.
"""

import reflex as rx
from gws_eln.items.item_dto import ItemDTO

from ..common.unit.unit_components import quantity_unit_input
from ..item_sheets.core.item_sheet_select_component import item_sheet_select_component
from ..locations.core.location_select_component import location_select_component
from ..suppliers.core.supplier_select_component import supplier_select_component


def receive_consume_form_section(
    unit_type: rx.Var[str],
    unit_value: rx.Var[str],
    on_unit_change: rx.EventHandler,
    quantity_label: rx.Var[str] | str,
    form_notes: rx.Var[str],
) -> rx.Component:
    """Form section for receive/consume operations: quantity + unit + notes."""
    return rx.fragment(
        quantity_unit_input(
            unit_type=unit_type,
            unit_value=unit_value,
            on_unit_change=on_unit_change,
            quantity_label=quantity_label,
        ),
        rx.vstack(
            rx.text("Notes", size="2", weight="bold"),
            rx.text_area(
                placeholder="Enter notes (optional)",
                name="notes",
                width="100%",
                default_value=form_notes,
                rows="3",
            ),
            width="100%",
            spacing="1",
        ),
    )


def move_form_section(
    form_location_id: rx.Var[str],
    on_location_change: rx.EventHandler,
) -> rx.Component:
    """Form section for move operation: destination location."""
    return rx.fragment(
        rx.vstack(
            rx.text("Destination Location*", size="2", weight="bold"),
            location_select_component(
                placeholder="Select destination location",
                value=form_location_id,
                on_change=on_location_change,
            ),
            width="100%",
            spacing="1",
        ),
    )


def use_discard_form_section(
    form_notes: rx.Var[str],
    notes_label: str = "Notes",
    notes_placeholder: str = "Enter notes (optional)",
) -> rx.Component:
    """Form section for use/discard operations: notes only."""
    return rx.fragment(
        rx.vstack(
            rx.text(notes_label, size="2", weight="bold"),
            rx.text_area(
                placeholder=notes_placeholder,
                name="notes",
                width="100%",
                default_value=form_notes,
                rows="3",
            ),
            width="100%",
            spacing="1",
        ),
    )


def relabel_form_section(
    form_item_number: rx.Var[str],
    form_label: rx.Var[str],
) -> rx.Component:
    """Form section for relabel operation: new item number + new label."""
    return rx.fragment(
        rx.vstack(
            rx.text("New Item Number*", size="2", weight="bold"),
            rx.input(
                placeholder="Enter new item number",
                name="item_number",
                required=True,
                width="100%",
                default_value=form_item_number,
            ),
            width="100%",
            spacing="1",
        ),
        rx.vstack(
            rx.text("New Label", size="2", weight="bold"),
            rx.input(
                placeholder="Enter new label (optional)",
                name="label",
                width="100%",
                default_value=form_label,
            ),
            width="100%",
            spacing="1",
        ),
    )


def create_item_form_section(
    form_item_sheet: rx.Var,
    on_item_sheet_change: rx.EventHandler,
    form_unit_type: rx.Var[str],
    form_unit: rx.Var[str],
    on_unit_change: rx.EventHandler,
    form_location_id: rx.Var[str],
    on_location_change: rx.EventHandler,
    form_supplier_id: rx.Var[str],
    on_supplier_change: rx.EventHandler,
    form_notes: rx.Var[str],
) -> rx.Component:
    """Form section for creating a new item: item number, quantity, unit, location, supplier, label, notes."""
    return rx.vstack(
        item_sheet_select_component(
            placeholder="Search an item sheet...",
            selected_item=form_item_sheet,
            item_selected=on_item_sheet_change,
        ),
        rx.cond(
            form_item_sheet,
            rx.fragment(
                # Item Number (required)
                rx.vstack(
                    rx.text("Item Number*", size="2", weight="bold"),
                    rx.input(
                        placeholder="Enter item number",
                        name="item_number",
                        required=True,
                        width="100%",
                    ),
                    width="100%",
                    spacing="1",
                ),
                # Quantity + Unit (required)
                quantity_unit_input(
                    unit_type=form_unit_type,
                    unit_value=form_unit,
                    on_unit_change=on_unit_change,
                    quantity_label="Initial Quantity",
                ),
                # Location + Supplier (optional, same row)
                rx.hstack(
                    rx.vstack(
                        rx.text("Location", size="2", weight="bold"),
                        location_select_component(
                            placeholder="Select location (defaults to 'labo')...",
                            value=form_location_id,
                            on_change=on_location_change,
                        ),
                        width="50%",
                        spacing="1",
                    ),
                    rx.vstack(
                        rx.text("Supplier", size="2", weight="bold"),
                        supplier_select_component(
                            placeholder="Select supplier (optional)...",
                            value=form_supplier_id,
                            on_change=on_supplier_change,
                            additional_option=("None", "__none__"),
                        ),
                        width="50%",
                        spacing="1",
                    ),
                    width="100%",
                    spacing="3",
                ),
                # Label (optional)
                rx.vstack(
                    rx.text("Label", size="2", weight="bold"),
                    rx.input(
                        placeholder="Enter label (optional)",
                        name="label",
                        width="100%",
                    ),
                    width="100%",
                    spacing="1",
                ),
                # Notes (optional)
                rx.vstack(
                    rx.text("Notes", size="2", weight="bold"),
                    rx.text_area(
                        placeholder="Enter notes (optional)",
                        name="notes",
                        width="100%",
                        default_value=form_notes,
                        rows="3",
                    ),
                    width="100%",
                    spacing="1",
                ),
            ),
        ),
        width="100%",
        spacing="3",
    )
