"""Home page: the app's landing page, offering the two main entry points."""

import reflex as rx
from gws_reflex_main import main_component

from ..common.eln_app_router import ElnAppRouter

# Hover choreography: the whole card lifts, its icon grows and the arrow slides.
# The nested selectors target the classes set on those two children below.
# The card keeps Radix's own border: a surface Card draws it as a ring on its
# ::after (box-shadow "0 0 0 1px var(--gray-a5)"), so declaring a `border` here
# would stack a second one on top. Overriding Radix's own variable recolors that
# single ring on hover instead.
_CARD_STYLE = {
    "transition": "transform 0.2s ease, box-shadow 0.2s ease",
    ":hover": {
        "transform": "translateY(-4px)",
        "box_shadow": "0 16px 32px -12px var(--accent-a7)",
        "--base-card-surface-box-shadow": "0 0 0 1px var(--accent-8)",
    },
    ":hover .home-card-icon": {"transform": "scale(1.06)"},
    ":hover .home-card-arrow": {"transform": "translateX(2px)"},
}


def _action_card(icon: str, title: str, description: str, url: str) -> rx.Component:
    """One clickable entry-point card.

    :param icon: The Lucide icon name shown in the card's gradient badge.
    :type icon: str
    :param title: The action title.
    :type title: str
    :param description: One line explaining what the action leads to.
    :type description: str
    :param url: The route the card navigates to.
    :type url: str
    :return: The card component.
    :rtype: rx.Component
    """
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.box(
                    rx.icon(icon, size=26, color="var(--accent-contrast)"),
                    class_name="home-card-icon",
                    background="linear-gradient(135deg, var(--accent-7), var(--accent-10))",
                    padding="0.85rem",
                    border_radius="1rem",
                    display="flex",
                    box_shadow="0 6px 16px -6px var(--accent-a9)",
                    style={"transition": "transform 0.2s ease"},
                ),
                rx.spacer(),
                rx.icon(
                    "arrow-right",
                    size=20,
                    color="var(--accent-9)",
                    class_name="home-card-arrow",
                    style={"transition": "transform 0.2s ease"},
                ),
                width="100%",
                align="center",
            ),
            rx.vstack(
                rx.heading(title, size="5"),
                rx.text(description, size="2", color="gray", line_height="1.6"),
                spacing="2",
                align="start",
                width="100%",
            ),
            spacing="5",
            align="start",
            height="100%",
            width="100%",
        ),
        on_click=rx.redirect(url),
        cursor="pointer",
        size="4",
        width="100%",
        height="100%",
        style=_CARD_STYLE,
    )


def _branding_header() -> rx.Component:
    """App branding shown on the landing page, since the sidebar (which
    normally carries it) is not displayed here.

    :return: The branding header component.
    :rtype: rx.Component
    """
    return rx.hstack(
        rx.image(src="/constellab-logo.svg", height="2.5rem"),
        rx.vstack(
            rx.heading("Lab flow", size="4", line_height="1em"),
            rx.text("By Constellab", size="1", color="var(--gray-9)", line_height="1em"),
            spacing="1",
        ),
        align="center",
        spacing="3",
    )


def home_page() -> rx.Component:
    """Create the home page with the two main entry points.

    One card leads to the item sheets (stock management), the other to the notes
    (protocols). The landing page has no sidebar: the navigation menu only
    appears once the user has entered one of the two sections.

    :return: The home page component.
    :rtype: rx.Component
    """
    return main_component(
        rx.box(
            rx.vstack(
                _branding_header(),
                rx.vstack(
                    rx.heading("What would you like to do?", size="7"),
                    rx.text(
                        "Pick one to get started.",
                        size="3",
                        color="gray",
                    ),
                    spacing="2",
                    align="start",
                    width="100%",
                ),
                rx.grid(
                    _action_card(
                        "package",
                        "Manage my stocks",
                        "Browse your item sheets, receive stock, transform items "
                        "and keep track of everything in the lab.",
                        ElnAppRouter.get_item_sheet_list_url(),
                    ),
                    _action_card(
                        "notebook-text",
                        "Create or resume a protocol",
                        "Write up your experiments and link them to the items you use.",
                        ElnAppRouter.get_notes_list_url(),
                    ),
                    columns=rx.breakpoints(initial="1", sm="2"),
                    spacing="5",
                    width="100%",
                    align_items="stretch",
                ),
                spacing="7",
                width="100%",
                max_width="900px",
                margin="0 auto",
                padding_top="3rem",
            ),
            width="100%",
            height="100vh",
            overflow_y="auto",
            padding="2em",
        )
    )
