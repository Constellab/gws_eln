"""Item actions menu component."""

from collections.abc import Callable

import reflex as rx
from gws_eln.items.item_dto import ItemDTO
from gws_eln.items.item_status import ItemStatus

EventHandlerOrCallable = rx.EventHandler | Callable


def item_actions_menu(
    item: ItemDTO,
    on_receive: EventHandlerOrCallable,
    on_use: EventHandlerOrCallable,
    on_move: EventHandlerOrCallable,
    on_update: EventHandlerOrCallable,
    on_relabel: EventHandlerOrCallable,
    on_delete: EventHandlerOrCallable,
    on_transform: EventHandlerOrCallable | None = None,
    stop_propagation: bool = False,
) -> rx.Component:
    """Create the actions menu for a item.

    :param item: The item DTO to determine which actions to show
    :type item: ItemDTO
    :param on_receive: Event handler for receive stock action (consumable only)
    :param on_use: Event handler for use action (non-consumable only)
    :param on_move: Event handler for move item action
    :param on_update: Event handler for update item action
    :param on_relabel: Event handler for relabel item action
    :param on_delete: Event handler for delete item action
    :param on_transform: Event handler for the (unified) transform action
    :param stop_propagation: Whether to stop event propagation (useful in table rows)
    :type stop_propagation: bool
    :return: The actions menu component
    :rtype: rx.Component
    """

    def _wrap_click(handler: EventHandlerOrCallable) -> EventHandlerOrCallable | list:
        """Wrap click handler with stop_propagation if needed."""
        return [rx.stop_propagation, handler] if stop_propagation else handler

    # Receive and the transforms reduce or add a quantity,
    # so they are only meaningful for consumable items. They are hidden for
    # non-consumable items (instruments).
    is_consumable = item.item_sheet.is_consumable

    def _consumable_item(handler: EventHandlerOrCallable, icon: str, label: str) -> rx.Component:
        """A menu entry shown only when the item is consumable."""
        return rx.cond(
            is_consumable,
            rx.menu.item(rx.icon(icon, size=16), label, on_click=_wrap_click(handler)),
            rx.fragment(),
        )

    def _non_consumable_item(handler: EventHandlerOrCallable, icon: str, label: str) -> rx.Component:
        """A menu entry shown only when the item is non-consumable (instrument)."""
        return rx.cond(
            is_consumable,
            rx.fragment(),
            rx.menu.item(rx.icon(icon, size=16), label, on_click=_wrap_click(handler)),
        )

    menu = rx.menu.root(
        rx.menu.trigger(
            rx.button(
                rx.icon("ellipsis-vertical", size=18),
                size="2",
                variant="ghost",
            ),
        ),
        rx.menu.content(
            _consumable_item(on_receive, "package-plus", "Receive Stock"),
            _non_consumable_item(on_use, "microscope", "Use Item"),
            # The group above always has one entry (consumable -> receive,
            # non-consumable -> use), so the separator is always shown.
            rx.menu.separator(),
            rx.menu.item(
                rx.icon("arrow-right-from-line", size=16),
                "Move Item",
                on_click=_wrap_click(on_move),
            ),
            rx.menu.item(
                rx.icon("tag", size=16),
                "Relabel Item",
                on_click=_wrap_click(on_relabel),
            ),
            rx.menu.item(
                rx.icon("pencil", size=16),
                "Update Item",
                on_click=_wrap_click(on_update),
            ),
            *(
                [
                    rx.menu.separator(),
                    rx.menu.item(
                        rx.icon("flask-conical", size=16),
                        "Transform",
                        on_click=_wrap_click(on_transform),
                    ),
                ]
                if on_transform is not None
                else []
            ),
            rx.menu.separator(),
            rx.menu.item(
                rx.icon("trash-2", size=16),
                "Delete Item",
                color="red",
                on_click=_wrap_click(on_delete),
            ),
        ),
    )

    # no activity can be recorded on a discarded item - hide the menu entirely.
    return rx.cond(
        item.status == ItemStatus.DISCARDED.value,
        rx.fragment(),
        menu,
    )
