"""Common page layout component with left sidebar navigation menu."""

import reflex as rx
from gws_reflex_base.component.reflex_sidebar_menu_component import (
    menu_item_component,
    sidebar_menu_component,
)
from gws_reflex_main import page_sidebar_component


def sidebar_content() -> rx.Component:
    """Create the sidebar content with logo and navigation links.

    :return: The sidebar content component
    :rtype: rx.Component
    """
    return sidebar_menu_component(
        title="Constellab ELN",
        menu_items=[
            menu_item_component("notebook-text", "Notes", "/"),
            menu_item_component("package", "Materials", "/materials"),
            menu_item_component("map-pin", "Locations", "/locations"),
            menu_item_component("truck", "Suppliers", "/suppliers"),
        ],
        logo_src="/constellab-logo.svg",
    )


def page_layout(
    content: rx.Component,
    header_content: rx.Component | None = None,
    height: str | None = None,
    **kwargs,
) -> rx.Component:
    """Create a common page layout with left sidebar menu and main content area.

    This is a convenience wrapper around page_sidebar_component with the default sidebar content.

    :param content: The main content to display
    :type content: rx.Component
    :param header_content: Optional header content to display at the top (optional)
    :type header_content: rx.Component | None
    :param height: The height of the layout (optional)
    :type height: str | None
    :return: The page layout component
    :rtype: rx.Component
    """
    return page_sidebar_component(
        sidebar_content=sidebar_content(),
        content=content,
        header_content=header_content,
        height=height,
        **kwargs,
    )
