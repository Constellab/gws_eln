"""Materials list page component."""

import reflex as rx
from gws_eln.materials.material_dto import MaterialDTO
from gws_reflex_main import main_component, user_with_date_component

from ..batches.core.batch_components import consumable_badge
from ..common.page_layout import page_layout
from ..common.unit.unit_type_select_component import unit_type_select_component
from ..suppliers.core.inline_supplier_component import inline_supplier_component
from ..suppliers.core.supplier_select_component import supplier_select_component
from .core.material_actions_menu import material_actions_menu
from .material_form_dialog.material_form_dialog_component import material_update_dialog
from .materials_list_state import ALL_FILTER_VALUE, MaterialsListState


def _filter_bar() -> rx.Component:
    """Create the filter bar with search and dropdown filters.

    :return: The filter bar component
    :rtype: rx.Component
    """
    return rx.hstack(
        # Search input
        rx.input(
            placeholder="Search materials...",
            value=MaterialsListState.search_text,
            on_change=MaterialsListState.handle_search_change,
            width="200px",
        ),
        # Supplier filter
        supplier_select_component(
            placeholder="Supplier",
            width="180px",
            additional_option=("All suppliers", ALL_FILTER_VALUE),
            value=MaterialsListState.filter_supplier_id,
            on_change=MaterialsListState.handle_supplier_filter_change,
        ),
        # Consumable filter
        rx.select.root(
            rx.select.trigger(placeholder="Type", width="160px"),
            rx.select.content(
                rx.select.item("All types", value=ALL_FILTER_VALUE),
                rx.select.item("Consumable", value="true"),
                rx.select.item("Non-consumable", value="false"),
            ),
            value=MaterialsListState.filter_is_consumable,
            on_change=MaterialsListState.handle_consumable_filter_change,
        ),
        # Unit type filter
        unit_type_select_component(
            placeholder="Unit type",
            width="180px",
            all_option=("All unit types", ALL_FILTER_VALUE),
            value=MaterialsListState.filter_unit_type,
            on_change=MaterialsListState.handle_unit_type_filter_change,
        ),
        # Clear filters button
        rx.button(
            "Clear",
            on_click=MaterialsListState.clear_filters,
            variant="outline",
            size="2",
        ),
        width="100%",
        spacing="3",
        wrap="wrap",
        align="center",
    )


def _create_material_button() -> rx.Component:
    """Create the button to open the create material dialog.

    :return: The create material button component
    :rtype: rx.Component
    """
    return rx.fragment(
        rx.button(
            rx.icon("plus", size=18),
            "Create New Material",
            size="3",
            on_click=MaterialsListState.open_create_dialog,
        ),
        material_update_dialog(),
    )


def _row(material: MaterialDTO) -> rx.Component:
    """Create a table row for a material.

    :param material: The material DTO to display
    :type material: MaterialDTO
    :return: The table row component
    :rtype: rx.Component
    """
    return rx.table.row(
        rx.table.cell(rx.text(material.name)),
        rx.table.cell(
            rx.cond(
                material.description,
                rx.text(material.description, size="2", color="gray"),
            )
        ),
        rx.table.cell(
            rx.cond(
                material.default_supplier,
                inline_supplier_component(material.default_supplier),
            )
        ),
        rx.table.cell(rx.box(consumable_badge(material.is_consumable), width="fit-content")),
        rx.table.cell(
            user_with_date_component(material.created_by, material.created_at, size="small")
        ),
        rx.table.cell(
            rx.box(
                material_actions_menu(
                    on_update=lambda: MaterialsListState.open_update_dialog(material),
                    on_delete=lambda: MaterialsListState.open_delete_dialog(material),
                    stop_propagation=True,
                ),
                display="flex",
                justify_content="flex-end",
                align_items="center",
            )
        ),
        style={":hover": {"background_color": "var(--gray-3)"}, "cursor": "pointer"},
        on_click=lambda: MaterialsListState.go_to_material(material.id),
    )


def materials_list_page() -> rx.Component:
    """Create the materials list page component.

    This component displays a table of materials with columns for
    name, description, supplier, type, created by, and created at.
    Includes filters for search, supplier, consumable type, and unit type.

    :return: The materials list page component
    :rtype: rx.Component
    """
    return main_component(
        page_layout(
            rx.vstack(
                _filter_bar(),
                rx.cond(
                    MaterialsListState.error_message != "",
                    rx.callout(
                        MaterialsListState.error_message,
                        icon="triangle_alert",
                        color_scheme="red",
                        role="alert",
                        margin_bottom="1rem",
                    ),
                ),
                rx.cond(
                    MaterialsListState.is_loading,
                    rx.center(rx.spinner(size="3"), padding="2rem"),
                    rx.cond(
                        MaterialsListState.materials.length() > 0,
                        rx.table.root(
                            rx.table.header(
                                rx.table.row(
                                    rx.table.column_header_cell("Name"),
                                    rx.table.column_header_cell("Description"),
                                    rx.table.column_header_cell("Default Supplier"),
                                    rx.table.column_header_cell("Type"),
                                    rx.table.column_header_cell("Creation"),
                                    rx.table.column_header_cell(
                                        "Actions", width="100px", justify="end"
                                    ),
                                ),
                            ),
                            rx.table.body(rx.foreach(MaterialsListState.materials, _row)),
                            width="100%",
                            variant="surface",
                        ),
                        rx.center(
                            rx.vstack(
                                rx.icon("package", size=48, color="gray"),
                                rx.text(
                                    "No materials found", size="4", color="gray", margin_top="1rem"
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
                rx.heading("Materials", size="6"),
                _create_material_button(),
                justify="between",
                align="center",
                width="100%",
            ),
        )
    )
