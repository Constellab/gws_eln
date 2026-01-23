"""Batch detail page component."""

import reflex as rx
from gws_reflex_main import main_component, user_inline_component

from ..activities.activities_list_component import activities_list_component
from ..common.batch.batch_components import expiry_date_badge
from ..common.detail_page_layout import detail_page_layout
from ..common.eln_app_router import ElnAppRouter
from ..common.location.inline_location_component import inline_location_component
from ..common.materials.material_components import (
    inline_material_component,
)
from ..common.page_layout import page_layout
from ..common.supplier.inline_supplier_component import inline_supplier_component
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
            rx.text("Label", size="2", color="gray", weight="medium"),
            rx.cond(
                BatchDetailState.batch.label,
                rx.text(BatchDetailState.batch.label, size="2"),
                rx.text("-", size="2", color="gray"),
            ),
            # Material Name
            rx.text("Material", size="2", color="gray", weight="medium"),
            inline_material_component(BatchDetailState.batch.material),
            # Location
            rx.text("Location", size="2", color="gray", weight="medium"),
            inline_location_component(BatchDetailState.batch.location),
            # Supplier
            rx.text("Supplier", size="2", color="gray", weight="medium"),
            rx.cond(
                BatchDetailState.batch.supplier,
                inline_supplier_component(BatchDetailState.batch.supplier),
                rx.text("-", size="2", color="gray"),
            ),
            # Quantity
            rx.text("Quantity", size="2", color="gray", weight="medium"),
            rx.text(BatchDetailState.batch.pretty_quantity, size="2"),
            # Expiry Date
            rx.text("Expiry Date", size="2", color="gray", weight="medium"),
            expiry_date_badge(BatchDetailState.batch.expiry_date),
            # Status
            rx.text("Status", size="2", color="gray", weight="medium"),
            rx.box(
                _status_badge(BatchDetailState.batch.status),
                width="fit-content",
            ),
            # Parent Batch
            rx.text("Parent Batch", size="2", color="gray", weight="medium"),
            rx.cond(
                BatchDetailState.batch.parent_batch_id,
                rx.link(
                    rx.text("View parent", size="2"),
                    href=ElnAppRouter.get_batch_detail_url(BatchDetailState.batch.parent_batch_id),
                ),
                rx.text("-", size="2", color="gray"),
            ),
            # Notes
            rx.text("Notes", size="2", color="gray", weight="medium"),
            rx.cond(
                BatchDetailState.batch.notes,
                rx.text(BatchDetailState.batch.notes, size="2"),
                rx.text("-", size="2", color="gray"),
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


def _back_button() -> rx.Component:
    """Create the back button to return to material detail page.

    :return: The back button component
    :rtype: rx.Component
    """
    return rx.link(
        rx.icon_button(
            rx.icon("arrow-left", size=18),
            variant="ghost",
            size="2",
        ),
        href=ElnAppRouter.get_material_detail_url(BatchDetailState.batch.material.id),
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
                rx.cond(
                    BatchDetailState.batch,
                    _back_button(),
                    rx.link(
                        rx.icon_button(
                            rx.icon("arrow-left", size=18),
                            variant="ghost",
                            size="2",
                        ),
                        href=ElnAppRouter.get_material_list_url(),
                    ),
                ),
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
                align="center",
                spacing="2",
            ),
        )
    )
