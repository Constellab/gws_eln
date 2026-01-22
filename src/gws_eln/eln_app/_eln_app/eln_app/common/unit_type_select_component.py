import reflex as rx

from .unit_type_select_state import UnitTypeSelectState


def unit_type_select_component(
    placeholder: str = "Select unit type...",
    name: str = None,
    disabled: bool = False,
    width: str = "100%",
    **kwargs
) -> rx.Component:
    """
    Reusable unit type select component.

    This component uses UnitTypeSelectState to provide unit type options.

    Args:
        placeholder: Placeholder text for the select
        name: Name attribute for the select element
        disabled: Whether the select is disabled
        width: Width of the select component
        **kwargs: Additional props to pass to the select.root component
                 (e.g., on_change, value, default_value)

    Returns:
        A reflex component for unit type selection

    Example:
        # With state binding for forms
        unit_type_select_component(
            name="unit_type",
            value=MyFormState.unit_type,
            on_change=MyFormState.set_unit_type,
            width="100%"
        )
    """
    return rx.select.root(
        rx.select.trigger(placeholder=placeholder, width=width),
        rx.select.content(
            rx.foreach(
                UnitTypeSelectState.unit_types,
                lambda unit_type: rx.select.item(
                    unit_type.label,
                    value=unit_type.value,
                ),
            )
        ),
        name=name,
        disabled=disabled,
        **kwargs,
    )
