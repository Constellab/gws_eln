"""Material detail page component."""

import reflex as rx
from gws_reflex_main import main_component, right_sidebar_close_button, user_inline_component

from ..batches.batches_list_component import batches_list_component
from ..batches.batches_list_state import BatchesListState
from ..batches.core.batch_components import consumable_badge
from ..common.breadcrumb.breadcrumb_component import breadcrumb_component
from ..common.breadcrumb.breadcrumb_state import BreadcrumbState
from ..common.detail_page_layout import detail_content_layout
from ..common.page_layout import page_layout
from ..suppliers.core.inline_supplier_component import inline_supplier_component
from .core.material_actions_menu import material_actions_menu
from .material_detail_state import MaterialDetailState
from .material_form_dialog.material_form_dialog_component import material_update_dialog


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
    """Create the details sidebar with material information.

    :return: The details sidebar component
    :rtype: rx.Component
    """
    return rx.vstack(
        # Heading with close button
        rx.hstack(
            _sidebar_section_label("Material details"),
            rx.spacer(),
            right_sidebar_close_button(),
            width="100%",
            align="center",
            margin_bottom="1rem",
        ),
        # Main info grid (label + value per row)
        rx.grid(
            # Name
            rx.text("Name", size="2", color="gray", weight="medium"),
            rx.text(MaterialDetailState.material.name, size="2"),
            # Default Supplier
            rx.cond(
                MaterialDetailState.material.default_supplier,
                rx.fragment(
                    rx.text("Default Supplier", size="2", color="gray", weight="medium"),
                    inline_supplier_component(MaterialDetailState.material.default_supplier),
                ),
            ),
            # Type
            rx.text("Type", size="2", color="gray", weight="medium"),
            rx.box(consumable_badge(MaterialDetailState.material.is_consumable), width="fit-content"),
            # Default Unit Type
            rx.text("Default Unit Type", size="2", color="gray", weight="medium"),
            rx.text(
                MaterialDetailState.material.default_unit_type,
                size="2",
                style={"text_transform": "capitalize"},
            ),
            columns="2",
            spacing="3",
            width="100%",
            row_gap="1rem",
        ),
        # Description section (separate, with title above)
        rx.cond(
            MaterialDetailState.material.description,
            rx.vstack(
                rx.divider(margin_top="1.5rem", margin_bottom="1.5rem"),
                _sidebar_section_label("Description"),
                rx.text(MaterialDetailState.material.description, size="2"),
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
                user_inline_component(MaterialDetailState.material.created_by, size="small"),
            ),
            _sidebar_metadata_row(
                "Created at",
                rx.text(
                    rx.moment(MaterialDetailState.material.created_at, format="MMM D, YYYY HH:mm"),
                    size="1",
                    weight="medium",
                ),
            ),
            _sidebar_metadata_row(
                "Last modified by",
                user_inline_component(MaterialDetailState.material.last_modified_by, size="small"),
            ),
            _sidebar_metadata_row(
                "Last modified at",
                rx.text(
                    rx.moment(
                        MaterialDetailState.material.last_modified_at, format="MMM D, YYYY HH:mm"
                    ),
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


def _create_batch_button() -> rx.Component:
    """Create the button to open the create batch dialog.

    :return: The create batch button component
    :rtype: rx.Component
    """
    return rx.button(
        rx.icon("plus", size=18),
        "Create New Batch",
        size="2",
        on_click=BatchesListState.open_create_dialog,
    )


def _header() -> rx.Component:
    """Create the header component for the material detail page.

    :return: The header component
    :rtype: rx.Component
    """
    return rx.hstack(
        rx.heading(MaterialDetailState.material.name, size="6"),
        rx.spacer(),
        _create_batch_button(),
        material_actions_menu(
            on_update=MaterialDetailState.open_update_dialog,
            on_delete=MaterialDetailState.open_delete_dialog,
        ),
        material_update_dialog(),
        width="100%",
        align="center",
        spacing="4",
    )


def _main_content() -> rx.Component:
    """Create the main content area with batches list.

    :return: The main content component
    :rtype: rx.Component
    """
    return batches_list_component(MaterialDetailState.material.id)


def material_detail_page() -> rx.Component:
    """Create the material detail page component.

    Displays material information in a sidebar on the right side,
    with a main content area on the left for batches list.

    :return: The material detail page component
    :rtype: rx.Component
    """
    return rx.box(
        main_component(
            page_layout(
                rx.cond(
                    MaterialDetailState.error_message != "",
                    rx.callout(
                        MaterialDetailState.error_message,
                        icon="triangle_alert",
                        color_scheme="red",
                        role="alert",
                    ),
                    rx.cond(
                        MaterialDetailState.is_loading,
                        rx.center(rx.spinner(size="3"), padding="2rem"),
                        rx.cond(
                            MaterialDetailState.material,
                            detail_content_layout(
                                main_content=_main_content(),
                                header_content=_header(),
                            ),
                            rx.center(
                                rx.vstack(
                                    rx.icon("package-x", size=48, color="gray"),
                                    rx.text(
                                        "Material not found",
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
            )
        ),
    )
