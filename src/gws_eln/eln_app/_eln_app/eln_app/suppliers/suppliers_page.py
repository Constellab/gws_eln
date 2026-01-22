"""Suppliers page component."""

import reflex as rx
from gws_reflex_main import main_component

from ..common.page_layout import page_layout


def suppliers_page() -> rx.Component:
    """Create the suppliers page component.

    :return: The suppliers page component
    :rtype: rx.Component
    """
    return main_component(
        page_layout(
            rx.vstack(
                rx.center(
                    rx.vstack(
                        rx.icon("truck", size=48, color="gray"),
                        rx.text("Suppliers page coming soon", size="4", color="gray", margin_top="1rem"),
                        spacing="2",
                        align="center",
                    ),
                    padding="3rem",
                    width="100%",
                ),
                width="100%",
                spacing="4",
            ),
            header_content=rx.heading("Suppliers", size="6"),
        )
    )
