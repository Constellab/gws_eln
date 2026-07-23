import reflex as rx
from gws_reflex_main.gws_components import select_component

from .supplier_select_state import SupplierSelectState


def supplier_select_component(
    placeholder: str = "Select a supplier...",
    name: str | None = None,
    disabled: bool = False,
    width: str = "100%",
    additional_option: tuple[str, str] | None = None,
    **kwargs,
) -> rx.Component:
    """
    Reusable supplier select component.

    Searchable single-select dropdown (type to filter) built on the shared
    ``select_component``. It uses SupplierSelectState to load suppliers from the
    database; the suppliers are loaded when the component mounts.

    Args:
        placeholder: Placeholder text for the select
        name: Name attribute for the select element
        disabled: Whether the select is disabled
        width: Width of the select component
        additional_option: Optional tuple of (label, value) for an additional option at the top
        **kwargs: Additional props to pass to the underlying select component
                 (e.g., on_change, value, default_value)

    Returns:
        A reflex component for supplier selection

    Example:
        # With state binding for forms
        supplier_select_component(
            name="supplier_id",
            value=MyFormState.supplier_id,
            on_change=MyFormState.set_supplier_id,
            width="100%"
        )

        # With "All" option for filters
        supplier_select_component(
            additional_option=("All suppliers", "all"),
            value=FilterState.supplier_id,
            on_change=FilterState.set_supplier_id,
        )
    """
    data = SupplierSelectState.suppliers
    if additional_option:
        data = (
            rx.Var.create([{"value": additional_option[1], "label": additional_option[0]}])
            + SupplierSelectState.suppliers
        )

    return select_component(
        data=data,
        placeholder=placeholder,
        searchable=True,
        name=name,
        disabled=disabled,
        width=width,
        on_mount=SupplierSelectState.ensure_loaded,
        **kwargs,
    )
