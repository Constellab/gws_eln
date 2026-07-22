import reflex as rx
from gws_eln.core.concentration_method import (
    CONCENTRATION_METHOD_LABELS,
    ConcentrationMethod,
)
from gws_reflex_main.gws_components import select_component

# Sentinel value for the "no method" option. rx.select cannot use an empty/None
# value, so this string represents "no selection".
NO_CONCENTRATION_METHOD_VALUE = "__none__"

_CONCENTRATION_METHOD_DATA = [
    {"value": NO_CONCENTRATION_METHOD_VALUE, "label": "No method"},
    *[
        {"value": method.value, "label": CONCENTRATION_METHOD_LABELS[method]}
        for method in ConcentrationMethod
    ],
]


def concentration_method_select(
    placeholder: str = "Select concentration method (optional)",
    name: str | None = None,
    width: str = "100%",
    **kwargs,
) -> rx.Component:
    """Reusable concentration method select component (concentrate audit).

    Methods come from :class:`gws_eln.core.concentration_method.ConcentrationMethod`.

    :param placeholder: Placeholder text shown when nothing is selected
    :param name: Name attribute for the select element
    :param width: Width of the select component
    :param kwargs: Additional props passed to select.root (e.g. value, on_change)
    :return: A reflex component for concentration method selection
    """
    return select_component(
        data=_CONCENTRATION_METHOD_DATA,
        placeholder=placeholder,
        name=name,
        width=width,
        **kwargs,
    )
