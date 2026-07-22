import reflex as rx
from gws_eln.core.concentration_unit import CONCENTRATION_UNITS
from gws_reflex_main.gws_components import select_component

# Sentinel value for the "no concentration unit" option. rx.select cannot use an
# empty/None value, so this string represents "no selection".
NO_CONCENTRATION_VALUE = "__none__"

_CONCENTRATION_UNIT_DATA = [
    {"value": NO_CONCENTRATION_VALUE, "label": "No concentration"},
    *[{"value": unit, "label": unit} for unit in CONCENTRATION_UNITS],
]


def concentration_unit_select(
    placeholder: str = "Select concentration unit (optional)",
    name: str | None = None,
    disabled: bool = False,
    width: str = "100%",
    **kwargs,
) -> rx.Component:
    """Reusable concentration unit select component.

    Concentration units are a flat, recordable list (see
    :mod:`gws_eln.core.concentration_unit`).

    :param placeholder: Placeholder text shown when nothing is selected
    :param name: Name attribute for the select element
    :param disabled: Whether the select is disabled
    :param width: Width of the select component
    :param kwargs: Additional props passed to select.root (e.g. value, on_change)
    :return: A reflex component for concentration unit selection
    """
    return select_component(
        data=_CONCENTRATION_UNIT_DATA,
        placeholder=placeholder,
        name=name,
        disabled=disabled,
        width=width,
        **kwargs,
    )
