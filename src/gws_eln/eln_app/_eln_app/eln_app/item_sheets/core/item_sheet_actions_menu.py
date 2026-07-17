from collections.abc import Callable

import reflex as rx


def item_sheet_actions_menu(
    on_update: rx.EventHandler | Callable,
    on_delete: rx.EventHandler | Callable,
    on_create_item: rx.EventHandler | Callable | None = None,
    stop_propagation: bool = False,
    disabled: rx.Var[bool] | bool = False,
) -> rx.Component:
    """Create the actions menu for a item_sheet.

    :param on_update: Event handler for the update action
    :type on_update: rx.EventHandler | Callable
    :param on_delete: Event handler for the delete action
    :type on_delete: rx.EventHandler | Callable
    :param on_create_item: Optional event handler to create an item for this sheet.
        When provided, a "Create item" entry is added at the top of the menu.
    :type on_create_item: rx.EventHandler | Callable | None
    :param stop_propagation: Whether to stop event propagation (useful in table rows)
    :type stop_propagation: bool
    :param disabled: When true, the whole menu is hidden so no action is possible
        (used for a discarded sheet, which is locked).
    :type disabled: rx.Var[bool] | bool
    :return: The actions menu component
    :rtype: rx.Component
    """

    def _click(handler: rx.EventHandler | Callable):
        return [rx.stop_propagation, handler] if stop_propagation else handler

    create_item_entries = []
    if on_create_item is not None:
        create_item_entries = [
            rx.menu.item(
                rx.icon("plus", size=16),
                "Create item",
                on_click=_click(on_create_item),
            ),
            rx.menu.separator(),
        ]

    menu = rx.menu.root(
        rx.menu.trigger(
            rx.button(
                rx.icon("ellipsis-vertical", size=18),
                variant="ghost",
                size="2",
            )
        ),
        rx.menu.content(
            *create_item_entries,
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

    # A discarded sheet is locked: hide the actions menu entirely.
    return rx.cond(disabled, rx.fragment(), menu)
