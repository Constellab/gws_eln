"""
Tests for quantity and unit validators.

Tests Story 2.3: Quantity & Unit Validators
"""

import unittest
from decimal import Decimal

from gws_core import BadRequestException
from gws_eln.core.unit_type import UnitType
from gws_eln.utils.validators import QuantityValidator


class TestValidateQuantity(unittest.TestCase):
    """Tests for QuantityValidator.validate_quantity()"""

    def test_validate_quantity_positive_integer(self):
        """Valid positive integer quantity"""
        result = QuantityValidator.validate_quantity(10)
        self.assertEqual(result, Decimal("10"))
        self.assertIsInstance(result, Decimal)

    def test_validate_quantity_positive_float(self):
        """Valid positive float quantity"""
        result = QuantityValidator.validate_quantity(10.5)
        self.assertEqual(result, Decimal("10.5"))
        self.assertIsInstance(result, Decimal)

    def test_validate_quantity_positive_decimal(self):
        """Valid positive Decimal quantity"""
        result = QuantityValidator.validate_quantity(Decimal("123.456"))
        self.assertEqual(result, Decimal("123.456"))
        self.assertIsInstance(result, Decimal)

    def test_validate_quantity_positive_string(self):
        """Valid positive string quantity"""
        result = QuantityValidator.validate_quantity("99.99")
        self.assertEqual(result, Decimal("99.99"))
        self.assertIsInstance(result, Decimal)

    def test_validate_quantity_negative_fails(self):
        """Negative quantity should fail"""
        with self.assertRaises(BadRequestException) as context:
            QuantityValidator.validate_quantity(-5)
        self.assertIn("must be positive", str(context.exception))

    def test_validate_quantity_zero_fails(self):
        """Zero quantity should fail"""
        with self.assertRaises(BadRequestException) as context:
            QuantityValidator.validate_quantity(0)
        self.assertIn("must be positive", str(context.exception))

    def test_validate_quantity_negative_zero_fails(self):
        """Negative zero should fail"""
        with self.assertRaises(BadRequestException) as context:
            QuantityValidator.validate_quantity(-0.0)
        self.assertIn("must be positive", str(context.exception))

    def test_validate_quantity_invalid_string_fails(self):
        """Invalid string should fail"""
        with self.assertRaises(BadRequestException) as context:
            QuantityValidator.validate_quantity("not_a_number")
        self.assertIn("must be a valid number", str(context.exception))

    def test_validate_quantity_none_fails(self):
        """None should fail"""
        with self.assertRaises(BadRequestException) as context:
            QuantityValidator.validate_quantity(None)
        self.assertIn("must be a valid number", str(context.exception))

    def test_validate_quantity_empty_string_fails(self):
        """Empty string should fail"""
        with self.assertRaises(BadRequestException) as context:
            QuantityValidator.validate_quantity("")
        self.assertIn("must be a valid number", str(context.exception))

    def test_validate_quantity_very_small_positive(self):
        """Very small positive quantity should pass"""
        result = QuantityValidator.validate_quantity(Decimal("0.000001"))
        self.assertEqual(result, Decimal("0.000001"))

    def test_validate_quantity_very_large_positive(self):
        """Very large positive quantity should pass"""
        result = QuantityValidator.validate_quantity(Decimal("999999999.999999"))
        self.assertEqual(result, Decimal("999999999.999999"))


