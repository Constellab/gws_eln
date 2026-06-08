"""Breadcrumb navigation component."""

import reflex as rx

from .breadcrumb_state import BreadcrumbItem


def breadcrumb_component(breadcrumbs: list[BreadcrumbItem]) -> rx.Component:
    """Create the breadcrumb navigation component.

    This component displays a clickable breadcrumb trail showing the hierarchy
    of the current page: ItemSheets > [ITEM_SHEET_NAME] > [ITEM_NUMBER] > [ALIQUOT_NUMBER]

    :param breadcrumbs: The list of breadcrumb items to display
    :type breadcrumbs: list[BreadcrumbItem]
    :return: The breadcrumb component
    :rtype: rx.Component
    """
    return rx.hstack(
        rx.foreach(breadcrumbs, _render_item_with_separator),
        spacing="0",
        align="center",
    )


def _render_item_with_separator(item: BreadcrumbItem, idx: int) -> rx.Component:
    """Render a breadcrumb item with a separator if not first.

    :param item: The breadcrumb item
    :param idx: The index of the item
    :return: The rendered component
    :rtype: rx.Component
    """
    # Add separator before all items except the first
    return rx.fragment(
        rx.cond(
            idx > 0,
            rx.icon("chevron-right", size=16, color="gray", margin_x="0.25rem"),
            rx.fragment(),
        ),
        rx.link(
            rx.text(item.label, size="2", weight="medium", _hover={"text_decoration": "underline"}),
            href=item.url,
            style={"text_decoration": "none"},
        ),
    )
