"""Materials page component."""

import reflex as rx

from .materials_list_component import materials_list_page


def materials_page() -> rx.Component:
    """Create the materials page component.

    :return: The materials page component
    :rtype: rx.Component
    """
    return materials_list_page()
