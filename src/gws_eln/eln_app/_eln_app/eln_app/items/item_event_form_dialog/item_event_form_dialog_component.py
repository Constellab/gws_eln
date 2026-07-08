"""Item event form dialog component for Receive, Increment, Decrement operations."""

import reflex as rx
from gws_reflex_main import form_dialog_component

from ...activities.activity_form_sections import receive_consume_form_section
from ..core.instrument_picker_component import instrument_picker_component
from .item_event_form_dialog_state import ItemEventFormDialogState


def _form_content() -> rx.Component:
    """Form content for entering item event details."""
    return rx.vstack(
        # Item info (read-only display): name and code side by side
        # Receive only: clarify the added stock inherits the item's characteristics.
        rx.cond(
            ~ItemEventFormDialogState.is_consume,
            rx.callout(
                "The received stock is added to this same item and keeps all its "
                "characteristics (expiry date, storage conditions, supplier, "
                "concentration…). To record stock with different characteristics, "
                "create a new item instead.",
                icon="info",
                size="1",
                color_scheme="blue",
            ),
        ),
        rx.hstack(
            rx.vstack(
                rx.text("Item name", size="2", weight="bold"),
                rx.text(
                    ItemEventFormDialogState.label,
                    size="2",
                    color="gray",
                ),
                width="50%",
                spacing="1",
            ),
            rx.vstack(
                rx.hstack(
                    rx.text("Item code", size="2", weight="bold"),
                    rx.tooltip(
                        rx.icon("info", size=14, color="gray"),
                        content=(
                            "Auto-generated identifier: the sheet's code followed by an "
                            "incrementing number."
                        ),
                    ),
                    align="center",
                    spacing="1",
                ),
                rx.text(
                    ItemEventFormDialogState.code,
                    size="2",
                    color="gray",
                ),
                width="50%",
                spacing="1",
            ),
            width="100%",
            spacing="3",
            align="start",
        ),
        # Current quantity display
        rx.vstack(
            rx.text("Current Quantity", size="2", weight="bold"),
            rx.badge(
                ItemEventFormDialogState.current_quantity,
                color_scheme="green",
                size="2",
            ),
            width="100%",
            spacing="1",
            align="start",
        ),
        # Reusable receive/consume form section
        receive_consume_form_section(
            unit_type=ItemEventFormDialogState.form_unit_type,
            unit_value=ItemEventFormDialogState.form_unit,
            on_unit_change=ItemEventFormDialogState.set_unit,
            quantity_label=ItemEventFormDialogState.quantity_label,
            form_notes=ItemEventFormDialogState.form_notes,
        ),
        # Optional instruments used (consume only - receive is a 0-input activity)
        rx.cond(
            ItemEventFormDialogState.is_consume,
            instrument_picker_component(
                ItemEventFormDialogState,
                label="Instruments",
                hint=(
                    "Instruments used during this consumption (optional); "
                    "recorded to trace which equipment was involved."
                ),
            ),
        ),
        width="100%",
        spacing="3",
    )


def _dialog() -> rx.Component:
    """The base dialog component without a trigger.

    This can be reused in different contexts with different triggers.

    :return: The dialog component
    :rtype: rx.Component
    """
    return form_dialog_component(
        state=ItemEventFormDialogState,
        title=ItemEventFormDialogState.dialog_title,
        subtitle=ItemEventFormDialogState.dialog_description,
        form_content=_form_content(),
        max_width="450px",
    )


def item_event_form_dialog() -> rx.Component:
    """Dialog component for item events (Receive, Increment, Decrement).

    This component provides just the dialog (without a trigger button).
    The dialog is controlled by the ItemEventFormDialogState.dialog_opened state.

    To open the dialog, call ItemEventFormDialogState.open_dialog_for_event(item_id, event_type)
    with the item ID and event type ('receive', 'increment', 'decrement').

    :return: The item event form dialog component
    :rtype: rx.Component
    """
    return _dialog()
