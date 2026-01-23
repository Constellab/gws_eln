"""Consumable badge component."""

import reflex as rx


def consumable_badge(is_consumable: bool) -> rx.Component:
    """Create a badge indicating if a material is consumable.

    :param is_consumable: Whether the material is consumable
    :type is_consumable: bool
    :return: The badge component
    :rtype: rx.Component
    """
    return rx.cond(
        is_consumable,
        rx.badge("Consumable", color_scheme="blue", size="1"),
        rx.badge("Non-consumable", color_scheme="gray", size="1"),
    )
