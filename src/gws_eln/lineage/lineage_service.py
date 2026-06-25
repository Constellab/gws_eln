"""
Lineage Service - derives the item lineage DAG from the Activity graph.

There is NO lineage table: ancestors/descendants are derived from
activity_inputs x activity_outputs:
- ancestors(X)   = inputs of activities that OUTPUT X, recursed.
- descendants(X) = outputs of activities where X is an input, recursed.
INSTRUMENT inputs are excluded (an instrument is not a parent).

The traversal is cycle-safe (a visited-set dedups diamond merges) and is the
same descendant walk the future tag-propagation will need - exposed via
``get_descendant_item_ids`` for reuse.
"""

from collections import defaultdict, deque

from gws_core import BadRequestException, CurrentUserService

from gws_eln.activities.activity import Activity
from gws_eln.activities.activity_input import ActivityInput
from gws_eln.activities.activity_input_role import ActivityInputRole
from gws_eln.activities.activity_output import ActivityOutput
from gws_eln.activities.activity_type import ActivityType
from gws_eln.items.item import Item
from gws_eln.lineage.lineage_dto import (
    LineageEdgeDTO,
    LineageGraphDTO,
    LineageNodeDTO,
)

# Layered-layout spacing (frontend pixels). Ancestors sit above the focus
# (negative y), descendants below; siblings spread horizontally.
_X_SPACING = 220
_Y_SPACING = 140


