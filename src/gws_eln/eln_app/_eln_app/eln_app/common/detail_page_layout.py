"""Common detail page layout component with sidebar on the right."""

import reflex as rx

from .breadcrumb.breadcrumb_component import breadcrumb_component


class DetailPageState(rx.State):
    """State for managing the detail page layout."""

    show_detail: bool = True

    def toggle_detail(self):
        """Toggle the visibility of the detail section."""
        self.show_detail = not self.show_detail


def detail_page_layout(
    main_content: rx.Component,
    sidebar_content: rx.Component,
) -> rx.Component:
    """Create a common layout for detail pages with breadcrumb, main content and sidebar.

    This component provides a two-column layout with:
    - Breadcrumb: Positioned at the top, constrained by center layout max width
    - Center section: Main content with max width of 1200px, centered on large screens
    - Right section: Sidebar with fixed width of 450px, styled with background and padding

    :param main_content: The main content to display in the center section
    :type main_content: rx.Component
    :param sidebar_content: The sidebar content to display on the right
    :type sidebar_content: rx.Component
    :return: The detail page layout component
    :rtype: rx.Component
    """
    return rx.vstack(
        # Header row with breadcrumb and toggle button
        rx.hstack(
            breadcrumb_component(),
            rx.spacer(),
            rx.tooltip(
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
            ),
            width="100%",
            align_items="center",
        ),
        rx.hstack(
            # Main content area (center, max width 1200px)
            rx.vstack(
                main_content,
                max_width="1200px",
                width="100%",
                height="100%",
            ),
            # Sidebar (right, fixed width with styling)
            rx.cond(
                DetailPageState.show_detail,
                rx.vstack(
                    sidebar_content,
                    width="450px",
                    min_width="450px",
                    padding="1.5rem",
                    background="var(--gray-2)",
                    border_radius="8px",
                    align_items="start",
                ),
            ),
            flex="1",
            min_height="0",
            width="100%",
            spacing="4",
            align_items="start",
            justify="center",
        ),
        height="100%",
        width="100%",
    )
