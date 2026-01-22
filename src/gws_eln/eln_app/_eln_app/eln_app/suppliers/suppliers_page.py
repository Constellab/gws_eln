"""Suppliers page component."""

import reflex as rx

from .suppliers_list_component import suppliers_list_page


def suppliers_page() -> rx.Component:
    """Create the suppliers page component.

    :return: The suppliers page component
    :rtype: rx.Component
    """
    return suppliers_list_page()
