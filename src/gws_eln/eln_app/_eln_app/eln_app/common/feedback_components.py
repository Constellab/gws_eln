"""Reusable inline feedback components (warnings, hints) shared across the app."""

import reflex as rx


def compact_warning(message) -> rx.Component:
    """A compact amber warning banner (small text on a soft amber background).

    Styled like a soft activity badge (amber ``3`` background, amber ``11``
    icon/text) so it stands out.

    :param message: The warning text (a plain string or a reactive Var).
    :return: An hstack banner with a small triangle-alert icon and the message.
    """
    return rx.hstack(
        rx.icon("triangle-alert", size=13, color="var(--amber-11)", flex_shrink="0"),
        rx.text(message, size="1", color="var(--amber-11)"),
        spacing="1",
        align="center",
        width="100%",
        background="var(--amber-3)",
        border="1px solid var(--amber-6)",
        padding="0.375rem 0.5rem",
        border_radius="0.5rem",
    )
