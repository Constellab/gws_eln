"""Items list component."""

import reflex as rx
from gws_eln.items.item_dto import ItemDTO

from ..common.eln_app_router import ElnAppRouter
from ..common.feedback_components import compact_error
from ..item_sheets.item_sheet_form_dialog.item_sheet_form_dialog_component import (
    item_sheet_update_dialog,
)
from ..locations.core.inline_location_component import inline_location_component
from ..locations.core.location_select_component import location_select_component
from ..suppliers.core.inline_supplier_component import inline_supplier_component
from ..suppliers.core.supplier_select_component import supplier_select_component
from .core.item_actions_menu import item_actions_menu
from .core.item_components import expiry_date_badge, quantity_badge, status_badge
from .core.item_status_select_component import item_status_select_component
from .delete_item_form_dialog.delete_item_form_dialog_component import (
    delete_item_dialog,
)
from .item_event_form_dialog.item_event_form_dialog_component import (
    item_event_form_dialog,
)
from .item_form_dialog.item_form_dialog_component import (
    create_item_dialog,
)
from .items_list_state import ALL_FILTER_VALUE, ItemsListState
from .move_item_form_dialog.move_item_form_dialog_component import move_item_dialog
from .relabel_item_form_dialog.relabel_item_form_dialog_component import (
    relabel_item_dialog,
)
from .transform_item_form_dialog.transform_item_form_dialog_component import (
    transform_item_dialog,
)
from .update_item_form_dialog.update_item_form_dialog_component import (
    update_item_dialog,
)
from .use_item_form_dialog.use_item_form_dialog_component import (
    use_item_dialog,
)


def _filter_bar() -> rx.Component:
    """Create the filter bar with search and dropdown filters.

    :return: The filter bar component
    :rtype: rx.Component
    """
    return rx.hstack(
        # Search input (item number). Filtering is done in memory (see
        # ItemsListState.items), so it stays instant without hitting the DB.
        # debounce_timeout=0 disables Reflex's implicit 300ms debounce on
        # controlled inputs, so the list filters on every keystroke.
        rx.input(
            placeholder="Search label or code...",
            value=ItemsListState.search_text,
            on_change=ItemsListState.handle_search_change,
            debounce_timeout=0,
            width="200px",
        ),
        # Location filter
        location_select_component(
            placeholder="Location",
            width="180px",
            all_option=("All locations", ALL_FILTER_VALUE),
            value=ItemsListState.filter_location_id,
            on_change=ItemsListState.handle_location_filter_change,
        ),
        # Supplier filter
        supplier_select_component(
            placeholder="Supplier",
            width="180px",
            additional_option=("All suppliers", ALL_FILTER_VALUE),
            value=ItemsListState.filter_supplier_id,
            on_change=ItemsListState.handle_supplier_filter_change,
        ),
        # Status filter
        item_status_select_component(
            placeholder="Status",
            width="140px",
            all_option=("All statuses", ALL_FILTER_VALUE),
            value=ItemsListState.filter_status,
            on_change=ItemsListState.handle_status_filter_change,
        ),
        # Clear filters button
        rx.button(
            "Clear",
            on_click=ItemsListState.clear_filters,
            variant="surface",
            size="2",
        ),
        width="100%",
        spacing="3",
        wrap="wrap",
        align="center",
    )


def _row(item: ItemDTO) -> rx.Component:
    """Create a table row for a item.

    :param item: The item DTO to display
    :type item: ItemDTO
    :return: The table row component
    :rtype: rx.Component
    """
    return rx.table.row(
        rx.table.cell(
            rx.text(item.label, weight="medium"),
        ),
        rx.table.cell(
            rx.code(item.code, size="1"),
            width="1%",
            white_space="nowrap",
        ),
        rx.table.cell(
            rx.vstack(
                rx.cond(
                    item.notes,
                    rx.text(item.notes, size="2", color="gray"),
                ),
                rx.cond(
                    item.discard_reason,
                    compact_error(f"Discarded — reason: {item.discard_reason}"),
                ),
                spacing="1",
                align="start",
            ),
            max_width="400px",
            white_space="normal",
            overflow_wrap="anywhere",
        ),
        rx.table.cell(
            rx.box(quantity_badge(item), width="fit-content"),
            width="1%",
            white_space="nowrap",
        ),
        rx.cond(
            ItemsListState.show_concentration_column,
            rx.table.cell(
                rx.cond(
                    item.concentration,
                    rx.box(
                        rx.badge(
                            item.pretty_concentration,
                            variant="soft",
                            color_scheme="iris",
                            size="1",
                        ),
                        width="fit-content",
                    ),
                    rx.text("—", color="gray"),
                ),
                width="1%",
                white_space="nowrap",
            ),
        ),
        rx.table.cell(
            inline_location_component(item.location),
            display=rx.breakpoints(initial="none", md="table-cell"),
        ),
        rx.table.cell(
            rx.cond(
                item.supplier,
                inline_supplier_component(item.supplier),
                rx.text("—", color="gray"),
            ),
            display=rx.breakpoints(initial="none", md="table-cell"),
        ),
        rx.table.cell(
            rx.cond(
                item.expiry_date,
                expiry_date_badge(item.expiry_date),
                rx.text("—", color="gray"),
            )
        ),
        rx.table.cell(rx.box(status_badge(item.status), width="fit-content")),
        rx.table.cell(
            rx.box(
                item_actions_menu(
                    item=item,
                    on_receive=lambda: ItemsListState.open_receive_dialog(item),
                    on_use=lambda: ItemsListState.open_use_dialog(item),
                    on_move=lambda: ItemsListState.open_move_dialog(item),
                    on_update=lambda: ItemsListState.open_update_dialog(item),
                    on_relabel=lambda: ItemsListState.open_relabel_dialog(item),
                    on_delete=lambda: ItemsListState.open_delete_dialog(item),
                    on_transform=lambda: ItemsListState.open_transform_dialog(item),
                    stop_propagation=True,
                ),
                display="flex",
                justify_content="flex-end",
                align_items="center",
            ),
        ),
        on_click=rx.redirect(ElnAppRouter.get_item_detail_url(item.id)),
        style={":hover": {"background_color": "var(--gray-3)"}, "cursor": "pointer"},
    )


