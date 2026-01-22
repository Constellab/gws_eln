"""
Unit conversion utilities for gws_eln.

This module provides a UnitConverter class for converting quantities between
user-friendly units and base storage units. All quantities are stored in base
units (L, kg, m, units) with DECIMAL(20,12) precision.

Base units:
- Volume: L (liters)
- Mass: kg (kilograms)
- Length: m (meters)
- Count: units (discrete count)

Supported user units:
- Volume: L, mL, µL (uL)
- Mass: kg, g, mg, µg (ug)
- Length: m, cm, mm
- Count: units
"""

from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Union

from gws_core import BadRequestException

from gws_eln.core.unit_type import UnitType


class UnitConverter:
    """
    Static class for unit conversion operations.

    Provides methods to convert between user-friendly units and base storage units.
    All quantities are stored in base units (L, kg, m, units) with DECIMAL(20,12) precision.
    """

    # Conversion factors to base units
    # Each factor represents: 1 user_unit = factor * base_unit
    CONVERSION_FACTORS: dict[UnitType, dict[str, Decimal]] = {
        UnitType.VOLUME: {
            "L": Decimal("1"),
            "mL": Decimal("0.001"),
            "µL": Decimal("0.000001"),
            "uL": Decimal("0.000001"),  # Alternative notation for µL
        },
        UnitType.MASS: {
            "kg": Decimal("1"),
            "g": Decimal("0.001"),
            "mg": Decimal("0.000001"),
            "µg": Decimal("0.000000001"),
            "ug": Decimal("0.000000001"),  # Alternative notation for µg
        },
        UnitType.LENGTH: {
            "m": Decimal("1"),
            "cm": Decimal("0.01"),
            "mm": Decimal("0.001"),
        },
        UnitType.COUNT: {
            "units": Decimal("1"),
        },
    }

    # Map from unit type to base unit symbol
    BASE_UNITS: dict[UnitType, str] = {
        UnitType.VOLUME: "L",
        UnitType.MASS: "kg",
        UnitType.LENGTH: "m",
        UnitType.COUNT: "units",
    }

    # All valid units by type
    VALID_UNITS: dict[UnitType, set[str]] = {
        unit_type: set(factors.keys())
        for unit_type, factors in CONVERSION_FACTORS.items()
    }

    @staticmethod
    def to_base_unit(
        value: Union[Decimal, float, int, str],
        from_unit: str,
        unit_type: UnitType
    ) -> Decimal:
        """
        Convert a value from a user-friendly unit to the base unit for storage.

        :param value: The quantity value to convert
        :type value: Union[Decimal, float, int, str]
        :param from_unit: The source unit (e.g., 'mL', 'g', 'cm')
        :type from_unit: str
        :param unit_type: The type of unit (VOLUME, MASS, LENGTH, COUNT)
        :type unit_type: UnitType
        :return: Value in base units with DECIMAL(20,12) precision
        :rtype: Decimal
        :raises BadRequestException: If unit is invalid or value cannot be converted

        Examples:
            >>> UnitConverter.to_base_unit(1, 'mL', UnitType.VOLUME)
            Decimal('0.001000000000')
            >>> UnitConverter.to_base_unit(500, 'g', UnitType.MASS)
            Decimal('0.500000000000')
            >>> UnitConverter.to_base_unit(10, 'cm', UnitType.LENGTH)
            Decimal('0.100000000000')
        """
        # Validate unit type
        if not isinstance(unit_type, UnitType):
            raise BadRequestException(f"Invalid unit type: {unit_type}")

        # Validate unit is valid for this type
        if from_unit not in UnitConverter.CONVERSION_FACTORS[unit_type]:
            valid_units = ", ".join(sorted(UnitConverter.VALID_UNITS[unit_type]))
            raise BadRequestException(
                f"Invalid unit '{from_unit}' for {unit_type.value}. "
                f"Valid units: {valid_units}"
            )

        # Convert value to Decimal
        try:
            decimal_value = Decimal(str(value))
        except (InvalidOperation, ValueError) as e:
            raise BadRequestException(f"Invalid numeric value: {value}") from e

        # Get conversion factor and calculate base value
        factor = UnitConverter.CONVERSION_FACTORS[unit_type][from_unit]
        base_value = decimal_value * factor

        # Round to 12 decimal places for DECIMAL(20,12) precision
        return base_value.quantize(Decimal("0.000000000001"), rounding=ROUND_HALF_UP)

    @staticmethod
    def from_base_unit(
        value: Union[Decimal, float, int, str],
        to_unit: str,
        unit_type: UnitType
    ) -> Decimal:
        """
        Convert a value from the base unit to a user-friendly unit for display.

        :param value: The quantity value in base units
        :type value: Union[Decimal, float, int, str]
        :param to_unit: The target unit (e.g., 'mL', 'g', 'cm')
        :type to_unit: str
        :param unit_type: The type of unit (VOLUME, MASS, LENGTH, COUNT)
        :type unit_type: UnitType
        :return: Value in the target unit with appropriate precision
        :rtype: Decimal
        :raises BadRequestException: If unit is invalid or value cannot be converted

        Examples:
            >>> UnitConverter.from_base_unit(Decimal('0.001'), 'mL', UnitType.VOLUME)
            Decimal('1.000000000000')
            >>> UnitConverter.from_base_unit(Decimal('0.5'), 'g', UnitType.MASS)
            Decimal('500.000000000000')
            >>> UnitConverter.from_base_unit(Decimal('0.1'), 'cm', UnitType.LENGTH)
            Decimal('10.000000000000')
        """
        # Validate unit type
        if not isinstance(unit_type, UnitType):
            raise BadRequestException(f"Invalid unit type: {unit_type}")

        # Validate unit is valid for this type
        if to_unit not in UnitConverter.CONVERSION_FACTORS[unit_type]:
            valid_units = ", ".join(sorted(UnitConverter.VALID_UNITS[unit_type]))
            raise BadRequestException(
                f"Invalid unit '{to_unit}' for {unit_type.value}. "
                f"Valid units: {valid_units}"
            )

        # Convert value to Decimal
        try:
            decimal_value = Decimal(str(value))
        except (InvalidOperation, ValueError) as e:
            raise BadRequestException(f"Invalid numeric value: {value}") from e

        # Get conversion factor and calculate user value (divide by factor)
        factor = UnitConverter.CONVERSION_FACTORS[unit_type][to_unit]
        user_value = decimal_value / factor

        # Round to 12 decimal places for consistency
        return user_value.quantize(Decimal("0.000000000001"), rounding=ROUND_HALF_UP)

    @staticmethod
    def get_base_unit(unit_type: UnitType) -> str:
        """
        Get the base unit symbol for a unit type.

        :param unit_type: The type of unit (VOLUME, MASS, LENGTH, COUNT)
        :type unit_type: UnitType
        :return: The base unit symbol (e.g., 'L', 'kg', 'm', 'units')
        :rtype: str
        :raises BadRequestException: If unit type is invalid
        """
        if not isinstance(unit_type, UnitType):
            raise BadRequestException(f"Invalid unit type: {unit_type}")

        return UnitConverter.BASE_UNITS[unit_type]

    @staticmethod
    def get_valid_units(unit_type: UnitType) -> list[str]:
        """
        Get list of valid units for a unit type.

        :param unit_type: The type of unit (VOLUME, MASS, LENGTH, COUNT)
        :type unit_type: UnitType
        :return: List of valid unit symbols
        :rtype: list[str]
        :raises BadRequestException: If unit type is invalid
        """
        if not isinstance(unit_type, UnitType):
            raise BadRequestException(f"Invalid unit type: {unit_type}")

        return sorted(UnitConverter.VALID_UNITS[unit_type])

    @staticmethod
    def is_valid_unit(unit: str, unit_type: UnitType) -> bool:
        """
        Check if a unit is valid for a given unit type.

        :param unit: The unit symbol to check
        :type unit: str
        :param unit_type: The type of unit (VOLUME, MASS, LENGTH, COUNT)
        :type unit_type: UnitType
        :return: True if the unit is valid for the unit type
        :rtype: bool
        """
        if not isinstance(unit_type, UnitType):
            return False

        return unit in UnitConverter.VALID_UNITS[unit_type]

    @staticmethod
    def convert_unit(
        value: Union[Decimal, float, int, str],
        from_unit: str,
        to_unit: str,
        unit_type: UnitType
    ) -> Decimal:
        """
        Convert a value between two units of the same type.

        This is a convenience method that converts from the source unit to base,
        then from base to the target unit.

        :param value: The quantity value to convert
        :type value: Union[Decimal, float, int, str]
        :param from_unit: The source unit (e.g., 'mL')
        :type from_unit: str
        :param to_unit: The target unit (e.g., 'L')
        :type to_unit: str
        :param unit_type: The type of unit (VOLUME, MASS, LENGTH, COUNT)
        :type unit_type: UnitType
        :return: Value in the target unit
        :rtype: Decimal
        :raises BadRequestException: If units are invalid or value cannot be converted

        Examples:
            >>> UnitConverter.convert_unit(1000, 'mL', 'L', UnitType.VOLUME)
            Decimal('1.000000000000')
            >>> UnitConverter.convert_unit(1, 'kg', 'g', UnitType.MASS)
            Decimal('1000.000000000000')
        """
        base_value = UnitConverter.to_base_unit(value, from_unit, unit_type)
        return UnitConverter.from_base_unit(base_value, to_unit, unit_type)
