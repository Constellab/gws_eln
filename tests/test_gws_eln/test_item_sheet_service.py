"""Test suite for ItemSheetService.

Covers item-sheet CRUD, the 4-char code rules, consumable filtering, the
unit_type immutability rule (locked once items exist), supplier references and
deletion constraints.
"""

from decimal import Decimal

from gws_core import BadRequestException, BaseTestCase, NotFoundException
from gws_eln.core.unit_type import UnitType
from gws_eln.items.item_dto import CreateItemDTO
from gws_eln.items.item_service import ItemService
from gws_eln.items.item_sheet_dto import CreateItemSheetDTO, UpdateItemSheetDTO
from gws_eln.items.item_sheet_service import ItemSheetService
from gws_eln.suppliers.supplier_dto import CreateSupplierDTO
from gws_eln.suppliers.supplier_service import SupplierService
from gws_eln.user.eln_user_sync_service import ElnUserSyncService


class TestItemSheetService(BaseTestCase):
    """Test suite for ItemSheetService."""

    @classmethod
    def init_before_test(cls):
        super().init_before_test()
        ElnUserSyncService().sync_all_users()

    # ------------------------------------------------------------------ helpers

    def _sheet(self, code: str, *, name: str | None = None, **kwargs):
        return ItemSheetService().create_item_sheet(
            CreateItemSheetDTO(name=name or f"Sheet {code}", code=code, **kwargs)
        )

    def _add_item(self, sheet) -> None:
        """Create one item referencing the sheet (COUNT 'units', quantity 1)."""
        ItemService().create_item(
            CreateItemDTO(item_sheet_id=sheet.id, quantity=Decimal(1), unit="units", label="Test item")
        )

    # ------------------------------------------------------------------- create

    def test_create_consumable_default(self):
        sheet = self._sheet("CRS1")
        self.assertEqual(sheet.code, "CRS1")
        self.assertTrue(sheet.is_consumable)
        self.assertEqual(sheet.unit_type, UnitType.COUNT)

    def test_create_non_consumable(self):
        sheet = self._sheet("CRS2", is_consumable=False)
        self.assertFalse(sheet.is_consumable)

    def test_create_with_supplier(self):
        supplier = SupplierService().create_supplier(CreateSupplierDTO(name="Acme CRS3"))
        sheet = self._sheet("CRS3", supplier_id=supplier.id)
        self.assertEqual(sheet.default_supplier.id, supplier.id)

    def test_create_with_invalid_supplier_fails(self):
        with self.assertRaises(BadRequestException):
            self._sheet("CRS4", supplier_id="does-not-exist")

    def test_create_trims_name(self):
        sheet = self._sheet("CRS5", name="  Ethanol  ")
        self.assertEqual(sheet.name, "Ethanol")

    def test_create_empty_name_fails(self):
        with self.assertRaises(BadRequestException):
            self._sheet("CRS6", name="   ")

    def test_create_all_unit_types(self):
        for idx, unit_type in enumerate(UnitType):
            sheet = self._sheet(f"UT{idx:02d}", unit_type=unit_type)
            self.assertEqual(sheet.unit_type, unit_type)

    # --------------------------------------------------------------------- code

    def test_code_is_normalized_uppercase(self):
        sheet = self._sheet("et1a")
        self.assertEqual(sheet.code, "ET1A")

    def test_code_wrong_length_fails(self):
        with self.assertRaises(BadRequestException):
            self._sheet("ABC")

    def test_code_invalid_chars_fails(self):
        with self.assertRaises(BadRequestException):
            self._sheet("AB-C")

    def test_code_duplicate_fails(self):
        self._sheet("DUPL")
        with self.assertRaises(BadRequestException):
            self._sheet("DUPL", name="Other")

    # ------------------------------------------------------------------ get/list

    def test_get_item_sheet(self):
        sheet = self._sheet("GET1")
        self.assertEqual(ItemSheetService().get_item_sheet(sheet.id).id, sheet.id)

    def test_get_item_sheet_not_found(self):
        with self.assertRaises(NotFoundException):
            ItemSheetService().get_item_sheet("does-not-exist")

    def test_list_and_filter_consumable(self):
        self._sheet("LST1", is_consumable=True)
        self._sheet("LST2", is_consumable=False)
        service = ItemSheetService()
        consumable_codes = {s.code for s in service.list_item_sheets(filter_consumable=True)}
        non_codes = {s.code for s in service.list_item_sheets(filter_consumable=False)}
        self.assertIn("LST1", consumable_codes)
        self.assertNotIn("LST2", consumable_codes)
        self.assertIn("LST2", non_codes)
        self.assertNotIn("LST1", non_codes)

    # ------------------------------------------------------------------- update

    def test_update_name_and_description(self):
        sheet = self._sheet("UPD1")
        updated = ItemSheetService().update_item_sheet(
            sheet.id, UpdateItemSheetDTO(name="Renamed", description="desc", unit_type=sheet.unit_type)
        )
        self.assertEqual(updated.name, "Renamed")
        self.assertEqual(updated.description, "desc")

    def test_update_unit_type_allowed_without_items(self):
        sheet = self._sheet("UPD2", unit_type=UnitType.COUNT)
        updated = ItemSheetService().update_item_sheet(
            sheet.id, UpdateItemSheetDTO(name=sheet.name, unit_type=UnitType.VOLUME)
        )
        self.assertEqual(updated.unit_type, UnitType.VOLUME)

    def test_update_unit_type_immutable_with_items(self):
        sheet = self._sheet("UPD3", unit_type=UnitType.COUNT)
        self._add_item(sheet)
        with self.assertRaises(BadRequestException):
            ItemSheetService().update_item_sheet(
                sheet.id, UpdateItemSheetDTO(name=sheet.name, unit_type=UnitType.VOLUME)
            )

    # ------------------------------------------------------------------- delete

    def test_delete_unused(self):
        sheet = self._sheet("DEL1")
        self.assertTrue(ItemSheetService().delete_item_sheet(sheet.id))

    def test_delete_with_items_fails(self):
        sheet = self._sheet("DEL2")
        self._add_item(sheet)
        with self.assertRaises(BadRequestException):
            ItemSheetService().delete_item_sheet(sheet.id)

    # --------------------------------------------------------------------- misc

    def test_is_code_available(self):
        service = ItemSheetService()
        self.assertTrue(service.is_code_available("FREE"))
        self._sheet("TAKN")
        self.assertFalse(service.is_code_available("TAKN"))

    def test_suggest_code(self):
        code = ItemSheetService().suggest_code("Éthanol 99%")
        self.assertEqual(code, "ETHA")

    def test_has_items(self):
        sheet = self._sheet("HAS1")
        service = ItemSheetService()
        self.assertFalse(service.has_items(sheet.id))
        self._add_item(sheet)
        self.assertTrue(service.has_items(sheet.id))