def _items_header() -> rx.Component:
    """Create the header section with title, create button, and filter bar.

    :return: The header component
    :rtype: rx.Component
    """
    return rx.vstack(
        _filter_bar(),
        rx.cond(
            ItemsListState.error_message != "",
            rx.callout(
                ItemsListState.error_message,
                icon="triangle_alert",
                color_scheme="red",
                role="alert",
                margin_bottom="1rem",
            ),
        ),
        width="100%",
        spacing="4",
    )


def _items_table() -> rx.Component:
    """Create the items table with loading, empty, and data states.

    :return: The table component
    :rtype: rx.Component
    """
    return rx.cond(
        ItemsListState.is_loading & (ItemsListState.items.length() == 0),
        rx.center(
            rx.vstack(
                rx.spinner(size="3"),
                rx.text("Loading items...", size="3", color="gray", margin_top="1rem"),
                spacing="2",
                align="center",
            ),
            padding="3rem",
            width="100%",
        ),
        rx.cond(
            ItemsListState.items.length() > 0,
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("Item"),
                        rx.table.column_header_cell(
                            "Code", width="1%", white_space="nowrap"
                        ),
                        rx.table.column_header_cell("Description", max_width="400px"),
                        # Shrink to the widest quantity value.
                        rx.table.column_header_cell(
                            "Quantity", width="1%", white_space="nowrap"
                        ),
                        rx.cond(
                            ItemsListState.show_concentration_column,
                            rx.table.column_header_cell(
                                "Concentration", width="1%", white_space="nowrap"
                            ),
                        ),
                        rx.table.column_header_cell(
                            "Location",
                            display=rx.breakpoints(initial="none", md="table-cell"),
                        ),
                        rx.table.column_header_cell(
                            "Supplier",
                            display=rx.breakpoints(initial="none", md="table-cell"),
                        ),
                        # Shrink to the date badge width. "Next due date" for a
                        # non-consumable sheet, "Expiry Date" otherwise.
                        rx.table.column_header_cell(
                            ItemsListState.expiry_column_label,
                            width="1%",
                            white_space="nowrap",
                        ),
                        # Shrink to the widest status badge.
                        rx.table.column_header_cell(
                            "Status", width="1%", white_space="nowrap"
                        ),
                        # No label; shrink to the menu button, which is right-aligned.
                        rx.table.column_header_cell(
                            "", width="1%", white_space="nowrap", justify="end"
                        ),
                    ),
                ),
                rx.table.body(rx.foreach(ItemsListState.items, _row)),
                width="100%",
                variant="surface",
            ),
            rx.center(
                rx.vstack(
                    rx.icon("package-open", size=48, color="gray"),
                    rx.text("No items found", size="4", color="gray", margin_top="1rem"),
                    spacing="2",
                    align="center",
                ),
                padding="3rem",
                width="100%",
            ),
        ),
    )


def items_list_component(item_sheet_id: rx.Var[str]) -> rx.Component:
    """Create the items list component for a specific item_sheet.

    This component displays a table of items with columns for
    item number, label, location, supplier, quantity,
    expiry date, status, created by, and created at.
    Includes filters for search, location, supplier, and status.

    The component uses on_mount to trigger item loading when mounted,
    and a key based on item_sheet_id to force remount when item_sheet changes.

    :param item_sheet_id: The ID of the item_sheet to display items for
    :type item_sheet_id: rx.Var[str]
    :return: The items list component
    :rtype: rx.Component
    """
    return rx.box(
        rx.vstack(
            _items_header(),
            _items_table(),
            create_item_dialog(),
            item_event_form_dialog(),
            move_item_dialog(),
            update_item_dialog(),
            relabel_item_dialog(),
            use_item_dialog(),
            transform_item_dialog(),
            item_sheet_update_dialog(),
            delete_item_dialog(),
            width="100%",
            spacing="4",
            on_mount=ItemsListState.fetch_items_on_mount(item_sheet_id),
            on_unmount=ItemsListState.on_unmount,
        ),
        key=item_sheet_id,
        width="100%",
    )
