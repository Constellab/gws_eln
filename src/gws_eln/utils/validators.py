"""
Validation utilities for gws_eln.

This module provides a QuantityValidator class for validating quantities, units,
and batch operations before they are processed or saved to the database.

Validators ensure:
- Quantities are positive numbers
- Units match their unit types
- Operations won't create negative stock
"""

from decimal import Decimal, InvalidOperation

from gws_core import BadRequestException

from gws_eln.core.unit_type import UnitType
from gws_eln.materials.material_batch import MaterialBatch
from gws_eln.utils.units import UnitConverter


class QuantityValidator:
    """
    Static class for validating quantities, units, and batch operations.

    Provides early error detection with clear error messages to prevent
    invalid data from corrupting the system.
    """

    @staticmethod
    def validate_quantity(value: Decimal | float | int | str) -> Decimal:
        """
        Validate that quantity is a positive number.

        :param value: The quantity to validate
        :type value: Union[Decimal, float, int, str]
        :return: Validated quantity as Decimal with proper precision
        :rtype: Decimal
        :raises BadRequestException: If quantity is invalid (negative, zero, or not a number)

        Examples:
            >>> QuantityValidator.validate_quantity(10.5)
            Decimal('10.5')
            >>> QuantityValidator.validate_quantity("100")
            Decimal('100')
            >>> QuantityValidator.validate_quantity(-5)  # Raises BadRequestException
            >>> QuantityValidator.validate_quantity(0)  # Raises BadRequestException
        """
        # Convert to Decimal
        try:
            quantity = Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError) as e:
            raise BadRequestException(f"Invalid quantity: '{value}' must be a valid number") from e

        # Check if positive
        if quantity <= 0:
            raise BadRequestException(f"Quantity must be positive, got: {quantity}")

        return quantity

    @staticmethod
    def validate_unit(unit: str, unit_type: UnitType) -> None:
        """
        Validate that a unit matches its unit type.

        :param unit: The specific unit (e.g., 'mL', 'g', 'cm', 'units')
        :type unit: str
        :param unit_type: The type of unit (VOLUME, MASS, LENGTH, COUNT)
        :type unit_type: UnitType
        :raises BadRequestException: If unit doesn't match unit_type

        Examples:
            >>> QuantityValidator.validate_unit('mL', UnitType.VOLUME)  # OK
            >>> QuantityValidator.validate_unit('g', UnitType.MASS)  # OK
            >>> QuantityValidator.validate_unit('g', UnitType.VOLUME)  # Raises BadRequestException
        """
        if not isinstance(unit_type, UnitType):
            raise BadRequestException(
                f"Invalid unit_type: '{unit_type}'. Must be a UnitType enum value"
            )

        if not UnitConverter.is_valid_unit(unit, unit_type):
            valid_units = UnitConverter.get_valid_units(unit_type)
            raise BadRequestException(
                f"Unit '{unit}' is not valid for unit_type '{unit_type.value}'. "
                f"Valid units: {', '.join(valid_units)}"
            )

    @staticmethod
    def validate_batch_operation(batch: MaterialBatch, quantity: Decimal, operation: str) -> None:
        """
        Validate that an operation won't result in negative stock.

        This validator checks:
        1. For decrement/consume/aliquot operations: batch has sufficient quantity
        2. For decrement/consume operations: batch material is consumable

        :param batch: The batch object to operate on (must have quantity and material attributes)
        :type batch: Any
        :param quantity: The quantity for the operation (in base units)
        :type quantity: Decimal
        :param operation: The operation type ('decrement', 'consume', 'aliquot', etc.)
        :type operation: str
        :raises BadRequestException: If operation would create negative stock or violate constraints

        Examples:
            >>> # Batch with 100 units, consumable
            >>> QuantityValidator.validate_batch_operation(batch, Decimal('50'), 'decrement')  # OK
            >>> QuantityValidator.validate_batch_operation(batch, Decimal('150'), 'decrement')  # Raises
            >>> # Non-consumable batch
            >>> QuantityValidator.validate_batch_operation(batch, Decimal('10'), 'decrement')  # Raises
        """
        # Operations that require quantity checks
        quantity_check_operations = ["decrement", "consume", "aliquot"]

        # Operations that require consumable check
        consumable_operations = ["decrement", "consume"]

        # Validate batch has required attributes
        if not hasattr(batch, "quantity"):
            raise BadRequestException("Batch object must have 'quantity' attribute")

        if operation in consumable_operations and not hasattr(batch, "material"):
            raise BadRequestException("Batch object must have 'material' attribute")

        # Check if batch has enough quantity
        if operation in quantity_check_operations and batch.quantity < quantity:
            raise BadRequestException(
                f"Insufficient quantity in batch {getattr(batch, 'id', 'unknown')}. "
                f"Available: {batch.quantity}, Required: {quantity}"
            )

        # Check that batch material is consumable for certain operations
        if operation in consumable_operations and not batch.is_consumable():
            raise BadRequestException(
                f"Cannot {operation} non-consumable material: '{batch.material.name}'"
            )

    @staticmethod
    def validate_non_negative_result(
        current_quantity: Decimal, quantity_change: Decimal, operation: str
    ) -> None:
        """
        Validate that an operation won't result in a negative quantity.

        This is a simpler validator for when you don't have the full batch object
        but want to ensure quantity calculations remain valid.

        :param current_quantity: The current quantity before the operation
        :type current_quantity: Decimal
        :param quantity_change: The quantity to add (positive) or subtract (negative)
        :type quantity_change: Decimal
        :param operation: Description of the operation for error messages
        :type operation: str
        :raises BadRequestException: If result would be negative

        Examples:
            >>> QuantityValidator.validate_non_negative_result(
            ...     Decimal('100'), Decimal('-50'), 'decrement'
            ... )  # OK, result is 50
            >>> QuantityValidator.validate_non_negative_result(
            ...     Decimal('100'), Decimal('-150'), 'decrement'
            ... )  # Raises, result would be -50
        """
        result = current_quantity + quantity_change

        if result < 0:
            raise BadRequestException(
                f"Operation '{operation}' would result in negative quantity. "
                f"Current: {current_quantity}, Change: {quantity_change}, "
                f"Result: {result}"
            )
