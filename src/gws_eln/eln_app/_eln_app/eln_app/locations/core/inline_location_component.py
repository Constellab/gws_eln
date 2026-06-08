"""Inline location component for displaying location info on a single line."""

import reflex as rx
from gws_eln.locations.location_dto import LocationDTO


def inline_location_component(location: LocationDTO) -> rx.Component:
    """Create an inline component to display location information.

    Displays the location name on a single line.

    :param location: The location DTO to display
    :type location: LocationDTO
    :return: The inline location component
    :rtype: rx.Component
    """
    return rx.text(location.name, size="2")
