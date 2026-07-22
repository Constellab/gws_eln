"""ItemSheets list page component."""

import reflex as rx
from gws_eln.items.item_sheet_dto import ItemSheetDTO
from gws_reflex_main import main_component, user_with_date_component
from gws_reflex_main.gws_components import select_component

from ..common.eln_app_router import ElnAppRouter
from ..common.feedback_components import compact_error
from ..common.page_layout import page_layout
from ..common.unit.unit_type_select_component import unit_type_select_component
from ..items.core.item_components import consumable_badge
from ..items.item_form_dialog.item_form_dialog_component import create_item_dialog
from ..suppliers.core.inline_supplier_component import inline_supplier_component
from ..suppliers.core.supplier_select_component import supplier_select_component
from .core.item_sheet_actions_menu import item_sheet_actions_menu
from .delete_item_sheet_form_dialog.delete_item_sheet_form_dialog_component import (
    delete_item_sheet_dialog,
)
from .item_sheet_form_dialog.item_sheet_form_dialog_component import item_sheet_update_dialog
from .item_sheets_list_state import ALL_FILTER_VALUE, ItemSheetsListState


def _filter_bar() -> rx.Component:
    """Create the filter bar with search and dropdown filters.

    :return: The filter bar component
    :rtype: rx.Component
    """
    return rx.hstack(
        # Search input. Filtering is done in memory (see
        # ItemSheetsListState.item_sheets), so it stays instant without hitting
        # the DB. debounce_timeout=0 disables Reflex's implicit 300ms debounce on
        # controlled inputs, so the list filters on every keystroke.
        rx.input(
            placeholder="Search item sheets...",
            value=ItemSheetsListState.search_text,
            on_change=ItemSheetsListState.handle_search_change,
            debounce_timeout=0,
            width="200px",
        ),
        # Supplier filter
        supplier_select_component(
            placeholder="Supplier",
            width="180px",
            additional_option=("All suppliers", ALL_FILTER_VALUE),
            value=ItemSheetsListState.filter_supplier_id,
            on_change=ItemSheetsListState.handle_supplier_filter_change,
        ),
        # Consumable filter
        select_component(
            data=[
                {"value": ALL_FILTER_VALUE, "label": "All types"},
                {"value": "true", "label": "Consumable"},
                {"value": "false", "label": "Non-consumable"},
            ],
            placeholder="Type",
            value=ItemSheetsListState.filter_is_consumable,
            on_change=ItemSheetsListState.handle_consumable_filter_change,
            width="160px",
        ),
        # Unit type filter
        unit_type_select_component(
            placeholder="Unit type",
            width="180px",
            all_option=("All unit types", ALL_FILTER_VALUE),
            value=ItemSheetsListState.filter_unit_type,
            on_change=ItemSheetsListState.handle_unit_type_filter_change,
        ),
        # Clear filters button
        rx.button(
            "Clear",
            on_click=ItemSheetsListState.clear_filters,
            variant="surface",
            size="2",
        ),
        width="100%",
        spacing="3",
        wrap="wrap",
        align="center",
    )


def _create_item_sheet_button() -> rx.Component:
    """Create the button to open the create item_sheet dialog.

    :return: The create item_sheet button component
    :rtype: rx.Component
    """
    return rx.fragment(
        rx.button(
            rx.icon("plus", size=18),
            "Create new item sheet",
            size="3",
            on_click=ItemSheetsListState.open_create_dialog,
        ),
        item_sheet_update_dialog(),
        # Controlled dialog (no trigger) for creating an item from a row's actions menu.
        create_item_dialog(),
        # Controlled dialog (no trigger) for deleting/discarding a sheet.
        delete_item_sheet_dialog(),
    )


