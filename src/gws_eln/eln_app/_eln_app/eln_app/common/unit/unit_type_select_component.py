import reflex as rx

from .unit_type_select_state import UnitTypeSelectState


def unit_type_select_component(
    placeholder: str = "Select unit type...",
    name: str | None = None,
    disabled: bool = False,
    width: str = "100%",
    all_option: tuple[str, str] | None = None,
    **kwargs,
) -> rx.Component:
    """
    Reusable unit type select component.

    This component uses UnitTypeSelectState to provide unit type options.

    Args:
        placeholder: Placeholder text for the select
        name: Name attribute for the select element
        disabled: Whether the select is disabled
        width: Width of the select component
        all_option: Optional tuple of (label, value) for an "All" option at the top
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

        # With "All" option for filters
        unit_type_select_component(
            all_option=("All unit types", "all"),
            value=FilterState.unit_type,
            on_change=FilterState.set_unit_type,
        )
    """
    all_item = rx.select.item(all_option[0], value=all_option[1]) if all_option else rx.fragment()

    return rx.select.root(
        rx.select.trigger(placeholder=placeholder, width=width),
        rx.select.content(
            all_item,
            rx.foreach(
                UnitTypeSelectState.unit_types,
                lambda unit_type: rx.select.item(
                    unit_type.label,
                    value=unit_type.value,
                ),
            ),
        ),
        name=name,
        disabled=disabled,
        **kwargs,
    )
