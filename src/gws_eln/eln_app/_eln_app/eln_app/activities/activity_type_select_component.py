import reflex as rx
from gws_eln.activities.activity_type import ActivityType
from gws_reflex_main.gws_components import select_component

ACTIVITY_TYPE_OPTIONS = [
    (ActivityType.RECEIVE.value, "Receive"),
    (ActivityType.CONSUME.value, "Consume"),
    (ActivityType.USE.value, "Use"),
    (ActivityType.MOVE.value, "Move"),
    (ActivityType.RELABEL.value, "Relabel"),
    (ActivityType.DISCARD.value, "Discard"),
    (ActivityType.SPLIT.value, "Split"),
    (ActivityType.COMBINE.value, "Combine"),
    (ActivityType.DILUTE.value, "Dilute"),
    (ActivityType.CONCENTRATE.value, "Concentrate"),
    (ActivityType.TRANSFORM.value, "Transform"),
]

_ACTIVITY_TYPE_DATA = [{"value": value, "label": label} for value, label in ACTIVITY_TYPE_OPTIONS]


def activity_type_select_component(
    placeholder: str = "Select an activity type...",
    name: str | None = None,
    disabled: bool = False,
    width: str = "100%",
    all_option: tuple[str, str] | None = None,
    **kwargs,
) -> rx.Component:
    """
    Reusable activity type select component.

    This component renders a select dropdown with all ActivityType enum values.

    Args:
        placeholder: Placeholder text for the select
        name: Name attribute for the select element
        disabled: Whether the select is disabled
        width: Width of the select component
        all_option: Optional tuple of (label, value) for an "All" option at the top
        **kwargs: Additional props to pass to the select.root component
                 (e.g., on_change, value, default_value)

    Returns:
        A reflex component for activity type selection

    Example:
        # With state binding for forms
        activity_type_select_component(
            name="activity_type",
            value=MyFormState.activity_type,
            on_change=MyFormState.set_activity_type,
            width="100%"
        )

        # With "All" option for filters
        activity_type_select_component(
            all_option=("All types", "all"),
            value=FilterState.activity_type,
            on_change=FilterState.set_activity_type,
        )
    """
    data = _ACTIVITY_TYPE_DATA
    if all_option:
        data = [{"value": all_option[1], "label": all_option[0]}, *_ACTIVITY_TYPE_DATA]

    return select_component(
        data=data,
        placeholder=placeholder,
        name=name,
        disabled=disabled,
        width=width,
        **kwargs,
    )
