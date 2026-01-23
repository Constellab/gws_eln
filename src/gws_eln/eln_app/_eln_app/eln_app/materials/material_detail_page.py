"""Material detail page component."""

import reflex as rx
from gws_reflex_main import main_component, user_inline_component

from ..batches.batches_list_component import batches_list_component
from ..common.batch.batch_components import consumable_badge
from ..common.detail_page_layout import detail_page_layout
from ..common.materials.material_actions_menu import material_actions_menu
from ..common.page_layout import page_layout
from ..common.supplier.inline_supplier_component import inline_supplier_component
from ..material_form_dialog.material_form_dialog_component import material_update_dialog
from .material_detail_state import MaterialDetailState


def _details_sidebar() -> rx.Component:
    """Create the details sidebar with material information.

    :return: The details sidebar component
    :rtype: rx.Component
    """
    return rx.vstack(
        rx.heading("Details", size="5", margin_bottom="1rem"),
        rx.grid(
            # Name
            rx.text("Name", size="2", color="gray", weight="medium"),
            rx.text(MaterialDetailState.material.name, size="2"),
            # Description
            rx.cond(
                MaterialDetailState.material.description,
                rx.fragment(
                    rx.text("Description", size="2", color="gray", weight="medium"),
                    rx.text(MaterialDetailState.material.description, size="2"),
                ),
            ),
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
            rx.box(
                consumable_badge(MaterialDetailState.material.is_consumable),
                width="fit-content",
            ),
            # Default Unit Type
            rx.text("Default Unit Type", size="2", color="gray", weight="medium"),
            rx.text(MaterialDetailState.material.default_unit_type, size="2"),
            # Divider before technical info
            rx.divider(margin_top="0.5rem", margin_bottom="0.5rem", grid_column="span 2"),
            # Created by
            rx.text("Created by", size="2", color="gray", weight="medium"),
            user_inline_component(MaterialDetailState.material.created_by, size="small"),
            # Created at
            rx.text("Created at", size="2", color="gray", weight="medium"),
            rx.text(
                rx.moment(MaterialDetailState.material.created_at, format="MMM D, YYYY HH:mm"),
                size="2",
            ),
            # Last modified by
            rx.text("Last modified by", size="2", color="gray", weight="medium"),
            user_inline_component(MaterialDetailState.material.last_modified_by, size="small"),
            # Last modified at
            rx.text("Last modified at", size="2", color="gray", weight="medium"),
            rx.text(
                rx.moment(
                    MaterialDetailState.material.last_modified_at, format="MMM D, YYYY HH:mm"
                ),
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
    """Create the main content area with batches list.

    :return: The main content component
    :rtype: rx.Component
    """
    return batches_list_component(MaterialDetailState.material.id)


def material_detail_page() -> rx.Component:
    """Create the material detail page component.

    Displays material information in a sidebar on the left side,
    with a main content area on the right for future content.

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
                            detail_page_layout(
                                main_content=_main_content(),
                                sidebar_content=_details_sidebar(),
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
                header_content=rx.hstack(
                    rx.heading(MaterialDetailState.material.name, size="6"),
                    rx.fragment(
                        material_actions_menu(
                            on_update=MaterialDetailState.open_update_dialog,
                            on_delete=MaterialDetailState.open_delete_dialog,
                        ),
                        material_update_dialog(),
                    ),
                    justify="between",
                    align="center",
                    width="100%",
                ),
            )
        ),
    )
