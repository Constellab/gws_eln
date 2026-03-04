"""Batch detail page component."""

import reflex as rx
from gws_reflex_main import main_component, right_sidebar_close_button, user_inline_component

from ..activities.activities_list_component import activities_list_component
from ..common.breadcrumb.breadcrumb_component import breadcrumb_component
from ..common.breadcrumb.breadcrumb_state import BreadcrumbState
from ..common.detail_page_layout import detail_content_layout
from ..common.page_layout import page_layout
from ..locations.core.inline_location_component import inline_location_component
from ..materials.core.material_components import (
    inline_material_link,
)
from ..suppliers.core.inline_supplier_component import inline_supplier_component
from .aliquot_form_dialog.aliquot_form_dialog_component import (
    aliquot_form_dialog,
)
from .batch_detail_state import BatchDetailState
from .batch_event_form_dialog.batch_event_form_dialog_component import (
    batch_event_form_dialog,
)
from .core.batch_actions_menu import batch_actions_menu
from .core.batch_components import batch_inline_link, expiry_date_badge, status_badge
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


def _sidebar_section_label(label: str) -> rx.Component:
    """Create a small uppercase gray label for a sidebar section.

    :param label: The label text
    :type label: str
    :return: The styled label component
    :rtype: rx.Component
    """
    return rx.text(
        label,
        size="1",
        color="gray",
        weight="bold",
        style={
            "text-transform": "uppercase",
            "letter-spacing": "0.06em",
        },
    )


def _sidebar_metadata_row(label: str, value: rx.Component) -> rx.Component:
    """Create a metadata row with a label on the left and value on the right.

    :param label: The label text
    :type label: str
    :param value: The value component
    :type value: rx.Component
    :return: The metadata row component
    :rtype: rx.Component
    """
    return rx.hstack(
        rx.text(label, size="2", color="gray"),
        rx.spacer(),
        value,
        width="100%",
        align="center",
    )


def _details_sidebar() -> rx.Component:
    """Create the details sidebar with batch information.

    :return: The details sidebar component
    :rtype: rx.Component
    """
    return rx.vstack(
        # Heading with close button
        rx.hstack(
            _sidebar_section_label("Batch details"),
            rx.spacer(),
            right_sidebar_close_button(),
            width="100%",
            align="center",
            margin_bottom="1rem",
        ),
        # Main info grid (label + value per row)
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
            # Material
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
            rx.box(expiry_date_badge(BatchDetailState.batch.expiry_date)),
            # Status
            rx.text("Status", size="2", color="gray", weight="medium"),
            rx.box(status_badge(BatchDetailState.batch.status), width="fit-content"),
            # Parent Batch
            rx.cond(
                BatchDetailState.batch.parent_batch,
                rx.fragment(
                    rx.text("Parent Batch", size="2", color="gray", weight="medium"),
                    batch_inline_link(BatchDetailState.batch.parent_batch),
                ),
            ),
            columns="2",
            spacing="3",
            width="100%",
            row_gap="1rem",
        ),
        # Notes section (separate, with title above)
        rx.cond(
            BatchDetailState.batch.notes,
            rx.vstack(
                rx.divider(margin_top="1.5rem", margin_bottom="1.5rem"),
                _sidebar_section_label("Notes"),
                rx.text(BatchDetailState.batch.notes, size="2"),
                spacing="0",
                align_items="start",
                width="100%",
                gap="0.5rem",
            ),
        ),
        # Divider + metadata section
        rx.vstack(
            rx.divider(margin_top="1.5rem", margin_bottom="1.5rem"),
            _sidebar_metadata_row(
                "Created by",
                user_inline_component(BatchDetailState.batch.created_by, size="small"),
            ),
            _sidebar_metadata_row(
                "Created at",
                rx.text(
                    rx.moment(BatchDetailState.batch.created_at, format="MMM D, YYYY HH:mm"),
                    size="1",
                    weight="medium",
                ),
            ),
            _sidebar_metadata_row(
                "Last modified by",
                user_inline_component(BatchDetailState.batch.last_modified_by, size="small"),
            ),
            _sidebar_metadata_row(
                "Last modified at",
                rx.text(
                    rx.moment(BatchDetailState.batch.last_modified_at, format="MMM D, YYYY HH:mm"),
                    size="1",
                    weight="medium",
                ),
            ),
            spacing="1",
            width="100%",
            padding_top="0.5rem",
        ),
        width="100%",
        spacing="0",
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


def _header() -> rx.Component:
    """Create the header component for the batch detail page.

    :return: The header component
    :rtype: rx.Component
    """
    return rx.hstack(
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
        rx.spacer(),
        rx.cond(
            BatchDetailState.batch,
            _actions_menu(),
        ),
        width="100%",
        align="center",
        spacing="2",
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
                        detail_content_layout(
                            main_content=_main_content(),
                            header_content=_header(),
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
            right_sidebar_content=_details_sidebar(),
            header_content=breadcrumb_component(BreadcrumbState.breadcrumbs),
            max_content_width="1200px",
            height="100vh",
            padding="0",
        ),
        batch_event_form_dialog(),
        move_batch_dialog(),
        update_batch_dialog(),
        relabel_batch_dialog(),
        delete_batch_dialog(),
        aliquot_form_dialog(),
    )
