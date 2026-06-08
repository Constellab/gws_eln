"""ItemSheets page component."""

import reflex as rx

from .item_sheets_list_component import item_sheets_list_page


def item_sheets_page() -> rx.Component:
    """Create the item_sheets page component.

    :return: The item_sheets page component
    :rtype: rx.Component
    """
    return item_sheets_list_page()
