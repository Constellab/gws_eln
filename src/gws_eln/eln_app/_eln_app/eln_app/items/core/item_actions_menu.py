"""Item actions menu component."""

from collections.abc import Callable

import reflex as rx
from gws_eln.items.item_dto import ItemDTO


def item_actions_menu(
    item: ItemDTO,
    on_receive: rx.EventHandler | Callable,
    on_consume: rx.EventHandler | Callable,
    on_move: rx.EventHandler | Callable,
    on_update: rx.EventHandler | Callable,
    on_relabel: rx.EventHandler | Callable,
    on_delete: rx.EventHandler | Callable,
    on_split: rx.EventHandler | Callable | None = None,
    on_combine: rx.EventHandler | Callable | None = None,
    stop_propagation: bool = False,
) -> rx.Component:
    """Create the actions menu for a item.

    :param item: The item DTO to determine which actions to show
    :type item: ItemDTO
    :param on_receive: Event handler for receive stock action
    :type on_receive: rx.EventHandler | Callable
    :param on_consume: Event handler for consume stock action
    :type on_consume: rx.EventHandler | Callable
    :param on_move: Event handler for move item action
    :type on_move: rx.EventHandler | Callable
    :param on_update: Event handler for update item action
    :type on_update: rx.EventHandler | Callable
    :param on_relabel: Event handler for relabel item action
    :type on_relabel: rx.EventHandler | Callable
    :param on_delete: Event handler for delete item action
    :type on_delete: rx.EventHandler | Callable
    :param on_split: Event handler for split item action. The Split entry is
                     only shown when this handler is provided.
    :type on_split: rx.EventHandler | Callable | None
    :param on_combine: Event handler for combine item action. The Combine entry
                       is only shown when this handler is provided.
    :type on_combine: rx.EventHandler | Callable | None
    :param stop_propagation: Whether to stop event propagation (useful in table rows)
    :type stop_propagation: bool
    :return: The actions menu component
    :rtype: rx.Component
    """

    def _wrap_click(handler: rx.EventHandler | Callable) -> rx.EventHandler | Callable | list:
        """Wrap click handler with stop_propagation if needed."""
        return [rx.stop_propagation, handler] if stop_propagation else handler

    # Consume and Split reduce a quantity, so they are only meaningful for
    # consumable items. They are hidden for non-consumable items (instruments).
    is_consumable = item.item_sheet.is_consumable

    consume_menu_item = rx.cond(
        is_consumable,
        rx.menu.item(
            rx.icon("flame", size=16),
            "Consume Stock",
            on_click=_wrap_click(on_consume),
        ),
        rx.fragment(),
    )

    # The Split entry is only shown when an on_split handler is provided AND the
    # item is consumable.
    split_menu_item = rx.fragment()
    if on_split is not None:
        split_menu_item = rx.cond(
            is_consumable,
            rx.menu.item(
                rx.icon("split", size=16),
                "Split Item",
                on_click=_wrap_click(on_split),
            ),
            rx.fragment(),
        )

    # The Combine entry is only shown when an on_combine handler is provided AND
    # the item is consumable (combine draws from consumable ingredients).
    combine_menu_item = rx.fragment()
    if on_combine is not None:
        combine_menu_item = rx.cond(
            is_consumable,
            rx.menu.item(
                rx.icon("git-merge", size=16),
                "Combine Items",
                on_click=_wrap_click(on_combine),
            ),
            rx.fragment(),
        )

    return rx.menu.root(
        rx.menu.trigger(
            rx.button(
                rx.icon("ellipsis-vertical", size=18),
                size="2",
                variant="ghost",
            ),
        ),
        rx.menu.content(
            rx.menu.item(
                rx.icon("package-plus", size=16),
                "Receive Stock",
                on_click=_wrap_click(on_receive),
            ),
            consume_menu_item,
            rx.menu.separator(),
            rx.menu.item(
                rx.icon("arrow-right-from-line", size=16),
                "Move Item",
                on_click=_wrap_click(on_move),
            ),
            rx.menu.item(
                rx.icon("pencil", size=16),
                "Update Item",
                on_click=_wrap_click(on_update),
            ),
            rx.menu.item(
                rx.icon("tag", size=16),
                "Relabel Item",
                on_click=_wrap_click(on_relabel),
            ),
            split_menu_item,
            combine_menu_item,
            rx.menu.separator(),
            rx.menu.item(
                rx.icon("trash-2", size=16),
                "Delete Item",
                color="red",
                on_click=_wrap_click(on_delete),
            ),
        ),
    )