def _row(item_sheet: ItemSheetDTO) -> rx.Component:
    """Create a table row for a item_sheet.

    :param item_sheet: The item_sheet DTO to display
    :type item_sheet: ItemSheetDTO
    :return: The table row component
    :rtype: rx.Component
    """
    return rx.table.row(
        rx.table.cell(rx.text(item_sheet.name)),
        rx.table.cell(rx.code(item_sheet.code)),
        rx.table.cell(
            rx.vstack(
                rx.cond(
                    item_sheet.description,
                    rx.text(item_sheet.description, size="2", color="gray"),
                ),
                rx.cond(
                    item_sheet.discard_reason,
                    compact_error(f"Discarded — reason: {item_sheet.discard_reason}"),
                ),
                spacing="1",
                align="start",
            )
        ),
        rx.table.cell(
            rx.cond(
                item_sheet.default_supplier,
                inline_supplier_component(item_sheet.default_supplier),
            )
        ),
        rx.table.cell(rx.box(consumable_badge(item_sheet.is_consumable), width="fit-content")),
        rx.table.cell(
            user_with_date_component(item_sheet.created_by, item_sheet.created_at, size="small")
        ),
        rx.table.cell(
            rx.box(
                item_sheet_actions_menu(
                    on_update=lambda: ItemSheetsListState.open_update_dialog(item_sheet),
                    on_delete=lambda: ItemSheetsListState.open_delete_dialog(item_sheet),
                    on_create_item=lambda: ItemSheetsListState.open_create_item_dialog(item_sheet),
                    stop_propagation=True,
                    # A discarded sheet is locked: no actions possible.
                    disabled=item_sheet.is_discarded,
                ),
                display="flex",
                justify_content="flex-end",
                align_items="center",
            )
        ),
        style={":hover": {"background_color": "var(--gray-3)"}, "cursor": "pointer"},
        on_click=lambda: [
            rx.redirect(ElnAppRouter.get_item_sheet_detail_url(item_sheet.id)),
            ItemSheetsListState.prepare_item_sheet_navigation(item_sheet.id),
        ],
    )


def item_sheets_list_page() -> rx.Component:
    """Create the item_sheets list page component.

    This component displays a table of item_sheets with columns for
    name, description, supplier, type, created by, and created at.
    Includes filters for search, supplier, consumable type, and unit type.

    :return: The item_sheets list page component
    :rtype: rx.Component
    """
    return main_component(
        page_layout(
            rx.vstack(
                _filter_bar(),
                rx.cond(
                    ItemSheetsListState.error_message != "",
                    rx.callout(
                        ItemSheetsListState.error_message,
                        icon="triangle_alert",
                        color_scheme="red",
                        role="alert",
                        margin_bottom="1rem",
                    ),
                ),
                rx.cond(
                    ItemSheetsListState.is_loading,
                    rx.center(rx.spinner(size="3"), padding="2rem"),
                    rx.cond(
                        ItemSheetsListState.item_sheets.length() > 0,
                        rx.table.root(
                            rx.table.header(
                                rx.table.row(
                                    rx.table.column_header_cell("Name"),
                                    rx.table.column_header_cell("Code"),
                                    rx.table.column_header_cell("Description"),
                                    rx.table.column_header_cell("Default Supplier"),
                                    rx.table.column_header_cell("Type"),
                                    rx.table.column_header_cell("Creation"),
                                    rx.table.column_header_cell(
                                        "", width="100px", justify="end"
                                    ),
                                ),
                            ),
                            rx.table.body(rx.foreach(ItemSheetsListState.item_sheets, _row)),
                            width="100%",
                            variant="surface",
                        ),
                        rx.center(
                            rx.vstack(
                                rx.icon("package", size=48, color="gray"),
                                rx.text(
                                    "No item sheets found",
                                    size="4",
                                    color="gray",
                                    margin_top="1rem",
                                ),
                                spacing="2",
                                align="center",
                            ),
                            padding="3rem",
                            width="100%",
                        ),
                    ),
                ),
                width="100%",
                spacing="4",
            ),
            header_content=rx.hstack(
                rx.heading("Item sheets", size="6"),
                _create_item_sheet_button(),
                justify="between",
                align="center",
                width="100%",
                margin_bottom="1rem",
            ),
        )
    )
