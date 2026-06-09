"""Concentration units for items.

Concentration units are a flat, recordable list of strings. Unlike quantity units,
concentration units are NOT convertable: the chosen unit is stored on the item and displayed
as is.

Interconversion between concentration units (e.g. mM <-> µM, or molar <-> mass/volume)
is intentionally out of scope, as it would require the molecular weight of the species.
"""

# Recordable concentration units, in display order.
CONCENTRATION_UNITS: list[str] = [
    "M",
    "mM",
    "µM",
    "nM",
    "ng/µL",
    "µg/mL",
    "mg/mL",
    "g/L",
    "U/µL",
    "U/mL",
    "cells/mL",
    "copies/µL",
]


def is_valid_concentration_unit(unit: str) -> bool:
    """Check if a string is a valid concentration unit.

    :param unit: The concentration unit symbol to check
    :type unit: str
    :return: True if the unit is in the recordable list
    :rtype: bool
    """
    return unit in CONCENTRATION_UNITS
