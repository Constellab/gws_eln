"""Test suite for ItemService.

Covers the Item user story: structured code generation (format, per-(sheet,year)
increment, width-4 padding, >9999 overflow, concurrency retry), status recompute
(ACTIVE / EXHAUSTED / DISCARDED), serial-number uniqueness, bulk creation,
consumable/non-consumable guards, and field-coupling validation.
"""

from decimal import Decimal
from unittest.mock import patch

from gws_core import BadRequestException, BaseTestCase, DateHelper
from gws_eln.activities.activity_input_role import ActivityInputRole
from gws_eln.core.unit_type import UnitType
from gws_eln.items.item import Item
from gws_eln.items.item_dto import (
    CombineInputDTO,
    CombineItemDTO,
    ConcentrateItemDTO,
    CreateItemDTO,
    CreateItemsBulkDTO,
    DecrementQuantityDTO,
    DeleteItemResultDTO,
    DiluteDiluentDTO,
    DiluteItemDTO,
    DiscardItemDTO,
    MoveItemDTO,
    ReceiveItemDTO,
    SplitItemDTO,
    SplitOutputDTO,
    UpdateItemDTO,
    UseItemDTO,
)
from gws_eln.items.item_service import ItemService
from gws_eln.items.item_sheet_dto import CreateItemSheetDTO
from gws_eln.items.item_sheet_service import ItemSheetService
from gws_eln.items.item_status import ItemStatus
from gws_eln.locations.location_dto import CreateLocationDTO
from gws_eln.locations.location_service import LocationService
from gws_eln.user.eln_user_sync_service import ElnUserSyncService


