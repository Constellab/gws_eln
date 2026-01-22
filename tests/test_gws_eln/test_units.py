"""
Test suite for unit conversion utilities.

Tests cover:
- All volume conversions (L <-> mL <-> µL)
- All mass conversions (kg <-> g <-> mg <-> µg)
- All length conversions (m <-> cm <-> mm)
- Count pass-through (units)
- Precision edge cases
- Invalid unit handling
- Cross-unit conversions
"""

from decimal import Decimal

from gws_core import BadRequestException, BaseTestCaseLight

from gws_eln.core.unit_type import UnitType
from gws_eln.utils.units import UnitConverter


class TestToBaseUnit(BaseTestCaseLight):
    """Tests for UnitConverter.to_base_unit method."""

    # ==================== VOLUME CONVERSIONS ====================

    def test_liters_to_base(self):
        """Test that liters pass through unchanged."""
        result = UnitConverter.to_base_unit(1, "L", UnitType.VOLUME)
        self.assertEqual(result, Decimal("1.000000000000"))

    def test_liters_to_base_decimal(self):
        """Test decimal liter values."""
        result = UnitConverter.to_base_unit(Decimal("2.5"), "L", UnitType.VOLUME)
        self.assertEqual(result, Decimal("2.500000000000"))

    def test_milliliters_to_base(self):
        """Test milliliter to liter conversion."""
        result = UnitConverter.to_base_unit(1, "mL", UnitType.VOLUME)
        self.assertEqual(result, Decimal("0.001000000000"))

    def test_milliliters_to_base_1000(self):
        """Test 1000 mL equals 1 L."""
        result = UnitConverter.to_base_unit(1000, "mL", UnitType.VOLUME)
        self.assertEqual(result, Decimal("1.000000000000"))

    def test_microliters_to_base(self):
        """Test microliter to liter conversion."""
        result = UnitConverter.to_base_unit(1, "µL", UnitType.VOLUME)
        self.assertEqual(result, Decimal("0.000001000000"))

    def test_microliters_to_base_ul_notation(self):
        """Test alternative uL notation for microliters."""
        result = UnitConverter.to_base_unit(1, "uL", UnitType.VOLUME)
        self.assertEqual(result, Decimal("0.000001000000"))

    def test_microliters_to_base_1000000(self):
        """Test 1,000,000 µL equals 1 L."""
        result = UnitConverter.to_base_unit(1000000, "µL", UnitType.VOLUME)
        self.assertEqual(result, Decimal("1.000000000000"))

    # ==================== MASS CONVERSIONS ====================

    def test_kilograms_to_base(self):
        """Test that kilograms pass through unchanged."""
        result = UnitConverter.to_base_unit(1, "kg", UnitType.MASS)
        self.assertEqual(result, Decimal("1.000000000000"))

    def test_grams_to_base(self):
        """Test gram to kilogram conversion."""
        result = UnitConverter.to_base_unit(1, "g", UnitType.MASS)
        self.assertEqual(result, Decimal("0.001000000000"))

    def test_grams_to_base_1000(self):
        """Test 1000 g equals 1 kg."""
        result = UnitConverter.to_base_unit(1000, "g", UnitType.MASS)
        self.assertEqual(result, Decimal("1.000000000000"))

    def test_milligrams_to_base(self):
        """Test milligram to kilogram conversion."""
        result = UnitConverter.to_base_unit(1, "mg", UnitType.MASS)
        self.assertEqual(result, Decimal("0.000001000000"))

    def test_milligrams_to_base_1000000(self):
        """Test 1,000,000 mg equals 1 kg."""
        result = UnitConverter.to_base_unit(1000000, "mg", UnitType.MASS)
        self.assertEqual(result, Decimal("1.000000000000"))

    def test_micrograms_to_base(self):
        """Test microgram to kilogram conversion."""
        result = UnitConverter.to_base_unit(1, "µg", UnitType.MASS)
        self.assertEqual(result, Decimal("0.000000001000"))

    def test_micrograms_to_base_ug_notation(self):
        """Test alternative ug notation for micrograms."""
        result = UnitConverter.to_base_unit(1, "ug", UnitType.MASS)
        self.assertEqual(result, Decimal("0.000000001000"))

    def test_micrograms_to_base_1000000000(self):
        """Test 1,000,000,000 µg equals 1 kg."""
        result = UnitConverter.to_base_unit(1000000000, "µg", UnitType.MASS)
        self.assertEqual(result, Decimal("1.000000000000"))

    # ==================== LENGTH CONVERSIONS ====================

    def test_meters_to_base(self):
        """Test that meters pass through unchanged."""
        result = UnitConverter.to_base_unit(1, "m", UnitType.LENGTH)
        self.assertEqual(result, Decimal("1.000000000000"))

    def test_centimeters_to_base(self):
        """Test centimeter to meter conversion."""
        result = UnitConverter.to_base_unit(1, "cm", UnitType.LENGTH)
        self.assertEqual(result, Decimal("0.010000000000"))

    def test_centimeters_to_base_100(self):
        """Test 100 cm equals 1 m."""
        result = UnitConverter.to_base_unit(100, "cm", UnitType.LENGTH)
        self.assertEqual(result, Decimal("1.000000000000"))

    def test_millimeters_to_base(self):
        """Test millimeter to meter conversion."""
        result = UnitConverter.to_base_unit(1, "mm", UnitType.LENGTH)
        self.assertEqual(result, Decimal("0.001000000000"))

    def test_millimeters_to_base_1000(self):
        """Test 1000 mm equals 1 m."""
        result = UnitConverter.to_base_unit(1000, "mm", UnitType.LENGTH)
        self.assertEqual(result, Decimal("1.000000000000"))

    # ==================== COUNT CONVERSIONS ====================

    def test_units_to_base(self):
        """Test that units pass through unchanged (1:1)."""
        result = UnitConverter.to_base_unit(1, "units", UnitType.COUNT)
        self.assertEqual(result, Decimal("1.000000000000"))

    def test_units_to_base_large(self):
        """Test large count values."""
        result = UnitConverter.to_base_unit(10000, "units", UnitType.COUNT)
        self.assertEqual(result, Decimal("10000.000000000000"))

    # ==================== INPUT TYPE HANDLING ====================

    def test_string_input(self):
        """Test string numeric input."""
        result = UnitConverter.to_base_unit("500", "mL", UnitType.VOLUME)
        self.assertEqual(result, Decimal("0.500000000000"))

    def test_float_input(self):
        """Test float input."""
        result = UnitConverter.to_base_unit(2.5, "g", UnitType.MASS)
        self.assertEqual(result, Decimal("0.002500000000"))

    def test_decimal_input(self):
        """Test Decimal input."""
        result = UnitConverter.to_base_unit(Decimal("0.5"), "L", UnitType.VOLUME)
        self.assertEqual(result, Decimal("0.500000000000"))

    # ==================== PRECISION EDGE CASES ====================

    def test_precision_very_small_value(self):
        """Test precision with very small values."""
        result = UnitConverter.to_base_unit(Decimal("0.001"), "µL", UnitType.VOLUME)
        # 0.001 µL = 0.001 * 0.000001 L = 0.000000001 L
        self.assertEqual(result, Decimal("0.000000001000"))

    def test_precision_large_value(self):
        """Test precision with large values."""
        result = UnitConverter.to_base_unit(Decimal("99999999.999999"), "L", UnitType.VOLUME)
        self.assertEqual(result, Decimal("99999999.999999000000"))

    def test_precision_repeating_decimal(self):
        """Test precision with value that could produce repeating decimal."""
        result = UnitConverter.to_base_unit(Decimal("1"), "mL", UnitType.VOLUME)
        # Should be exactly 0.001, not 0.000999999...
        self.assertEqual(result, Decimal("0.001000000000"))


