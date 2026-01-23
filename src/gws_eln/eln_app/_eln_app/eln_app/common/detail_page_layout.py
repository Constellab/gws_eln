"""Common detail page layout component with sidebar on the right."""

import reflex as rx


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
    """Create a common layout for detail pages with main content on the left and sidebar on the right.

    This component provides a two-column layout with:
    - Left section: Main content area that fills remaining space
    - Right section: Sidebar with fixed width of 350px, styled with background and padding

    :param main_content: The main content to display on the left
    :type main_content: rx.Component
    :param sidebar_content: The sidebar content to display on the right
    :type sidebar_content: rx.Component
    :return: The detail page layout component
    :rtype: rx.Component
    """
    return rx.hstack(
        # Main content area (left, fills remaining space)
        rx.vstack(
            main_content,
            width="100%",
            flex="1",
        ),
        # Sidebar section (right) with toggle button above
        rx.vstack(
            # Toggle button
            rx.hstack(
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
                justify="end",
            ),
            # Sidebar content
            rx.cond(
                DetailPageState.show_detail,
                rx.vstack(
                    sidebar_content,
                    width="350px",
                    min_width="350px",
                    padding="1.5rem",
                    background="var(--gray-2)",
                    border_radius="8px",
                    align_items="start",
                ),
            ),
            align_items="end",
            spacing="2",
        ),
        flex="1",
        min_height="0",
        width="100%",
        spacing="4",
        align_items="start",
        class_name="detail-page-layout",
    )
