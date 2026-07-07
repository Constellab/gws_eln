"""Item detail page component."""

import reflex as rx
from gws_reflex_main import main_component, right_sidebar_close_button, user_inline_component

from ..activities.activities_list_component import activities_list_component
from ..common.breadcrumb.breadcrumb_component import breadcrumb_component
from ..common.breadcrumb.breadcrumb_state import BreadcrumbState
from ..common.detail_page_layout import detail_content_layout
from ..common.page_layout import page_layout
from ..item_sheets.core.item_sheet_components import (
    inline_item_sheet_link,
)
from ..item_sheets.item_sheet_form_dialog.item_sheet_form_dialog_component import (
    item_sheet_update_dialog,
)
from ..lineage.lineage_graph_component import lineage_graph_component
from ..locations.core.inline_location_component import inline_location_component
from ..suppliers.core.inline_supplier_component import inline_supplier_component
from .core.item_actions_menu import item_actions_menu
from .core.item_components import expiry_date_badge, status_badge
from .delete_item_form_dialog.delete_item_form_dialog_component import (
    delete_item_dialog,
)
from .item_detail_state import ItemDetailState
from .item_event_form_dialog.item_event_form_dialog_component import (
    item_event_form_dialog,
)
from .item_form_dialog.item_form_dialog_component import (
    create_item_dialog,
)
from .move_item_form_dialog.move_item_form_dialog_component import (
    move_item_dialog,
)
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
    """Create the details sidebar with item information.

    :return: The details sidebar component
    :rtype: rx.Component
    """
    return rx.vstack(
        # Heading with close button
        rx.hstack(
            _sidebar_section_label("Item details"),
            rx.spacer(),
            right_sidebar_close_button(),
            width="100%",
            align="center",
            margin_bottom="1rem",
        ),
        # Main info grid (label + value per row)
        rx.grid(
            # Code
            rx.text("Code", size="2", color="gray", weight="medium"),
            rx.code(ItemDetailState.item.code, size="2"),
            # Label
            rx.cond(
                ItemDetailState.item.label,
                rx.fragment(
                    rx.text("Label", size="2", color="gray", weight="medium"),
                    rx.text(ItemDetailState.item.label, size="2"),
                ),
            ),
            # ItemSheet
            rx.text("Item sheet", size="2", color="gray", weight="medium"),
            inline_item_sheet_link(ItemDetailState.item.item_sheet),
            # Location
            rx.text("Location", size="2", color="gray", weight="medium"),
            inline_location_component(ItemDetailState.item.location),
            # Supplier
            rx.cond(
                ItemDetailState.item.supplier,
                rx.fragment(
                    rx.text("Supplier", size="2", color="gray", weight="medium"),
                    inline_supplier_component(ItemDetailState.item.supplier),
                ),
            ),
            # Serial number (non-consumable serialized units)
            rx.cond(
                ItemDetailState.item.serial_number,
                rx.fragment(
                    rx.text("Serial number", size="2", color="gray", weight="medium"),
                    rx.code(ItemDetailState.item.serial_number, size="2"),
                ),
            ),
            # Quantity
            rx.text("Quantity", size="2", color="gray", weight="medium"),
            rx.text(ItemDetailState.item.pretty_quantity, size="2"),
            # Concentration unit
            rx.cond(
                ItemDetailState.item.concentration,
                rx.fragment(
                    rx.text("Concentration", size="2", color="gray", weight="medium"),
                    rx.text(
                        f"{ItemDetailState.item.concentration} {ItemDetailState.item.concentration_unit}",
                        size="2",
                    ),
                ),
            ),
            # Storage conditions (always shown; "—" when not set)
            rx.text("Storage conditions", size="2", color="gray", weight="medium"),
            rx.text(
                rx.cond(
                    ItemDetailState.item.storage_conditions,
                    ItemDetailState.item.storage_conditions,
                    "—",
                ),
                size="2",
            ),
            # Expiry Date
            rx.text("Expiry Date", size="2", color="gray", weight="medium"),
            rx.box(expiry_date_badge(ItemDetailState.item.expiry_date)),
            # Status
            rx.text("Status", size="2", color="gray", weight="medium"),
            rx.box(status_badge(ItemDetailState.item.status), width="fit-content"),
            columns="2",
            spacing="3",
            width="100%",
            row_gap="1rem",
        ),
        # Notes section (separate, with title above)
        rx.cond(
            ItemDetailState.item.notes,
            rx.vstack(
                rx.divider(margin_top="1.5rem", margin_bottom="1.5rem"),
                _sidebar_section_label("Notes"),
                rx.text(ItemDetailState.item.notes, size="2"),
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
                user_inline_component(ItemDetailState.item.created_by, size="small"),
            ),
            _sidebar_metadata_row(
                "Created at",
                rx.text(
                    rx.moment(ItemDetailState.item.created_at, format="MMM D, YYYY HH:mm"),
                    size="1",
                    weight="medium",
                ),
            ),
            _sidebar_metadata_row(
                "Last modified by",
                user_inline_component(ItemDetailState.item.last_modified_by, size="small"),
            ),
            _sidebar_metadata_row(
                "Last modified at",
                rx.text(
                    rx.moment(ItemDetailState.item.last_modified_at, format="MMM D, YYYY HH:mm"),
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


def _main_content() -> rx.Component:
    """Create the main content area: tabs for activities and lineage.

    Instruments (non-consumable item sheets) have no meaningful lineage - they
    are only referenced through USE activities - so the Lineage tab is hidden for
    them and the activities list is enough.

    :return: The main content component
    :rtype: rx.Component
    """
    is_consumable = ItemDetailState.item.item_sheet.is_consumable
    return rx.tabs.root(
        rx.tabs.list(
            rx.tabs.trigger("Activities", value="activities"),
            rx.cond(
                is_consumable,
                rx.tabs.trigger("Lineage", value="lineage"),
            ),
        ),
        rx.tabs.content(
            activities_list_component(ItemDetailState.item.id),
            value="activities",
            padding_top="1rem",
        ),
        rx.cond(
            is_consumable,
            rx.tabs.content(
                lineage_graph_component(ItemDetailState.item.id),
                value="lineage",
                padding_top="1rem",
            ),
        ),
        default_value="activities",
        width="100%",
    )


def _actions_menu() -> rx.Component:
    """Create the actions dropdown menu for item operations.

    :return: The actions menu component
    :rtype: rx.Component
    """
    return item_actions_menu(
        item=ItemDetailState.item,
        on_receive=ItemDetailState.open_receive_dialog,
        on_consume=ItemDetailState.open_consume_dialog,
        on_use=ItemDetailState.open_use_dialog,
        on_move=ItemDetailState.open_move_dialog,
        on_update=ItemDetailState.open_update_dialog,
        on_relabel=ItemDetailState.open_relabel_dialog,
        on_delete=ItemDetailState.open_delete_dialog,
        on_transform=ItemDetailState.open_transform_dialog,
    )


def _header() -> rx.Component:
    """Create the header component for the item detail page.

    :return: The header component
    :rtype: rx.Component
    """
    return rx.hstack(
        rx.cond(
            ItemDetailState.item.label,
            # With a label: label is the title, code shown as a badge below
            rx.vstack(
                rx.heading(ItemDetailState.item.label, size="6"),
                rx.code(ItemDetailState.item.code, size="2"),
                spacing="1",
                align="start",
            ),
            # No label: the code is the title
            rx.heading(ItemDetailState.item.code, size="6"),
        ),
        rx.spacer(),
        rx.cond(
            ItemDetailState.item,
            _actions_menu(),
        ),
        width="100%",
        align="center",
        spacing="2",
    )


def item_detail_page() -> rx.Component:
    """Create the item detail page component.

    Displays item information in a sidebar on the right side,
    with a main content area on the left for activities list.

    :return: The item detail page component
    :rtype: rx.Component
    """
    return main_component(
        page_layout(
            rx.cond(
                ItemDetailState.error_message != "",
                rx.callout(
                    ItemDetailState.error_message,
                    icon="triangle_alert",
                    color_scheme="red",
                    role="alert",
                ),
                rx.cond(
                    ItemDetailState.is_loading,
                    rx.center(rx.spinner(size="3"), padding="2rem"),
                    rx.cond(
                        ItemDetailState.item,
                        detail_content_layout(
                            main_content=_main_content(),
                            header_content=_header(),
                        ),
                        rx.center(
                            rx.vstack(
                                rx.icon("package-x", size=48, color="gray"),
                                rx.text(
                                    "Item not found",
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
        ),
        item_event_form_dialog(),
        move_item_dialog(),
        update_item_dialog(),
        relabel_item_dialog(),
        use_item_dialog(),
        transform_item_dialog(),
        create_item_dialog(),
        item_sheet_update_dialog(),
        delete_item_dialog(),
    )
