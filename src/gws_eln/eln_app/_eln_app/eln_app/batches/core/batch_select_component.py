import reflex as rx

from .batch_select_state import BatchSelectState


def batch_select_component(
    placeholder: str = "Select a batch...",
    name: str | None = None,
    disabled: bool = False,
    width: str = "100%",
    all_option: tuple[str, str] | None = None,
    **kwargs,
) -> rx.Component:
    """
    Reusable material batch select component.

    This component uses BatchSelectState to load batches from the database.
    The batches are loaded when the component mounts via on_load.

    Args:
        placeholder: Placeholder text for the select
        name: Name attribute for the select element
        disabled: Whether the select is disabled
        width: Width of the select component
        all_option: Optional tuple of (label, value) for an "All" option at the top
        **kwargs: Additional props to pass to the select.root component
                 (e.g., on_change, value, default_value)

    Returns:
        A reflex component for material batch selection

    Example:
        # With state binding for forms
        batch_select_component(
            name="batch_id",
            value=MyFormState.batch_id,
            on_change=MyFormState.set_batch_id,
            width="100%"
        )

        # With "All" option for filters
        batch_select_component(
            all_option=("All batches", "all"),
            value=FilterState.batch_id,
            on_change=FilterState.set_batch_id,
        )
    """
    all_item = rx.select.item(all_option[0], value=all_option[1]) if all_option else rx.fragment()

    return rx.select.root(
        rx.select.trigger(placeholder=placeholder, width=width),
        rx.select.content(
            all_item,
            rx.foreach(
                BatchSelectState.batches,
                lambda batch: rx.select.item(
                    batch.label,
                    value=batch.value,
                ),
            ),
        ),
        name=name,
        disabled=disabled,
        **kwargs,
    )
