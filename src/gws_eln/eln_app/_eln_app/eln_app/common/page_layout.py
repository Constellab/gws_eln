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
        title="Lab flow",
        subtitle="By Constellab",
        menu_items=[
            menu_item_component(
                "notebook-text", "Notes", "/", additional_active_route_prefixes=["/notes"]
            ),
            menu_item_component(
                "package",
                "Item sheets",
                "/item_sheets",
                additional_active_route_prefixes=["/item_sheets", "/items"],
            ),
            menu_item_component("map-pin", "Locations", "/locations"),
            menu_item_component("truck", "Suppliers", "/suppliers"),
        ],
        logo_src="/constellab-logo.svg",
    )


def page_layout(
    content: rx.Component,
    header_content: rx.Component | None = None,
    height: str | None = None,
    right_sidebar_content: rx.Component | None = None,
    right_sidebar_width: str = "350px",
    max_content_width: str | None = None,
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
    :param right_sidebar_content: Optional content for a right sidebar panel (optional)
    :type right_sidebar_content: rx.Component | None
    :param right_sidebar_width: The width of the right sidebar (default: "350px")
    :type right_sidebar_width: str
    :param max_content_width: Optional max width to constrain header and content area (optional)
    :type max_content_width: str | None
    :return: The page layout component
    :rtype: rx.Component
    """
    content = rx.box(content, width="100%", padding_bottom="2rem")

    return page_sidebar_component(
        sidebar_content=sidebar_content(),
        content=content,
        header_content=header_content,
        height=height,
        right_sidebar_content=right_sidebar_content,
        right_sidebar_width=right_sidebar_width,
        max_content_width=max_content_width,
        **kwargs,
    )
