"""Batch detail page component."""

import reflex as rx
from gws_reflex_main import main_component, user_inline_component

from ..activities.activities_list_component import activities_list_component
from ..common.detail_page_layout import detail_page_layout
from ..common.page_layout import page_layout
from ..locations.core.inline_location_component import inline_location_component
from ..materials.core.material_components import (
    inline_material_link,
)
from ..suppliers.core.inline_supplier_component import inline_supplier_component
from .aliquot_form_dialog.aliquot_form_dialog_component import (
    aliquot_form_dialog,
)
from .batch_event_form_dialog.batch_event_form_dialog_component import (
    batch_event_form_dialog,
)
from .core.batch_actions_menu import batch_actions_menu
from .core.batch_components import batch_inline_link, expiry_date_badge
from .delete_batch_form_dialog.delete_batch_form_dialog_component import (
    delete_batch_dialog,
)
from .move_batch_form_dialog.move_batch_form_dialog_component import (
    move_batch_dialog,
)
from .relabel_batch_form_dialog.relabel_batch_form_dialog_component import (
    relabel_batch_dialog,
)
from .update_batch_form_dialog.update_batch_form_dialog_component import (
    update_batch_dialog,
)
from .batch_detail_state import BatchDetailState


def _status_badge(status: str) -> rx.Component:
    """Create a badge indicating the batch status.

    :param status: The batch status
    :type status: str
    :return: The badge component
    :rtype: rx.Component
    """
    return rx.cond(
        status == "active",
        rx.badge("Active", color_scheme="green", size="1"),
        rx.badge("Discarded", color_scheme="red", size="1"),
    )


def _details_sidebar() -> rx.Component:
    """Create the details sidebar with batch information.

    :return: The details sidebar component
    :rtype: rx.Component
    """
    return rx.vstack(
        rx.heading("Details", size="5", margin_bottom="1rem"),
        rx.grid(
            # Batch Number
            rx.text("Batch Number", size="2", color="gray", weight="medium"),
            rx.text(BatchDetailState.batch.batch_number, size="2", weight="medium"),
            # Label
            rx.cond(
                BatchDetailState.batch.label,
                rx.fragment(
                    rx.text("Label", size="2", color="gray", weight="medium"),
                    rx.text(BatchDetailState.batch.label, size="2"),
                ),
            ),
            # Material Name
            rx.text("Material", size="2", color="gray", weight="medium"),
            inline_material_link(BatchDetailState.batch.material),
            # Location
            rx.text("Location", size="2", color="gray", weight="medium"),
            inline_location_component(BatchDetailState.batch.location),
            # Supplier
            rx.cond(
                BatchDetailState.batch.supplier,
                rx.fragment(
                    rx.text("Supplier", size="2", color="gray", weight="medium"),
                    inline_supplier_component(BatchDetailState.batch.supplier),
                ),
            ),
            # Quantity
            rx.text("Quantity", size="2", color="gray", weight="medium"),
            rx.text(BatchDetailState.batch.pretty_quantity, size="2"),
            # Expiry Date
            rx.text("Expiry Date", size="2", color="gray", weight="medium"),
            rx.box(
                expiry_date_badge(BatchDetailState.batch.expiry_date),
            ),
            # Status
            rx.text("Status", size="2", color="gray", weight="medium"),
            rx.box(
                _status_badge(BatchDetailState.batch.status),
                width="fit-content",
            ),
            # Parent Batch
            rx.cond(
                BatchDetailState.batch.parent_batch,
                rx.fragment(
                    rx.text("Parent Batch", size="2", color="gray", weight="medium"),
                    batch_inline_link(BatchDetailState.batch.parent_batch),
                ),
            ),
            # Notes
            rx.cond(
                BatchDetailState.batch.notes,
                rx.fragment(
                    rx.text("Notes", size="2", color="gray", weight="medium"),
                    rx.text(BatchDetailState.batch.notes, size="2"),
                ),
            ),
            # Divider before technical info
            rx.divider(margin_top="0.5rem", margin_bottom="0.5rem", grid_column="span 2"),
            # Created by
            rx.text("Created by", size="2", color="gray", weight="medium"),
            user_inline_component(BatchDetailState.batch.created_by, size="small"),
            # Created at
            rx.text("Created at", size="2", color="gray", weight="medium"),
            rx.text(
                rx.moment(BatchDetailState.batch.created_at, format="MMM D, YYYY HH:mm"),
                size="2",
            ),
            # Last modified by
            rx.text("Last modified by", size="2", color="gray", weight="medium"),
            user_inline_component(BatchDetailState.batch.last_modified_by, size="small"),
            # Last modified at
            rx.text("Last modified at", size="2", color="gray", weight="medium"),
            rx.text(
                rx.moment(BatchDetailState.batch.last_modified_at, format="MMM D, YYYY HH:mm"),
                size="2",
            ),
            columns="2",
            spacing="3",
            width="100%",
            row_gap="1rem",
        ),
        width="100%",
        spacing="3",
        align_items="start",
    )


