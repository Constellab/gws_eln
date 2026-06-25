"""Test suite for LineageService.

Covers the derived lineage DAG: ancestors/descendants
traversal from the Activity inputs/outputs, INSTRUMENT exclusion, diamond-merge
dedup (visited-set), and the layered layout (ancestors above, descendants below).
"""

from decimal import Decimal

from gws_core import BaseTestCase
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
from gws_eln.lineage.lineage_service import LineageService
from gws_eln.user.eln_user_sync_service import ElnUserSyncService


class TestLineageService(BaseTestCase):
    """Test suite for LineageService."""

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

    def _edge_set(self, graph):
        return {(e.source_id, e.target_id) for e in graph.edges}

    # -------------------------------------------------------------------- tests

    def test_ancestors_and_descendants(self):
        """combine A+B -> D, then split D -> D1, D2; focus D sees the full DAG."""
        item_a = self._count_item("LNAA")
        item_b = self._count_item("LNAB")
        d = self._combine(item_a, item_b, "LNAD")
        d1, d2 = self._split(d, ["x", "y"])

        graph = LineageService().get_lineage_graph(d.id)

        node_ids = {n.id for n in graph.nodes}
        self.assertEqual(node_ids, {item_a.id, item_b.id, d.id, d1.id, d2.id})
        self.assertEqual(
            self._edge_set(graph),
            {
                (item_a.id, d.id),
                (item_b.id, d.id),
                (d.id, d1.id),
                (d.id, d2.id),
            },
        )

        # Focus flag set on D only.
        self.assertTrue(next(n for n in graph.nodes if n.id == d.id).is_focus)
        self.assertEqual(sum(1 for n in graph.nodes if n.is_focus), 1)

    def test_instrument_inputs_excluded(self):
        """An INSTRUMENT input of the combine is not a lineage parent."""
        item_a = self._count_item("LNIA")
        item_b = self._count_item("LNIB")
        instrument = self._instrument("LNIN")
        d = self._combine(item_a, item_b, "LNID", instrument_ids=[instrument.id])

        graph = LineageService().get_lineage_graph(d.id)

        node_ids = {n.id for n in graph.nodes}
        self.assertIn(item_a.id, node_ids)
        self.assertIn(item_b.id, node_ids)
        self.assertNotIn(instrument.id, node_ids)

    def test_diamond_merge_dedup(self):
        """A->B, A->C, B->D, C->D: D and A are each visited once."""
        a = self._count_item("LNDA")
        b, c = self._split(a, ["b", "c"])  # A -> B, A -> C
        d = self._combine(b, c, "LNDD", draw=1)  # B -> D, C -> D

        graph = LineageService().get_lineage_graph(d.id)

        node_ids = [n.id for n in graph.nodes]
        # No duplicate nodes (visited-set), exactly the 4 items.
        self.assertEqual(len(node_ids), len(set(node_ids)))
        self.assertEqual(set(node_ids), {a.id, b.id, c.id, d.id})
        self.assertEqual(
            self._edge_set(graph),
            {(a.id, b.id), (a.id, c.id), (b.id, d.id), (c.id, d.id)},
        )

    def test_layout_orientation(self):
        """Ancestors sit above the focus (y<0), descendants below (y>0)."""
        item_a = self._count_item("LNLA")
        item_b = self._count_item("LNLB")
        d = self._combine(item_a, item_b, "LNLD")
        d1, _ = self._split(d, ["x", "y"])

        graph = LineageService().get_lineage_graph(d.id)
        by_id = {n.id: n for n in graph.nodes}

        self.assertEqual(by_id[d.id].position_y, 0)
        self.assertLess(by_id[item_a.id].position_y, 0)
        self.assertLess(by_id[item_b.id].position_y, 0)
        self.assertGreater(by_id[d1.id].position_y, 0)

    def test_isolated_item_has_single_node_no_edges(self):
        """An item with no lineage yields just itself and no edges."""
        item = self._count_item("LNSO")
        graph = LineageService().get_lineage_graph(item.id)
        self.assertEqual(len(graph.nodes), 1)
        self.assertEqual(graph.nodes[0].id, item.id)
        self.assertEqual(graph.edges, [])
