"""Split item form dialog component."""

import reflex as rx
from gws_reflex_main import form_dialog_component

from ...common.unit.unit_components import quantity_unit_input
from .split_item_form_dialog_state import SplitItemFormDialogState, SplitOutputRow


def _output_row(row: SplitOutputRow, index: int) -> rx.Component:
    """Render one editable output row.

    :param row: The output row data (from the state's outputs list)
    :param index: The row index within the outputs list
    :return: The output row component
    """
    return rx.vstack(
        # Header: output number + remove button
        rx.hstack(
            rx.text(f"Output #{index + 1}", size="2", weight="bold"),
            rx.spacer(),
            rx.icon_button(
                rx.icon("trash-2", size=14),
                type="button",
                variant="soft",
                color_scheme="gray",
                size="1",
                disabled=~SplitItemFormDialogState.can_remove_row,
                on_click=lambda: SplitItemFormDialogState.remove_row(index),
            ),
            width="100%",
            align="center",
        ),
        # Quantity + unit (unit type shared from the source item)
        quantity_unit_input(
            unit_type=SplitItemFormDialogState.form_unit_type,
            quantity_value=row.quantity,
            unit_value=row.unit,
            on_quantity_change=lambda v: SplitItemFormDialogState.set_row_quantity(index, v),
            on_unit_change=lambda v: SplitItemFormDialogState.set_row_unit(index, v),
            quantity_required=False,
        ),
        # Label (optional)
        rx.vstack(
            rx.text("Label", size="1", weight="medium", color="gray"),
            rx.input(
                placeholder="Enter label (optional)",
                value=row.label,
                on_change=lambda v: SplitItemFormDialogState.set_row_label(index, v),
                width="100%",
            ),
            width="100%",
            spacing="1",
        ),
        width="100%",
        spacing="2",
        padding="0.75rem",
        border="1px solid var(--gray-5)",
        border_radius="0.5rem",
    )


def _form_content() -> rx.Component:
    """Form content for splitting an item."""
    return rx.vstack(
        # Source item (read-only display)
        rx.vstack(
            rx.text("Source Item", size="2", weight="bold"),
            rx.code(SplitItemFormDialogState.code, size="2"),
            width="100%",
            spacing="1",
            align="start",
        ),
        # Current quantity (read-only display)
        rx.vstack(
            rx.text("Available Quantity", size="2", weight="bold"),
            rx.text(SplitItemFormDialogState.current_quantity, size="2", color="gray"),
            width="100%",
            spacing="1",
        ),
        rx.divider(margin_y="0.25rem"),
        # Dynamic list of output rows
        rx.foreach(SplitItemFormDialogState.outputs, _output_row),
        # Add output button
        rx.button(
            rx.icon("plus", size=16),
            "Add output",
            type="button",
            variant="soft",
            color_scheme="gray",
            on_click=SplitItemFormDialogState.add_row,
            width="100%",
        ),
        # Notes (optional) - read from the HTML form on submit
        rx.vstack(
            rx.text("Notes", size="2", weight="bold"),
            rx.text_area(
                placeholder="Enter notes (optional)",
                name="notes",
                width="100%",
                rows="2",
            ),
            width="100%",
            spacing="1",
        ),
        width="100%",
        spacing="3",
    )


def _dialog() -> rx.Component:
    """The base split dialog component without a trigger.

    :return: The dialog component
    :rtype: rx.Component
    """
    return form_dialog_component(
        state=SplitItemFormDialogState,
        title="Split Item",
        description=(
            "Split this item into one or more new items. The source quantity is "
            "reduced by the total of the outputs; the leftover stays in the source."
        ),
        form_content=_form_content(),
        max_width="520px",
    )


def split_item_dialog() -> rx.Component:
    """Dialog component for splitting an item.

    This component provides just the dialog (without a trigger button).
    The dialog is controlled by SplitItemFormDialogState.dialog_opened.

    To open the dialog, call SplitItemFormDialogState.open_split_dialog(item)
    with the source item to split.

    :return: The split item dialog component
    :rtype: rx.Component
    """
    return _dialog()
