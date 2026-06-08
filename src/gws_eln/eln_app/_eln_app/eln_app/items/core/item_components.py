"""Item-related badge components."""

from datetime import date, timedelta
from typing import cast

import reflex as rx
from gws_eln.items.item_status import ItemStatus
from gws_eln.items.item_dto import ItemSimpleDTO
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
    return rx.cond(
        status == ItemStatus.ACTIVE.value,
        rx.badge("Active", color_scheme=ReflexTheme.SECONDARY, size="1"),
        rx.badge("Discarded", color_scheme=ReflexTheme.TERTIARY, size="1"),
    )


def item_inline(item: ItemSimpleDTO) -> rx.Component:
    """Create an inline component displaying item number and label.

    :param item: The item DTO to display
    :type item: ItemSimpleDTO
    :return: The inline item component
    :rtype: rx.Component
    """
    return rx.vstack(
        rx.text(item.item_number, weight="medium"),
        rx.cond(item.label, rx.text(f"{item.label}", size="1", color="gray")),
        spacing="0",
    )


def item_inline_link(item: ItemSimpleDTO) -> rx.Component:
    """Create an inline component displaying item number and label.

    :param item: The item DTO to display
    :type item: ItemSimpleDTO
    :return: The inline item component
    :rtype: rx.Component
    """
    return rx.link(item_inline(item), href=ElnAppRouter.get_item_detail_url(item.id))
