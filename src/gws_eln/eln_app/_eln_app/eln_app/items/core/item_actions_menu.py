"""Item actions menu component."""

from collections.abc import Callable
from dataclasses import dataclass

import reflex as rx
from gws_eln.items.item_dto import ItemDTO
from gws_eln.items.item_status import ItemStatus

EventHandlerOrCallable = rx.EventHandler | Callable


@dataclass
class ItemTransformActions:
    """Optional consumable-only transform handlers for the item actions menu.

    Each entry is only shown when its handler is provided AND the item is
    consumable (these transforms all reduce a quantity, so they make no sense
    for non-consumable items / instruments).
    """

    on_split: EventHandlerOrCallable | None = None
    on_combine: EventHandlerOrCallable | None = None
    on_concentrate: EventHandlerOrCallable | None = None
    on_dilute: EventHandlerOrCallable | None = None


def item_actions_menu(
    item: ItemDTO,
    on_receive: EventHandlerOrCallable,
    on_consume: EventHandlerOrCallable,
    on_move: EventHandlerOrCallable,
    on_update: EventHandlerOrCallable,
    on_relabel: EventHandlerOrCallable,
    on_delete: EventHandlerOrCallable,
    transforms: ItemTransformActions | None = None,
    stop_propagation: bool = False,
) -> rx.Component:
    """Create the actions menu for a item.

    :param item: The item DTO to determine which actions to show
    :type item: ItemDTO
    :param on_receive: Event handler for receive stock action
    :param on_consume: Event handler for consume stock action (consumable only)
    :param on_move: Event handler for move item action
    :param on_update: Event handler for update item action
    :param on_relabel: Event handler for relabel item action
    :param on_delete: Event handler for delete item action
    :param transforms: Optional consumable-only transform handlers (split,
                       combine, concentrate, dilute). Each entry is shown only
                       when its handler is provided and the item is consumable.
    :type transforms: ItemTransformActions | None
    :param stop_propagation: Whether to stop event propagation (useful in table rows)
    :type stop_propagation: bool
    :return: The actions menu component
    :rtype: rx.Component
    """
    transforms = transforms or ItemTransformActions()

    def _wrap_click(handler: EventHandlerOrCallable) -> EventHandlerOrCallable | list:
        """Wrap click handler with stop_propagation if needed."""
        return [rx.stop_propagation, handler] if stop_propagation else handler

    # Consume and the transforms reduce a quantity, so they are only meaningful
    # for consumable items. They are hidden for non-consumable items (instruments).
    is_consumable = item.item_sheet.is_consumable

    def _consumable_item(handler: EventHandlerOrCallable, icon: str, label: str) -> rx.Component:
        """A menu entry shown only when the item is consumable."""
        return rx.cond(
            is_consumable,
            rx.menu.item(rx.icon(icon, size=16), label, on_click=_wrap_click(handler)),
            rx.fragment(),
        )

    # Optional transform entries (shown only when their handler is provided)
    transform_specs = [
        (transforms.on_split, "split", "Split Item"),
        (transforms.on_combine, "git-merge", "Combine Items"),
        (transforms.on_concentrate, "shrink", "Concentrate Item"),
        (transforms.on_dilute, "droplets", "Dilute Item"),
    ]
    transform_items = [
        _consumable_item(handler, icon, label)
        for handler, icon, label in transform_specs
        if handler is not None
    ]

    menu = rx.menu.root(
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
            _consumable_item(on_consume, "flame", "Consume Stock"),
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
            *transform_items,
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
