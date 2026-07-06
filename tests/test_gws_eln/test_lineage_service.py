"""Test suite for LineageService.

Covers the derived BIPARTITE lineage DAG: item nodes + activity nodes,
ancestor/descendant traversal, INSTRUMENT exclusion, diamond-merge dedup,
the alternating item/activity rows, and focus co-participant expansion.
"""

from decimal import Decimal

from gws_core import BaseTestCase
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
from gws_eln.lineage.lineage_dto import LineageNodeKind
from gws_eln.lineage.lineage_service import _ACTIVITY_MIN_GAP, LineageService
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
                label="Test item",
            )
        ).item

    def _instrument(self, code: str) -> Item:
        sheet = self._sheet(code, is_consumable=False)
        return ItemService().create_items_bulk(
            CreateItemsBulkDTO(item_sheet_id=sheet.id, serial_numbers=[f"{code}-1"], label="Test item")
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
                output_label="Combined output",
                instrument_item_ids=instrument_ids or [],
            )
        )
        return result.outputs[0]

    def _split(self, source, out_codes) -> list[Item]:
        result = ItemService().split_item(
            source.id,
            SplitItemDTO(
                quantity_contributed=Decimal(len(out_codes)),
                unit="units",
                outputs=[SplitOutputDTO(quantity=Decimal(1), unit="units", label="Output") for _ in out_codes],
            ),
        )
        return result.outputs

    def _items(self, graph):
        return [n for n in graph.nodes if n.kind == LineageNodeKind.ITEM]

    def _activities(self, graph):
        return [n for n in graph.nodes if n.kind == LineageNodeKind.ACTIVITY]

    def _activity_node(self, graph, activity_type: ActivityType):
        matches = [n for n in self._activities(graph) if n.activity_type == activity_type]
        self.assertEqual(len(matches), 1, f"expected one {activity_type} node")
        return matches[0]

    def _edge_set(self, graph):
        return {(e.source_id, e.target_id) for e in graph.edges}

    def _by_id(self, graph):
        return {n.id: n for n in graph.nodes}

    # -------------------------------------------------------------------- tests

    def test_bipartite_ancestors_and_descendants(self):
        """combine A+B -> D, then split D -> D1, D2; focus D sees a bipartite DAG."""
        item_a = self._count_item("LNAA")
        item_b = self._count_item("LNAB")
        d = self._combine(item_a, item_b, "LNAD")
        d1, d2 = self._split(d, ["x", "y"])

        graph = LineageService().get_lineage_graph(d.id)

        # Items present, plus exactly two activity nodes (combine + split).
        self.assertEqual(
            {n.id for n in self._items(graph)},
            {item_a.id, item_b.id, d.id, d1.id, d2.id},
        )
        combine = self._activity_node(graph, ActivityType.COMBINE)
        split = self._activity_node(graph, ActivityType.SPLIT)

        # Edges route through the activity nodes.
        self.assertEqual(
            self._edge_set(graph),
            {
                (item_a.id, combine.id),
                (item_b.id, combine.id),
                (combine.id, d.id),
                (d.id, split.id),
                (split.id, d1.id),
                (split.id, d2.id),
            },
        )

        # Focus flag set on D only (items only).
        self.assertTrue(self._by_id(graph)[d.id].is_focus)
        self.assertEqual(sum(1 for n in graph.nodes if n.is_focus), 1)

    def test_split_siblings_shown_for_focus(self):
        """Focus on one split output -> its sibling outputs are shown."""
        source = self._count_item("LNSS", "10")
        d1, d2, d3 = self._split(source, ["a", "b", "c"])

        graph = LineageService().get_lineage_graph(d1.id)

        # All three siblings + the source are present.
        item_ids = {n.id for n in self._items(graph)}
        self.assertEqual(item_ids, {source.id, d1.id, d2.id, d3.id})
        # The split activity fans out to the three outputs.
        split = self._activity_node(graph, ActivityType.SPLIT)
        self.assertEqual(
            {(e.source_id, e.target_id) for e in graph.edges if e.source_id == split.id},
            {(split.id, d1.id), (split.id, d2.id), (split.id, d3.id)},
        )

    def test_combine_co_inputs_shown_for_focus(self):
        """Focus on one combine input -> the items it was combined with show."""
        item_a = self._count_item("LNCA")
        item_b = self._count_item("LNCB")
        d = self._combine(item_a, item_b, "LNCD")

        # Focus on A: B is what it was combined with.
        graph = LineageService().get_lineage_graph(item_a.id)

        item_ids = {n.id for n in self._items(graph)}
        self.assertEqual(item_ids, {item_a.id, item_b.id, d.id})
        combine = self._activity_node(graph, ActivityType.COMBINE)
        # Both ingredients feed the combine; one output.
        self.assertEqual(
            {(e.source_id, e.target_id) for e in graph.edges},
            {(item_a.id, combine.id), (item_b.id, combine.id), (combine.id, d.id)},
        )

    def test_instrument_inputs_excluded(self):
        """An INSTRUMENT input of the combine is not a lineage parent."""
        item_a = self._count_item("LNIA")
        item_b = self._count_item("LNIB")
        instrument = self._instrument("LNIN")
        d = self._combine(item_a, item_b, "LNID", instrument_ids=[instrument.id])

        graph = LineageService().get_lineage_graph(d.id)

        item_ids = {n.id for n in self._items(graph)}
        self.assertIn(item_a.id, item_ids)
        self.assertIn(item_b.id, item_ids)
        self.assertNotIn(instrument.id, item_ids)
        # Combine is fed by exactly the two ingredient inputs (no instrument).
        combine = self._activity_node(graph, ActivityType.COMBINE)
        self.assertEqual(
            {e.source_id for e in graph.edges if e.target_id == combine.id},
            {item_a.id, item_b.id},
        )

    def test_diamond_merge_dedup(self):
        """A->(split)->B,C ; B,C->(combine)->D : nodes are not duplicated."""
        a = self._count_item("LNDA")
        b, c = self._split(a, ["b", "c"])  # A -> B, A -> C
        d = self._combine(b, c, "LNDD", draw=1)  # B -> D, C -> D

        graph = LineageService().get_lineage_graph(d.id)

        node_ids = [n.id for n in graph.nodes]
        self.assertEqual(len(node_ids), len(set(node_ids)))  # no duplicates
        self.assertEqual({n.id for n in self._items(graph)}, {a.id, b.id, c.id, d.id})

        split = self._activity_node(graph, ActivityType.SPLIT)
        combine = self._activity_node(graph, ActivityType.COMBINE)
        self.assertEqual(
            self._edge_set(graph),
            {
                (a.id, split.id),
                (split.id, b.id),
                (split.id, c.id),
                (b.id, combine.id),
                (c.id, combine.id),
                (combine.id, d.id),
            },
        )

        # Each activity row sits strictly between the rows of the items it links.
        by_id = self._by_id(graph)
        for activity in self._activities(graph):
            neighbour_ys = [
                by_id[e.source_id].position_y if e.target_id == activity.id else by_id[e.target_id].position_y
                for e in graph.edges
                if activity.id in (e.source_id, e.target_id)
            ]
            self.assertLess(min(neighbour_ys), activity.position_y)
            self.assertGreater(max(neighbour_ys), activity.position_y)

    def test_layout_orientation(self):
        """Ancestors sit above the focus (y<0), descendants below (y>0)."""
        item_a = self._count_item("LNLA")
        item_b = self._count_item("LNLB")
        d = self._combine(item_a, item_b, "LNLD")
        d1, _ = self._split(d, ["x", "y"])

        by_id = self._by_id(LineageService().get_lineage_graph(d.id))

        self.assertEqual(by_id[d.id].position_y, 0)
        self.assertLess(by_id[item_a.id].position_y, 0)
        self.assertLess(by_id[item_b.id].position_y, 0)
        self.assertGreater(by_id[d1.id].position_y, 0)

    def test_sibling_outputs_grouped_under_activity(self):
        """Same-activity outputs stay contiguous, and activity badges sharing a
        row are kept at least the min gap apart so they never overlap."""
        f = self._count_item("LNGF", "10")
        g = self._count_item("LNGG")
        x1, x2 = self._split(f, ["x1", "x2"])  # split: F -> X1, X2
        y = self._combine(f, g, "LNGY")  # combine: F + G -> Y

        graph = LineageService().get_lineage_graph(f.id)
        by_id = self._by_id(graph)

        # X1, X2 (split) and Y (combine) all sit one layer below the focus F.
        layer = sorted([by_id[x1.id], by_id[x2.id], by_id[y.id]], key=lambda n: n.position_x)
        ordered_ids = [n.id for n in layer]
        # The two split siblings are adjacent (Y is not wedged between them).
        self.assertEqual(abs(ordered_ids.index(x1.id) - ordered_ids.index(x2.id)), 1)

        # Split and combine share a row and keep at least the min gap apart.
        split = self._activity_node(graph, ActivityType.SPLIT)
        combine = self._activity_node(graph, ActivityType.COMBINE)
        self.assertGreaterEqual(abs(split.position_x - combine.position_x), _ACTIVITY_MIN_GAP - 1e-6)

    def test_isolated_item_has_single_node_no_edges(self):
        """An item with no lineage yields just itself: 1 item node, no activity."""
        item = self._count_item("LNSO")
        graph = LineageService().get_lineage_graph(item.id)
        self.assertEqual(len(graph.nodes), 1)
        self.assertEqual(graph.nodes[0].id, item.id)
        self.assertEqual(graph.nodes[0].kind, LineageNodeKind.ITEM)
        self.assertEqual(graph.edges, [])
