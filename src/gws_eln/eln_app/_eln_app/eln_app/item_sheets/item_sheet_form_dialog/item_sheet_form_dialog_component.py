import reflex as rx
from gws_reflex_main import form_dialog_component
from gws_reflex_main.gws_components import select_component

from ...common.select_with_create_component import select_with_create
from .item_sheet_form_dialog_state import ItemSheetFormDialogState


def item_sheet_form_content() -> rx.Component:
    """Public alias of :func:`_form_content`, for reuse outside this module
    (e.g. the Transform output wizard)."""
    return _form_content()


def _form_content() -> rx.Component:
    """Form content for entering item_sheet details."""
    return rx.vstack(
        # ItemSheet Name (70%) + Code (30%, create only) on one line.
        # In update mode the code is hidden, so the name fills the row.
        rx.hstack(
            rx.vstack(
                rx.hstack(
                    rx.text("Item sheet name*", size="2", weight="bold"),
                    rx.tooltip(
                        rx.icon("info", size=14, color="gray"),
                        content=(
                            "Human-readable name of the product or substance this sheet "
                            "describes."
                        ),
                    ),
                    align="center",
                    spacing="1",
                ),
                rx.debounce_input(
                    rx.input(
                        placeholder="e.g. Ethanol",
                        name="name",
                        required=True,
                        width="100%",
                        value=ItemSheetFormDialogState.form_name,
                        on_change=[
                            ItemSheetFormDialogState.set_form_name,
                            ItemSheetFormDialogState.suggest_code_from_name,
                        ],
                    ),
                    debounce_timeout=500,
                ),
                flex="7",
                min_width="0",
                spacing="1",
            ),
            rx.cond(
                ItemSheetFormDialogState.is_update_mode,
                rx.fragment(),
                rx.vstack(
                    rx.hstack(
                        rx.text("Code*", size="2", weight="bold"),
                        rx.tooltip(
                            rx.icon("info", size=14, color="gray"),
                            content=(
                                "Short prefix (max 4 characters) used to auto-generate the "
                                "code of every item on this sheet, e.g. ETHA → ETHA-0001."
                            ),
                        ),
                        align="center",
                        spacing="1",
                    ),
                    rx.input(
                        placeholder="e.g. ETHA",
                        name="code",
                        required=True,
                        max_length=4,
                        width="100%",
                        value=ItemSheetFormDialogState.form_code,
                        on_change=ItemSheetFormDialogState.set_form_code,
                    ),
                    flex="3",
                    min_width="0",
                    spacing="1",
                ),
            ),
            width="100%",
            spacing="3",
            align="end",
        ),
        # Default Supplier (50%) + Unit type (50%) on one line.
        rx.hstack(
            # Unit Type (immutable once the sheet has at least an item)
            rx.vstack(
                rx.hstack(
                    rx.text("Unit type*", size="2", weight="bold"),
                    rx.tooltip(
                        rx.icon("info", size=14, color="gray"),
                        content=(
                            "Physical dimension every item on this sheet is measured in. "
                            "Once set to e.g. volume, items can only be expressed in volume "
                            "units (L, mL, µL…). Fixed once the sheet has items."
                        ),
                    ),
                    align="center",
                    spacing="1",
                ),
                select_component(
                    data=ItemSheetFormDialogState.unit_type_options,
                    placeholder="Select a unit type",
                    value=ItemSheetFormDialogState.form_unit_type,
                    on_change=ItemSheetFormDialogState.set_unit_type,
                    disabled=ItemSheetFormDialogState.unit_type_locked,
                    width="100%",
                ),
                rx.cond(
                    ItemSheetFormDialogState.unit_type_locked,
                    rx.text(
                        "Can't change the unit type because this item sheet already has items.",
                        size="1",
                        color="gray",
                    ),
                ),
                flex="1",
                min_width="0",
                spacing="1",
            ),
            rx.vstack(
                rx.hstack(
                    rx.text("Default Supplier", size="2", weight="bold"),
                    rx.tooltip(
                        rx.icon("info", size=14, color="gray"),
                        content=(
                            "Supplier prefilled by default when creating an item on this "
                            "sheet (optional, overridable per item)."
                        ),
                    ),
                    align="center",
                    spacing="1",
                ),
                select_with_create(
                    select_component(
                        data=(
                            rx.Var.create([{"value": "__none__", "label": "No supplier"}])
                            + ItemSheetFormDialogState.supplier_options
                        ),
                        placeholder="Select a supplier (optional)",
                        searchable=True,
                        value=ItemSheetFormDialogState.form_supplier_id,
                        on_change=ItemSheetFormDialogState.set_supplier_id,
                        width="100%",
                        key=ItemSheetFormDialogState.supplier_select_key.to_string(),
                    ),
                    on_create=ItemSheetFormDialogState.open_create_supplier_dialog,
                    tooltip="Create a new supplier",
                ),
                flex="1",
                min_width="0",
                spacing="1",
            ),
            width="100%",
            spacing="3",
            align="start",
        ),
        # Description field
        rx.vstack(
            rx.text("Description", size="2", weight="bold"),
            rx.text_area(
                placeholder="Enter item sheet description (optional)",
                name="description",
                width="100%",
                default_value=ItemSheetFormDialogState.form_description,
                rows="3",
            ),
            width="100%",
            spacing="1",
        ),
        # Storage conditions field (default for items of this sheet)
        rx.vstack(
            rx.hstack(
                rx.text("Storage conditions", size="2", weight="bold"),
                rx.tooltip(
                    rx.icon("info", size=14, color="gray"),
                    content=(
                        "Default storage condition for items of this sheet "
                        "(overridable per item)."
                    ),
                ),
                align="center",
                spacing="1",
            ),
            rx.input(
                placeholder="e.g. -20°C (optional)",
                name="storage_conditions",
                width="100%",
                default_value=ItemSheetFormDialogState.form_storage_conditions,
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
                    disabled=ItemSheetFormDialogState.consumable_locked,
                ),
                rx.text("Consumable item sheet", size="2"),
                rx.tooltip(
                    rx.icon("info", size=14, color="gray"),
                    content="Consumable item sheets, such as chemicals and reagents, track quantities that decrease with use. Non-consumable items, such as instruments and equipment, are tracked by reference only.",
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
            ItemSheetFormDialogState.is_update_mode, "Update item sheet", "Create new item sheet"
        ),
        subtitle=rx.cond(
            ItemSheetFormDialogState.is_update_mode,
            "Update the item sheet details below.",
            "Fill in the details below to create a new item sheet.",
        ),
        form_content=_form_content(),
        max_width="500px",
        dismissable=False,
    )


def item_sheet_update_dialog() -> rx.Component:
    """Dialog component for updating an existing item_sheet.

    This component provides just the dialog (without a trigger button).
    The dialog is controlled by the ItemSheetFormDialogState.dialog_opened state.

    :return: The update item_sheet dialog component
    :rtype: rx.Component
    """
    return _dialog()
