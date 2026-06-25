"""Reusable inline feedback components (warnings, hints) shared across the app."""

import reflex as rx


def compact_warning(message) -> rx.Component:
    """A compact amber warning line (small text, like a secondary label).

    :param message: The warning text (a plain string or a reactive Var).
    :return: An hstack with a small triangle-alert icon and the message.
    """
    return rx.hstack(
        rx.icon("triangle-alert", size=13, color="var(--amber-11)", flex_shrink="0"),
        rx.text(message, size="1", color="var(--amber-11)"),
        spacing="1",
        align="start",
        width="100%",
    )
