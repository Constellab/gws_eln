"""Locations page component."""

import reflex as rx

from .locations_list_component import locations_list_page


def locations_page() -> rx.Component:
    """Create the locations page component.

    :return: The locations page component
    :rtype: rx.Component
    """
    return locations_list_page()
