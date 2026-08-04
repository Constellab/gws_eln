import reflex as rx
from gws_reflex_main import form_dialog_component

from ...common.feedback_components import compact_warning
from ...common.select_with_create_component import select_with_create
from ...common.unit.concentration_unit_components import concentration_unit_select
from ...common.unit.unit_components import quantity_unit_input
from ...locations.core.location_select_component import (
    location_select_component,
)
from ...locations.location_form_dialog.location_form_dialog_component import location_update_dialog
from ...suppliers.core.supplier_select_component import (
    supplier_select_component,
)
from ...suppliers.supplier_form_dialog.supplier_form_dialog_component import supplier_update_dialog
from .item_form_dialog_state import ItemFormDialogState


def _consumable_quantity_section(
    extra_content: rx.Component | None = None,
) -> rx.Component:
    """Quantity + concentration inputs for a consumable item (single item).

    ``extra_content`` is rendered right after the concentration row (used by the
    Transform output wizard to slot in the dilution-factor field).
    """
    return rx.vstack(
        quantity_unit_input(
            unit_type=ItemFormDialogState.form_unit_type,
            quantity_value=ItemFormDialogState.form_quantity,
            unit_value=ItemFormDialogState.form_unit,
            on_quantity_change=ItemFormDialogState.set_quantity,
            on_unit_change=ItemFormDialogState.set_unit,
            unit_hint=(
                "Measurement unit for the quantity, limited to the sheet's unit type "
                "(e.g. for a volume: L, mL, µL, nL)."
            ),
        ),
        # Concentration value + unit (optional, recorded verbatim).
        # Independent of the quantity unit: describes the proportion of a
        # component in the product (e.g. 500 g of powder at 10 mg/g).
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
                    value=ItemFormDialogState.form_concentration,
                    on_change=ItemFormDialogState.set_concentration,
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
        *([extra_content] if extra_content is not None else []),
        width="100%",
        spacing="3",
    )


def _bulk_units_section() -> rx.Component:
    """Number of units + one serial input per unit.

    Serialized units become distinct items (qty 1); units left without a serial
    are indistinguishable and are stacked into a single item.
    """
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
        rx.hstack(
            rx.text("Serial numbers", size="2", weight="bold"),
            rx.tooltip(
                rx.icon("info", size=14, color="gray"),
                content=(
                    "Units left without a serial number are indistinguishable and "
                    "grouped into a single stacked item."
                ),
            ),
            align="center",
            spacing="1",
        ),
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


def item_form_content(
    extra_concentration_content: rx.Component | None = None,
) -> rx.Component:
    """Public alias of :func:`_form_content`, for reuse outside this module
    (e.g. the Transform output wizard).

    ``extra_concentration_content`` is slotted right after the concentration row
    (the Transform output wizard uses it for the dilution-factor field).
    """
    return _form_content(extra_concentration_content)


