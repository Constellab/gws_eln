"""Batches list component."""

import reflex as rx
from gws_eln.eln_app._eln_app.eln_app.material_batch_form_dialog.material_batch_form_dialog_component import (
    create_material_batch_dialog,
)
from gws_eln.locations.location_dto import LocationDTO
from gws_eln.materials.batch_status import BatchStatus
from gws_eln.materials.material_batch_dto import MaterialBatchDTO
from gws_eln.suppliers.supplier_dto import SupplierDTO
from gws_reflex_main import user_inline_component

from .batches_list_state import ALL_FILTER_VALUE, BatchesListState


def _location_filter_option(location: LocationDTO) -> rx.Component:
    """Create a select option for a location filter."""
    return rx.select.item(location.name, value=location.id)


def _supplier_filter_option(supplier: SupplierDTO) -> rx.Component:
    """Create a select option for a supplier filter."""
    return rx.select.item(supplier.name, value=supplier.id)


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
        rx.select.root(
            rx.select.trigger(placeholder="Location", width="180px"),
            rx.select.content(
                rx.select.item("All locations", value=ALL_FILTER_VALUE),
                rx.foreach(BatchesListState.available_locations, _location_filter_option),
            ),
            value=BatchesListState.filter_location_id,
            on_change=BatchesListState.handle_location_filter_change,
        ),
        # Supplier filter
        rx.select.root(
            rx.select.trigger(placeholder="Supplier", width="180px"),
            rx.select.content(
                rx.select.item("All suppliers", value=ALL_FILTER_VALUE),
                rx.foreach(BatchesListState.available_suppliers, _supplier_filter_option),
            ),
            value=BatchesListState.filter_supplier_id,
            on_change=BatchesListState.handle_supplier_filter_change,
        ),
        # Status filter
        rx.select.root(
            rx.select.trigger(placeholder="Status", width="140px"),
            rx.select.content(
                rx.select.item("All statuses", value=ALL_FILTER_VALUE),
                rx.select.item("Active", value=BatchStatus.ACTIVE.value),
                rx.select.item("Discarded", value=BatchStatus.DISCARDED.value),
            ),
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
            rx.text(batch.batch_number, weight="medium"),
        ),
        rx.table.cell(
            rx.cond(
                batch.label,
                rx.text(batch.label, size="2"),
                rx.text("-", size="2", color="gray"),
            )
        ),
        rx.table.cell(
            rx.text(batch.location.name, size="2"),
        ),
        rx.table.cell(
            rx.cond(
                batch.supplier,
                rx.text(batch.supplier.name, size="2"),
                rx.text("-", size="2", color="gray"),
            )
        ),
        rx.table.cell(
            rx.hstack(
                rx.text(batch.quantity, size="2"),
                rx.text(batch.unit_type, size="2", color="gray"),
                spacing="1",
            )
        ),
        rx.table.cell(
            rx.cond(
                batch.expiry_date,
                rx.moment(batch.expiry_date, format="MMM D, YYYY"),
                rx.text("-", size="2", color="gray"),
            )
        ),
        rx.table.cell(rx.box(_status_badge(batch.status), width="fit-content")),
        rx.table.cell(user_inline_component(batch.created_by, size="small")),
        rx.table.cell(rx.moment(batch.created_at, format="MMM D, YYYY")),
        style={":hover": {"background_color": "var(--gray-3)"}},
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
                        rx.table.column_header_cell("Label"),
                        rx.table.column_header_cell("Location"),
                        rx.table.column_header_cell("Supplier"),
                        rx.table.column_header_cell("Quantity"),
                        rx.table.column_header_cell("Expiry Date"),
                        rx.table.column_header_cell("Status"),
                        rx.table.column_header_cell("Created By"),
                        rx.table.column_header_cell("Created At"),
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
