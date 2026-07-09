"""Wrap a select with an inline "+" button to create a new option on the fly."""

import reflex as rx


def select_with_create(
    select: rx.Component,
    on_create: rx.EventHandler,
    tooltip: str = "Create a new one",
) -> rx.Component:
    """Render a select next to a small "+" button that opens a create dialog.

    Lets the user create a missing option without aborting the current form.

    Args:
        select: The select component (takes the remaining width)
        on_create: Handler opening the create dialog (must be type="button" safe)
        tooltip: Tooltip shown on the "+" button
    """
    return rx.hstack(
        rx.box(select, flex="1", min_width="0"),
        rx.tooltip(
            rx.icon_button(
                rx.icon("plus"),
                type="button",
                variant="soft",
                size="1",
                on_click=on_create,
            ),
            content=tooltip,
        ),
        spacing="1",
        align="center",
        width="100%",
    )
