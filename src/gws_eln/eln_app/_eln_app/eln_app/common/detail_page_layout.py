"""Common detail page layout component with sidebar on the right."""

import reflex as rx

from .breadcrumb.breadcrumb_component import breadcrumb_component
from .breadcrumb.breadcrumb_state import BreadcrumbState

# Breakpoint for small screens (in pixels)
SMALL_SCREEN_BREAKPOINT = "900px"


class DetailPageState(rx.State):
    """State for managing the detail page layout."""

    show_detail: bool = True

    def toggle_detail(self):
        """Toggle the visibility of the detail section."""
        self.show_detail = not self.show_detail


def _sidebar_content_box(sidebar_content: rx.Component) -> rx.Component:
    """Create the styled sidebar content box.

    :param sidebar_content: The content to display in the sidebar
    :type sidebar_content: rx.Component
    :return: The styled sidebar box
    :rtype: rx.Component
    """
    return rx.vstack(
        sidebar_content,
        padding="1.5rem",
        background="var(--gray-2)",
        border_radius="8px",
        align_items="start",
        width="100%",
        height="100%",
        overflow_y="auto",
    )


def _desktop_sidebar(sidebar_content: rx.Component) -> rx.Component:
    """Create the desktop sidebar (inline, side-by-side with content).

    :param sidebar_content: The content to display in the sidebar
    :type sidebar_content: rx.Component
    :return: The desktop sidebar component
    :rtype: rx.Component
    """
    return rx.box(
        _sidebar_content_box(sidebar_content),
        width="450px",
        min_width="450px",
        display=rx.breakpoints(initial="none", lg="block"),
    )


def _mobile_sidebar_overlay(sidebar_content: rx.Component) -> rx.Component:
    """Create the mobile sidebar overlay (slides over content on small screens).

    :param sidebar_content: The content to display in the sidebar
    :type sidebar_content: rx.Component
    :return: The mobile sidebar overlay component
    :rtype: rx.Component
    """
    return rx.box(
        # Backdrop overlay
        rx.box(
            position="fixed",
            top="0",
            left="0",
            right="0",
            bottom="0",
            background="rgba(0, 0, 0, 0.4)",
            z_index="998",
            on_click=DetailPageState.toggle_detail,
        ),
        # Sidebar panel
        rx.box(
            rx.hstack(
                rx.icon_button(
                    rx.icon("x", size=20),
                    on_click=DetailPageState.toggle_detail,
                    variant="ghost",
                    size="2",
                    cursor="pointer",
                ),
                justify="end",
                width="100%",
                padding_bottom="0.5rem",
            ),
            _sidebar_content_box(sidebar_content),
            position="fixed",
            top="0",
            right="0",
            bottom="0",
            width="min(450px, 90vw)",
            background="var(--color-background)",
            box_shadow="-4px 0 20px rgba(0, 0, 0, 0.15)",
            z_index="999",
            padding="1rem",
            display="flex",
            flex_direction="column",
            overflow_y="auto",
        ),
        display=rx.breakpoints(initial="block", lg="none"),
    )


def detail_toggle_sidebar_button() -> rx.Component:
    """Create a button to toggle the sidebar visibility.

    :return: The toggle button component
    :rtype: rx.Component
    """
    return rx.tooltip(
        rx.icon_button(
            rx.cond(
                DetailPageState.show_detail,
                rx.icon("chevron-right", size=20),
                rx.icon("chevron-left", size=20),
            ),
            on_click=DetailPageState.toggle_detail,
            variant="soft",
            size="2",
            cursor="pointer",
        ),
        content=rx.cond(
            DetailPageState.show_detail,
            "Hide detail panel",
            "Show detail panel",
        ),
    )


def detail_page_layout(
    main_content: rx.Component,
    sidebar_content: rx.Component,
    show_header: bool = True,
) -> rx.Component:
    """Create a common layout for detail pages with breadcrumb, main content and sidebar.

    This component provides a two-column layout with:
    - Breadcrumb: Positioned at the top, constrained by center layout max width
    - Center section: Main content with max width of 1200px, centered on large screens
    - Right section: Sidebar with fixed width of 450px, styled with background and padding

    On small screens (< 900px), the sidebar opens as an overlay panel that slides in
    from the right side, with a backdrop that can be clicked to close it.

    :param main_content: The main content to display in the center section
    :type main_content: rx.Component
    :param sidebar_content: The sidebar content to display on the right
    :type sidebar_content: rx.Component
    :param show_header: Whether to show the header with breadcrumb and toggle button, defaults to True
    :type show_header: bool, optional
    :return: The detail page layout component
    :rtype: rx.Component
    """
    return rx.vstack(
        # Header row with breadcrumb and toggle button
        rx.cond(
            show_header,
            rx.hstack(
                breadcrumb_component(BreadcrumbState.breadcrumbs),
                rx.spacer(),
                detail_toggle_sidebar_button(),
                width="100%",
                align_items="center",
            ),
        ),
        rx.hstack(
            # Main content area (center, max width 1200px)
            rx.vstack(
                main_content,
                max_width="1200px",
                width="100%",
                height="100%",
                class_name="detail-page-main-content",
            ),
            # Desktop sidebar (inline, visible on larger screens)
            rx.cond(
                DetailPageState.show_detail,
                _desktop_sidebar(sidebar_content),
            ),
            flex="1",
            min_height="0",
            width="100%",
            spacing="4",
            align_items="start",
            justify="center",
        ),
        # Mobile sidebar overlay (visible on small screens when open)
        rx.cond(
            DetailPageState.show_detail,
            _mobile_sidebar_overlay(sidebar_content),
        ),
        width="100%",
        position="relative",
        flex=1,
        display="flex",
        flex_direction="column",
        class_name="detail-page-layout-container",
    )


def detail_content_layout(
    main_content: rx.Component,
    header_content: rx.Component | None = None,
) -> rx.Component:
    """Create a layout for detail pages with header and main content.

    The right sidebar is handled at the page_layout / page_sidebar_component level.
    This component only manages the main content column.

    :param main_content: The main content to display
    :type main_content: rx.Component
    :param header_content: Optional header content to display below the breadcrumb
    :type header_content: rx.Component | None
    :return: The detail content layout component
    :rtype: rx.Component
    """
    return rx.vstack(
        # Optional header content
        rx.cond(
            header_content is not None,
            rx.box(
                header_content,
                width="100%",
            ),
            rx.fragment(),
        ),
        # Main content area
        rx.vstack(
            main_content,
            width="100%",
            flex="1",
            min_height="0",
        ),
        flex="1",
        width="100%",
        height="100%",
    )
