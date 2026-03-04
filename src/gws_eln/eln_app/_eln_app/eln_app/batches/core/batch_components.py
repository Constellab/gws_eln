"""Batch-related badge components."""

from datetime import date, timedelta
from typing import cast

import reflex as rx
from gws_eln.materials.batch_status import BatchStatus
from gws_eln.materials.material_batch_dto import MaterialBatchSimpleDTO
from gws_reflex_main import ReflexTheme

from ...common.eln_app_router import ElnAppRouter


def expiry_date_badge(expiry_date: date | None, warning_days: int = 30) -> rx.Component:
    """Create a badge indicating the expiry status of a batch.

    - Green: expiry date is more than warning_days away
    - Orange/Warning: expiry date is within warning_days
    - Red/Error: expired (expiry date is in the past)
    - Gray dash: no expiry date set

    :param expiry_date: The expiry date of the batch
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
                content="This batch has expired",
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
                    content=f"This batch expires within {warning_days} days",
                ),
                # OK - not expiring soon
                rx.moment(expiry_date, format="MMM D, YYYY"),
            ),
        ),
    )


def consumable_badge(is_consumable: bool) -> rx.Component:
    """Create a badge indicating if a material is consumable.

    :param is_consumable: Whether the material is consumable
    :type is_consumable: bool
    :return: The badge component
    :rtype: rx.Component
    """
    return rx.cond(
        is_consumable,
        rx.badge("Consumable", color_scheme=ReflexTheme.SECONDARY, size="1"),
        rx.badge("Non-consumable", color_scheme=ReflexTheme.TERTIARY, size="1"),
    )


def status_badge(status: BatchStatus) -> rx.Component:
    """Create a badge indicating the batch status.

    :param status: The batch status
    :type status: BatchStatus
    :return: The badge component
    :rtype: rx.Component
    """
    return rx.cond(
        status == BatchStatus.ACTIVE.value,
        rx.badge("Active", color_scheme=ReflexTheme.SECONDARY, size="1"),
        rx.badge("Discarded", color_scheme=ReflexTheme.TERTIARY, size="1"),
    )


def batch_inline(batch: MaterialBatchSimpleDTO) -> rx.Component:
    """Create an inline component displaying batch number and label.

    :param batch: The batch DTO to display
    :type batch: MaterialBatchSimpleDTO
    :return: The inline batch component
    :rtype: rx.Component
    """
    return rx.vstack(
        rx.text(batch.batch_number, weight="medium"),
        rx.cond(batch.label, rx.text(f"{batch.label}", size="1", color="gray")),
        spacing="0",
    )


def batch_inline_link(batch: MaterialBatchSimpleDTO) -> rx.Component:
    """Create an inline component displaying batch number and label.

    :param batch: The batch DTO to display
    :type batch: MaterialBatchSimpleDTO
    :return: The inline batch component
    :rtype: rx.Component
    """
    return rx.link(batch_inline(batch), href=ElnAppRouter.get_batch_detail_url(batch.id))
