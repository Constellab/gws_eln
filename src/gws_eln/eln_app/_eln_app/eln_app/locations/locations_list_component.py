"""Locations list page component."""

import reflex as rx
from gws_eln.locations.location_dto import LocationDTO
from gws_reflex_main import main_component, user_inline_component

from ..common.page_layout import page_layout
from .location_form_dialog.location_form_dialog_component import location_update_dialog
from .locations_list_state import LocationsListState


def _filter_bar() -> rx.Component:
    """Create the filter bar with search filter.

    :return: The filter bar component
    :rtype: rx.Component
    """
    return rx.hstack(
        rx.input(
            placeholder="Search locations...",
            value=LocationsListState.search_text,
            on_change=LocationsListState.handle_search_change,
            min_width="300px",
        ),
        rx.button(
            "Clear",
            on_click=LocationsListState.clear_filters,
            variant="surface",
            size="2",
        ),
        width="100%",
        spacing="3",
        wrap="wrap",
    )


def _create_location_button() -> rx.Component:
    """Create the button to open the create location dialog.

    :return: The create location button component
    :rtype: rx.Component
    """
    return rx.fragment(
        rx.button(
            rx.icon("plus", size=18),
            "Create New Location",
            size="3",
            on_click=LocationsListState.open_create_dialog,
        ),
        location_update_dialog(),
    )


def _actions_menu(location: LocationDTO) -> rx.Component:
    """Create the actions menu for a location.

    :param location: The location DTO
    :type location: LocationDTO
    :return: The actions menu component
    :rtype: rx.Component
    """
    return rx.menu.root(
        rx.menu.trigger(rx.button(rx.icon("ellipsis-vertical", size=18), variant="soft", size="2")),
        rx.menu.content(
            rx.menu.item(
                rx.icon("pencil", size=16),
                "Update",
                on_click=lambda: LocationsListState.open_update_dialog(location),
            ),
            rx.menu.separator(),
            rx.menu.item(
                rx.icon("trash-2", size=16),
                "Delete",
                color="red",
                on_click=lambda: LocationsListState.open_delete_dialog(location),
            ),
        ),
    )


def _row(location: LocationDTO) -> rx.Component:
    """Create a table row for a location.

    :param location: The location DTO to display
    :type location: LocationDTO
    :return: The table row component
    :rtype: rx.Component
    """
    return rx.table.row(
        rx.table.cell(rx.text(location.name)),
        rx.table.cell(
            rx.cond(
                location.description,
                rx.text(location.description, size="2", color="gray"),
            )
        ),
        rx.table.cell(user_inline_component(location.created_by, size="small")),
        rx.table.cell(rx.moment(location.created_at, format="MMM D, YYYY")),
        rx.table.cell(
            rx.box(
                _actions_menu(location),
                display="flex",
                justify_content="flex-end",
                align_items="center",
            )
        ),
        style={":hover": {"background_color": "var(--gray-3)"}},
    )


def locations_list_page() -> rx.Component:
    """Create the locations list page component.

    This component displays a table of locations with columns for
    name, description, created by, and created at.
    Includes a search filter for filtering by location name.

    :return: The locations list page component
    :rtype: rx.Component
    """
    return main_component(
        page_layout(
            rx.vstack(
                _filter_bar(),
                rx.cond(
                    LocationsListState.error_message != "",
                    rx.callout(
                        LocationsListState.error_message,
                        icon="triangle_alert",
                        color_scheme="red",
                        role="alert",
                        margin_bottom="1rem",
                    ),
                ),
                rx.cond(
                    LocationsListState.is_loading,
                    rx.center(rx.spinner(size="3"), padding="2rem"),
                    rx.cond(
                        LocationsListState.locations.length() > 0,
                        rx.table.root(
                            rx.table.header(
                                rx.table.row(
                                    rx.table.column_header_cell("Name"),
                                    rx.table.column_header_cell("Description"),
                                    rx.table.column_header_cell("Created By"),
                                    rx.table.column_header_cell("Created At"),
                                    rx.table.column_header_cell(
                                        "Actions", width="100px", justify="end"
                                    ),
                                ),
                            ),
                            rx.table.body(rx.foreach(LocationsListState.locations, _row)),
                            width="100%",
                            variant="surface",
                        ),
                        rx.center(
                            rx.vstack(
                                rx.icon("map-pin", size=48, color="gray"),
                                rx.text(
                                    "No locations found", size="4", color="gray", margin_top="1rem"
                                ),
                                spacing="2",
                                align="center",
                            ),
                            padding="3rem",
                            width="100%",
                        ),
                    ),
                ),
                width="100%",
                spacing="4",
            ),
            header_content=rx.hstack(
                rx.heading("Locations", size="6"),
                _create_location_button(),
                justify="between",
                align="center",
                width="100%",
                margin_bottom="1rem",
            ),
        )
    )
