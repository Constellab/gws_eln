"""Concentration units for items.

Concentration units are grouped into **families** (molar, mass/volume,
activity/volume, …). Within a family the units convert losslessly (e.g.
``mM`` <-> ``µM``, ``mg/mL`` <-> ``µg/mL``). Across families there is **no**
conversion: molar <-> mass/volume needs the molecular weight, and entity-based
families (cells vs copies) are not interconvertible.

The chosen unit is stored as is on the item; conversion is only used to
compare two concentrations expressed in different units of the same family.
"""

from decimal import Decimal
from enum import Enum

from gws_core import BadRequestException


class ConcentrationUnitFamily(Enum):
    """A group of concentration units that convert losslessly within the group."""

    MOLAR = "molar"
    MASS_VOLUME = "mass_volume"
    ACTIVITY_VOLUME = "activity_volume"
    CELLS_VOLUME = "cells_volume"
    COPIES_VOLUME = "copies_volume"


# Human-readable family labels (e.g. for grouping the unit dropdown).
CONCENTRATION_FAMILY_LABELS: dict[ConcentrationUnitFamily, str] = {
    ConcentrationUnitFamily.MOLAR: "Molar",
    ConcentrationUnitFamily.MASS_VOLUME: "Mass / volume",
    ConcentrationUnitFamily.ACTIVITY_VOLUME: "Activity / volume",
    ConcentrationUnitFamily.CELLS_VOLUME: "Cells / volume",
    ConcentrationUnitFamily.COPIES_VOLUME: "Copies / volume",
}

# Conversion factors to each family's base unit: 1 unit = factor * base_unit.
# Only ratios within a family matter (the base choice is arbitrary). Insertion
# order is the display order.
CONCENTRATION_CONVERSION_FACTORS: dict[ConcentrationUnitFamily, dict[str, Decimal]] = {
    # base: M
    ConcentrationUnitFamily.MOLAR: {
        "M": Decimal("1"),
        "mM": Decimal("1E-3"),
        "µM": Decimal("1E-6"),
        "nM": Decimal("1E-9"),
    },
    # base: g/L  (1 mg/mL = 1 g/L ; 1 µg/mL = 1 ng/µL = 1E-3 g/L)
    ConcentrationUnitFamily.MASS_VOLUME: {
        "g/L": Decimal("1"),
        "mg/mL": Decimal("1"),
        "µg/mL": Decimal("1E-3"),
        "ng/µL": Decimal("1E-3"),
    },
    # base: U/mL  (1 U/µL = 1E3 U/mL)
    ConcentrationUnitFamily.ACTIVITY_VOLUME: {
        "U/mL": Decimal("1"),
        "U/µL": Decimal("1000"),
    },
    ConcentrationUnitFamily.CELLS_VOLUME: {
        "cells/mL": Decimal("1"),
    },
    ConcentrationUnitFamily.COPIES_VOLUME: {
        "copies/µL": Decimal("1"),
    },
}

# Flat recordable list, in family + display order (public, unchanged contents).
CONCENTRATION_UNITS: list[str] = [
    unit
    for factors in CONCENTRATION_CONVERSION_FACTORS.values()
    for unit in factors
]

# unit -> family lookup
_UNIT_TO_FAMILY: dict[str, ConcentrationUnitFamily] = {
    unit: family
    for family, factors in CONCENTRATION_CONVERSION_FACTORS.items()
    for unit in factors
}


def is_valid_concentration_unit(unit: str) -> bool:
    """Check if a string is a valid (recordable) concentration unit.

    :param unit: The concentration unit symbol to check
    :type unit: str
    :return: True if the unit is known
    :rtype: bool
    """
    return unit in _UNIT_TO_FAMILY


def get_concentration_unit_family(unit: str) -> ConcentrationUnitFamily | None:
    """Return the family a concentration unit belongs to (None if unknown)."""
    return _UNIT_TO_FAMILY.get(unit)


def same_concentration_family(unit_a: str, unit_b: str) -> bool:
    """Whether two concentration units belong to the same (known) family."""
    family_a = _UNIT_TO_FAMILY.get(unit_a)
    family_b = _UNIT_TO_FAMILY.get(unit_b)
    return family_a is not None and family_a == family_b


def convert_concentration(
    value: Decimal | float | int | str, from_unit: str, to_unit: str
) -> Decimal:
    """Convert a concentration value between two units of the same family.

    :param value: The concentration value to convert
    :param from_unit: The source concentration unit (e.g. ``"mM"``)
    :param to_unit: The target concentration unit (e.g. ``"µM"``)
    :return: The value expressed in ``to_unit``
    :rtype: Decimal
    :raises BadRequestException: if either unit is unknown, or they belong to
        different families (no cross-family conversion).
    """
    family_from = _UNIT_TO_FAMILY.get(from_unit)
    family_to = _UNIT_TO_FAMILY.get(to_unit)
    if family_from is None:
        raise BadRequestException(f"Unknown concentration unit '{from_unit}'")
    if family_to is None:
        raise BadRequestException(f"Unknown concentration unit '{to_unit}'")
    if family_from != family_to:
        raise BadRequestException(
            f"Cannot convert '{from_unit}' to '{to_unit}': different concentration "
            "families (no cross-family conversion)"
        )

    factor_from = CONCENTRATION_CONVERSION_FACTORS[family_from][from_unit]
    factor_to = CONCENTRATION_CONVERSION_FACTORS[family_to][to_unit]
    return Decimal(str(value)) * factor_from / factor_to


def get_concentration_units_by_family() -> list[tuple[str, list[str]]]:
    """Return ``(family_label, [units…])`` pairs in display order (for grouping)."""
    return [
        (CONCENTRATION_FAMILY_LABELS[family], list(factors.keys()))
        for family, factors in CONCENTRATION_CONVERSION_FACTORS.items()
    ]