class TestFromBaseUnit(BaseTestCaseLight):
    """Tests for UnitConverter.from_base_unit method."""

    # ==================== VOLUME CONVERSIONS ====================

    def test_base_to_liters(self):
        """Test base to liters unchanged."""
        result = UnitConverter.from_base_unit(Decimal("1"), "L", UnitType.VOLUME)
        self.assertEqual(result, Decimal("1.000000000000"))

    def test_base_to_milliliters(self):
        """Test base to milliliters."""
        result = UnitConverter.from_base_unit(Decimal("0.001"), "mL", UnitType.VOLUME)
        self.assertEqual(result, Decimal("1.000000000000"))

    def test_base_to_milliliters_large(self):
        """Test 1 L to mL."""
        result = UnitConverter.from_base_unit(Decimal("1"), "mL", UnitType.VOLUME)
        self.assertEqual(result, Decimal("1000.000000000000"))

    def test_base_to_microliters(self):
        """Test base to microliters."""
        result = UnitConverter.from_base_unit(Decimal("0.000001"), "µL", UnitType.VOLUME)
        self.assertEqual(result, Decimal("1.000000000000"))

    def test_base_to_microliters_ul_notation(self):
        """Test alternative uL notation."""
        result = UnitConverter.from_base_unit(Decimal("0.000001"), "uL", UnitType.VOLUME)
        self.assertEqual(result, Decimal("1.000000000000"))

    # ==================== MASS CONVERSIONS ====================

    def test_base_to_kilograms(self):
        """Test base to kilograms unchanged."""
        result = UnitConverter.from_base_unit(Decimal("1"), "kg", UnitType.MASS)
        self.assertEqual(result, Decimal("1.000000000000"))

    def test_base_to_grams(self):
        """Test base to grams."""
        result = UnitConverter.from_base_unit(Decimal("0.001"), "g", UnitType.MASS)
        self.assertEqual(result, Decimal("1.000000000000"))

    def test_base_to_grams_large(self):
        """Test 1 kg to g."""
        result = UnitConverter.from_base_unit(Decimal("1"), "g", UnitType.MASS)
        self.assertEqual(result, Decimal("1000.000000000000"))

    def test_base_to_milligrams(self):
        """Test base to milligrams."""
        result = UnitConverter.from_base_unit(Decimal("0.000001"), "mg", UnitType.MASS)
        self.assertEqual(result, Decimal("1.000000000000"))

    def test_base_to_micrograms(self):
        """Test base to micrograms."""
        result = UnitConverter.from_base_unit(Decimal("0.000000001"), "µg", UnitType.MASS)
        self.assertEqual(result, Decimal("1.000000000000"))

    # ==================== LENGTH CONVERSIONS ====================

    def test_base_to_meters(self):
        """Test base to meters unchanged."""
        result = UnitConverter.from_base_unit(Decimal("1"), "m", UnitType.LENGTH)
        self.assertEqual(result, Decimal("1.000000000000"))

    def test_base_to_centimeters(self):
        """Test base to centimeters."""
        result = UnitConverter.from_base_unit(Decimal("0.01"), "cm", UnitType.LENGTH)
        self.assertEqual(result, Decimal("1.000000000000"))

    def test_base_to_centimeters_large(self):
        """Test 1 m to cm."""
        result = UnitConverter.from_base_unit(Decimal("1"), "cm", UnitType.LENGTH)
        self.assertEqual(result, Decimal("100.000000000000"))

    def test_base_to_millimeters(self):
        """Test base to millimeters."""
        result = UnitConverter.from_base_unit(Decimal("0.001"), "mm", UnitType.LENGTH)
        self.assertEqual(result, Decimal("1.000000000000"))

    def test_base_to_millimeters_large(self):
        """Test 1 m to mm."""
        result = UnitConverter.from_base_unit(Decimal("1"), "mm", UnitType.LENGTH)
        self.assertEqual(result, Decimal("1000.000000000000"))

    # ==================== COUNT CONVERSIONS ====================

    def test_base_to_units(self):
        """Test base to units unchanged (1:1)."""
        result = UnitConverter.from_base_unit(Decimal("100"), "units", UnitType.COUNT)
        self.assertEqual(result, Decimal("100.000000000000"))


