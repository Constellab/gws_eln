"""Test suite for LineageRepo.

Covers the request-scoped DB cache used to build the lineage DAG: the in/out
accessors, INGREDIENT-only filtering, instrument exclusion, batched loading,
empty-bucket behaviour for unknown ids, and that loaded rows are served from
memory (not re-queried).
"""

from decimal import Decimal

from gws_core import BaseTestCase
from gws_eln.activities.activity_input import ActivityInput
from gws_eln.activities.activity_type import ActivityType
from gws_eln.core.unit_type import UnitType
from gws_eln.items.item import Item
from gws_eln.items.item_dto import (
    CombineInputDTO,
    CombineItemDTO,
    CreateItemDTO,
    CreateItemsBulkDTO,
    SplitItemDTO,
    SplitOutputDTO,
)
from gws_eln.items.item_service import ItemService
from gws_eln.items.item_sheet_dto import CreateItemSheetDTO
from gws_eln.items.item_sheet_service import ItemSheetService
from gws_eln.lineage.lineage_repo import LineageRepo
from gws_eln.user.eln_user_sync_service import ElnUserSyncService


class TestLineageRepo(BaseTestCase):
    """Test suite for LineageRepo."""

    @classmethod
    def init_before_test(cls):
        super().init_before_test()
        ElnUserSyncService().sync_all_users()

    # ------------------------------------------------------------------ helpers

    def _sheet(self, code: str, *, is_consumable: bool = True):
        return ItemSheetService().create_item_sheet(
            CreateItemSheetDTO(
                name=f"Sheet {code}",
                code=code,
                is_consumable=is_consumable,
                unit_type=UnitType.COUNT,
            )
        )

    def _count_item(self, code: str, quantity: str = "10") -> Item:
        return ItemService().create_item(
            CreateItemDTO(
                item_sheet_id=self._sheet(code).id,
                quantity=Decimal(quantity),
                unit="units",
            )
        ).item

    def _instrument(self, code: str) -> Item:
        sheet = self._sheet(code, is_consumable=False)
        return ItemService().create_items_bulk(
            CreateItemsBulkDTO(item_sheet_id=sheet.id, serial_numbers=[f"{code}-1"])
        )[0]

    def _combine(self, item_a, item_b, out_code: str, instrument_ids=None, draw: int = 4) -> Item:
        out_sheet = self._sheet(out_code)
        result = ItemService().combine_items(
            CombineItemDTO(
                inputs=[
                    CombineInputDTO(item_id=item_a.id, quantity=Decimal(draw), unit="units"),
                    CombineInputDTO(item_id=item_b.id, quantity=Decimal(draw), unit="units"),
                ],
                output_item_sheet_id=out_sheet.id,
                output_quantity=Decimal(2 * draw),
                output_unit="units",
                instrument_item_ids=instrument_ids or [],
            )
        )
        return result.outputs[0]

    def _split(self, source, out_codes) -> list[Item]:
        result = ItemService().split_item(
            source.id,
            SplitItemDTO(
                outputs=[SplitOutputDTO(quantity=Decimal(1), unit="units") for _ in out_codes]
            ),
        )
        return result.outputs

    def _only(self, ids: list[str]) -> str:
        """Assert a single-element list and return its element."""
        self.assertEqual(len(ids), 1)
        return ids[0]

    # -------------------------------------------------------------------- tests

    def test_ingredient_inputs_and_outputs(self):
        """A combine activity exposes its two ingredient inputs and one output."""
        a = self._count_item("RPAX")
        b = self._count_item("RPBX")
        d = self._combine(a, b, "RPDX")

        repo = LineageRepo()
        combine_id = self._only(repo.activity_ids_with_input_item(a.id))

        self.assertEqual({i.item_id for i in repo.ingredient_inputs(combine_id)}, {a.id, b.id})
        self.assertEqual({o.item_id for o in repo.outputs(combine_id)}, {d.id})

    def test_activity_type(self):
        """activity_type resolves the type of combine and split activities."""
        a = self._count_item("RTAX")
        b = self._count_item("RTBX")
        d = self._combine(a, b, "RTDX")
        self._split(d, ["x", "y"])

        repo = LineageRepo()
        combine_id = self._only(repo.activity_ids_with_input_item(a.id))
        split_id = self._only(repo.activity_ids_with_input_item(d.id))

        self.assertEqual(repo.activity_type(combine_id), ActivityType.COMBINE)
        self.assertEqual(repo.activity_type(split_id), ActivityType.SPLIT)

    def test_instrument_input_excluded(self):
        """An INSTRUMENT input is not an ingredient input, of any activity."""
        a = self._count_item("RIAX")
        b = self._count_item("RIBX")
        instrument = self._instrument("RINX")
        self._combine(a, b, "RIDX", instrument_ids=[instrument.id])

        repo = LineageRepo()
        combine_id = self._only(repo.activity_ids_with_input_item(a.id))

        self.assertEqual({i.item_id for i in repo.ingredient_inputs(combine_id)}, {a.id, b.id})
        self.assertEqual(repo.activity_ids_with_input_item(instrument.id), [])

    def test_adjacency_lookups(self):
        """Both combine inputs map to the same activity; its output maps back."""
        a = self._count_item("RAAX")
        b = self._count_item("RABX")
        d = self._combine(a, b, "RADX")

        repo = LineageRepo()
        combine_id = self._only(repo.activity_ids_with_input_item(a.id))

        self.assertEqual(repo.activity_ids_with_input_item(b.id), [combine_id])
        self.assertEqual(repo.activity_ids_with_output_item(d.id), [combine_id])

    def test_activity_ids_by_input_items_batched(self):
        """A whole frontier resolves to its activities in one batched lookup."""
        a = self._count_item("RFAX")
        b = self._count_item("RFBX")
        d = self._combine(a, b, "RFDX")

        repo = LineageRepo()
        combine_id = self._only(repo.activity_ids_with_output_item(d.id))

        # Both inputs map to the combine; an unrelated item maps to nothing.
        result = repo.activity_ids_by_input_items([a.id, b.id, d.id])
        self.assertEqual(result[a.id], [combine_id])
        self.assertEqual(result[b.id], [combine_id])
        self.assertEqual(result[d.id], [])

    def test_load_activities_batch(self):
        """load_activities warms several activities at once for memory reads."""
        a = self._count_item("RBAX")
        b = self._count_item("RBBX")
        d = self._combine(a, b, "RBDX")
        d1, d2 = self._split(d, ["x", "y"])

        repo = LineageRepo()
        combine_id = self._only(repo.activity_ids_with_input_item(a.id))
        split_id = self._only(repo.activity_ids_with_input_item(d.id))

        repo.load_activities([combine_id, split_id])

        self.assertEqual({o.item_id for o in repo.outputs(combine_id)}, {d.id})
        self.assertEqual({o.item_id for o in repo.outputs(split_id)}, {d1.id, d2.id})
        self.assertEqual(repo.activity_type(split_id), ActivityType.SPLIT)

    def test_unknown_activity_returns_empty_collections(self):
        """Accessors return [] for an activity id with no rows (empty bucket)."""
        repo = LineageRepo()
        self.assertEqual(repo.outputs("does-not-exist"), [])
        self.assertEqual(repo.ingredient_inputs("does-not-exist"), [])

    def test_unknown_item_has_no_adjacency(self):
        """Adjacency lookups return [] for an item that feeds/produces nothing."""
        repo = LineageRepo()
        self.assertEqual(repo.activity_ids_with_input_item("nope"), [])
        self.assertEqual(repo.activity_ids_with_output_item("nope"), [])

    def test_activity_io_is_cached_not_requeried(self):
        """Once loaded, an activity's inputs are served from memory, not the DB."""
        a = self._count_item("RCAX")
        b = self._count_item("RCBX")
        self._combine(a, b, "RCDX")

        repo = LineageRepo()
        combine_id = self._only(repo.activity_ids_with_input_item(a.id))
        self.assertEqual(len(repo.ingredient_inputs(combine_id)), 2)  # warm the cache

        # Drop the rows straight from the DB, bypassing the repo.
        ActivityInput.delete().where(ActivityInput.activity == combine_id).execute()

        # The same repo keeps serving the cached rows...
        self.assertEqual(len(repo.ingredient_inputs(combine_id)), 2)
        # ...while a fresh repo re-queries and sees the deletion.
        self.assertEqual(LineageRepo().ingredient_inputs(combine_id), [])

    def test_adjacency_is_cached_not_requeried(self):
        """Item adjacency is cached too: a stale repo keeps the first result."""
        a = self._count_item("RDAX")
        b = self._count_item("RDBX")
        self._combine(a, b, "RDDX")

        repo = LineageRepo()
        first = repo.activity_ids_with_input_item(a.id)
        self.assertEqual(len(first), 1)

        ActivityInput.delete().where(ActivityInput.item == a.id).execute()

        self.assertEqual(repo.activity_ids_with_input_item(a.id), first)  # cached
        self.assertEqual(LineageRepo().activity_ids_with_input_item(a.id), [])  # fresh
