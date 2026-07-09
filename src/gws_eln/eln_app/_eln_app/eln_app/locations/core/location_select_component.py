import reflex as rx

from .location_select_state import LocationSelectState


def location_select_component(
    placeholder: str = "Select a location...",
    name: str | None = None,
    disabled: bool = False,
    width: str = "100%",
    all_option: tuple[str, str] | None = None,
    **kwargs,
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
        all_option: Optional tuple of (label, value) for an "All" option at the top
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

        # With "All" option for filters
        location_select_component(
            all_option=("All locations", "all"),
            value=FilterState.location_id,
            on_change=FilterState.set_location_id,
        )
    """
    all_item = rx.select.item(all_option[0], value=all_option[1]) if all_option else rx.fragment()

    return rx.select.root(
        rx.select.trigger(placeholder=placeholder, width=width),
        rx.select.content(
            all_item,
            rx.foreach(
                LocationSelectState.locations,
                lambda location: rx.select.item(
                    location.label,
                    value=location.value,
                ),
            ),
        ),
        name=name,
        disabled=disabled,
        on_mount=LocationSelectState.ensure_loaded,
        **kwargs,
    )