class TestRoundTripConversions(BaseTestCaseLight):
    """Tests to verify round-trip conversion accuracy."""

    def test_roundtrip_volume_ml(self):
        """Test mL -> base -> mL round trip."""
        original = Decimal("250")
        base = UnitConverter.to_base_unit(original, "mL", UnitType.VOLUME)
        result = UnitConverter.from_base_unit(base, "mL", UnitType.VOLUME)
        self.assertEqual(result, Decimal("250.000000000000"))

    def test_roundtrip_volume_ul(self):
        """Test µL -> base -> µL round trip."""
        original = Decimal("500")
        base = UnitConverter.to_base_unit(original, "µL", UnitType.VOLUME)
        result = UnitConverter.from_base_unit(base, "µL", UnitType.VOLUME)
        self.assertEqual(result, Decimal("500.000000000000"))

    def test_roundtrip_mass_g(self):
        """Test g -> base -> g round trip."""
        original = Decimal("150.5")
        base = UnitConverter.to_base_unit(original, "g", UnitType.MASS)
        result = UnitConverter.from_base_unit(base, "g", UnitType.MASS)
        self.assertEqual(result, Decimal("150.500000000000"))

    def test_roundtrip_mass_mg(self):
        """Test mg -> base -> mg round trip."""
        original = Decimal("25")
        base = UnitConverter.to_base_unit(original, "mg", UnitType.MASS)
        result = UnitConverter.from_base_unit(base, "mg", UnitType.MASS)
        self.assertEqual(result, Decimal("25.000000000000"))

    def test_roundtrip_mass_ug(self):
        """Test µg -> base -> µg round trip."""
        original = Decimal("100")
        base = UnitConverter.to_base_unit(original, "µg", UnitType.MASS)
        result = UnitConverter.from_base_unit(base, "µg", UnitType.MASS)
        self.assertEqual(result, Decimal("100.000000000000"))

    def test_roundtrip_length_cm(self):
        """Test cm -> base -> cm round trip."""
        original = Decimal("50")
        base = UnitConverter.to_base_unit(original, "cm", UnitType.LENGTH)
        result = UnitConverter.from_base_unit(base, "cm", UnitType.LENGTH)
        self.assertEqual(result, Decimal("50.000000000000"))

    def test_roundtrip_length_mm(self):
        """Test mm -> base -> mm round trip."""
        original = Decimal("75.5")
        base = UnitConverter.to_base_unit(original, "mm", UnitType.LENGTH)
        result = UnitConverter.from_base_unit(base, "mm", UnitType.LENGTH)
        self.assertEqual(result, Decimal("75.500000000000"))


