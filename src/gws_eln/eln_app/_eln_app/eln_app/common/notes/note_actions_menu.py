"""Actions menu component for notes."""

from collections.abc import Callable

import reflex as rx


def note_actions_menu(
    on_update: rx.EventHandler | Callable,
    on_delete: rx.EventHandler | Callable,
    stop_propagation: bool = False,
) -> rx.Component:
    """Create the actions menu for a note.

    :param on_update: Event handler for the update action
    :type on_update: rx.EventHandler | Callable
    :param on_delete: Event handler for the delete action
    :type on_delete: rx.EventHandler | Callable
    :param stop_propagation: Whether to stop event propagation (useful in table rows)
    :type stop_propagation: bool
    :return: The actions menu component
    :rtype: rx.Component
    """
    update_click = [rx.stop_propagation, on_update] if stop_propagation else on_update
    delete_click = [rx.stop_propagation, on_delete] if stop_propagation else on_delete

    return rx.menu.root(
        rx.menu.trigger(
            rx.button(
                rx.icon("ellipsis-vertical", size=18),
                variant="soft",
                size="2",
            )
        ),
        rx.menu.content(
            rx.menu.item(
                rx.icon("pencil", size=16),
                "Update",
                on_click=update_click,
            ),
            rx.menu.separator(),
            rx.menu.item(
                rx.icon("trash-2", size=16),
                "Delete",
                color="red",
                on_click=delete_click,
            ),
        ),
    )
