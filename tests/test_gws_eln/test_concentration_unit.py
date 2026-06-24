"""
Test suite for concentration unit families and intra-family conversion.

Tests cover:
- Intra-family conversions (molar, mass/volume, activity/volume)
- Family membership / same-family checks
- Cross-family and unknown-unit rejection
- Recordable list + grouping helpers
"""

from decimal import Decimal

from gws_core import BadRequestException, BaseTestCaseLight
from gws_eln.core.concentration_unit import (
    CONCENTRATION_UNITS,
    ConcentrationUnitFamily,
    convert_concentration,
    get_concentration_unit_family,
    get_concentration_units_by_family,
    is_valid_concentration_unit,
    same_concentration_family,
)


class TestConvertConcentration(BaseTestCaseLight):
    """Tests for convert_concentration (intra-family only)."""

    # ==================== MOLAR ====================

    def test_molar_to_milli(self):
        self.assertEqual(convert_concentration(1, "M", "mM"), Decimal("1000"))

    def test_milli_to_micro(self):
        self.assertEqual(convert_concentration(1, "mM", "µM"), Decimal("1000"))

    def test_micro_to_nano(self):
        self.assertEqual(convert_concentration(5, "µM", "nM"), Decimal("5000"))

    def test_nano_to_molar(self):
        self.assertEqual(convert_concentration(1, "nM", "M"), Decimal("1E-9"))

    def test_same_unit_is_identity(self):
        self.assertEqual(convert_concentration(Decimal("2.5"), "mM", "mM"), Decimal("2.5"))

    # ==================== MASS / VOLUME ====================

    def test_mg_per_ml_equals_g_per_l(self):
        self.assertEqual(convert_concentration(1, "mg/mL", "g/L"), Decimal("1"))

    def test_mg_per_ml_to_ug_per_ml(self):
        self.assertEqual(convert_concentration(1, "mg/mL", "µg/mL"), Decimal("1000"))

    def test_ng_per_ul_equals_ug_per_ml(self):
        self.assertEqual(convert_concentration(1, "ng/µL", "µg/mL"), Decimal("1"))

    def test_g_per_l_to_mg_per_ml(self):
        self.assertEqual(convert_concentration(Decimal("2.5"), "g/L", "mg/mL"), Decimal("2.5"))

    # ==================== ACTIVITY / VOLUME ====================

    def test_u_per_ul_to_u_per_ml(self):
        self.assertEqual(convert_concentration(1, "U/µL", "U/mL"), Decimal("1000"))

    def test_u_per_ml_to_u_per_ul(self):
        self.assertEqual(convert_concentration(1000, "U/mL", "U/µL"), Decimal("1"))

    # ==================== ERRORS ====================

    def test_cross_family_molar_to_mass_raises(self):
        with self.assertRaises(BadRequestException):
            convert_concentration(1, "M", "mg/mL")

    def test_cross_family_cells_to_copies_raises(self):
        with self.assertRaises(BadRequestException):
            convert_concentration(1, "cells/mL", "copies/µL")

    def test_unknown_from_unit_raises(self):
        with self.assertRaises(BadRequestException):
            convert_concentration(1, "foo", "mM")

    def test_unknown_to_unit_raises(self):
        with self.assertRaises(BadRequestException):
            convert_concentration(1, "mM", "foo")


class TestConcentrationFamilies(BaseTestCaseLight):
    """Tests for family membership helpers."""

    def test_get_family_molar(self):
        self.assertEqual(
            get_concentration_unit_family("µM"), ConcentrationUnitFamily.MOLAR
        )

    def test_get_family_mass_volume(self):
        self.assertEqual(
            get_concentration_unit_family("ng/µL"), ConcentrationUnitFamily.MASS_VOLUME
        )

    def test_get_family_unknown_is_none(self):
        self.assertIsNone(get_concentration_unit_family("foo"))

    def test_same_family_true(self):
        self.assertTrue(same_concentration_family("mM", "µM"))

    def test_same_family_false_across_families(self):
        self.assertFalse(same_concentration_family("M", "mg/mL"))

    def test_same_family_false_unknown(self):
        self.assertFalse(same_concentration_family("mM", "foo"))


class TestConcentrationUnitList(BaseTestCaseLight):
    """Tests for the recordable list and grouping helpers."""

    def test_is_valid_concentration_unit(self):
        self.assertTrue(is_valid_concentration_unit("mM"))
        self.assertFalse(is_valid_concentration_unit("foo"))

    def test_units_list_contains_expected(self):
        for unit in ["M", "mM", "µM", "nM", "g/L", "mg/mL", "µg/mL", "ng/µL",
                     "U/mL", "U/µL", "cells/mL", "copies/µL"]:
            self.assertIn(unit, CONCENTRATION_UNITS)

    def test_units_list_has_no_duplicates(self):
        self.assertEqual(len(CONCENTRATION_UNITS), len(set(CONCENTRATION_UNITS)))

    def test_grouping_covers_all_units(self):
        grouped = [u for _, units in get_concentration_units_by_family() for u in units]
        self.assertEqual(sorted(grouped), sorted(CONCENTRATION_UNITS))
