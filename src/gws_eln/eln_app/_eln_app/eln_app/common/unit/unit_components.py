import reflex as rx
from gws_eln.core.unit_type import UnitType
from gws_eln.utils.units_converter import UnitConverter


def quantity_unit_input(
    unit_type: rx.Var[str],
    quantity_name: str = "quantity",
    unit_name: str = "unit",
    quantity_value: rx.Var | str = "",
    unit_value: rx.Var | str | None = None,
    on_quantity_change: rx.EventHandler | None = None,
    on_unit_change: rx.EventHandler | None = None,
    quantity_placeholder: str = "Enter quantity",
    quantity_label: str = "Quantity",
    unit_label: str = "Unit",
    quantity_required: bool = True,
    disabled: bool = False,
    quantity_width: str = "60%",
    unit_width: str = "40%",
    spacing: str = "3",
) -> rx.Component:
    """
    Reusable quantity input component with dynamic unit selection.

    This component generates two form fields:
    1. A numeric input for the quantity
    2. A select dropdown for the unit based on the unit_type from state

    Args:
        quantity_name: Name attribute for the quantity input field
        unit_name: Name attribute for the unit select field
        unit_type: The UnitType rx.Var from state that determines available units
        quantity_value: Default/bound value for quantity input
        unit_value: Default/bound value for unit select
        on_quantity_change: Event handler for quantity changes
        on_unit_change: Event handler for unit selection changes
        quantity_placeholder: Placeholder text for quantity input
        quantity_label: Label text for quantity field
        unit_label: Label text for unit field
        quantity_required: Whether quantity is required
        disabled: Whether both fields are disabled
        quantity_width: Width of the quantity input
        unit_width: Width of the unit select
        spacing: Spacing between the two fields

    Returns:
        A reflex component with quantity input and unit select side by side

    Example:
        quantity_unit_input(
            unit_type=MyState.selected_unit_type,
            quantity_value=MyState.quantity,
            unit_value=MyState.unit,
            on_quantity_change=MyState.set_quantity,
            on_unit_change=MyState.set_unit,
        )
    """
    # Build unit options from UnitConverter data
    volume_units = UnitConverter.get_units_for_select(UnitType.VOLUME)
    mass_units = UnitConverter.get_units_for_select(UnitType.MASS)
    length_units = UnitConverter.get_units_for_select(UnitType.LENGTH)
    count_units = UnitConverter.get_units_for_select(UnitType.COUNT)

    unit_select = rx.select.root(
        rx.select.trigger(placeholder="Select unit", width="100%"),
        rx.select.content(
            rx.match(
                unit_type,
                (
                    UnitType.VOLUME.value,
                    rx.fragment(
                        *[rx.select.item(label, value=symbol) for symbol, label in volume_units]
                    ),
                ),
                (
                    UnitType.MASS.value,
                    rx.fragment(
                        *[rx.select.item(label, value=symbol) for symbol, label in mass_units]
                    ),
                ),
                (
                    UnitType.LENGTH.value,
                    rx.fragment(
                        *[rx.select.item(label, value=symbol) for symbol, label in length_units]
                    ),
                ),
                (
                    UnitType.COUNT.value,
                    rx.fragment(
                        *[rx.select.item(label, value=symbol) for symbol, label in count_units]
                    ),
                ),
                # Default case
                rx.fragment(
                    *[rx.select.item(label, value=symbol) for symbol, label in count_units]
                ),
            ),
        ),
        name=unit_name,
        value=unit_value,
        on_change=on_unit_change,
        disabled=disabled,
        width="100%",
    )

    # Build quantity input props
    quantity_props = {
        "placeholder": quantity_placeholder,
        "name": quantity_name,
        "type": "number",
        "min": "0",
        "step": "any",
        "required": quantity_required,
        "width": "100%",
        "disabled": disabled,
    }

    if isinstance(quantity_value, rx.Var):
        quantity_props["value"] = quantity_value
    else:
        quantity_props["default_value"] = quantity_value

    if on_quantity_change:
        quantity_props["on_change"] = on_quantity_change

    return rx.hstack(
        rx.vstack(
            rx.text(quantity_label, size="2", weight="bold"),
            rx.input(**quantity_props),
            width=quantity_width,
            spacing="1",
        ),
        rx.vstack(
            rx.text(unit_label, size="2", weight="bold"),
            unit_select,
            width=unit_width,
            spacing="1",
        ),
        width="100%",
        spacing=spacing,
    )
