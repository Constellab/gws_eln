"""Reusable multi-instrument picker component.

Renders a search input (active non-consumable items only) plus the list of
already-selected instruments as removable chips. The selection lives in the
host dialog state via :class:`InstrumentPickerMixin`; pass that state class in.
"""

import reflex as rx

from .instrument_picker_mixin import InstrumentRow
from .instrument_select_component import instrument_select_component


def _instrument_chip(state, row: InstrumentRow, index: int) -> rx.Component:
    """Render one selected instrument as a removable chip."""
    return rx.badge(
        rx.text(row.display, size="1"),
        rx.icon_button(
            rx.icon("x", size=12),
            type="button",
            variant="ghost",
            color_scheme="gray",
            size="1",
            on_click=lambda: state.remove_instrument(index),
        ),
        variant="soft",
        color_scheme="gray",
        size="2",
    )


def instrument_picker_component(
    state,
    label: str = "Instruments (optional)",
    placeholder: str = "Search an instrument...",
    hint: str | None = None,
) -> rx.Component:
    """Render the optional multi-instrument picker for a transform dialog.

    Args:
        state: The host dialog state class (must mix in InstrumentPickerMixin)
        label: Section label shown above the picker
        placeholder: Placeholder for the search input
        hint: Optional help text shown as an info tooltip next to the label
    """
    label_component = rx.text(label, size="2", weight="bold")
    if hint:
        label_component = rx.hstack(
            label_component,
            rx.tooltip(rx.icon("info", size=14, color="gray"), content=hint),
            align="center",
            spacing="1",
        )

    return rx.vstack(
        label_component,
        instrument_select_component(
            placeholder=placeholder,
            item_selected=state.add_instrument,
        ),
        rx.cond(
            state.instruments.length() > 0,
            rx.hstack(
                rx.foreach(
                    state.instruments,
                    lambda row, index: _instrument_chip(state, row, index),
                ),
                wrap="wrap",
                spacing="2",
                width="100%",
            ),
        ),
        width="100%",
        spacing="2",
    )
