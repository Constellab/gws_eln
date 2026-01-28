import reflex as rx

from .material_select_state import MaterialSelectState


def material_select_component(
    placeholder: str = "Select a material...",
    name: str | None = None,
    disabled: bool = False,
    width: str = "100%",
    all_option: tuple[str, str] | None = None,
    **kwargs,
) -> rx.Component:
    """
    Reusable material select component.

    This component uses MaterialSelectState to load materials from the database.
    The materials are loaded when the component mounts via on_load.

    Args:
        placeholder: Placeholder text for the select
        name: Name attribute for the select element
        disabled: Whether the select is disabled
        width: Width of the select component
        all_option: Optional tuple of (label, value) for an "All" option at the top
        **kwargs: Additional props to pass to the select.root component
                 (e.g., on_change, value, default_value)

    Returns:
        A reflex component for material selection

    Example:
        # With state binding for forms
        material_select_component(
            name="material_id",
            value=MyFormState.material_id,
            on_change=MyFormState.set_material_id,
            width="100%"
        )

        # With "All" option for filters
        material_select_component(
            all_option=("All materials", "all"),
            value=FilterState.material_id,
            on_change=FilterState.set_material_id,
        )
    """
    all_item = rx.select.item(all_option[0], value=all_option[1]) if all_option else rx.fragment()

    return rx.select.root(
        rx.select.trigger(placeholder=placeholder, width=width),
        rx.select.content(
            all_item,
            rx.foreach(
                MaterialSelectState.materials,
                lambda material: rx.select.item(
                    material.label,
                    value=material.value,
                ),
            ),
        ),
        name=name,
        disabled=disabled,
        **kwargs,
    )
