from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from gws_core import BadRequestException

from gws_eln.core.unit_type import UnitType


class UnitConverter:
    """
    Unit conversion utilities for gws_eln.

    This module provides a UnitConverter class for converting quantities between
    user-friendly units and base storage units. All quantities are stored in base
    units (L, g, m, units) with DECIMAL(20,12) precision.

    Base units:
    - Volume: L (liters)
    - Mass: g (grams)
    - Length: m (meters)
    - Count: units (discrete count)

    Supported user units:
    - Volume: L, mL, µL (uL)
    - Mass: kg, g, mg, µg (ug)
    - Length: m, cm, mm
    - Count: units
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
            "kg": Decimal("1000"),
            "g": Decimal("1"),
            "mg": Decimal("0.001"),
            "µg": Decimal("0.000001"),
            "ug": Decimal("0.000001"),  # Alternative notation for µg
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
        UnitType.MASS: "g",
        UnitType.LENGTH: "m",
        UnitType.COUNT: "units",
    }

    # All valid units by type
    VALID_UNITS: dict[UnitType, set[str]] = {
        unit_type: set(factors.keys()) for unit_type, factors in CONVERSION_FACTORS.items()
    }

    # User-friendly labels for units
    UNIT_LABELS: dict[str, str] = {
        "L": "L (liters)",
        "mL": "mL (milliliters)",
        "µL": "µL (microliters)",
        "uL": "µL (microliters)",
        "kg": "kg (kilograms)",
        "g": "g (grams)",
        "mg": "mg (milligrams)",
        "µg": "µg (micrograms)",
        "ug": "µg (micrograms)",
        "m": "m (meters)",
        "cm": "cm (centimeters)",
        "mm": "mm (millimeters)",
        "units": "units",
    }

    # Default units to preselect for each unit type
    DEFAULT_UNITS: dict[UnitType, str] = {
        UnitType.VOLUME: "mL",
        UnitType.MASS: "g",
        UnitType.LENGTH: "cm",
        UnitType.COUNT: "units",
    }

    # Display order of units for each type (excluding aliases)
    UNIT_ORDER: dict[UnitType, list[str]] = {
        UnitType.VOLUME: ["L", "mL", "µL"],
        UnitType.MASS: ["kg", "g", "mg", "µg"],
        UnitType.LENGTH: ["m", "cm", "mm"],
        UnitType.COUNT: ["units"],
    }

    @staticmethod
    def to_base_unit(
        value: Decimal | float | int | str, from_unit: str, unit_type: UnitType
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
            >>> UnitConverter.to_base_unit(500, 'mg', UnitType.MASS)
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
                f"Invalid unit '{from_unit}' for {unit_type.value}. Valid units: {valid_units}"
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
        value: Decimal | float | int | str, to_unit: str, unit_type: UnitType
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
            >>> UnitConverter.from_base_unit(Decimal('500'), 'mg', UnitType.MASS)
            Decimal('500000.000000000000')
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
                f"Invalid unit '{to_unit}' for {unit_type.value}. Valid units: {valid_units}"
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
        :return: The base unit symbol (e.g., 'L', 'g', 'm', 'units')
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
    def get_unit_label(unit: str) -> str:
        """
        Get the user-friendly label for a unit.

        :param unit: The unit symbol (e.g., 'mL', 'g', 'cm')
        :type unit: str
        :return: The user-friendly label (e.g., 'mL (milliliters)')
        :rtype: str
        """
        return UnitConverter.UNIT_LABELS.get(unit, unit)

    @staticmethod
    def get_default_unit(unit_type: UnitType) -> str:
        """
        Get the default unit for a unit type.

        :param unit_type: The type of unit (VOLUME, MASS, LENGTH, COUNT)
        :type unit_type: UnitType
        :return: The default unit symbol (e.g., 'mL' for VOLUME)
        :rtype: str
        :raises BadRequestException: If unit type is invalid
        """
        if not isinstance(unit_type, UnitType):
            raise BadRequestException(f"Invalid unit type: {unit_type}")

        return UnitConverter.DEFAULT_UNITS[unit_type]

    @staticmethod
    def get_units_for_select(unit_type: UnitType) -> list[tuple[str, str]]:
        """
        Get units for a select dropdown, with labels, in display order.

        Returns units in a logical order (largest to smallest) without aliases.

        :param unit_type: The type of unit (VOLUME, MASS, LENGTH, COUNT)
        :type unit_type: UnitType
        :return: List of tuples (unit_symbol, label) in display order
        :rtype: list[tuple[str, str]]
        :raises BadRequestException: If unit type is invalid

        Examples:
            >>> UnitConverter.get_units_for_select(UnitType.VOLUME)
            [('L', 'L (liters)'), ('mL', 'mL (milliliters)'), ('µL', 'µL (microliters)')]
        """
        if not isinstance(unit_type, UnitType):
            raise BadRequestException(f"Invalid unit type: {unit_type}")

        units = UnitConverter.UNIT_ORDER[unit_type]
        return [(unit, UnitConverter.UNIT_LABELS.get(unit, unit)) for unit in units]

    @staticmethod
    def convert_unit(
        value: Decimal | float | int | str, from_unit: str, to_unit: str, unit_type: UnitType
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

    @staticmethod
    def format_value(
        value: Decimal | float | int | str, unit_type: UnitType, unit: str | None = None
    ) -> str:
        """
        Format a value with its unit for human-readable display.

        Automatically selects the most appropriate unit for readability if no unit
        is specified. Removes trailing zeros for cleaner output.

        :param value: The quantity value (in base units if unit is None)
        :type value: Union[Decimal, float, int, str]
        :param unit_type: The type of unit (VOLUME, MASS, LENGTH, COUNT)
        :type unit_type: UnitType
        :param unit: Optional unit to display. If None, auto-selects the best unit.
        :type unit: Optional[str]
        :return: Formatted string with value and unit (e.g., "1.5 kg", "250 mL")
        :rtype: str
        :raises BadRequestException: If unit type or unit is invalid

        Examples:
            >>> UnitConverter.format_value(1500, UnitType.MASS)
            '1.5 kg'
            >>> UnitConverter.format_value(0.5, UnitType.VOLUME)
            '500 mL'
            >>> UnitConverter.format_value(1500, UnitType.MASS, 'g')
            '1500 g'
        """
        if not isinstance(unit_type, UnitType):
            raise BadRequestException(f"Invalid unit type: {unit_type}")

        try:
            decimal_value = Decimal(str(value))
        except (InvalidOperation, ValueError) as e:
            raise BadRequestException(f"Invalid numeric value: {value}") from e

        if unit is not None:
            if unit not in UnitConverter.CONVERSION_FACTORS[unit_type]:
                valid_units = ", ".join(sorted(UnitConverter.VALID_UNITS[unit_type]))
                raise BadRequestException(
                    f"Invalid unit '{unit}' for {unit_type.value}. Valid units: {valid_units}"
                )
            display_value = UnitConverter.from_base_unit(decimal_value, unit, unit_type)
            display_unit = unit
        else:
            display_unit, display_value = UnitConverter._select_best_unit(decimal_value, unit_type)

        formatted_value = UnitConverter.format_number(display_value)
        return f"{formatted_value} {display_unit}"

    @staticmethod
    def _select_best_unit(value: Decimal, unit_type: UnitType) -> tuple[str, Decimal]:
        """
        Select the most appropriate unit for a given value.

        Chooses the unit that results in a value between 1 and 1000 when possible.
        """
        unit_order: dict[UnitType, list[str]] = {
            UnitType.VOLUME: ["L", "mL", "µL"],
            UnitType.MASS: ["kg", "g", "mg", "µg"],
            UnitType.LENGTH: ["m", "cm", "mm"],
            UnitType.COUNT: ["units"],
        }

        units = unit_order[unit_type]

        for unit in units:
            converted = UnitConverter.from_base_unit(value, unit, unit_type)
            abs_converted = abs(converted)
            if Decimal("1") <= abs_converted < Decimal("1000") or unit == units[-1]:
                return unit, converted

        base_unit = UnitConverter.BASE_UNITS[unit_type]
        return base_unit, value

    @staticmethod
    def format_number(value: Decimal) -> str:
        """
        Format a Decimal number for display, removing unnecessary trailing zeros.
        """
        normalized = value.normalize()
        if normalized == normalized.to_integral_value():
            return str(int(normalized))
        return str(normalized)
