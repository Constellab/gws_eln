import reflex as rx

from .location_select_state import LocationSelectState


def location_select_component(
    placeholder: str = "Select a location...",
    name: str = None,
    disabled: bool = False,
    width: str = "100%",
    **kwargs
) -> rx.Component:
    """
    Reusable location select component.

    This component uses LocationSelectState to load locations from the database.
    The locations are loaded when the component mounts via on_load.

    Args:
        placeholder: Placeholder text for the select
        name: Name attribute for the select element
        disabled: Whether the select is disabled
        width: Width of the select component
        **kwargs: Additional props to pass to the select.root component
                 (e.g., on_change, value, default_value)

    Returns:
        A reflex component for location selection

    Example:
        # With state binding for forms
        location_select_component(
            name="location_id",
            value=MyFormState.location_id,
            on_change=MyFormState.set_location_id,
            width="100%"
        )
    """
    return rx.select.root(
        rx.select.trigger(placeholder=placeholder, width=width),
        rx.select.content(
            rx.foreach(
                LocationSelectState.locations,
                lambda location: rx.select.item(
                    location.label,
                    value=location.value,
                ),
            )
        ),
        name=name,
        disabled=disabled,
        **kwargs,
    )