def _form_content(extra_concentration_content: rx.Component | None = None) -> rx.Component:
    """Form content for entering item_sheet item details."""
    return rx.vstack(
        # ItemSheet + Code (read-only, side by side, equal width)
        rx.hstack(
            rx.vstack(
                rx.text("Item sheet", size="2", weight="bold"),
                rx.text(
                    ItemFormDialogState.item_sheet_name,
                    size="2",
                    color="gray",
                ),
                width="50%",
                spacing="1",
            ),
            rx.vstack(
                rx.hstack(
                    rx.text("Code", size="2", weight="bold"),
                    rx.tooltip(
                        rx.icon("info", size=14, color="gray"),
                        content=(
                            "Auto-generated at creation: the sheet's code followed by an "
                            "incrementing number (the preview shown here is indicative)."
                        ),
                    ),
                    align="center",
                    spacing="1",
                ),
                rx.code(ItemFormDialogState.code_preview, size="2"),
                width="50%",
                spacing="1",
                align="start",
            ),
            width="100%",
            spacing="3",
            align="start",
        ),
        # Label field (human-readable name for the item, required)
        rx.vstack(
            rx.hstack(
                rx.text("Label*", size="2", weight="bold"),
                rx.tooltip(
                    rx.icon("info", size=14, color="gray"),
                    content=(
                        "Human-readable name for this item, used to identify it alongside "
                        "its auto-generated code."
                    ),
                ),
                align="center",
                spacing="1",
            ),
            rx.input(
                placeholder="Enter a label to name this item",
                name="label",
                width="100%",
                # Required is validated in the state, not via the native HTML
                # attribute, which would steal focus and block submit.
                default_value=ItemFormDialogState.form_label,
                # Tracked live so the label-divergence warning below reacts.
                on_change=ItemFormDialogState.set_label,
            ),
            # Shown when the label diverges from a caller-set reference (e.g. a
            # split output vs its source): warn and require a justification.
            rx.cond(
                ItemFormDialogState.label_changed,
                rx.vstack(
                    compact_warning(
                        "This label differs from the original. Please give a reason for the change."
                    ),
                    rx.text_area(
                        placeholder="Reason for changing the label (required)",
                        value=ItemFormDialogState.form_override_reason,
                        on_change=ItemFormDialogState.set_override_reason,
                        width="100%",
                        rows="2",
                    ),
                    width="100%",
                    spacing="1",
                    align="stretch",
                ),
            ),
            width="100%",
            spacing="1",
        ),
        # Batch / lot number (consumable origin items only; hidden for transform
        # outputs, which inherit their lot numbers from their ancestors, and for
        # non-consumables, which carry serial numbers instead).
        rx.cond(
            ItemFormDialogState.is_consumable & ~ItemFormDialogState.collect_mode,
            rx.vstack(
                rx.hstack(
                    rx.text("Batch / lot number", size="2", weight="bold"),
                    rx.tooltip(
                        rx.icon("info", size=14, color="gray"),
                        content=(
                            "Supplier lot number for this delivery (optional). Set once at "
                            "creation; items derived from this one inherit its lot number."
                        ),
                    ),
                    align="center",
                    spacing="1",
                ),
                rx.input(
                    placeholder="Enter the batch/lot number (optional)",
                    name="batch_number",
                    width="100%",
                    default_value=ItemFormDialogState.form_batch_number,
                ),
                width="100%",
                spacing="1",
            ),
        ),
        # Consumable: quantity + concentration. Non-consumable: N units + serials.
        # In collect mode (Transform output) always use the single-item form.
        rx.cond(
            ItemFormDialogState.is_consumable | ItemFormDialogState.collect_mode,
            _consumable_quantity_section(extra_concentration_content),
            _bulk_units_section(),
        ),
        # Location + Supplier (side by side, equal width)
        rx.hstack(
            rx.vstack(
                rx.hstack(
                    rx.text("Location*", size="2", weight="bold"),
                    rx.tooltip(
                        rx.icon("info", size=14, color="gray"),
                        content="Physical storage location where this item is kept.",
                    ),
                    align="center",
                    spacing="1",
                ),
                select_with_create(
                    location_select_component(
                        placeholder="Select a location",
                        value=ItemFormDialogState.form_location_id,
                        on_change=ItemFormDialogState.set_location_id,
                        key=ItemFormDialogState.location_select_key.to_string(),
                    ),
                    on_create=ItemFormDialogState.open_create_location_dialog,
                    tooltip="Create a new location",
                ),
                width="50%",
                spacing="1",
            ),
            rx.vstack(
                rx.hstack(
                    rx.text("Supplier", size="2", weight="bold"),
                    rx.tooltip(
                        rx.icon("info", size=14, color="gray"),
                        content=(
                            "Who supplied this item (optional); prefilled from the sheet's "
                            "default supplier when it has one."
                        ),
                    ),
                    align="center",
                    spacing="1",
                ),
                select_with_create(
                    supplier_select_component(
                        placeholder="Select a supplier (optional)",
                        additional_option=("No supplier", "__none__"),
                        value=ItemFormDialogState.form_supplier_id,
                        on_change=ItemFormDialogState.set_supplier_id,
                        key=ItemFormDialogState.supplier_select_key.to_string(),
                    ),
                    on_create=ItemFormDialogState.open_create_supplier_dialog,
                    tooltip="Create a new supplier",
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
                # Non-consumables track a "Next due date" (calibration/maintenance)
                # rather than an expiry date. Expiry date is required for
                # consumables; the next due date stays optional.
                rx.text(
                    rx.cond(ItemFormDialogState.is_consumable, "Expiry Date*", "Next due date"),
                    size="2",
                    weight="bold",
                ),
                rx.input(
                    placeholder=rx.cond(
                        ItemFormDialogState.is_consumable,
                        "Select expiry date",
                        "Select next due date (optional)",
                    ),
                    name="expiry_date",
                    type="date",
                    width="100%",
                    # Required is validated in the state, not via the native HTML
                    # attribute, which would steal focus and block submit.
                    default_value=ItemFormDialogState.form_expiry_date,
                    on_change=ItemFormDialogState.set_expiry_date,
                ),
                width="50%",
                spacing="1",
            ),
            rx.vstack(
                rx.hstack(
                    rx.text("Storage conditions", size="2", weight="bold"),
                    rx.tooltip(
                        rx.icon("info", size=14, color="gray"),
                        content=(
                            "Storage conditions are prefilled from the item sheet's "
                            "default; edit to override for this item."
                        ),
                    ),
                    align="center",
                    spacing="1",
                ),
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
        # Notes field
        rx.vstack(
            rx.text("Notes", size="2", weight="bold"),
            rx.text_area(
                placeholder="Enter notes (optional)",
                name="notes",
                width="100%",
                # Controlled: a text_area value is not reliably collected by the
                # form's on_submit, so track it in state and read it there.
                value=ItemFormDialogState.form_notes,
                on_change=ItemFormDialogState.set_notes,
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
        subtitle="Fill in the details below to create a new item sheet item.",
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

    The supplier/location create dialogs are mounted alongside so the form's
    "+" buttons can spawn one on the fly. This component is present on every
    page that shows an item or item-sheet form, so it is also the single mount
    point those two shared dialogs need.

    :return: The create item_sheet item dialog component
    :rtype: rx.Component
    """
    return rx.fragment(
        _dialog(),
        supplier_update_dialog(),
        location_update_dialog(),
    )
