"""Batches list component."""

import reflex as rx
from gws_eln.materials.batch_status import BatchStatus
from gws_eln.materials.material_batch_dto import MaterialBatchDTO
from gws_reflex_main import user_with_date_component

from ..common.batch.batch_components import batch_inline, expiry_date_badge
from ..common.batch.batch_status_select_component import batch_status_select_component
from ..common.location.inline_location_component import inline_location_component
from ..common.location.location_select_component import location_select_component
from ..common.supplier.inline_supplier_component import inline_supplier_component
from ..common.supplier.supplier_select_component import supplier_select_component
from ..material_batch_form_dialog.material_batch_form_dialog_component import (
    create_material_batch_dialog,
)
from .batches_list_state import ALL_FILTER_VALUE, BatchesListState


def _filter_bar() -> rx.Component:
    """Create the filter bar with search and dropdown filters.

    :return: The filter bar component
    :rtype: rx.Component
    """
    return rx.hstack(
        # Search input (batch number)
        rx.input(
            placeholder="Search batch number...",
            value=BatchesListState.search_text,
            on_change=BatchesListState.handle_search_change,
            width="200px",
        ),
        # Location filter
        location_select_component(
            placeholder="Location",
            width="180px",
            all_option=("All locations", ALL_FILTER_VALUE),
            value=BatchesListState.filter_location_id,
            on_change=BatchesListState.handle_location_filter_change,
        ),
        # Supplier filter
        supplier_select_component(
            placeholder="Supplier",
            width="180px",
            additional_option=("All suppliers", ALL_FILTER_VALUE),
            value=BatchesListState.filter_supplier_id,
            on_change=BatchesListState.handle_supplier_filter_change,
        ),
        # Status filter
        batch_status_select_component(
            placeholder="Status",
            width="140px",
            all_option=("All statuses", ALL_FILTER_VALUE),
            value=BatchesListState.filter_status,
            on_change=BatchesListState.handle_status_filter_change,
        ),
        # Clear filters button
        rx.button(
            "Clear",
            on_click=BatchesListState.clear_filters,
            variant="outline",
            size="2",
        ),
        width="100%",
        spacing="3",
        wrap="wrap",
        align="center",
    )


def _create_batch_button() -> rx.Component:
    """Create the button to open the create batch dialog.

    :return: The create batch button component
    :rtype: rx.Component
    """
    return rx.button(
        rx.icon("plus", size=18),
        "Create New Batch",
        size="3",
        on_click=BatchesListState.open_create_dialog,
    )


def _status_badge(status: BatchStatus) -> rx.Component:
    """Create a badge indicating the batch status.

    :param status: The batch status
    :type status: BatchStatus
    :return: The badge component
    :rtype: rx.Component
    """
    return rx.cond(
        status == BatchStatus.ACTIVE.value,
        rx.badge("Active", color_scheme="green", size="1"),
        rx.badge("Discarded", color_scheme="red", size="1"),
    )


def _row(batch: MaterialBatchDTO) -> rx.Component:
    """Create a table row for a batch.

    :param batch: The batch DTO to display
    :type batch: MaterialBatchDTO
    :return: The table row component
    :rtype: rx.Component
    """
    return rx.table.row(
        rx.table.cell(
            batch_inline(batch),
        ),
        rx.table.cell(
            inline_location_component(batch.location),
        ),
        rx.table.cell(
            rx.cond(
                batch.supplier,
                inline_supplier_component(batch.supplier),
            )
        ),
        rx.table.cell(
            rx.text(batch.pretty_quantity),
        ),
        rx.table.cell(expiry_date_badge(batch.expiry_date)),
        rx.table.cell(rx.box(_status_badge(batch.status), width="fit-content")),
        rx.table.cell(
            user_with_date_component(
                batch.created_by,
                batch.created_at,
                size="small",
            )
        ),
        on_click=rx.redirect(f"/batches/{batch.id}"),
        style={":hover": {"background_color": "var(--gray-3)"}, "cursor": "pointer"},
    )


def _batches_header() -> rx.Component:
    """Create the header section with title, create button, and filter bar.

    :return: The header component
    :rtype: rx.Component
    """
    return rx.vstack(
        rx.hstack(
            rx.heading("Batches", size="5"),
            rx.spacer(),
            _create_batch_button(),
            width="100%",
            align="center",
        ),
        _filter_bar(),
        rx.cond(
            BatchesListState.error_message != "",
            rx.callout(
                BatchesListState.error_message,
                icon="triangle_alert",
                color_scheme="red",
                role="alert",
                margin_bottom="1rem",
            ),
        ),
        width="100%",
        spacing="4",
    )


def _batches_table() -> rx.Component:
    """Create the batches table with loading, empty, and data states.

    :return: The table component
    :rtype: rx.Component
    """
    return rx.cond(
        BatchesListState.is_loading & (BatchesListState.batches.length() == 0),
        rx.center(
            rx.vstack(
                rx.spinner(size="3"),
                rx.text("Loading batches...", size="3", color="gray", margin_top="1rem"),
                spacing="2",
                align="center",
            ),
            padding="3rem",
            width="100%",
        ),
        rx.cond(
            BatchesListState.batches.length() > 0,
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("Batch Number"),
                        rx.table.column_header_cell("Location"),
                        rx.table.column_header_cell("Supplier"),
                        rx.table.column_header_cell("Quantity"),
                        rx.table.column_header_cell("Expiry Date"),
                        rx.table.column_header_cell("Status"),
                        rx.table.column_header_cell("Creation"),
                    ),
                ),
                rx.table.body(rx.foreach(BatchesListState.batches, _row)),
                width="100%",
                variant="surface",
            ),
            rx.center(
                rx.vstack(
                    rx.icon("package-open", size=48, color="gray"),
                    rx.text("No batches found", size="4", color="gray", margin_top="1rem"),
                    spacing="2",
                    align="center",
                ),
                padding="3rem",
                width="100%",
            ),
        ),
    )


def batches_list_component(material_id: rx.Var[str]) -> rx.Component:
    """Create the batches list component for a specific material.

    This component displays a table of batches with columns for
    batch number, label, location, supplier, quantity,
    expiry date, status, created by, and created at.
    Includes filters for search, location, supplier, and status.

    The component uses on_mount to trigger batch loading when mounted,
    and a key based on material_id to force remount when material changes.

    :param material_id: The ID of the material to display batches for
    :type material_id: rx.Var[str]
    :return: The batches list component
    :rtype: rx.Component
    """
    return rx.box(
        rx.vstack(
            _batches_header(),
            _batches_table(),
            create_material_batch_dialog(),
            width="100%",
            spacing="4",
            on_mount=BatchesListState.fetch_batches_on_mount(material_id),
        ),
        key=material_id,
        width="100%",
    )
