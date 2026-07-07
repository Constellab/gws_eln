from collections.abc import Callable

import reflex as rx


def item_sheet_actions_menu(
    on_update: rx.EventHandler | Callable,
    on_delete: rx.EventHandler | Callable,
    on_create_item: rx.EventHandler | Callable,
    stop_propagation: bool = False,
) -> rx.Component:
    """Create the actions menu for a item_sheet.

    :param on_update: Event handler for the update action
    :type on_update: rx.EventHandler | Callable
    :param on_delete: Event handler for the delete action
    :type on_delete: rx.EventHandler | Callable
    :param on_create_item: Event handler to create an item for this sheet.
    :type on_create_item: rx.EventHandler | Callable
    :param stop_propagation: Whether to stop event propagation (useful in table rows)
    :type stop_propagation: bool
    :return: The actions menu component
    :rtype: rx.Component
    """

    def _click(handler: rx.EventHandler | Callable):
        return [rx.stop_propagation, handler] if stop_propagation else handler

    return rx.menu.root(
        rx.menu.trigger(
            rx.button(
                rx.icon("ellipsis-vertical", size=18),
                variant="ghost",
                size="2",
            )
        ),
        rx.menu.content(
            rx.menu.item(
                rx.icon("plus", size=16),
                "Create item",
                on_click=_click(on_create_item),
            ),
            rx.menu.separator(),
            rx.menu.item(
                rx.icon("pencil", size=16),
                "Update",
                on_click=_click(on_update),
            ),
            rx.menu.separator(),
            rx.menu.item(
                rx.icon("trash-2", size=16),
                "Delete",
                color="red",
                on_click=_click(on_delete),
            ),
        ),
    )