class TestConvertUnit(BaseTestCaseLight):
    """Tests for UnitConverter.convert_unit method."""

    def test_convert_ml_to_l(self):
        """Test mL to L conversion."""
        result = UnitConverter.convert_unit(1000, "mL", "L", UnitType.VOLUME)
        self.assertEqual(result, Decimal("1.000000000000"))

    def test_convert_l_to_ml(self):
        """Test L to mL conversion."""
        result = UnitConverter.convert_unit(1, "L", "mL", UnitType.VOLUME)
        self.assertEqual(result, Decimal("1000.000000000000"))

    def test_convert_ml_to_ul(self):
        """Test mL to µL conversion."""
        result = UnitConverter.convert_unit(1, "mL", "µL", UnitType.VOLUME)
        self.assertEqual(result, Decimal("1000.000000000000"))

    def test_convert_g_to_kg(self):
        """Test g to kg conversion."""
        result = UnitConverter.convert_unit(500, "g", "kg", UnitType.MASS)
        self.assertEqual(result, Decimal("0.500000000000"))

    def test_convert_kg_to_g(self):
        """Test kg to g conversion."""
        result = UnitConverter.convert_unit(1, "kg", "g", UnitType.MASS)
        self.assertEqual(result, Decimal("1000.000000000000"))

    def test_convert_mg_to_g(self):
        """Test mg to g conversion."""
        result = UnitConverter.convert_unit(1000, "mg", "g", UnitType.MASS)
        self.assertEqual(result, Decimal("1.000000000000"))

    def test_convert_g_to_ug(self):
        """Test g to µg conversion."""
        result = UnitConverter.convert_unit(1, "g", "µg", UnitType.MASS)
        self.assertEqual(result, Decimal("1000000.000000000000"))

    def test_convert_cm_to_m(self):
        """Test cm to m conversion."""
        result = UnitConverter.convert_unit(100, "cm", "m", UnitType.LENGTH)
        self.assertEqual(result, Decimal("1.000000000000"))

    def test_convert_mm_to_cm(self):
        """Test mm to cm conversion."""
        result = UnitConverter.convert_unit(10, "mm", "cm", UnitType.LENGTH)
        self.assertEqual(result, Decimal("1.000000000000"))


