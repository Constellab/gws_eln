"""Activities list component."""

from typing import cast

import reflex as rx
from gws_eln.activities.activity_dto import ActivityDTO
from gws_eln.activities.activity_type import ActivityType
from gws_reflex_main import user_with_date_component

from ..common.batch.batch_components import batch_inline_link
from ..common.location.inline_location_component import inline_location_component
from .activities_list_state import ALL_FILTER_VALUE, ALLIQUOT_FILTER_VALUE, ActivitiesListState
from .activity_type_component import activity_type_badge


def _type_specific_description(activity: ActivityDTO) -> rx.Component:
    """Create a type-specific description component.

    :param activity: The activity DTO
    :type activity: ActivityDTO
    :return: The type-specific description component
    :rtype: rx.Component
    """
    return cast(
        rx.Component,
        rx.match(
            activity.activity_type,
            (
                ActivityType.MOVE.value,
                rx.hstack(
                    rx.icon("map-pin", size=18),
                    rx.cond(
                        activity.from_location,
                        inline_location_component(activity.from_location),
                    ),
                    rx.icon("arrow-right", size=14),
                    rx.cond(
                        activity.to_location,
                        inline_location_component(activity.to_location),
                    ),
                    spacing="1",
                    align="center",
                    align_items="center",
                ),
            ),
            (ActivityType.ALIQUOT.value, batch_inline_link(activity.related_batch)),
            (ActivityType.ALIQUOT_CREATED.value, batch_inline_link(activity.related_batch)),
            rx.fragment(),
        ),
    )


def _activity_description(activity: ActivityDTO) -> rx.Component:
    """Create a description component based on activity type.

    Shows type-specific description (for RECEIVE, MOVE, ALIQUOT, ALIQUOT_CREATED)
    and always shows notes if present.

    :param activity: The activity DTO
    :type activity: ActivityDTO
    :return: The description component
    :rtype: rx.Component
    """
    return rx.vstack(
        _type_specific_description(activity),
        rx.cond(
            activity.notes,
            rx.text(activity.notes, size="2", color="gray"),
            rx.fragment(),
        ),
        spacing="1",
        align="start",
    )


def _filter_bar() -> rx.Component:
    """Create the filter bar with activity type dropdown.

    :return: The filter bar component
    :rtype: rx.Component
    """
    return rx.hstack(
        rx.select.root(
            rx.select.trigger(placeholder="Activity type", width="180px"),
            rx.select.content(
                rx.select.item("All types", value=ALL_FILTER_VALUE),
                rx.select.item("Received", value=ActivityType.RECEIVE.value),
                rx.select.item("Moved", value=ActivityType.MOVE.value),
                rx.select.item("Consumed", value=ActivityType.CONSUME.value),
                rx.select.item("Used", value=ActivityType.USE.value),
                rx.select.item("Discarded", value=ActivityType.DISCARD.value),
                rx.select.item("Aliquot", value=ALLIQUOT_FILTER_VALUE),
                rx.select.item("Relabeled", value=ActivityType.RELABEL.value),
            ),
            value=ActivitiesListState.filter_activity_type,
            on_change=ActivitiesListState.handle_activity_type_filter_change,
        ),
        rx.button(
            "Clear",
            on_click=ActivitiesListState.clear_filters,
            variant="outline",
            size="2",
        ),
        width="100%",
        spacing="3",
        wrap="wrap",
        align="center",
    )


def _row(activity: ActivityDTO) -> rx.Component:
    """Create a table row for an activity.

    :param activity: The activity DTO to display
    :type activity: ActivityDTO
    :return: The table row component
    :rtype: rx.Component
    """
    return rx.table.row(
        rx.table.cell(
            rx.box(activity_type_badge(activity.activity_type), width="fit-content"),
        ),
        rx.table.cell(_activity_description(activity)),
        rx.table.cell(activity.pretty_quantity),
        rx.table.cell(
            user_with_date_component(
                activity.created_by,
                activity.created_at,
                size="small",
            )
        ),
        style={":hover": {"background_color": "var(--gray-3)"}},
    )


def _activities_header() -> rx.Component:
    """Create the header section with title and filter bar.

    :return: The header component
    :rtype: rx.Component
    """
    return rx.vstack(
        rx.hstack(
            rx.heading("Activity History", size="5"),
            rx.spacer(),
            width="100%",
            align="center",
        ),
        _filter_bar(),
        rx.cond(
            ActivitiesListState.error_message != "",
            rx.callout(
                ActivitiesListState.error_message,
                icon="triangle_alert",
                color_scheme="red",
                role="alert",
                margin_bottom="1rem",
            ),
        ),
        width="100%",
        spacing="4",
    )


def _activities_table() -> rx.Component:
    """Create the activities table with loading, empty, and data states.

    :return: The table component
    :rtype: rx.Component
    """
    return rx.cond(
        ActivitiesListState.is_loading & (ActivitiesListState.activities.length() == 0),
        rx.center(
            rx.vstack(
                rx.spinner(size="3"),
                rx.text("Loading activities...", size="3", color="gray", margin_top="1rem"),
                spacing="2",
                align="center",
            ),
            padding="3rem",
            width="100%",
        ),
        rx.cond(
            ActivitiesListState.activities.length() > 0,
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("Type"),
                        rx.table.column_header_cell("Description"),
                        rx.table.column_header_cell("Quantity"),
                        rx.table.column_header_cell("By"),
                    ),
                ),
                rx.table.body(rx.foreach(ActivitiesListState.activities, _row)),
                width="100%",
                variant="surface",
            ),
            rx.center(
                rx.vstack(
                    rx.icon("activity", size=48, color="gray"),
                    rx.text("No activities found", size="4", color="gray", margin_top="1rem"),
                    spacing="2",
                    align="center",
                ),
                padding="3rem",
                width="100%",
            ),
        ),
    )


def activities_list_component(batch_id: rx.Var[str]) -> rx.Component:
    """Create the activities list component for a specific batch.

    This component displays a table of activities with columns for
    type, description, quantity, and user/date.
    Includes a filter for activity type.

    The component uses on_mount to trigger activity loading when mounted,
    and a key based on batch_id to force remount when batch changes.

    :param batch_id: The ID of the batch to display activities for
    :type batch_id: rx.Var[str]
    :return: The activities list component
    :rtype: rx.Component
    """
    return rx.box(
        rx.vstack(
            _activities_header(),
            _activities_table(),
            width="100%",
            spacing="4",
            on_mount=ActivitiesListState.fetch_activities_on_mount(batch_id),
        ),
        key=batch_id,
        width="100%",
    )
