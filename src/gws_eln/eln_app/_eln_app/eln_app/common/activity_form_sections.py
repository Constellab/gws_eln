"""Reusable form sections for batch activity dialogs.

Each function returns the editable form fields for a specific activity type.
These are used by both the standalone form dialogs and the note activity dialog.
"""

import reflex as rx

from .location.location_select_component import location_select_component
from .materials.material_select_component import material_select_component
from .supplier.supplier_select_component import supplier_select_component
from .unit.unit_components import quantity_unit_input


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
    form_batch_number: rx.Var[str],
    form_label: rx.Var[str],
) -> rx.Component:
    """Form section for relabel operation: new batch number + new label."""
    return rx.fragment(
        rx.vstack(
            rx.text("New Batch Number*", size="2", weight="bold"),
            rx.input(
                placeholder="Enter new batch number",
                name="batch_number",
                required=True,
                width="100%",
                default_value=form_batch_number,
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


def create_batch_form_section(
    form_unit_type: rx.Var[str],
    form_unit: rx.Var[str],
    on_unit_change: rx.EventHandler,
    form_location_id: rx.Var[str],
    on_location_change: rx.EventHandler,
    form_supplier_id: rx.Var[str],
    on_supplier_change: rx.EventHandler,
    form_notes: rx.Var[str],
) -> rx.Component:
    """Form section for creating a new batch: batch number, quantity, unit, location, supplier, label, notes."""
    return rx.vstack(
        # Batch Number (required)
        rx.vstack(
            rx.text("Batch Number*", size="2", weight="bold"),
            rx.input(
                placeholder="Enter batch number",
                name="batch_number",
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
            quantity_label="Initial Quantity*",
        ),
        # Location (optional)
        rx.vstack(
            rx.text("Location", size="2", weight="bold"),
            location_select_component(
                placeholder="Select location (defaults to 'labo')...",
                value=form_location_id,
                on_change=on_location_change,
            ),
            width="100%",
            spacing="1",
        ),
        # Supplier (optional)
        rx.vstack(
            rx.text("Supplier", size="2", weight="bold"),
            supplier_select_component(
                placeholder="Select supplier (optional)...",
                value=form_supplier_id,
                on_change=on_supplier_change,
                additional_option=("None", "__none__"),
            ),
            width="100%",
            spacing="1",
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
        width="100%",
        spacing="3",
    )


def _step_header(step_number: int, title: str) -> rx.Component:
    """Render a step header with number badge and title."""
    return rx.hstack(
        rx.box(
            rx.text(str(step_number), size="2", weight="bold"),
            background="var(--accent-9)",
            color="white",
            padding_x="8px",
            padding_y="2px",
            border_radius="5px",
        ),
        rx.text(title, size="3", weight="bold"),
        spacing="2",
        align="center",
    )


def aliquot_form_section(
    form_unit_type: rx.Var[str],
    form_source_unit: rx.Var[str],
    on_source_unit_change: rx.EventHandler,
    form_aliquot_unit_type: rx.Var[str],
    form_aliquot_unit: rx.Var[str],
    on_aliquot_unit_change: rx.EventHandler,
    form_location_id: rx.Var[str],
    on_location_change: rx.EventHandler,
    form_supplier_id: rx.Var[str],
    on_supplier_change: rx.EventHandler,
    form_notes: rx.Var[str],
    form_target_material_id: rx.Var[str],
    on_target_material_change: rx.EventHandler,
    parent_batch_number: rx.Var[str] | None = None,
    parent_available_quantity: rx.Var[str] | None = None,
) -> rx.Component:
    """Form section for aliquot creation with two steps: source extraction and new aliquot details."""
    # Step 1: Parent batch section (only shown if parent_batch_number is provided)
    parent_section = rx.fragment()
    if parent_batch_number is not None and parent_available_quantity is not None:
        parent_section = rx.fragment(
            rx.box(
                rx.vstack(
                    _step_header(1, "Source"),
                    rx.text(
                        "Select how much to extract from the parent batch",
                        size="1",
                        color="gray",
                    ),
                    rx.hstack(
                        rx.vstack(
                            rx.text("Batch Number", size="2", weight="medium", color="gray"),
                            rx.text(parent_batch_number, size="2"),
                            spacing="1",
                            width="60%",
                        ),
                        rx.vstack(
                            rx.text("Available", size="2", weight="medium", color="gray"),
                            rx.text(parent_available_quantity, size="2"),
                            spacing="1",
                            width="40%",
                        ),
                        width="100%",
                        spacing="3",
                    ),
                    # Source quantity (amount to take from parent)
                    quantity_unit_input(
                        unit_type=form_unit_type,
                        quantity_name="source_quantity",
                        unit_name="source_unit",
                        unit_value=form_source_unit,
                        on_unit_change=on_source_unit_change,
                        quantity_label="Quantity to Extract*",
                        unit_label="Unit",
                        quantity_placeholder="Amount to take",
                    ),
                    width="100%",
                    spacing="3",
                ),
                padding="12px",
                border="1px solid var(--gray-5)",
                border_radius="8px",
                width="100%",
            ),
        )

    # Determine step number for new aliquot section
    new_aliquot_step = 2 if parent_batch_number is not None else 1

    return rx.vstack(
        parent_section,
        # Step 2: New aliquot section
        rx.box(
            rx.vstack(
                _step_header(new_aliquot_step, "New Aliquot"),
                rx.text(
                    "Configure the new aliquot batch",
                    size="1",
                    color="gray",
                ),
                # Target material selection (required)
                rx.vstack(
                    rx.text("Target Material*", size="2", weight="bold"),
                    material_select_component(
                        placeholder="Select target material...",
                        name="target_material_id",
                        value=form_target_material_id,
                        on_change=on_target_material_change,
                    ),
                    rx.text(
                        "The material type for the new aliquot (defines the unit type)",
                        size="1",
                        color="gray",
                    ),
                    width="100%",
                    spacing="1",
                ),
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
                # Aliquot quantity (amount for the new aliquot)
                quantity_unit_input(
                    unit_type=form_aliquot_unit_type,
                    quantity_name="aliquot_quantity",
                    unit_name="aliquot_unit",
                    unit_value=form_aliquot_unit,
                    on_unit_change=on_aliquot_unit_change,
                    quantity_label="Initial Quantity*",
                    unit_label="Unit",
                    quantity_placeholder="Starting amount",
                ),
                rx.text(
                    "Usually equals the extracted quantity, unless there is loss during transfer",
                    size="1",
                    color="gray",
                    margin_top="-8px",
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
                        value=form_location_id,
                        on_change=on_location_change,
                    ),
                    width="100%",
                    spacing="1",
                ),
                # Supplier (optional)
                rx.vstack(
                    rx.text("Supplier", size="2", weight="bold"),
                    supplier_select_component(
                        placeholder="Select supplier (optional)...",
                        value=form_supplier_id,
                        on_change=on_supplier_change,
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
                        default_value=form_notes,
                        rows="3",
                    ),
                    width="100%",
                    spacing="1",
                ),
                width="100%",
                spacing="3",
            ),
            padding="12px",
            border="1px solid var(--gray-5)",
            border_radius="8px",
            width="100%",
        ),
        width="100%",
        spacing="3",
    )
