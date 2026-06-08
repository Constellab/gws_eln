"""ItemSheet detail page component."""

import reflex as rx
from gws_reflex_main import main_component, right_sidebar_close_button, user_inline_component

from ..items.items_list_component import items_list_component
from ..items.items_list_state import ItemsListState
from ..items.core.item_components import consumable_badge
from ..common.breadcrumb.breadcrumb_component import breadcrumb_component
from ..common.breadcrumb.breadcrumb_state import BreadcrumbState
from ..common.detail_page_layout import detail_content_layout
from ..common.page_layout import page_layout
from ..suppliers.core.inline_supplier_component import inline_supplier_component
from .core.item_sheet_actions_menu import item_sheet_actions_menu
from .item_sheet_detail_state import ItemSheetDetailState
from .item_sheet_form_dialog.item_sheet_form_dialog_component import item_sheet_update_dialog


def _sidebar_section_label(label: str) -> rx.Component:
    """Create a small uppercase gray label for a sidebar section.

    :param label: The label text
    :type label: str
    :return: The styled label component
    :rtype: rx.Component
    """
    return rx.text(
        label,
        size="1",
        color="gray",
        weight="bold",
        style={
            "text-transform": "uppercase",
            "letter-spacing": "0.06em",
        },
    )


def _sidebar_metadata_row(label: str, value: rx.Component) -> rx.Component:
    """Create a metadata row with a label on the left and value on the right.

    :param label: The label text
    :type label: str
    :param value: The value component
    :type value: rx.Component
    :return: The metadata row component
    :rtype: rx.Component
    """
    return rx.hstack(
        rx.text(label, size="2", color="gray"),
        rx.spacer(),
        value,
        width="100%",
        align="center",
    )


def _details_sidebar() -> rx.Component:
    """Create the details sidebar with item_sheet information.

    :return: The details sidebar component
    :rtype: rx.Component
    """
    return rx.vstack(
        # Heading with close button
        rx.hstack(
            _sidebar_section_label("ItemSheet details"),
            rx.spacer(),
            right_sidebar_close_button(),
            width="100%",
            align="center",
            margin_bottom="1rem",
        ),
        # Main info grid (label + value per row)
        rx.grid(
            # Name
            rx.text("Name", size="2", color="gray", weight="medium"),
            rx.text(ItemSheetDetailState.item_sheet.name, size="2"),
            # Default Supplier
            rx.cond(
                ItemSheetDetailState.item_sheet.default_supplier,
                rx.fragment(
                    rx.text("Default Supplier", size="2", color="gray", weight="medium"),
                    inline_supplier_component(ItemSheetDetailState.item_sheet.default_supplier),
                ),
            ),
            # Type
            rx.text("Type", size="2", color="gray", weight="medium"),
            rx.box(consumable_badge(ItemSheetDetailState.item_sheet.is_consumable), width="fit-content"),
            # Default Unit Type
            rx.text("Default Unit Type", size="2", color="gray", weight="medium"),
            rx.text(
                ItemSheetDetailState.item_sheet.default_unit_type,
                size="2",
                style={"text_transform": "capitalize"},
            ),
            columns="2",
            spacing="3",
            width="100%",
            row_gap="1rem",
        ),
        # Description section (separate, with title above)
        rx.cond(
            ItemSheetDetailState.item_sheet.description,
            rx.vstack(
                rx.divider(margin_top="1.5rem", margin_bottom="1.5rem"),
                _sidebar_section_label("Description"),
                rx.text(ItemSheetDetailState.item_sheet.description, size="2"),
                spacing="0",
                align_items="start",
                width="100%",
                gap="0.5rem",
            ),
        ),
        # Divider + metadata section
        rx.vstack(
            rx.divider(margin_top="1.5rem", margin_bottom="1.5rem"),
            _sidebar_metadata_row(
                "Created by",
                user_inline_component(ItemSheetDetailState.item_sheet.created_by, size="small"),
            ),
            _sidebar_metadata_row(
                "Created at",
                rx.text(
                    rx.moment(ItemSheetDetailState.item_sheet.created_at, format="MMM D, YYYY HH:mm"),
                    size="1",
                    weight="medium",
                ),
            ),
            _sidebar_metadata_row(
                "Last modified by",
                user_inline_component(ItemSheetDetailState.item_sheet.last_modified_by, size="small"),
            ),
            _sidebar_metadata_row(
                "Last modified at",
                rx.text(
                    rx.moment(
                        ItemSheetDetailState.item_sheet.last_modified_at, format="MMM D, YYYY HH:mm"
                    ),
                    size="1",
                    weight="medium",
                ),
            ),
            spacing="1",
            width="100%",
            padding_top="0.5rem",
        ),
        width="100%",
        spacing="0",
        align_items="start",
    )


def _create_item_button() -> rx.Component:
    """Create the button to open the create item dialog.

    :return: The create item button component
    :rtype: rx.Component
    """
    return rx.button(
        rx.icon("plus", size=18),
        "Create New Item",
        size="2",
        on_click=ItemsListState.open_create_dialog,
    )


def _header() -> rx.Component:
    """Create the header component for the item_sheet detail page.

    :return: The header component
    :rtype: rx.Component
    """
    return rx.hstack(
        rx.heading(ItemSheetDetailState.item_sheet.name, size="6"),
        rx.spacer(),
        _create_item_button(),
        item_sheet_actions_menu(
            on_update=ItemSheetDetailState.open_update_dialog,
            on_delete=ItemSheetDetailState.open_delete_dialog,
        ),
        item_sheet_update_dialog(),
        width="100%",
        align="center",
        spacing="4",
    )


def _main_content() -> rx.Component:
    """Create the main content area with items list.

    :return: The main content component
    :rtype: rx.Component
    """
    return items_list_component(ItemSheetDetailState.item_sheet.id)


def item_sheet_detail_page() -> rx.Component:
    """Create the item_sheet detail page component.

    Displays item_sheet information in a sidebar on the right side,
    with a main content area on the left for items list.

    :return: The item_sheet detail page component
    :rtype: rx.Component
    """
    return rx.box(
        main_component(
            page_layout(
                rx.cond(
                    ItemSheetDetailState.error_message != "",
                    rx.callout(
                        ItemSheetDetailState.error_message,
                        icon="triangle_alert",
                        color_scheme="red",
                        role="alert",
                    ),
                    rx.cond(
                        ItemSheetDetailState.is_loading,
                        rx.center(rx.spinner(size="3"), padding="2rem"),
                        rx.cond(
                            ItemSheetDetailState.item_sheet,
                            detail_content_layout(
                                main_content=_main_content(),
                                header_content=_header(),
                            ),
                            rx.center(
                                rx.vstack(
                                    rx.icon("package-x", size=48, color="gray"),
                                    rx.text(
                                        "ItemSheet not found",
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
                ),
                right_sidebar_content=_details_sidebar(),
                header_content=breadcrumb_component(BreadcrumbState.breadcrumbs),
                max_content_width="1200px",
                height="100vh",
                padding="0",
            )
        ),
    )