class TestInvalidUnitHandling(BaseTestCaseLight):
    """Tests for invalid unit/type error handling."""

    def test_invalid_unit_for_volume(self):
        """Test invalid unit for volume type."""
        with self.assertRaises(BadRequestException) as context:
            UnitConverter.to_base_unit(1, "kg", UnitType.VOLUME)
        self.assertIn("Invalid unit", str(context.exception))
        self.assertIn("kg", str(context.exception))

    def test_invalid_unit_for_mass(self):
        """Test invalid unit for mass type."""
        with self.assertRaises(BadRequestException) as context:
            UnitConverter.to_base_unit(1, "mL", UnitType.MASS)
        self.assertIn("Invalid unit", str(context.exception))
        self.assertIn("mL", str(context.exception))

    def test_invalid_unit_for_length(self):
        """Test invalid unit for length type."""
        with self.assertRaises(BadRequestException) as context:
            UnitConverter.to_base_unit(1, "g", UnitType.LENGTH)
        self.assertIn("Invalid unit", str(context.exception))

    def test_invalid_unit_for_count(self):
        """Test invalid unit for count type."""
        with self.assertRaises(BadRequestException) as context:
            UnitConverter.to_base_unit(1, "mL", UnitType.COUNT)
        self.assertIn("Invalid unit", str(context.exception))

    def test_unknown_unit(self):
        """Test completely unknown unit."""
        with self.assertRaises(BadRequestException) as context:
            UnitConverter.to_base_unit(1, "xyz", UnitType.VOLUME)
        self.assertIn("Invalid unit", str(context.exception))

    def test_invalid_unit_type_string(self):
        """Test invalid unit type as string."""
        with self.assertRaises(BadRequestException) as context:
            UnitConverter.to_base_unit(1, "mL", "volume")  # type: ignore
        self.assertIn("Invalid unit type", str(context.exception))

    def test_invalid_value_string(self):
        """Test invalid non-numeric value."""
        with self.assertRaises(BadRequestException) as context:
            UnitConverter.to_base_unit("abc", "mL", UnitType.VOLUME)
        self.assertIn("Invalid numeric value", str(context.exception))

    def test_invalid_value_empty_string(self):
        """Test empty string value."""
        with self.assertRaises(BadRequestException) as context:
            UnitConverter.to_base_unit("", "mL", UnitType.VOLUME)
        self.assertIn("Invalid numeric value", str(context.exception))

    def test_from_base_invalid_unit(self):
        """Test from_base_unit with invalid unit."""
        with self.assertRaises(BadRequestException) as context:
            UnitConverter.from_base_unit(1, "invalid", UnitType.VOLUME)
        self.assertIn("Invalid unit", str(context.exception))

    def test_convert_unit_invalid_from_unit(self):
        """Test convert_unit with invalid from_unit."""
        with self.assertRaises(BadRequestException) as context:
            UnitConverter.convert_unit(1, "invalid", "L", UnitType.VOLUME)
        self.assertIn("Invalid unit", str(context.exception))

    def test_convert_unit_invalid_to_unit(self):
        """Test convert_unit with invalid to_unit."""
        with self.assertRaises(BadRequestException) as context:
            UnitConverter.convert_unit(1, "L", "invalid", UnitType.VOLUME)
        self.assertIn("Invalid unit", str(context.exception))


