import reflex as rx
from gws_reflex_main.gws_components import select_component

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

    Searchable single-select dropdown (type to filter) built on the shared
    ``select_component``. It uses LocationSelectState to load locations from the
    database; the locations are loaded when the component mounts.

    Args:
        placeholder: Placeholder text for the select
        name: Name attribute for the select element
        disabled: Whether the select is disabled
        width: Width of the select component
        all_option: Optional tuple of (label, value) for an "All" option at the top
        **kwargs: Additional props to pass to the underlying select component
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
    data = LocationSelectState.locations
    if all_option:
        data = (
            rx.Var.create([{"value": all_option[1], "label": all_option[0]}])
            + LocationSelectState.locations
        )

    return select_component(
        data=data,
        placeholder=placeholder,
        searchable=True,
        clearable=True,
        name=name,
        disabled=disabled,
        width=width,
        on_mount=LocationSelectState.ensure_loaded,
        **kwargs,
    )
