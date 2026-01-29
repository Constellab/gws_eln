"""Suppliers list page component."""

import reflex as rx
from gws_eln.suppliers.supplier_dto import SupplierDTO
from gws_reflex_main import main_component, user_inline_component

from ..common.page_layout import page_layout
from .supplier_form_dialog.supplier_form_dialog_component import supplier_update_dialog
from .suppliers_list_state import SuppliersListState


def _filter_bar() -> rx.Component:
    """Create the filter bar with search filter.

    :return: The filter bar component
    :rtype: rx.Component
    """
    return rx.hstack(
        rx.input(
            placeholder="Search suppliers...",
            value=SuppliersListState.search_text,
            on_change=SuppliersListState.handle_search_change,
            min_width="300px",
        ),
        rx.button(
            "Clear",
            on_click=SuppliersListState.clear_filters,
            variant="outline",
            size="2",
        ),
        width="100%",
        spacing="3",
        wrap="wrap",
    )


def _create_supplier_button() -> rx.Component:
    """Create the button to open the create supplier dialog.

    :return: The create supplier button component
    :rtype: rx.Component
    """
    return rx.fragment(
        rx.button(
            rx.icon("plus", size=18),
            "Create New Supplier",
            size="3",
            on_click=SuppliersListState.open_create_dialog,
        ),
        supplier_update_dialog(),
    )


def _actions_menu(supplier: SupplierDTO) -> rx.Component:
    """Create the actions menu for a supplier.

    :param supplier: The supplier DTO
    :type supplier: SupplierDTO
    :return: The actions menu component
    :rtype: rx.Component
    """
    return rx.menu.root(
        rx.menu.trigger(rx.button(rx.icon("ellipsis-vertical", size=18), variant="soft", size="2")),
        rx.menu.content(
            rx.menu.item(
                rx.icon("pencil", size=16),
                "Update",
                on_click=lambda: SuppliersListState.open_update_dialog(supplier),
            ),
            rx.menu.separator(),
            rx.menu.item(
                rx.icon("trash-2", size=16),
                "Delete",
                color="red",
                on_click=lambda: SuppliersListState.open_delete_dialog(supplier),
            ),
        ),
    )


def _row(supplier: SupplierDTO) -> rx.Component:
    """Create a table row for a supplier.

    :param supplier: The supplier DTO to display
    :type supplier: SupplierDTO
    :return: The table row component
    :rtype: rx.Component
    """
    return rx.table.row(
        rx.table.cell(rx.text(supplier.name)),
        rx.table.cell(
            rx.cond(
                supplier.description,
                rx.text(supplier.description, size="2", color="gray"),
            )
        ),
        rx.table.cell(user_inline_component(supplier.created_by, size="small")),
        rx.table.cell(rx.moment(supplier.created_at, format="MMM D, YYYY")),
        rx.table.cell(
            rx.box(
                _actions_menu(supplier),
                display="flex",
                justify_content="flex-end",
                align_items="center",
            )
        ),
        style={":hover": {"background_color": "var(--gray-3)"}},
    )


def suppliers_list_page() -> rx.Component:
    """Create the suppliers list page component.

    This component displays a table of suppliers with columns for
    name, description, created by, and created at.
    Includes a search filter for filtering by supplier name.

    :return: The suppliers list page component
    :rtype: rx.Component
    """
    return main_component(
        page_layout(
            rx.vstack(
                _filter_bar(),
                rx.cond(
                    SuppliersListState.error_message != "",
                    rx.callout(
                        SuppliersListState.error_message,
                        icon="triangle_alert",
                        color_scheme="red",
                        role="alert",
                        margin_bottom="1rem",
                    ),
                ),
                rx.cond(
                    SuppliersListState.is_loading,
                    rx.center(rx.spinner(size="3"), padding="2rem"),
                    rx.cond(
                        SuppliersListState.suppliers.length() > 0,
                        rx.table.root(
                            rx.table.header(
                                rx.table.row(
                                    rx.table.column_header_cell("Name"),
                                    rx.table.column_header_cell("Description"),
                                    rx.table.column_header_cell("Created By"),
                                    rx.table.column_header_cell("Created At"),
                                    rx.table.column_header_cell(
                                        "Actions", width="100px", justify="end"
                                    ),
                                ),
                            ),
                            rx.table.body(rx.foreach(SuppliersListState.suppliers, _row)),
                            width="100%",
                            variant="surface",
                        ),
                        rx.center(
                            rx.vstack(
                                rx.icon("truck", size=48, color="gray"),
                                rx.text(
                                    "No suppliers found", size="4", color="gray", margin_top="1rem"
                                ),
                                spacing="2",
                                align="center",
                            ),
                            padding="3rem",
                            width="100%",
                        ),
                    ),
                ),
                width="100%",
                spacing="4",
            ),
            header_content=rx.hstack(
                rx.heading("Suppliers", size="6"),
                _create_supplier_button(),
                justify="between",
                align="center",
                width="100%",
            ),
        )
    )