def _main_content() -> rx.Component:
    """Create the main content area with activities list.

    :return: The main content component
    :rtype: rx.Component
    """
    return activities_list_component(BatchDetailState.batch.id)


def _actions_menu() -> rx.Component:
    """Create the actions dropdown menu for batch operations.

    :return: The actions menu component
    :rtype: rx.Component
    """
    return batch_actions_menu(
        batch=BatchDetailState.batch,
        on_receive=BatchDetailState.open_receive_dialog,
        on_consume=BatchDetailState.open_consume_dialog,
        on_aliquot=BatchDetailState.open_aliquot_dialog,
        on_move=BatchDetailState.open_move_dialog,
        on_update=BatchDetailState.open_update_dialog,
        on_relabel=BatchDetailState.open_relabel_dialog,
        on_delete=BatchDetailState.open_delete_dialog,
    )


def batch_detail_page() -> rx.Component:
    """Create the batch detail page component.

    Displays batch information in a sidebar on the right side,
    with a main content area on the left for activities list.

    :return: The batch detail page component
    :rtype: rx.Component
    """
    return main_component(
        page_layout(
            rx.cond(
                BatchDetailState.error_message != "",
                rx.callout(
                    BatchDetailState.error_message,
                    icon="triangle_alert",
                    color_scheme="red",
                    role="alert",
                ),
                rx.cond(
                    BatchDetailState.is_loading,
                    rx.center(rx.spinner(size="3"), padding="2rem"),
                    rx.cond(
                        BatchDetailState.batch,
                        detail_page_layout(
                            main_content=_main_content(),
                            sidebar_content=_details_sidebar(),
                        ),
                        rx.center(
                            rx.vstack(
                                rx.icon("package-x", size=48, color="gray"),
                                rx.text(
                                    "Batch not found",
                                    size="4",
                                    color="gray",
                                    margin_top="1rem",
                                ),
                                spacing="2",
                                align="center",
                            ),
                            padding="3rem",
                            width="100%",
                        ),
                    ),
                ),
            ),
            header_content=rx.hstack(
                rx.vstack(
                    rx.heading(BatchDetailState.batch.batch_number, size="6"),
                    rx.cond(
                        BatchDetailState.batch.label,
                        rx.text(
                            f"{BatchDetailState.batch.label}",
                            size="2",
                            color="gray",
                        ),
                    ),
                    spacing="0",
                ),
                rx.cond(
                    BatchDetailState.batch,
                    _actions_menu(),
                ),
                justify="between",
                align="center",
                width="100%",
            ),
        ),
        batch_event_form_dialog(),
        move_batch_dialog(),
        update_batch_dialog(),
        relabel_batch_dialog(),
        delete_batch_dialog(),
        aliquot_form_dialog(),
    )