class TestValidateUnit(unittest.TestCase):
    """Tests for QuantityValidator.validate_unit()"""

    def test_validate_unit_volume_valid(self):
        """Valid volume units should pass"""
        QuantityValidator.validate_unit("L", UnitType.VOLUME)
        QuantityValidator.validate_unit("mL", UnitType.VOLUME)
        QuantityValidator.validate_unit("µL", UnitType.VOLUME)
        QuantityValidator.validate_unit("uL", UnitType.VOLUME)

    def test_validate_unit_mass_valid(self):
        """Valid mass units should pass"""
        QuantityValidator.validate_unit("kg", UnitType.MASS)
        QuantityValidator.validate_unit("g", UnitType.MASS)
        QuantityValidator.validate_unit("mg", UnitType.MASS)
        QuantityValidator.validate_unit("µg", UnitType.MASS)
        QuantityValidator.validate_unit("ug", UnitType.MASS)

    def test_validate_unit_length_valid(self):
        """Valid length units should pass"""
        QuantityValidator.validate_unit("m", UnitType.LENGTH)
        QuantityValidator.validate_unit("cm", UnitType.LENGTH)
        QuantityValidator.validate_unit("mm", UnitType.LENGTH)

    def test_validate_unit_count_valid(self):
        """Valid count units should pass"""
        QuantityValidator.validate_unit("units", UnitType.COUNT)

    def test_validate_unit_volume_with_mass_unit_fails(self):
        """Mass unit with volume type should fail"""
        with self.assertRaises(BadRequestException) as context:
            QuantityValidator.validate_unit("g", UnitType.VOLUME)
        self.assertIn("not valid for unit_type", str(context.exception))

    def test_validate_unit_mass_with_volume_unit_fails(self):
        """Volume unit with mass type should fail"""
        with self.assertRaises(BadRequestException) as context:
            QuantityValidator.validate_unit("mL", UnitType.MASS)
        self.assertIn("not valid for unit_type", str(context.exception))

    def test_validate_unit_invalid_unit_fails(self):
        """Invalid unit should fail"""
        with self.assertRaises(BadRequestException) as context:
            QuantityValidator.validate_unit("invalid", UnitType.VOLUME)
        self.assertIn("not valid for unit_type", str(context.exception))

    def test_validate_unit_case_sensitive(self):
        """Unit validation should be case-sensitive"""
        with self.assertRaises(BadRequestException) as context:
            QuantityValidator.validate_unit("ML", UnitType.VOLUME)  # Should be 'mL'
        self.assertIn("not valid for unit_type", str(context.exception))

    def test_validate_unit_invalid_type_fails(self):
        """Invalid unit type should fail"""
        with self.assertRaises(BadRequestException) as context:
            QuantityValidator.validate_unit("mL", "volume")  # String instead of UnitType
        self.assertIn("Invalid unit_type", str(context.exception))


class TestValidateNonNegativeResult(unittest.TestCase):
    """Tests for QuantityValidator.validate_non_negative_result()"""

    def test_validate_non_negative_result_positive_result(self):
        """Operation resulting in positive value should pass"""
        QuantityValidator.validate_non_negative_result(Decimal("100"), Decimal("-50"), "decrement")

    def test_validate_non_negative_result_zero_result(self):
        """Operation resulting in exactly zero should pass"""
        QuantityValidator.validate_non_negative_result(Decimal("50"), Decimal("-50"), "decrement")

    def test_validate_non_negative_result_positive_change(self):
        """Positive change (increment) should always pass"""
        QuantityValidator.validate_non_negative_result(Decimal("50"), Decimal("100"), "increment")

    def test_validate_non_negative_result_negative_result_fails(self):
        """Operation resulting in negative value should fail"""
        with self.assertRaises(BadRequestException) as context:
            QuantityValidator.validate_non_negative_result(
                Decimal("50"), Decimal("-100"), "decrement"
            )
        self.assertIn("would result in negative quantity", str(context.exception))

    def test_validate_non_negative_result_slightly_negative_fails(self):
        """Operation resulting in slightly negative value should fail"""
        with self.assertRaises(BadRequestException) as context:
            QuantityValidator.validate_non_negative_result(
                Decimal("10"), Decimal("-10.000001"), "decrement"
            )
        self.assertIn("would result in negative quantity", str(context.exception))

    def test_validate_non_negative_result_zero_with_negative_change(self):
        """Zero quantity with negative change should fail"""
        with self.assertRaises(BadRequestException) as context:
            QuantityValidator.validate_non_negative_result(Decimal("0"), Decimal("-1"), "decrement")
        self.assertIn("would result in negative quantity", str(context.exception))

    def test_validate_non_negative_result_large_numbers(self):
        """Should work with large numbers"""
        QuantityValidator.validate_non_negative_result(
            Decimal("999999"), Decimal("-999998"), "decrement"
        )

    def test_validate_non_negative_result_small_numbers(self):
        """Should work with very small numbers"""
        QuantityValidator.validate_non_negative_result(
            Decimal("0.000002"), Decimal("-0.000001"), "decrement"
        )
