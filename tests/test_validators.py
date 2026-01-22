"""
Tests for quantity and unit validators.

Tests Story 2.3: Quantity & Unit Validators
"""

import unittest
from decimal import Decimal
from unittest.mock import Mock

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


class TestValidateBatchOperation(unittest.TestCase):
    """Tests for QuantityValidator.validate_batch_operation()"""

    def create_mock_batch(self, quantity: Decimal, is_consumable: bool = True):
        """Helper to create a mock batch with metarial"""
        metarial = Mock()
        metarial.name = "Test Metarial"
        metarial.is_consumable = is_consumable

        batch = Mock()
        batch.id = 1
        batch.quantity = quantity
        batch.metarial = metarial

        return batch

    def test_validate_batch_operation_sufficient_stock_decrement(self):
        """Decrement operation with sufficient stock should pass"""
        batch = self.create_mock_batch(Decimal("100"))
        QuantityValidator.validate_batch_operation(batch, Decimal("50"), "decrement")

    def test_validate_batch_operation_sufficient_stock_consume(self):
        """Consume operation with sufficient stock should pass"""
        batch = self.create_mock_batch(Decimal("100"))
        QuantityValidator.validate_batch_operation(batch, Decimal("100"), "consume")

    def test_validate_batch_operation_sufficient_stock_aliquot(self):
        """Aliquot operation with sufficient stock should pass"""
        batch = self.create_mock_batch(Decimal("100"))
        QuantityValidator.validate_batch_operation(batch, Decimal("25"), "aliquot")

    def test_validate_batch_operation_insufficient_stock_fails(self):
        """Operation with insufficient stock should fail"""
        batch = self.create_mock_batch(Decimal("10"))
        with self.assertRaises(BadRequestException) as context:
            QuantityValidator.validate_batch_operation(batch, Decimal("20"), "decrement")
        self.assertIn("Insufficient quantity", str(context.exception))

    def test_validate_batch_operation_exact_quantity(self):
        """Operation with exact quantity should pass"""
        batch = self.create_mock_batch(Decimal("50"))
        QuantityValidator.validate_batch_operation(batch, Decimal("50"), "consume")

    def test_validate_batch_operation_non_consumable_aliquot_passes(self):
        """Can create aliquot from non-consumable metarial (doesn't check consumable)"""
        batch = self.create_mock_batch(Decimal("100"), is_consumable=False)
        # Aliquot only checks quantity, not consumable status
        QuantityValidator.validate_batch_operation(batch, Decimal("10"), "aliquot")

    def test_validate_batch_operation_move_no_checks(self):
        """Move operation doesn't check quantity or consumable"""
        batch = self.create_mock_batch(Decimal("10"), is_consumable=False)
        # Move operation doesn't trigger any checks
        QuantityValidator.validate_batch_operation(batch, Decimal("999"), "move")

    def test_validate_batch_operation_batch_missing_quantity_fails(self):
        """Batch without quantity attribute should fail"""
        batch = Mock(spec=[])  # No attributes
        with self.assertRaises(BadRequestException) as context:
            QuantityValidator.validate_batch_operation(batch, Decimal("10"), "decrement")
        self.assertIn("must have 'quantity' attribute", str(context.exception))

    def test_validate_batch_operation_batch_missing_metarial_fails(self):
        """Batch without metarial attribute should fail for consumable operations"""
        batch = Mock(spec=["quantity"])  # Only has quantity, no metarial
        batch.quantity = Decimal("100")
        # No metarial attribute
        with self.assertRaises(BadRequestException) as context:
            QuantityValidator.validate_batch_operation(batch, Decimal("10"), "decrement")
        self.assertIn("must have 'metarial' attribute", str(context.exception))

    def test_validate_batch_operation_zero_quantity_fails(self):
        """Cannot operate on batch with zero quantity"""
        batch = self.create_mock_batch(Decimal("0"))
        with self.assertRaises(BadRequestException) as context:
            QuantityValidator.validate_batch_operation(batch, Decimal("1"), "consume")
        self.assertIn("Insufficient quantity", str(context.exception))

    def test_validate_batch_operation_edge_case_slightly_over(self):
        """Operation slightly over available quantity should fail"""
        batch = self.create_mock_batch(Decimal("10.0"))
        with self.assertRaises(BadRequestException) as context:
            QuantityValidator.validate_batch_operation(batch, Decimal("10.000001"), "decrement")
        self.assertIn("Insufficient quantity", str(context.exception))


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