class LineageService:
    """Builds the lineage DAG (nodes + edges + layout) for a focus item."""

    def get_lineage_graph(self, item_id: str) -> LineageGraphDTO:
        """Build the full ancestor + descendant DAG for one focus item.

        :param item_id: The item the graph is centered on.
        :type item_id: str
        :return: Nodes (deduplicated) + edges + layered layout positions.
        :rtype: LineageGraphDTO
        :raises BadRequestException: If the item does not exist.
        """
        CurrentUserService.get_and_check_current_user()
        self._get_item_or_throw(item_id)

        node_ids: set[str] = {item_id}
        edges: dict[tuple[str, str, str], LineageEdgeDTO] = {}

        self._walk(item_id, "up", node_ids, edges)
        self._walk(item_id, "down", node_ids, edges)

        items = list(Item.select().where(Item.id.in_(list(node_ids))))
        nodes = [self._to_node(item, focus_id=item_id) for item in items]

        self._assign_layout(nodes, list(edges.values()), focus_id=item_id)

        return LineageGraphDTO(
            focus_item_id=item_id,
            nodes=nodes,
            edges=list(edges.values()),
        )

    def get_descendant_item_ids(self, item_id: str) -> set[str]:
        """Return all descendant item ids of an item (excludes the item itself).

        Shared descendant walk - reusable by the future tag propagation.

        :param item_id: The item to walk down from.
        :type item_id: str
        :return: Set of descendant item ids.
        :rtype: set[str]
        """
        node_ids: set[str] = {item_id}
        self._walk(item_id, "down", node_ids, {})
        node_ids.discard(item_id)
        return node_ids

    def _walk(
        self,
        start_id: str,
        direction: str,
        node_ids: set[str],
        edges: dict[tuple[str, str, str], LineageEdgeDTO],
    ) -> None:
        """Breadth-first traversal in one direction, cycle-safe (visited-set).

        Accumulates reached item ids into ``node_ids`` and parent->child links
        into ``edges`` (keyed by (source, target, activity) to dedup).

        :param start_id: Item id to start from.
        :param direction: "up" (ancestors) or "down" (descendants).
        :param node_ids: Mutated in place with every reached item id.
        :param edges: Mutated in place with every discovered edge.
        """
        visited: set[str] = set()
        queue: deque[str] = deque([start_id])

        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)

            if direction == "down":
                steps = self._children_edges(current)
                for child_id, activity_id, activity_type in steps:
                    node_ids.add(child_id)
                    edges[(current, child_id, activity_id)] = LineageEdgeDTO(
                        source_id=current,
                        target_id=child_id,
                        activity_id=activity_id,
                        activity_type=activity_type,
                    )
                    queue.append(child_id)
            else:
                steps = self._parents_edges(current)
                for parent_id, activity_id, activity_type in steps:
                    node_ids.add(parent_id)
                    edges[(parent_id, current, activity_id)] = LineageEdgeDTO(
                        source_id=parent_id,
                        target_id=current,
                        activity_id=activity_id,
                        activity_type=activity_type,
                    )
                    queue.append(parent_id)

    def _children_edges(self, item_id: str) -> list[tuple[str, str, ActivityType]]:
        """Direct children of an item: outputs of activities where it is an
        INGREDIENT input.

        :return: List of (child_item_id, activity_id, activity_type).
        """
        inputs = ActivityInput.select().where(
            (ActivityInput.item == item_id)
            & (ActivityInput.role == ActivityInputRole.INGREDIENT)
        )
        activity_ids = [ai.activity_id for ai in inputs]
        if not activity_ids:
            return []

        activity_types = self._activity_types(activity_ids)
        outputs = ActivityOutput.select().where(ActivityOutput.activity.in_(activity_ids))
        return [
            (out.item_id, out.activity_id, activity_types[out.activity_id])
            for out in outputs
        ]

    def _parents_edges(self, item_id: str) -> list[tuple[str, str, ActivityType]]:
        """Direct parents of an item: INGREDIENT inputs of activities that
        output it.

        :return: List of (parent_item_id, activity_id, activity_type).
        """
        outputs = ActivityOutput.select().where(ActivityOutput.item == item_id)
        activity_ids = [out.activity_id for out in outputs]
        if not activity_ids:
            return []

        activity_types = self._activity_types(activity_ids)
        inputs = ActivityInput.select().where(
            (ActivityInput.activity.in_(activity_ids))
            & (ActivityInput.role == ActivityInputRole.INGREDIENT)
        )
        return [
            (inp.item_id, inp.activity_id, activity_types[inp.activity_id])
            for inp in inputs
        ]

    def _activity_types(self, activity_ids: list[str]) -> dict[str, ActivityType]:
        """Map activity id -> activity type for a set of activities."""
        return {
            activity.id: activity.activity_type
            for activity in Activity.select(Activity.id, Activity.activity_type).where(
                Activity.id.in_(activity_ids)
            )
        }

    def _to_node(self, item: Item, focus_id: str) -> LineageNodeDTO:
        """Build a lineage node DTO for an item (positions filled later)."""
        return LineageNodeDTO(
            id=item.id,
            code=item.code,
            label=item.label,
            item_sheet_name=item.item_sheet.name,
            pretty_quantity=item.get_pretty_quantity(),
            status=item.status,
            is_focus=item.id == focus_id,
            position_x=0.0,
            position_y=0.0,
        )

    def _assign_layout(
        self,
        nodes: list[LineageNodeDTO],
        edges: list[LineageEdgeDTO],
        focus_id: str,
    ) -> None:
        """Assign a layered DAG layout (longest-path depth) in place.

        Focus is at layer 0; descendants take positive layers (below),
        ancestors negative layers (above). Within a layer, nodes spread out
        horizontally and centered. Longest-path relaxation keeps an edge from
        ever pointing within or against its layer (clean in diamond merges).
        """
        children: dict[str, list[str]] = defaultdict(list)
        parents: dict[str, list[str]] = defaultdict(list)
        for edge in edges:
            children[edge.source_id].append(edge.target_id)
            parents[edge.target_id].append(edge.source_id)

        layer: dict[str, int] = {focus_id: 0}
        # Descendants take positive layers (longest path down), ancestors
        # negative layers (longest path up).
        self._relax_layers(focus_id, children, layer, step=1)
        self._relax_layers(focus_id, parents, layer, step=-1)

        by_layer: dict[int, list[LineageNodeDTO]] = defaultdict(list)
        for node in nodes:
            by_layer[layer.get(node.id, 0)].append(node)

        for level, layer_nodes in by_layer.items():
            count = len(layer_nodes)
            for index, node in enumerate(layer_nodes):
                node.position_x = (index - (count - 1) / 2) * _X_SPACING
                node.position_y = level * _Y_SPACING

    def _relax_layers(
        self,
        focus_id: str,
        adjacency: dict[str, list[str]],
        layer: dict[str, int],
        step: int,
    ) -> None:
        """Longest-path relaxation from the focus along one direction, in place.

        ``step`` is +1 to push descendants down (later layers) and -1 to push
        ancestors up. A neighbour is (re)assigned whenever the new candidate
        layer is farther from the focus than its current one, keeping edges from
        ever pointing within or against their layer.
        """
        queue: deque[str] = deque([focus_id])
        while queue:
            current = queue.popleft()
            for neighbour in adjacency[current]:
                candidate = layer[current] + step
                if neighbour not in layer or candidate * step > layer[neighbour] * step:
                    layer[neighbour] = candidate
                    queue.append(neighbour)

    def _get_item_or_throw(self, item_id: str) -> Item:
        """Validate that an item exists.

        :raises BadRequestException: If the item does not exist.
        """
        item = Item.get_by_id(item_id)
        if not item:
            raise BadRequestException(f"Item with ID '{item_id}' does not exist")
        return item
