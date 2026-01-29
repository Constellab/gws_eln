import reflex as rx

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

    This component uses SupplierSelectState to load suppliers from the database.
    The suppliers are loaded when the component mounts via on_load.

    Args:
        placeholder: Placeholder text for the select
        name: Name attribute for the select element
        disabled: Whether the select is disabled
        width: Width of the select component
        additional_option: Optional tuple of (label, value) for an additional option at the top
        **kwargs: Additional props to pass to the select.root component
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
    all_item = (
        rx.select.item(additional_option[0], value=additional_option[1])
        if additional_option
        else rx.fragment()
    )

    return rx.select.root(
        rx.select.trigger(placeholder=placeholder, width=width),
        rx.select.content(
            all_item,
            rx.foreach(
                SupplierSelectState.suppliers,
                lambda supplier: rx.select.item(
                    supplier.label,
                    value=supplier.value,
                ),
            ),
        ),
        name=name,
        disabled=disabled,
        **kwargs,
    )