class TestHelperMethods(BaseTestCaseLight):
    """Tests for helper methods."""

    def test_get_base_unit_volume(self):
        """Test get_base_unit for volume."""
        self.assertEqual(UnitConverter.get_base_unit(UnitType.VOLUME), "L")

    def test_get_base_unit_mass(self):
        """Test get_base_unit for mass."""
        self.assertEqual(UnitConverter.get_base_unit(UnitType.MASS), "kg")

    def test_get_base_unit_length(self):
        """Test get_base_unit for length."""
        self.assertEqual(UnitConverter.get_base_unit(UnitType.LENGTH), "m")

    def test_get_base_unit_count(self):
        """Test get_base_unit for count."""
        self.assertEqual(UnitConverter.get_base_unit(UnitType.COUNT), "units")

    def test_get_base_unit_invalid_type(self):
        """Test get_base_unit with invalid type."""
        with self.assertRaises(BadRequestException):
            UnitConverter.get_base_unit("invalid")  # type: ignore

    def test_get_valid_units_volume(self):
        """Test get_valid_units for volume."""
        units = UnitConverter.get_valid_units(UnitType.VOLUME)
        self.assertIn("L", units)
        self.assertIn("mL", units)
        self.assertIn("µL", units)
        self.assertIn("uL", units)

    def test_get_valid_units_mass(self):
        """Test get_valid_units for mass."""
        units = UnitConverter.get_valid_units(UnitType.MASS)
        self.assertIn("kg", units)
        self.assertIn("g", units)
        self.assertIn("mg", units)
        self.assertIn("µg", units)
        self.assertIn("ug", units)

    def test_get_valid_units_length(self):
        """Test get_valid_units for length."""
        units = UnitConverter.get_valid_units(UnitType.LENGTH)
        self.assertIn("m", units)
        self.assertIn("cm", units)
        self.assertIn("mm", units)

    def test_get_valid_units_count(self):
        """Test get_valid_units for count."""
        units = UnitConverter.get_valid_units(UnitType.COUNT)
        self.assertIn("units", units)

    def test_get_valid_units_invalid_type(self):
        """Test get_valid_units with invalid type."""
        with self.assertRaises(BadRequestException):
            UnitConverter.get_valid_units("invalid")  # type: ignore

    def test_is_valid_unit_true(self):
        """Test is_valid_unit returns True for valid unit."""
        self.assertTrue(UnitConverter.is_valid_unit("mL", UnitType.VOLUME))
        self.assertTrue(UnitConverter.is_valid_unit("g", UnitType.MASS))
        self.assertTrue(UnitConverter.is_valid_unit("cm", UnitType.LENGTH))
        self.assertTrue(UnitConverter.is_valid_unit("units", UnitType.COUNT))

    def test_is_valid_unit_false_wrong_type(self):
        """Test is_valid_unit returns False for wrong type."""
        self.assertFalse(UnitConverter.is_valid_unit("mL", UnitType.MASS))
        self.assertFalse(UnitConverter.is_valid_unit("g", UnitType.VOLUME))
        self.assertFalse(UnitConverter.is_valid_unit("cm", UnitType.COUNT))

    def test_is_valid_unit_false_unknown(self):
        """Test is_valid_unit returns False for unknown unit."""
        self.assertFalse(UnitConverter.is_valid_unit("xyz", UnitType.VOLUME))

    def test_is_valid_unit_invalid_type(self):
        """Test is_valid_unit with invalid type returns False."""
        self.assertFalse(UnitConverter.is_valid_unit("mL", "invalid"))  # type: ignore
