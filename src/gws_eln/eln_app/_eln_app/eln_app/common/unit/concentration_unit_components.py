import reflex as rx
from gws_eln.core.concentration_unit import CONCENTRATION_UNITS

# Sentinel value for the "no concentration unit" option. rx.select cannot use an
# empty/None value, so this string represents "no selection".
NO_CONCENTRATION_VALUE = "__none__"


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
    none_item = rx.select.item("No concentration", value=NO_CONCENTRATION_VALUE)

    return rx.select.root(
        rx.select.trigger(placeholder=placeholder, width=width),
        rx.select.content(
            none_item,
            *[rx.select.item(unit, value=unit) for unit in CONCENTRATION_UNITS],
        ),
        name=name,
        disabled=disabled,
        width=width,
        **kwargs,
    )