class TestItemService(BaseTestCase):
    """Test suite for ItemService."""

    @classmethod
    def init_before_test(cls):
        """Sync users so the current user exists in the gws_eln_user table."""
        super().init_before_test()
        ElnUserSyncService().sync_all_users()

    # ------------------------------------------------------------------ helpers

    @property
    def _year(self) -> int:
        return DateHelper.now_utc().year

    def _sheet(self, code: str, *, is_consumable: bool = True, unit_type: UnitType = UnitType.VOLUME):
        """Create an item sheet (consumable VOLUME by default)."""
        return ItemSheetService().create_item_sheet(
            CreateItemSheetDTO(
                name=f"Sheet {code}",
                code=code,
                is_consumable=is_consumable,
                unit_type=unit_type,
            )
        )

    def _create_consumable(self, sheet, quantity: str = "10", unit: str = "mL", **kwargs) -> Item:
        """Create a single consumable item and return it."""
        return ItemService().create_item(
            CreateItemDTO(
                item_sheet_id=sheet.id, quantity=Decimal(quantity), unit=unit, **kwargs
            )
        ).item

    def _count_item(self, code: str, quantity: str = "10") -> Item:
        """Create a COUNT consumable item ('units', factor 1) for whole-number maths."""
        return self._create_consumable(
            self._sheet(code, unit_type=UnitType.COUNT), quantity=quantity, unit="units"
        )

    def _save_raw_item(self, sheet, code: str) -> Item:
        """Persist an item with a chosen code (to set up code-generation edge cases)."""
        item = Item()
        item.item_sheet = sheet
        item.code = code
        item.quantity = Decimal(1)
        item.unit_type = sheet.unit_type
        item.location = LocationService().get_default_location()
        item.save()
        return item

    # ------------------------------------------------------------- code generation

    def test_code_format_and_increment(self):
        sheet = self._sheet("CGN1")
        first = self._create_consumable(sheet)
        second = self._create_consumable(sheet)
        self.assertEqual(first.code, f"CGN1-{self._year}-0001")
        self.assertEqual(second.code, f"CGN1-{self._year}-0002")

    def test_code_increment_scoped_per_sheet(self):
        sheet_a = self._sheet("CGN2")
        sheet_b = self._sheet("CGN3")
        item_a = self._create_consumable(sheet_a)
        item_b = self._create_consumable(sheet_b)
        # Independent counters per sheet
        self.assertEqual(item_a.code, f"CGN2-{self._year}-0001")
        self.assertEqual(item_b.code, f"CGN3-{self._year}-0001")

    def test_code_overflow_past_9999(self):
        sheet = self._sheet("COVF")
        self._save_raw_item(sheet, code=f"COVF-{self._year}-9999")
        nxt = self._create_consumable(sheet)
        self.assertEqual(nxt.code, f"COVF-{self._year}-10000")

    def test_is_duplicate_code_error_discriminates(self):
        service = ItemService()
        self.assertTrue(
            service._is_duplicate_code_error(
                Exception("(1062, \"Duplicate entry 'X' for key 'gws_eln_items.code'\")")
            )
        )
        self.assertFalse(
            service._is_duplicate_code_error(
                Exception("(1062, \"Duplicate entry 'X' for key 'gws_eln_items.serial_number'\")")
            )
        )

    def test_code_collision_is_retried(self):
        sheet = self._sheet("CRTY")
        first = self._create_consumable(sheet)  # CRTY-year-0001

        service = ItemService()
        # First generation returns an already-used code (collision), then a free one.
        codes = iter([first.code, f"{sheet.code}-{self._year}-0002"])
        with patch.object(service, "_generate_item_code", side_effect=lambda *_a, **_k: next(codes)):
            item = service.create_item(
                CreateItemDTO(item_sheet_id=sheet.id, quantity=Decimal(5), unit="mL")
            ).item
        self.assertEqual(item.code, f"{sheet.code}-{self._year}-0002")

    # ------------------------------------------------------------- status recompute

    def test_status_active_on_create(self):
        item = self._create_consumable(self._sheet("STA1"), quantity="5")
        self.assertEqual(item.status, ItemStatus.ACTIVE)

    def test_status_exhausted_when_consumed_to_zero(self):
        item = self._create_consumable(self._sheet("STA2"), quantity="5", unit="mL")
        ItemService().consume_quantity(item.id, DecrementQuantityDTO(quantity=Decimal(5), unit="mL"))
        self.assertEqual(ItemService().get_item(item.id).status, ItemStatus.EXHAUSTED)

    def test_status_back_to_active_after_receive(self):
        item = self._create_consumable(self._sheet("STA3"), quantity="5", unit="mL")
        ItemService().consume_quantity(item.id, DecrementQuantityDTO(quantity=Decimal(5), unit="mL"))
        ItemService().receive_item(item.id, ReceiveItemDTO(quantity=Decimal(3), unit="mL"))
        self.assertEqual(ItemService().get_item(item.id).status, ItemStatus.ACTIVE)

    def test_status_discarded_is_terminal(self):
        item = self._create_consumable(self._sheet("STA4"), quantity="5", unit="mL")
        ItemService().discard_item(item.id, DiscardItemDTO())
        self.assertEqual(ItemService().get_item(item.id).status, ItemStatus.DISCARDED)

    def test_non_consumable_never_exhausted(self):
        sheet = self._sheet("STA5", is_consumable=False, unit_type=UnitType.COUNT)
        items = ItemService().create_items_bulk(
            CreateItemsBulkDTO(item_sheet_id=sheet.id, serial_numbers=["NX1"])
        )
        self.assertEqual(items[0].status, ItemStatus.ACTIVE)

    # ------------------------------------------------------------- serial uniqueness

    def test_serial_unique_lab_wide(self):
        sheet = self._sheet("SER1", is_consumable=False, unit_type=UnitType.COUNT)
        ItemService().create_items_bulk(
            CreateItemsBulkDTO(item_sheet_id=sheet.id, serial_numbers=["UNIQ-1"])
        )
        with self.assertRaises(BadRequestException):
            ItemService().create_items_bulk(
                CreateItemsBulkDTO(item_sheet_id=sheet.id, serial_numbers=["UNIQ-1"])
            )

    def test_serial_set_and_duplicate_via_create_item(self):
        sheet = self._sheet("SER2", is_consumable=False, unit_type=UnitType.COUNT)
        item = ItemService().create_item(
            CreateItemDTO(
                item_sheet_id=sheet.id, quantity=Decimal(1), unit="units", serial_number="SVC-1"
            )
        ).item
        self.assertEqual(item.serial_number, "SVC-1")
        with self.assertRaises(BadRequestException):
            ItemService().create_item(
                CreateItemDTO(
                    item_sheet_id=sheet.id, quantity=Decimal(1), unit="units", serial_number="SVC-1"
                )
            )

    # --------------------------------------------------------------- bulk creation

    def test_bulk_creates_sequential_items(self):
        sheet = self._sheet("BLK1", is_consumable=False, unit_type=UnitType.COUNT)
        items = ItemService().create_items_bulk(
            CreateItemsBulkDTO(item_sheet_id=sheet.id, serial_numbers=["A1", "A2", "A3"])
        )
        self.assertEqual(len(items), 3)
        self.assertEqual(
            sorted(i.code for i in items),
            [f"BLK1-{self._year}-000{n}" for n in (1, 2, 3)],
        )
        self.assertTrue(all(i.quantity == Decimal(1) for i in items))
        self.assertEqual({i.serial_number for i in items}, {"A1", "A2", "A3"})

    def test_bulk_rejects_consumable_sheet(self):
        sheet = self._sheet("BLK2")  # consumable
        with self.assertRaises(BadRequestException):
            ItemService().create_items_bulk(
                CreateItemsBulkDTO(item_sheet_id=sheet.id, serial_numbers=["X1"])
            )

    def test_bulk_rejects_duplicate_serial_in_batch(self):
        sheet = self._sheet("BLK3", is_consumable=False, unit_type=UnitType.COUNT)
        with self.assertRaises(BadRequestException):
            ItemService().create_items_bulk(
                CreateItemsBulkDTO(item_sheet_id=sheet.id, serial_numbers=["DUP", "DUP"])
            )

    def test_bulk_allows_null_serials(self):
        sheet = self._sheet("BLK4", is_consumable=False, unit_type=UnitType.COUNT)
        items = ItemService().create_items_bulk(
            CreateItemsBulkDTO(item_sheet_id=sheet.id, serial_numbers=[None, None])
        )
        self.assertEqual(len(items), 2)
        self.assertTrue(all(i.serial_number is None for i in items))

    # ---------------------------------------------------- consumable/non-consumable guards

    def test_consume_non_consumable_raises(self):
        sheet = self._sheet("GRD1", is_consumable=False, unit_type=UnitType.COUNT)
        item = ItemService().create_items_bulk(
            CreateItemsBulkDTO(item_sheet_id=sheet.id, serial_numbers=["G1"])
        )[0]
        with self.assertRaises(BadRequestException):
            ItemService().consume_quantity(
                item.id, DecrementQuantityDTO(quantity=Decimal(1), unit="units")
            )

    def test_use_consumable_raises(self):
        item = self._create_consumable(self._sheet("GRD2"))
        with self.assertRaises(BadRequestException):
            ItemService().use_item(item.id, UseItemDTO())

    def test_use_non_consumable_ok(self):
        sheet = self._sheet("GRD3", is_consumable=False, unit_type=UnitType.COUNT)
        item = ItemService().create_items_bulk(
            CreateItemsBulkDTO(item_sheet_id=sheet.id, serial_numbers=["G3"])
        )[0]
        result = ItemService().use_item(item.id, UseItemDTO())
        self.assertIsNotNone(result.activity)

    # ------------------------------------------------------------- field coupling

    def test_consumable_with_serial_rejected(self):
        sheet = self._sheet("CPL1")  # consumable
        with self.assertRaises(BadRequestException):
            ItemService().create_item(
                CreateItemDTO(
                    item_sheet_id=sheet.id, quantity=Decimal(5), unit="mL", serial_number="NOPE"
                )
            )

    def test_non_consumable_quantity_must_be_one(self):
        sheet = self._sheet("CPL2", is_consumable=False, unit_type=UnitType.COUNT)
        with self.assertRaises(BadRequestException):
            ItemService().create_item(
                CreateItemDTO(item_sheet_id=sheet.id, quantity=Decimal(5), unit="units")
            )

    # ------------------------------------------------------------------- split

    def test_split_reduces_source_and_creates_outputs(self):
        # COUNT consumable so the base unit is "units" (factor 1) and quantities
        # stay whole numbers.
        sheet = self._sheet("SPL1", unit_type=UnitType.COUNT)
        source = self._create_consumable(sheet, quantity="10", unit="units")
        result = ItemService().split_item(
            source.id,
            SplitItemDTO(
                outputs=[
                    SplitOutputDTO(quantity=Decimal(3), unit="units"),
                    SplitOutputDTO(quantity=Decimal(4), unit="units"),
                ]
            ),
        )
        self.assertEqual(len(result.outputs), 2)
        # Source reduced in place by the sum of the outputs (10 - 7 = 3)
        self.assertEqual(ItemService().get_item(source.id).quantity, Decimal(3))
        self.assertEqual({o.quantity for o in result.outputs}, {Decimal(3), Decimal(4)})

    def test_split_full_quantity_exhausts_source(self):
        sheet = self._sheet("SPL2")
        source = self._create_consumable(sheet, quantity="5", unit="mL")
        ItemService().split_item(
            source.id, SplitItemDTO(outputs=[SplitOutputDTO(quantity=Decimal(5), unit="mL")])
        )
        self.assertEqual(ItemService().get_item(source.id).status, ItemStatus.EXHAUSTED)

    def test_split_more_than_available_fails(self):
        sheet = self._sheet("SPL3")
        source = self._create_consumable(sheet, quantity="2", unit="mL")
        with self.assertRaises(BadRequestException):
            ItemService().split_item(
                source.id, SplitItemDTO(outputs=[SplitOutputDTO(quantity=Decimal(5), unit="mL")])
            )

    def test_split_non_consumable_fails(self):
        sheet = self._sheet("SPL4", is_consumable=False, unit_type=UnitType.COUNT)
        item = ItemService().create_items_bulk(
            CreateItemsBulkDTO(item_sheet_id=sheet.id, serial_numbers=["S4"])
        )[0]
        with self.assertRaises(BadRequestException):
            ItemService().split_item(
                item.id, SplitItemDTO(outputs=[SplitOutputDTO(quantity=Decimal(1), unit="units")])
            )

    # ----------------------------------------------------------------- combine

    def test_combine_reduces_inputs_and_creates_output(self):
        item_a = self._count_item("CMBA", "10")
        item_b = self._count_item("CMBB", "10")
        out_sheet = self._sheet("CMBO", unit_type=UnitType.COUNT)
        result = ItemService().combine_items(
            CombineItemDTO(
                inputs=[
                    CombineInputDTO(item_id=item_a.id, quantity=Decimal(4), unit="units"),
                    CombineInputDTO(item_id=item_b.id, quantity=Decimal(6), unit="units"),
                ],
                output_item_sheet_id=out_sheet.id,
                output_quantity=Decimal(10),
                output_unit="units",
            )
        )
        self.assertEqual(len(result.outputs), 1)
        self.assertEqual(result.outputs[0].quantity, Decimal(10))
        # Each ingredient reduced in place by its contribution
        self.assertEqual(ItemService().get_item(item_a.id).quantity, Decimal(6))
        self.assertEqual(ItemService().get_item(item_b.id).quantity, Decimal(4))

    def test_combine_requires_two_ingredients(self):
        item_a = self._count_item("CMB1", "10")
        out_sheet = self._sheet("CMB2", unit_type=UnitType.COUNT)
        with self.assertRaises(BadRequestException):
            ItemService().combine_items(
                CombineItemDTO(
                    inputs=[CombineInputDTO(item_id=item_a.id, quantity=Decimal(1), unit="units")],
                    output_item_sheet_id=out_sheet.id,
                    output_quantity=Decimal(1),
                    output_unit="units",
                )
            )

    # ------------------------------------------------------------- concentrate

    def test_concentrate_reduces_source_and_creates_output(self):
        source = self._count_item("CON1", "10")
        result = ItemService().concentrate_item(
            source.id,
            ConcentrateItemDTO(
                quantity_contributed=Decimal(10),
                unit="units",
                output_quantity=Decimal(4),
                output_unit="units",
            ),
        )
        self.assertEqual(len(result.outputs), 1)
        self.assertEqual(result.outputs[0].quantity, Decimal(4))
        # Source fully drawn -> 0 -> EXHAUSTED
        source_after = ItemService().get_item(source.id)
        self.assertEqual(source_after.quantity, Decimal(0))
        self.assertEqual(source_after.status, ItemStatus.EXHAUSTED)

    def test_concentrate_non_consumable_fails(self):
        sheet = self._sheet("CON2", is_consumable=False, unit_type=UnitType.COUNT)
        item = ItemService().create_items_bulk(
            CreateItemsBulkDTO(item_sheet_id=sheet.id, serial_numbers=["C2"])
        )[0]
        with self.assertRaises(BadRequestException):
            ItemService().concentrate_item(
                item.id,
                ConcentrateItemDTO(
                    quantity_contributed=Decimal(1),
                    unit="units",
                    output_quantity=Decimal(1),
                    output_unit="units",
                ),
            )

    # ---------------------------------------------------------------- dilute

    def test_dilute_reduces_target_and_diluent(self):
        target = self._count_item("DIL1", "10")
        diluent = self._count_item("DIL2", "10")
        result = ItemService().dilute_item(
            target.id,
            DiluteItemDTO(
                quantity_contributed=Decimal(5),
                unit="units",
                diluents=[
                    DiluteDiluentDTO(
                        item_id=diluent.id, quantity_contributed=Decimal(5), unit="units"
                    )
                ],
                output_quantity=Decimal(10),
                output_unit="units",
            ),
        )
        self.assertEqual(len(result.outputs), 1)
        self.assertEqual(result.outputs[0].quantity, Decimal(10))
        # Both the target and the diluent are reduced in place
        self.assertEqual(ItemService().get_item(target.id).quantity, Decimal(5))
        self.assertEqual(ItemService().get_item(diluent.id).quantity, Decimal(5))

    def test_dilute_reduces_every_diluent(self):
        target = self._count_item("MDL1", "10")
        diluent_a = self._count_item("MDL2", "10")
        diluent_b = self._count_item("MDL3", "10")
        result = ItemService().dilute_item(
            target.id,
            DiluteItemDTO(
                quantity_contributed=Decimal(4),
                unit="units",
                diluents=[
                    DiluteDiluentDTO(item_id=diluent_a.id, quantity_contributed=Decimal(3), unit="units"),
                    DiluteDiluentDTO(item_id=diluent_b.id, quantity_contributed=Decimal(2), unit="units"),
                ],
                output_quantity=Decimal(9),
                output_unit="units",
            ),
        )
        self.assertEqual(len(result.outputs), 1)
        # Target and every diluent are reduced in place
        self.assertEqual(ItemService().get_item(target.id).quantity, Decimal(6))
        self.assertEqual(ItemService().get_item(diluent_a.id).quantity, Decimal(7))
        self.assertEqual(ItemService().get_item(diluent_b.id).quantity, Decimal(8))
        # Both diluents are recorded as INGREDIENT inputs (with the target)
        self.assertEqual(len(result.inputs), 3)

    def test_dilute_requires_at_least_one_diluent(self):
        target = self._count_item("NODL", "10")
        with self.assertRaises(BadRequestException):
            ItemService().dilute_item(
                target.id,
                DiluteItemDTO(
                    quantity_contributed=Decimal(5),
                    unit="units",
                    diluents=[],
                    output_quantity=Decimal(5),
                    output_unit="units",
                ),
            )

    # ----------------------------------------------------- transform instruments

    def _instrument(self, code: str, serial: str) -> Item:
        """Create a non-consumable item usable as an INSTRUMENT input."""
        sheet = self._sheet(code, is_consumable=False, unit_type=UnitType.COUNT)
        return ItemService().create_items_bulk(
            CreateItemsBulkDTO(item_sheet_id=sheet.id, serial_numbers=[serial])
        )[0]

    def _instrument_input_ids(self, activity) -> set[str]:
        """Return the item ids recorded as INSTRUMENT inputs of an activity."""
        return {
            inp.item.id
            for inp in activity.inputs
            if inp.role == ActivityInputRole.INSTRUMENT
        }

    def test_consume_records_instruments(self):
        source = self._count_item("INCS", "10")
        balance = self._instrument("INSB", "BAL-1")
        result = ItemService().consume_quantity(
            source.id,
            DecrementQuantityDTO(
                quantity=Decimal(3), unit="units", instrument_item_ids=[balance.id]
            ),
        )
        self.assertEqual(self._instrument_input_ids(result.activity), {balance.id})

    def test_split_records_instruments(self):
        sheet = self._sheet("INS1", unit_type=UnitType.COUNT)
        source = self._create_consumable(sheet, quantity="10", unit="units")
        pipette = self._instrument("INSP", "PIP-1")
        result = ItemService().split_item(
            source.id,
            SplitItemDTO(
                outputs=[SplitOutputDTO(quantity=Decimal(3), unit="units")],
                instrument_item_ids=[pipette.id],
            ),
        )
        self.assertEqual(self._instrument_input_ids(result.activity), {pipette.id})

    def test_combine_records_instruments(self):
        item_a = self._count_item("INCA", "10")
        item_b = self._count_item("INCB", "10")
        out_sheet = self._sheet("INCO", unit_type=UnitType.COUNT)
        centrifuge = self._instrument("INCI", "CEN-1")
        result = ItemService().combine_items(
            CombineItemDTO(
                inputs=[
                    CombineInputDTO(item_id=item_a.id, quantity=Decimal(4), unit="units"),
                    CombineInputDTO(item_id=item_b.id, quantity=Decimal(6), unit="units"),
                ],
                output_item_sheet_id=out_sheet.id,
                output_quantity=Decimal(10),
                output_unit="units",
                instrument_item_ids=[centrifuge.id],
            )
        )
        self.assertEqual(self._instrument_input_ids(result.activity), {centrifuge.id})

    def test_concentrate_records_instruments(self):
        source = self._count_item("INCC", "10")
        rotovap = self._instrument("INCR", "ROT-1")
        result = ItemService().concentrate_item(
            source.id,
            ConcentrateItemDTO(
                quantity_contributed=Decimal(5),
                unit="units",
                output_quantity=Decimal(4),
                output_unit="units",
                instrument_item_ids=[rotovap.id],
            ),
        )
        self.assertEqual(self._instrument_input_ids(result.activity), {rotovap.id})

    def test_dilute_records_instruments(self):
        target = self._count_item("INDT", "10")
        diluent = self._count_item("INDD", "10")
        vortex = self._instrument("INDV", "VTX-1")
        result = ItemService().dilute_item(
            target.id,
            DiluteItemDTO(
                quantity_contributed=Decimal(5),
                unit="units",
                diluents=[
                    DiluteDiluentDTO(
                        item_id=diluent.id, quantity_contributed=Decimal(5), unit="units"
                    )
                ],
                output_quantity=Decimal(10),
                output_unit="units",
                instrument_item_ids=[vortex.id],
            ),
        )
        self.assertEqual(self._instrument_input_ids(result.activity), {vortex.id})

    def test_transform_instrument_must_be_non_consumable(self):
        # A consumable item cannot be recorded as an INSTRUMENT input.
        source = self._count_item("INMA", "10")
        consumable = self._count_item("INMB", "10")
        with self.assertRaises(BadRequestException):
            ItemService().split_item(
                source.id,
                SplitItemDTO(
                    outputs=[SplitOutputDTO(quantity=Decimal(1), unit="units")],
                    instrument_item_ids=[consumable.id],
                ),
            )

    def test_transform_instrument_discarded_rejected(self):
        source = self._count_item("INDA", "10")
        instrument = self._instrument("INDI", "DIS-1")
        ItemService().discard_item(instrument.id, DiscardItemDTO())
        with self.assertRaises(BadRequestException):
            ItemService().split_item(
                source.id,
                SplitItemDTO(
                    outputs=[SplitOutputDTO(quantity=Decimal(1), unit="units")],
                    instrument_item_ids=[instrument.id],
                ),
            )

    # -------------------------------------------------------------- move / update

    def test_move_changes_location(self):
        item = self._create_consumable(self._sheet("MOV1"))
        fridge = LocationService().create_location(CreateLocationDTO(name="Fridge MOV1"))
        ItemService().move_item(item.id, MoveItemDTO(to_location_id=fridge.id))
        self.assertEqual(ItemService().get_item(item.id).location.id, fridge.id)

    def test_update_item_metadata(self):
        item = self._create_consumable(self._sheet("UPD1"))
        ItemService().update_item(item.id, UpdateItemDTO(notes="updated note"))
        self.assertEqual(ItemService().get_item(item.id).notes, "updated note")

    # ------------------------------------------------------------------- delete

    def test_delete_item_without_history_is_hard_deleted(self):
        item = self._create_consumable(self._sheet("DEL1"))
        result = ItemService().delete_item(item.id)
        self.assertEqual(result, DeleteItemResultDTO.DELETED)

    def test_delete_item_with_history_is_discarded(self):
        item = self._create_consumable(self._sheet("DEL2"), quantity="10", unit="mL")
        # A consume adds activity history, so the item is soft-deleted (discarded).
        ItemService().consume_quantity(item.id, DecrementQuantityDTO(quantity=Decimal(2), unit="mL"))
        result = ItemService().delete_item(item.id, notes="no longer needed")
        self.assertEqual(result, DeleteItemResultDTO.DISCARDED)
        self.assertEqual(ItemService().get_item(item.id).status, ItemStatus.DISCARDED)
