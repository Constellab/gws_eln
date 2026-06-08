import reflex as rx

from .item_status_select_state import ItemStatusSelectState


def item_status_select_component(
    placeholder: str = "Select status...",
    name: str | None = None,
    disabled: bool = False,
    width: str = "100%",
    all_option: tuple[str, str] | None = None,
    **kwargs,
) -> rx.Component:
    """
    Reusable item status select component.

    This component uses ItemStatusSelectState to provide item status options.

    Args:
        placeholder: Placeholder text for the select
        name: Name attribute for the select element
        disabled: Whether the select is disabled
        width: Width of the select component
        all_option: Optional tuple of (label, value) for an "All" option at the top
        **kwargs: Additional props to pass to the select.root component
                 (e.g., on_change, value, default_value)

    Returns:
        A reflex component for item status selection

    Example:
        # With state binding for forms
        item_status_select_component(
            name="status",
            value=MyFormState.status,
            on_change=MyFormState.set_status,
            width="100%"
        )

        # With "All" option for filters
        item_status_select_component(
            all_option=("All statuses", "all"),
            value=FilterState.status,
            on_change=FilterState.set_status,
        )
    """
    all_item = rx.select.item(all_option[0], value=all_option[1]) if all_option else rx.fragment()

    return rx.select.root(
        rx.select.trigger(placeholder=placeholder, width=width),
        rx.select.content(
            all_item,
            rx.foreach(
                ItemStatusSelectState.statuses,
                lambda status: rx.select.item(
                    status.label,
                    value=status.value,
                ),
            ),
        ),
        name=name,
        disabled=disabled,
        **kwargs,
    )
