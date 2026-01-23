"""Activity type badge component."""

from typing import cast

import reflex as rx
from gws_eln.activities.activity_type import ActivityType


def activity_type_badge(activity_type: ActivityType) -> rx.Component:
    """Create a badge indicating the activity type with an icon.

    :param activity_type: The activity type
    :type activity_type: ActivityType
    :return: The badge component
    :rtype: rx.Component
    """
    return cast(
        rx.Component,
        rx.match(
            activity_type,
            (
                ActivityType.RECEIVE.value,
                rx.badge(
                    rx.icon("package-plus", size=12), "Received", color_scheme="green", size="1"
                ),
            ),
            (
                ActivityType.MOVE.value,
                rx.badge(
                    rx.icon("arrow-right-from-line", size=12),
                    "Moved",
                    color_scheme="blue",
                    size="1",
                ),
            ),
            (
                ActivityType.CONSUME.value,
                rx.badge(rx.icon("flame", size=12), "Consumed", color_scheme="orange", size="1"),
            ),
            (
                ActivityType.USE.value,
                rx.badge(rx.icon("hand", size=12), "Used", color_scheme="purple", size="1"),
            ),
            (
                ActivityType.DISCARD.value,
                rx.badge(rx.icon("trash-2", size=12), "Discarded", color_scheme="red", size="1"),
            ),
            (
                ActivityType.ALIQUOT.value,
                rx.badge(rx.icon("split", size=12), "Aliquot", color_scheme="cyan", size="1"),
            ),
            (
                ActivityType.ALIQUOT_CREATED.value,
                rx.badge(
                    rx.icon("arrow-down-to-dot", size=12),
                    "Aliquot creation",
                    color_scheme="teal",
                    size="1",
                ),
            ),
            (
                ActivityType.RELABEL.value,
                rx.badge(rx.icon("tag", size=12), "Relabeled", color_scheme="gray", size="1"),
            ),
            rx.badge(activity_type, color_scheme="gray", size="1"),
        ),
    )
