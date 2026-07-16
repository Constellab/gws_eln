"""Item-related badge components."""

from datetime import date, timedelta
from typing import cast

import reflex as rx
from gws_eln.items.item_dto import ItemDTO, ItemSimpleDTO
from gws_eln.items.item_status import ItemStatus
from gws_reflex_main import ReflexTheme

from ...common.eln_app_router import ElnAppRouter


def expiry_date_badge(expiry_date: date | None, warning_days: int = 30) -> rx.Component:
    """Create a badge indicating the expiry status of a item.

    - Green: expiry date is more than warning_days away
    - Orange/Warning: expiry date is within warning_days
    - Red/Error: expired (expiry date is in the past)
    - Gray dash: no expiry date set

    :param expiry_date: The expiry date of the item
    :type expiry_date: date | None
    :param warning_days: Number of days before expiry to show warning (default 30)
    :type warning_days: int
    :return: The badge component
    :rtype: rx.Component
    """
    today = date.today()
    warning_threshold = today + timedelta(days=warning_days)

    # Cast to date for type checker - rx.cond handles None at runtime
    expiry = cast(date, expiry_date)

    return rx.cond(
        expiry_date,
        rx.cond(
            expiry < today,
            # Expired
            rx.tooltip(
                rx.badge(
                    rx.hstack(
                        rx.icon("circle-alert", size=12),
                        rx.moment(expiry_date, format="MMM D, YYYY"),
                        spacing="1",
                        align="center",
                    ),
                    color_scheme=ReflexTheme.TERTIARY,
                    size="1",
                ),
                content="This item has expired",
            ),
            rx.cond(
                expiry <= warning_threshold,
                # Warning - expiring soon
                rx.tooltip(
                    rx.badge(
                        rx.hstack(
                            rx.icon("triangle-alert", size=12),
                            rx.moment(expiry_date, format="MMM D, YYYY"),
                            spacing="1",
                            align="center",
                        ),
                        color_scheme=ReflexTheme.SECONDARY,
                        size="1",
                    ),
                    content=f"This item expires within {warning_days} days",
                ),
                # OK - not expiring soon
                rx.moment(expiry_date, format="MMM D, YYYY"),
            ),
        ),
    )


def consumable_badge(is_consumable: bool) -> rx.Component:
    """Create a badge indicating if a item_sheet is consumable.

    :param is_consumable: Whether the item_sheet is consumable
    :type is_consumable: bool
    :return: The badge component
    :rtype: rx.Component
    """
    return rx.cond(
        is_consumable,
        rx.badge("Consumable", color_scheme=ReflexTheme.SECONDARY, size="1"),
        rx.badge("Non-consumable", color_scheme=ReflexTheme.TERTIARY, size="1"),
    )


def status_badge(status: ItemStatus) -> rx.Component:
    """Create a badge indicating the item status.

    :param status: The item status
    :type status: ItemStatus
    :return: The badge component
    :rtype: rx.Component
    """
    return rx.match(
        status,
        (
            ItemStatus.ACTIVE.value,
            rx.badge("Active", color_scheme=ReflexTheme.SECONDARY, size="1"),
        ),
        (
            ItemStatus.EXHAUSTED.value,
            rx.badge("Exhausted", color_scheme="amber", size="1"),
        ),
        rx.badge("Discarded", color_scheme="ruby", size="1"),
    )


def quantity_badge(item: ItemDTO) -> rx.Component:
    """Badge visualising an item's remaining quantity.

    - Discarded item: red, like a removed item in the Transform dialog.
    - Exhausted (quantity 0): amber, like the Exhausted status.
    - Positive quantity: green.

    :param item: The item DTO to display
    :type item: ItemDTO
    :return: The quantity badge component
    :rtype: rx.Component
    """
    return rx.cond(
        item.status == ItemStatus.DISCARDED.value,
        rx.badge(item.pretty_quantity, color_scheme="ruby", size="1"),
        rx.cond(
            item.quantity == 0,
            rx.badge(item.pretty_quantity, color_scheme="amber", size="1"),
            rx.badge(item.pretty_quantity, color_scheme="grass", size="1"),
        ),
    )


def item_inline(item: ItemSimpleDTO) -> rx.Component:
    """Create an inline component displaying the item label and code.

    The label (the human-readable name) is the primary line and the
    auto-generated code is shown as a monospace badge below it.

    :param item: The item DTO to display
    :type item: ItemSimpleDTO
    :return: The inline item component
    :rtype: rx.Component
    """
    return rx.vstack(
        rx.text(item.label, weight="medium"),
        rx.code(item.code, size="1"),
        spacing="1",
        align="start",
    )


def item_inline_link(item: ItemSimpleDTO) -> rx.Component:
    """Create an inline component displaying the item label and code.

    :param item: The item DTO to display
    :type item: ItemSimpleDTO
    :return: The inline item component
    :rtype: rx.Component
    """
    return rx.link(item_inline(item), href=ElnAppRouter.get_item_detail_url(item.id))
