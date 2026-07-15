"""Test suite for ItemService.

Covers the Item user story: structured code generation (format, per-sheet
increment, width-4 padding, >9999 overflow, concurrency retry), status recompute
(ACTIVE / EXHAUSTED / DISCARDED), serial-number uniqueness, bulk creation,
consumable/non-consumable guards, and field-coupling validation.
"""

from decimal import Decimal
from unittest.mock import patch

from gws_core import BadRequestException, BaseTestCase
from gws_eln.activities.activity_input_role import ActivityInputRole
from gws_eln.core.concentration_method import ConcentrationMethod
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
    TransformInputDTO,
    TransformItemsDTO,
    TransformOutputDTO,
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
        kwargs.setdefault("label", "Test item")
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

    def _concentration_item(
        self, code: str, quantity: str = "10", concentration: str = "2"
    ) -> Item:
        """Create a VOLUME consumable item with a concentration.

        Dilute/concentrate require the source/target to already carry a
        concentration. 'L' (base unit, factor 1) keeps the quantity maths whole.
        """
        return self._create_consumable(
            self._sheet(code, unit_type=UnitType.VOLUME),
            quantity=quantity,
            unit="L",
            concentration=Decimal(concentration),
            concentration_unit="g/L",
        )

    def _volume_item(self, code: str, quantity: str = "10") -> Item:
        """Create a plain VOLUME consumable item (no concentration), e.g. a diluent."""
        return self._create_consumable(
            self._sheet(code, unit_type=UnitType.VOLUME), quantity=quantity, unit="L"
        )

    def _save_raw_item(self, sheet, code: str) -> Item:
        """Persist an item with a chosen code (to set up code-generation edge cases)."""
        item = Item()
        item.item_sheet = sheet
        item.code = code
        item.label = "Raw item"
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
        self.assertEqual(first.code, "CGN1-0001")
        self.assertEqual(second.code, "CGN1-0002")

    def test_code_increment_scoped_per_sheet(self):
        sheet_a = self._sheet("CGN2")
        sheet_b = self._sheet("CGN3")
        item_a = self._create_consumable(sheet_a)
        item_b = self._create_consumable(sheet_b)
        # Independent counters per sheet
        self.assertEqual(item_a.code, "CGN2-0001")
        self.assertEqual(item_b.code, "CGN3-0001")

    def test_code_overflow_past_9999(self):
        sheet = self._sheet("COVF")
        self._save_raw_item(sheet, code="COVF-9999")
        nxt = self._create_consumable(sheet)
        self.assertEqual(nxt.code, "COVF-10000")

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
        first = self._create_consumable(sheet)  # CRTY-0001

        service = ItemService()
        # First generation returns an already-used code (collision), then a free one.
        codes = iter([first.code, f"{sheet.code}-0002"])
        with patch.object(service, "_generate_item_code", side_effect=lambda *_a, **_k: next(codes)):
            item = service.create_item(
                CreateItemDTO(item_sheet_id=sheet.id, quantity=Decimal(5), unit="mL", label="Test item")
            ).item
        self.assertEqual(item.code, f"{sheet.code}-0002")

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
            CreateItemsBulkDTO(item_sheet_id=sheet.id, serial_numbers=["NX1"], label="Test item")
        )
        self.assertEqual(items[0].status, ItemStatus.ACTIVE)

    # ------------------------------------------------------------- serial uniqueness

    def test_serial_unique_lab_wide(self):
        sheet = self._sheet("SER1", is_consumable=False, unit_type=UnitType.COUNT)
        ItemService().create_items_bulk(
            CreateItemsBulkDTO(item_sheet_id=sheet.id, serial_numbers=["UNIQ-1"], label="Test item")
        )
        with self.assertRaises(BadRequestException):
            ItemService().create_items_bulk(
                CreateItemsBulkDTO(item_sheet_id=sheet.id, serial_numbers=["UNIQ-1"], label="Test item")
            )

    def test_serial_set_and_duplicate_via_create_item(self):
        sheet = self._sheet("SER2", is_consumable=False, unit_type=UnitType.COUNT)
        item = ItemService().create_item(
            CreateItemDTO(
                item_sheet_id=sheet.id, quantity=Decimal(1), unit="units", serial_number="SVC-1",
                label="Test item"
            )
        ).item
        self.assertEqual(item.serial_number, "SVC-1")
        with self.assertRaises(BadRequestException):
            ItemService().create_item(
                CreateItemDTO(
                    item_sheet_id=sheet.id, quantity=Decimal(1), unit="units", serial_number="SVC-1",
                    label="Test item"
                )
            )

    # --------------------------------------------------------------- bulk creation

    def test_bulk_creates_sequential_items(self):
        sheet = self._sheet("BLK1", is_consumable=False, unit_type=UnitType.COUNT)
        items = ItemService().create_items_bulk(
            CreateItemsBulkDTO(item_sheet_id=sheet.id, serial_numbers=["A1", "A2", "A3"], label="Test item")
        )
        self.assertEqual(len(items), 3)
        self.assertEqual(
            sorted(i.code for i in items),
            [f"BLK1-000{n}" for n in (1, 2, 3)],
        )
        self.assertTrue(all(i.quantity == Decimal(1) for i in items))
        self.assertEqual({i.serial_number for i in items}, {"A1", "A2", "A3"})

    def test_bulk_rejects_consumable_sheet(self):
        sheet = self._sheet("BLK2")  # consumable
        with self.assertRaises(BadRequestException):
            ItemService().create_items_bulk(
                CreateItemsBulkDTO(item_sheet_id=sheet.id, serial_numbers=["X1"], label="Test item")
            )

    def test_bulk_rejects_duplicate_serial_in_batch(self):
        sheet = self._sheet("BLK3", is_consumable=False, unit_type=UnitType.COUNT)
        with self.assertRaises(BadRequestException):
            ItemService().create_items_bulk(
                CreateItemsBulkDTO(item_sheet_id=sheet.id, serial_numbers=["DUP", "DUP"], label="Test item")
            )

    def test_bulk_allows_null_serials(self):
        # Serial-less units are indistinguishable: they collapse into a single
        # stacked item whose quantity is their count.
        sheet = self._sheet("BLK4", is_consumable=False, unit_type=UnitType.COUNT)
        items = ItemService().create_items_bulk(
            CreateItemsBulkDTO(item_sheet_id=sheet.id, serial_numbers=[None, None], label="Test item")
        )
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].quantity, Decimal(2))
        self.assertIsNone(items[0].serial_number)

    # ---------------------------------------------------- consumable/non-consumable guards

    def test_consume_non_consumable_raises(self):
        sheet = self._sheet("GRD1", is_consumable=False, unit_type=UnitType.COUNT)
        item = ItemService().create_items_bulk(
            CreateItemsBulkDTO(item_sheet_id=sheet.id, serial_numbers=["G1"], label="Test item")
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
            CreateItemsBulkDTO(item_sheet_id=sheet.id, serial_numbers=["G3"], label="Test item")
        )[0]
        result = ItemService().use_item(item.id, UseItemDTO())
        self.assertIsNotNone(result.activity)

    # ------------------------------------------------------------- label required

    def test_create_item_requires_label(self):
        """A blank label is rejected by the service."""
        sheet = self._sheet("LBL1")
        with self.assertRaises(BadRequestException):
            ItemService().create_item(
                CreateItemDTO(item_sheet_id=sheet.id, quantity=Decimal(5), unit="mL", label="   ")
            )

    def test_create_item_allows_duplicate_labels(self):
        """Two items on the same sheet may share the same label."""
        sheet = self._sheet("LBL2")
        first = self._create_consumable(sheet, label="Shared label")
        second = self._create_consumable(sheet, label="Shared label")
        self.assertEqual(first.label, "Shared label")
        self.assertEqual(second.label, "Shared label")
        self.assertNotEqual(first.id, second.id)

    # ------------------------------------------------------------- field coupling

    def test_consumable_with_serial_rejected(self):
        sheet = self._sheet("CPL1")  # consumable
        with self.assertRaises(BadRequestException):
            ItemService().create_item(
                CreateItemDTO(
                    item_sheet_id=sheet.id, quantity=Decimal(5), unit="mL", serial_number="NOPE",
                    label="Test item"
                )
            )

    def test_non_consumable_serialized_quantity_must_be_one(self):
        # A serialized non-consumable unit is one physical thing: quantity must be 1.
        # (Serial-less units may be stacked with quantity > 1.)
        sheet = self._sheet("CPL2", is_consumable=False, unit_type=UnitType.COUNT)
        with self.assertRaises(BadRequestException):
            ItemService().create_item(
                CreateItemDTO(
                    item_sheet_id=sheet.id, quantity=Decimal(5), unit="units",
                    serial_number="SER-5", label="Test item"
                )
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
                quantity_contributed=Decimal(7),
                unit="units",
                outputs=[
                    SplitOutputDTO(quantity=Decimal(3), unit="units", label="Output A"),
                    SplitOutputDTO(quantity=Decimal(4), unit="units", label="Output B"),
                ],
            ),
        )
        self.assertEqual(len(result.outputs), 2)
        # Source reduced in place by the consumed quantity (10 - 7 = 3)
        self.assertEqual(ItemService().get_item(source.id).quantity, Decimal(3))
        self.assertEqual({o.quantity for o in result.outputs}, {Decimal(3), Decimal(4)})

    def test_split_loss_reduces_source_by_full_consumed_quantity(self):
        # Outputs may sum to less than the consumed quantity; the remainder is
        # lost (the source is still reduced by the full consumed amount).
        sheet = self._sheet("SPLW", unit_type=UnitType.COUNT)
        source = self._create_consumable(sheet, quantity="10", unit="units")
        result = ItemService().split_item(
            source.id,
            SplitItemDTO(
                quantity_contributed=Decimal(8),
                unit="units",
                outputs=[
                    SplitOutputDTO(quantity=Decimal(3), unit="units", label="Output A"),
                    SplitOutputDTO(quantity=Decimal(4), unit="units", label="Output B"),
                ],
            ),
        )
        self.assertEqual(len(result.outputs), 2)
        # Source reduced by the full 8 consumed (10 - 8 = 2), 1 unit lost.
        self.assertEqual(ItemService().get_item(source.id).quantity, Decimal(2))

    def test_split_outputs_exceeding_consumed_fails(self):
        sheet = self._sheet("SPLX", unit_type=UnitType.COUNT)
        source = self._create_consumable(sheet, quantity="10", unit="units")
        with self.assertRaises(BadRequestException):
            ItemService().split_item(
                source.id,
                SplitItemDTO(
                    quantity_contributed=Decimal(5),
                    unit="units",
                    outputs=[
                        SplitOutputDTO(quantity=Decimal(3), unit="units", label="Output A"),
                        SplitOutputDTO(quantity=Decimal(4), unit="units", label="Output B"),
                    ],
                ),
            )

    def test_split_full_quantity_exhausts_source(self):
        sheet = self._sheet("SPL2")
        source = self._create_consumable(sheet, quantity="5", unit="mL")
        ItemService().split_item(
            source.id,
            SplitItemDTO(
                quantity_contributed=Decimal(5),
                unit="mL",
                outputs=[SplitOutputDTO(quantity=Decimal(5), unit="mL", label="Output")],
            ),
        )
        self.assertEqual(ItemService().get_item(source.id).status, ItemStatus.EXHAUSTED)

    def test_split_more_than_available_fails(self):
        sheet = self._sheet("SPL3")
        source = self._create_consumable(sheet, quantity="2", unit="mL")
        with self.assertRaises(BadRequestException):
            ItemService().split_item(
                source.id,
                SplitItemDTO(
                    quantity_contributed=Decimal(5),
                    unit="mL",
                    outputs=[SplitOutputDTO(quantity=Decimal(5), unit="mL", label="Output")],
                ),
            )

    def test_split_non_consumable_fails(self):
        sheet = self._sheet("SPL4", is_consumable=False, unit_type=UnitType.COUNT)
        item = ItemService().create_items_bulk(
            CreateItemsBulkDTO(item_sheet_id=sheet.id, serial_numbers=["S4"], label="Test item")
        )[0]
        with self.assertRaises(BadRequestException):
            ItemService().split_item(
                item.id,
                SplitItemDTO(
                    quantity_contributed=Decimal(1),
                    unit="units",
                    outputs=[SplitOutputDTO(quantity=Decimal(1), unit="units", label="Output")],
                ),
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
                output_label="Combined output",
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
                    output_label="Combined output",
                )
            )

    # ------------------------------------------------------------- concentrate

    def test_concentrate_reduces_source_and_creates_output(self):
        source = self._concentration_item("CON1", "10")
        result = ItemService().concentrate_item(
            source.id,
            ConcentrateItemDTO(
                quantity_contributed=Decimal(10),
                unit="L",
                output_quantity=Decimal(4),
                output_unit="L",
                output_label="Concentrated output",
            ),
        )
        self.assertEqual(len(result.outputs), 1)
        self.assertEqual(result.outputs[0].quantity, Decimal(4))
        # Source fully drawn -> 0 -> EXHAUSTED
        source_after = ItemService().get_item(source.id)
        self.assertEqual(source_after.quantity, Decimal(0))
        self.assertEqual(source_after.status, ItemStatus.EXHAUSTED)

    def test_concentrate_persists_concentration_method(self):
        source = self._concentration_item("CONM", "10")
        result = ItemService().concentrate_item(
            source.id,
            ConcentrateItemDTO(
                quantity_contributed=Decimal(10),
                unit="L",
                output_quantity=Decimal(4),
                output_unit="L",
                concentration_method=ConcentrationMethod.LYOPHILIZATION,
                output_label="Concentrated output",
            ),
        )
        self.assertEqual(
            result.activity.concentration_method, ConcentrationMethod.LYOPHILIZATION
        )

    def test_concentrate_non_consumable_fails(self):
        sheet = self._sheet("CON2", is_consumable=False, unit_type=UnitType.COUNT)
        item = ItemService().create_items_bulk(
            CreateItemsBulkDTO(item_sheet_id=sheet.id, serial_numbers=["C2"], label="Test item")
        )[0]
        with self.assertRaises(BadRequestException):
            ItemService().concentrate_item(
                item.id,
                ConcentrateItemDTO(
                    quantity_contributed=Decimal(1),
                    unit="units",
                    output_quantity=Decimal(1),
                    output_unit="units",
                    output_label="Concentrated output",
                ),
            )

    # ---------------------------------------------------------------- dilute

    def test_dilute_reduces_target_and_diluent(self):
        target = self._concentration_item("DIL1", "10")
        diluent = self._volume_item("DIL2", "10")
        result = ItemService().dilute_item(
            target.id,
            DiluteItemDTO(
                quantity_contributed=Decimal(5),
                unit="L",
                diluents=[
                    DiluteDiluentDTO(
                        item_id=diluent.id, quantity_contributed=Decimal(5), unit="L"
                    )
                ],
                output_quantity=Decimal(10),
                output_unit="L",
                output_label="Diluted output",
            ),
        )
        self.assertEqual(len(result.outputs), 1)
        self.assertEqual(result.outputs[0].quantity, Decimal(10))
        # Both the target and the diluent are reduced in place
        self.assertEqual(ItemService().get_item(target.id).quantity, Decimal(5))
        self.assertEqual(ItemService().get_item(diluent.id).quantity, Decimal(5))

    def test_dilute_reduces_every_diluent(self):
        target = self._concentration_item("MDL1", "10")
        diluent_a = self._volume_item("MDL2", "10")
        diluent_b = self._volume_item("MDL3", "10")
        result = ItemService().dilute_item(
            target.id,
            DiluteItemDTO(
                quantity_contributed=Decimal(4),
                unit="L",
                diluents=[
                    DiluteDiluentDTO(item_id=diluent_a.id, quantity_contributed=Decimal(3), unit="L"),
                    DiluteDiluentDTO(item_id=diluent_b.id, quantity_contributed=Decimal(2), unit="L"),
                ],
                output_quantity=Decimal(9),
                output_unit="L",
                output_label="Diluted output",
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
                    output_label="Diluted output",
                ),
            )

    # ----------------------------------------------------- transform instruments

    def _instrument(self, code: str, serial: str) -> Item:
        """Create a non-consumable item usable as an INSTRUMENT input."""
        sheet = self._sheet(code, is_consumable=False, unit_type=UnitType.COUNT)
        return ItemService().create_items_bulk(
            CreateItemsBulkDTO(item_sheet_id=sheet.id, serial_numbers=[serial], label="Test item")
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
                quantity_contributed=Decimal(3),
                unit="units",
                outputs=[SplitOutputDTO(quantity=Decimal(3), unit="units", label="Output")],
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
                output_label="Combined output",
                instrument_item_ids=[centrifuge.id],
            )
        )
        self.assertEqual(self._instrument_input_ids(result.activity), {centrifuge.id})

    def test_concentrate_records_instruments(self):
        source = self._concentration_item("INCC", "10")
        rotovap = self._instrument("INCR", "ROT-1")
        result = ItemService().concentrate_item(
            source.id,
            ConcentrateItemDTO(
                quantity_contributed=Decimal(5),
                unit="L",
                output_quantity=Decimal(4),
                output_unit="L",
                output_label="Concentrated output",
                instrument_item_ids=[rotovap.id],
            ),
        )
        self.assertEqual(self._instrument_input_ids(result.activity), {rotovap.id})

    def test_dilute_records_instruments(self):
        target = self._concentration_item("INDT", "10")
        diluent = self._volume_item("INDD", "10")
        vortex = self._instrument("INDV", "VTX-1")
        result = ItemService().dilute_item(
            target.id,
            DiluteItemDTO(
                quantity_contributed=Decimal(5),
                unit="L",
                diluents=[
                    DiluteDiluentDTO(
                        item_id=diluent.id, quantity_contributed=Decimal(5), unit="L"
                    )
                ],
                output_quantity=Decimal(10),
                output_unit="L",
                output_label="Diluted output",
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
                    quantity_contributed=Decimal(1),
                    unit="units",
                    outputs=[SplitOutputDTO(quantity=Decimal(1), unit="units", label="Output")],
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
                    quantity_contributed=Decimal(1),
                    unit="units",
                    outputs=[SplitOutputDTO(quantity=Decimal(1), unit="units", label="Output")],
                    instrument_item_ids=[instrument.id],
                ),
            )

    # -------------------------------------------- transform_items (generic N->M)

    def _ingredient_input_ids(self, activity) -> set[str]:
        """Return the item ids recorded as INGREDIENT inputs of an activity."""
        return {
            inp.item.id for inp in activity.inputs if inp.role == ActivityInputRole.INGREDIENT
        }

    def test_transform_reduces_consumables_records_instruments_and_creates_outputs(self):
        # N inputs (one consumable ingredient + one instrument) -> M outputs.
        consumable = self._count_item("TRF1", "10")
        instrument = self._instrument("TRFI", "TRF-1")
        out_sheet_a = self._sheet("TRFA", unit_type=UnitType.COUNT)
        out_sheet_b = self._sheet("TRFB", unit_type=UnitType.COUNT)
        result = ItemService().transform_items(
            TransformItemsDTO(
                inputs=[
                    TransformInputDTO(item_id=consumable.id, quantity=Decimal(4), unit="units"),
                    TransformInputDTO(item_id=instrument.id),
                ],
                outputs=[
                    TransformOutputDTO(
                        output_item_sheet_id=out_sheet_a.id, quantity=Decimal(3),
                        unit="units", label="Out A",
                    ),
                    TransformOutputDTO(
                        output_item_sheet_id=out_sheet_b.id, quantity=Decimal(7),
                        unit="units", label="Out B",
                    ),
                ],
            )
        )
        # Both outputs created with their own user-entered quantities.
        self.assertEqual(len(result.outputs), 2)
        self.assertEqual(sorted(o.quantity for o in result.outputs), [Decimal(3), Decimal(7)])
        # Consumable reduced in place; the instrument is untouched.
        self.assertEqual(ItemService().get_item(consumable.id).quantity, Decimal(6))
        self.assertEqual(ItemService().get_item(instrument.id).quantity, Decimal(1))
        # Roles: consumable -> INGREDIENT, non-consumable -> INSTRUMENT.
        self.assertEqual(self._ingredient_input_ids(result.activity), {consumable.id})
        self.assertEqual(self._instrument_input_ids(result.activity), {instrument.id})

    def test_transform_requires_at_least_one_input(self):
        out_sheet = self._sheet("TRNI", unit_type=UnitType.COUNT)
        with self.assertRaises(BadRequestException):
            ItemService().transform_items(
                TransformItemsDTO(
                    inputs=[],
                    outputs=[
                        TransformOutputDTO(
                            output_item_sheet_id=out_sheet.id, quantity=Decimal(1),
                            unit="units", label="Out",
                        )
                    ],
                )
            )

    def test_transform_requires_at_least_one_output(self):
        source = self._count_item("TRNO", "10")
        with self.assertRaises(BadRequestException):
            ItemService().transform_items(
                TransformItemsDTO(
                    inputs=[
                        TransformInputDTO(item_id=source.id, quantity=Decimal(1), unit="units")
                    ],
                    outputs=[],
                )
            )

    def test_transform_consumable_input_requires_quantity(self):
        # A consumable input with no quantity/unit is rejected.
        consumable = self._count_item("TRNQ", "10")
        out_sheet = self._sheet("TRNR", unit_type=UnitType.COUNT)
        with self.assertRaises(BadRequestException):
            ItemService().transform_items(
                TransformItemsDTO(
                    inputs=[TransformInputDTO(item_id=consumable.id)],
                    outputs=[
                        TransformOutputDTO(
                            output_item_sheet_id=out_sheet.id, quantity=Decimal(1),
                            unit="units", label="Out",
                        )
                    ],
                )
            )

    # ------------------------------------------------- concentration preconditions

    def test_concentrate_requires_a_concentration(self):
        # An item with no recorded concentration cannot be concentrated.
        source = self._count_item("CONX", "10")
        with self.assertRaises(BadRequestException):
            ItemService().concentrate_item(
                source.id,
                ConcentrateItemDTO(
                    quantity_contributed=Decimal(5), unit="units",
                    output_quantity=Decimal(2), output_unit="units",
                    output_label="Concentrated output",
                ),
            )

    def test_dilute_requires_a_concentration(self):
        # A target with no recorded concentration cannot be diluted.
        target = self._count_item("DILX", "10")
        diluent = self._volume_item("DILY", "10")
        with self.assertRaises(BadRequestException):
            ItemService().dilute_item(
                target.id,
                DiluteItemDTO(
                    quantity_contributed=Decimal(5), unit="units",
                    diluents=[
                        DiluteDiluentDTO(item_id=diluent.id, quantity_contributed=Decimal(5), unit="L")
                    ],
                    output_quantity=Decimal(10), output_unit="units",
                    output_label="Diluted output",
                ),
            )

    def test_split_outputs_inherit_source_concentration(self):
        # Concentration is intensive: split outputs inherit the source's unchanged.
        source = self._concentration_item("SPLC", "10")
        result = ItemService().split_item(
            source.id,
            SplitItemDTO(
                quantity_contributed=Decimal(6),
                unit="L",
                outputs=[SplitOutputDTO(quantity=Decimal(3), unit="L", label="Out")],
            ),
        )
        output = result.outputs[0]
        self.assertEqual(output.concentration, source.concentration)
        self.assertEqual(output.concentration_unit, source.concentration_unit)

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

    # ------------------------------------------------------------- batch / lot numbers

    def _count_item_with_batch(self, code: str, batch_number: str, quantity: str = "10") -> Item:
        """Create a COUNT origin item carrying a single lot number."""
        return self._create_consumable(
            self._sheet(code, unit_type=UnitType.COUNT),
            quantity=quantity,
            unit="units",
            batch_number=batch_number,
        )

    def test_create_item_stores_single_batch_number(self):
        item = self._create_consumable(self._sheet("BAT1"), batch_number="LOT-A")
        self.assertEqual(item.batch_number, "LOT-A")
        # An origin item's lots are just its own single lot.
        self.assertEqual(ItemService().get_batch_numbers(item.id), ["LOT-A"])

    def test_create_item_without_batch_number_has_no_lots(self):
        item = self._create_consumable(self._sheet("BAT2"))
        self.assertIsNone(item.batch_number)
        self.assertEqual(ItemService().get_batch_numbers(item.id), [])

    def test_create_items_bulk_shares_batch_number(self):
        sheet = self._sheet("BAT3", is_consumable=False, unit_type=UnitType.COUNT)
        items = ItemService().create_items_bulk(
            CreateItemsBulkDTO(
                item_sheet_id=sheet.id, serial_numbers=["S1", "S2"],
                batch_number="LOT-B", label="Test item",
            )
        )
        self.assertTrue(all(i.batch_number == "LOT-B" for i in items))

    def test_derived_item_inherits_union_of_parents_batch_numbers(self):
        # Combine two origins carrying different lots: the output carries no own
        # lot, and its lots are the union of its ancestors' (derived from lineage).
        item_a = self._count_item_with_batch("BAT4", "LOT-A")
        item_b = self._count_item_with_batch("BAT5", "LOT-B")
        out_sheet = self._sheet("BAT6", unit_type=UnitType.COUNT)
        result = ItemService().combine_items(
            CombineItemDTO(
                inputs=[
                    CombineInputDTO(item_id=item_a.id, quantity=Decimal(4), unit="units"),
                    CombineInputDTO(item_id=item_b.id, quantity=Decimal(6), unit="units"),
                ],
                output_item_sheet_id=out_sheet.id,
                output_quantity=Decimal(10),
                output_unit="units",
                output_label="Combined output",
            )
        )
        output = result.outputs[0]
        self.assertIsNone(output.batch_number)
        self.assertEqual(ItemService().get_batch_numbers(output.id), ["LOT-A", "LOT-B"])

    def test_derived_item_deduplicates_shared_batch_number(self):
        # Two parents sharing the same lot yield that lot once (union, sorted).
        item_a = self._count_item_with_batch("BAT7", "LOT-X")
        item_b = self._count_item_with_batch("BAT8", "LOT-X")
        out_sheet = self._sheet("BAT9", unit_type=UnitType.COUNT)
        result = ItemService().combine_items(
            CombineItemDTO(
                inputs=[
                    CombineInputDTO(item_id=item_a.id, quantity=Decimal(5), unit="units"),
                    CombineInputDTO(item_id=item_b.id, quantity=Decimal(5), unit="units"),
                ],
                output_item_sheet_id=out_sheet.id,
                output_quantity=Decimal(10),
                output_unit="units",
                output_label="Combined output",
            )
        )
        self.assertEqual(ItemService().get_batch_numbers(result.outputs[0].id), ["LOT-X"])
