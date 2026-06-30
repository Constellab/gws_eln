"""
Lineage Service - derives the item lineage DAG from the Activity graph.

There is NO lineage table: ancestors/descendants are derived from
activity_inputs x activity_outputs:
- ancestors(X)   = inputs of activities that OUTPUT X, recursed.
- descendants(X) = outputs of activities where X is an input, recursed.
INSTRUMENT inputs are excluded (an instrument is not a parent).

The graph is rendered BIPARTITE: item nodes and activity nodes alternate in
rows (items on even rows, activities on the odd rows between them), with edges
item -> activity -> item. Every node has a single centered source/target
handle, shared by all its edges.
"""

from collections import defaultdict, deque

from gws_core import BadRequestException, CurrentUserService

from gws_eln.activities.activity_type import ActivityType
from gws_eln.items.item import Item
from gws_eln.lineage.lineage_dto import (
    LineageEdgeDTO,
    LineageGraphDTO,
    LineageNodeDTO,
    LineageNodeKind,
)
from gws_eln.lineage.lineage_repo import LineageRepo

# One item layer is two rows tall: the item row plus the activity row above its
# outputs. Item layer L sits at y = L * 2 * ROW_GAP (even rows); an activity
# sits on the odd row just above its outputs.
_ROW_GAP = 150
# Horizontal spacing between sibling items on the same layer (frontend pixels).
_X_SPACING = 220

# Key identifying a raw item->item lineage link, before it is split through an
# activity node: (source_item_id, target_item_id, activity_id).
_RawEdgeKey = tuple[str, str, str]
# Accumulated raw edges, keyed to dedup. The value is just the link's activity
# type - the key already carries the source/target/activity ids.
_RawEdges = dict[_RawEdgeKey, ActivityType]
# A raw link flattened back into a single tuple for the assembly steps:
# (source_item_id, target_item_id, activity_id, activity_type).
_RawEdge = tuple[str, str, str, ActivityType]


class LineageService:
    """Builds the bipartite lineage DAG (item + activity nodes) for a focus item."""

    def get_lineage_graph(self, item_id: str) -> LineageGraphDTO:
        """Build the full ancestor + descendant DAG for one focus item.

        :param item_id: The item the graph is centered on.
        :type item_id: str
        :return: Bipartite nodes (items + activities) + edges.
        :rtype: LineageGraphDTO
        :raises BadRequestException: If the item does not exist.
        """
        CurrentUserService.get_and_check_current_user()
        self._get_item_or_throw(item_id)

        # Single DB cache shared by every phase below (load each row once).
        repo = LineageRepo()

        # 1. Traverse: reach every item and every raw item->item link.
        node_ids: set[str] = {item_id}
        raw_edges: _RawEdges = {}
        self._walk(repo, item_id, "up", node_ids, raw_edges)
        self._walk(repo, item_id, "down", node_ids, raw_edges)
        # Complete every activity reached so each shows its full input/output
        # set (split siblings, combine co-inputs) - one hop, not recursed.
        self._expand_activities(repo, node_ids, raw_edges)
        raw: list[_RawEdge] = [(*key, activity_type) for key, activity_type in raw_edges.items()]

        items = list(Item.select().where(Item.id.in_(list(node_ids))))

        # 2. Item layers (longest path) and item node positions.
        item_layer = self._compute_item_layers(item_id, raw)
        item_nodes = self._build_item_nodes(items, item_layer, focus_id=item_id)
        position_by_id: dict[str, tuple[float, float]] = {
            node.id: (node.position_x, node.position_y) for node in item_nodes
        }

        # 3. One activity node per activity, placed on the row above its outputs.
        activities = self._group_activities(raw)
        activity_nodes = self._build_activity_nodes(activities, item_layer, position_by_id)

        # 4. Bipartite edges (item -> activity -> item), labelled with the
        # contributed (input) / produced (output) quantity.
        input_qty, output_qty = self._edge_quantities(repo, list(activities.keys()))
        edges = self._build_edges(activities, input_qty, output_qty)

        return LineageGraphDTO(
            focus_item_id=item_id,
            nodes=item_nodes + activity_nodes,
            edges=edges,
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
        self._walk(LineageRepo(), item_id, "down", node_ids, {})
        node_ids.discard(item_id)
        return node_ids

    # ----------------------------------------------------------- traversal

    def _walk(
        self,
        repo: LineageRepo,
        start_id: str,
        direction: str,
        node_ids: set[str],
        raw_edges: _RawEdges,
    ) -> None:
        """Breadth-first traversal in one direction, cycle-safe (visited-set).

        Accumulates reached item ids into ``node_ids`` and raw item->item links
        into ``raw_edges`` (keyed by (source, target, activity) to dedup).

        :param repo: Request-scoped DB cache.
        :param start_id: Item id to start from.
        :param direction: "up" (ancestors) or "down" (descendants).
        :param node_ids: Mutated in place with every reached item id.
        :param raw_edges: Mutated in place with every discovered link.
        """
        visited_ids: set[str] = set()
        queue: deque[str] = deque([start_id])

        while queue:
            current_id = queue.popleft()
            if current_id in visited_ids:
                continue
            visited_ids.add(current_id)

            if direction == "down":
                for child_id, activity_id, activity_type in self._children_edges(repo, current_id):
                    node_ids.add(child_id)
                    raw_edges[(current_id, child_id, activity_id)] = activity_type
                    queue.append(child_id)
            else:
                for parent_id, activity_id, activity_type in self._parents_edges(repo, current_id):
                    node_ids.add(parent_id)
                    raw_edges[(parent_id, current_id, activity_id)] = activity_type
                    queue.append(parent_id)

    def _children_edges(
        self, repo: LineageRepo, item_id: str
    ) -> list[tuple[str, str, ActivityType]]:
        """Direct children of an item: outputs of activities where it is an
        INGREDIENT input.

        :return: List of (child_item_id, activity_id, activity_type).
        """
        activity_ids = repo.activity_ids_with_input_item(item_id)
        if not activity_ids:
            return []

        repo.load_activities(activity_ids)
        return [
            (out.item_id, activity_id, repo.activity_type(activity_id))
            for activity_id in activity_ids
            for out in repo.outputs(activity_id)
        ]

    def _parents_edges(
        self, repo: LineageRepo, item_id: str
    ) -> list[tuple[str, str, ActivityType]]:
        """Direct parents of an item: INGREDIENT inputs of activities that
        output it.

        :return: List of (parent_item_id, activity_id, activity_type).
        """
        activity_ids = repo.activity_ids_with_output_item(item_id)
        if not activity_ids:
            return []

        repo.load_activities(activity_ids)
        return [
            (inp.item_id, activity_id, repo.activity_type(activity_id))
            for activity_id in activity_ids
            for inp in repo.ingredient_inputs(activity_id)
        ]

    def _expand_activities(
        self,
        repo: LineageRepo,
        node_ids: set[str],
        raw_edges: _RawEdges,
    ) -> None:
        """Complete every activity already reached with its full input/output set.

        The directional walk only records the inputs/outputs that lie on the
        path to the focus item, so an activity can be shown with missing
        co-participants. For each activity in ``raw_edges`` this adds every
        input / output of that activity.
        """
        activity_types = {
            activity_id: activity_type
            for (_source, _target, activity_id), activity_type in raw_edges.items()
        }
        repo.load_activities(list(activity_types.keys()))
        for activity_id, activity_type in activity_types.items():
            input_ids = [inp.item_id for inp in repo.ingredient_inputs(activity_id)]
            output_ids = [out.item_id for out in repo.outputs(activity_id)]
            for source_id in input_ids:
                for target_id in output_ids:
                    raw_edges[(source_id, target_id, activity_id)] = activity_type
                    node_ids.add(source_id)
                    node_ids.add(target_id)

    # ----------------------------------------------------------- assembly

    def _group_activities(self, raw: list[tuple[str, str, str, ActivityType]]) -> dict[str, dict]:
        """Group raw item->item links by activity.

        :return: ``activity_id -> {"type", "sources": [item ids], "targets": [item ids]}``
            with sources/targets kept as ordered, de-duplicated lists.
        """
        activities: dict[str, dict] = {}
        for source_id, target_id, activity_id, activity_type in raw:
            entry = activities.setdefault(
                activity_id, {"type": activity_type, "sources": [], "targets": []}
            )
            if source_id not in entry["sources"]:
                entry["sources"].append(source_id)
            if target_id not in entry["targets"]:
                entry["targets"].append(target_id)
        return activities

    def _compute_item_layers(
        self, focus_id: str, raw: list[tuple[str, str, str, ActivityType]]
    ) -> dict[str, int]:
        """Assign each item an integer layer by longest path from the focus.

        Focus is layer 0; descendants take positive layers, ancestors negative.
        """
        children: dict[str, list[str]] = defaultdict(list)
        parents: dict[str, list[str]] = defaultdict(list)
        for source_id, target_id, *_ in raw:
            children[source_id].append(target_id)
            parents[target_id].append(source_id)

        layer: dict[str, int] = {focus_id: 0}
        self._relax_layers(focus_id, children, layer, step=1)
        self._relax_layers(focus_id, parents, layer, step=-1)
        return layer

    def _relax_layers(
        self,
        focus_id: str,
        adjacency: dict[str, list[str]],
        layer: dict[str, int],
        step: int,
    ) -> None:
        """Longest-path relaxation from the focus along one direction, in place.

        ``step`` is +1 to push descendants down (later layers) and -1 to push
        ancestors up.

        Ex:
        Path 1: F -> A -> C
        Path 2: F -> C
        The longest path to C is through A, so C's layer is 2 (F=0, A=1, C=2).
        """
        queue: deque[str] = deque([focus_id])
        while queue:
            current = queue.popleft()
            for neighbour in adjacency[current]:
                candidate = layer[current] + step
                if neighbour not in layer or candidate * step > layer[neighbour] * step:
                    layer[neighbour] = candidate
                    queue.append(neighbour)

    def _build_item_nodes(
        self, items: list[Item], item_layer: dict[str, int], focus_id: str
    ) -> list[LineageNodeDTO]:
        """Build item nodes, positioned on even rows (y = layer * 2 * ROW_GAP),
        siblings spread and centered within each layer."""
        by_layer: dict[int, list[Item]] = defaultdict(list)
        for item in items:
            by_layer[item_layer.get(item.id, 0)].append(item)

        nodes: list[LineageNodeDTO] = []
        for level, layer_items in by_layer.items():
            layer_items.sort(key=lambda item: item.id)
            count = len(layer_items)
            for index, item in enumerate(layer_items):
                nodes.append(
                    LineageNodeDTO(
                        id=item.id,
                        kind=LineageNodeKind.ITEM,
                        position_x=(index - (count - 1) / 2) * _X_SPACING,
                        position_y=level * 2 * _ROW_GAP,
                        is_focus=item.id == focus_id,
                        code=item.code,
                        label=item.label,
                        item_sheet_name=item.item_sheet.name,
                        pretty_quantity=item.get_pretty_quantity(),
                        status=item.status,
                    )
                )
        return nodes

    def _build_activity_nodes(
        self,
        activities: dict[str, dict],
        item_layer: dict[str, int],
        position_by_id: dict[str, tuple[float, float]],
    ) -> list[LineageNodeDTO]:
        """Build one node per activity, on the odd row just above its outputs.

        Activities sharing a row are spread side-by-side with the same
        ``_X_SPACING`` as items (and centered), ordered by the centroid of the
        items they link so they line up under their outputs without stacking.
        Updates ``position_by_id``.
        """
        # Group activities by their row, keeping the centroid x for ordering.
        by_row: dict[int, list[tuple[str, dict, float]]] = defaultdict(list)
        for activity_id, entry in activities.items():
            connected = entry["sources"] + entry["targets"]
            output_layers = [item_layer.get(t, 0) for t in entry["targets"]] or [0]
            row = min(output_layers) * 2 - 1
            xs = [position_by_id[i][0] for i in connected if i in position_by_id]
            centroid_x = sum(xs) / len(xs) if xs else 0.0
            by_row[row].append((activity_id, entry, centroid_x))

        nodes: list[LineageNodeDTO] = []
        for row, row_activities in by_row.items():
            # Order by centroid (tie-break on id for stability), then spread
            # evenly and centered, mirroring the item layout.
            row_activities.sort(key=lambda item: (item[2], item[0]))
            count = len(row_activities)
            position_y = row * _ROW_GAP
            for index, (activity_id, entry, _centroid_x) in enumerate(row_activities):
                position_x = (index - (count - 1) / 2) * _X_SPACING

                position_by_id[activity_id] = (position_x, position_y)
                nodes.append(
                    LineageNodeDTO(
                        id=activity_id,
                        kind=LineageNodeKind.ACTIVITY,
                        position_x=position_x,
                        position_y=position_y,
                        is_focus=False,
                        activity_type=entry["type"],
                    )
                )
        return nodes

    def _edge_quantities(
        self, repo: LineageRepo, activity_ids: list[str]
    ) -> tuple[dict[tuple[str, str], str], dict[tuple[str, str], str]]:
        """Map (activity_id, item_id) -> pretty signed quantity for in/outputs.

        Used to label input contributions (``-5 L``) and output productions (``+2 L``).

        :return: ``(input_qty, output_qty)`` lookups keyed by (activity, item).
        """
        repo.load_activities(activity_ids)

        input_qty: dict[tuple[str, str], str] = {}
        output_qty: dict[tuple[str, str], str] = {}
        for activity_id in activity_ids:
            for inp in repo.ingredient_inputs(activity_id):
                pretty = inp.get_pretty_quantity()
                if pretty:
                    input_qty[(activity_id, inp.item_id)] = pretty
            for out in repo.outputs(activity_id):
                pretty = out.get_pretty_quantity()
                if pretty:
                    output_qty[(activity_id, out.item_id)] = pretty

        return input_qty, output_qty

    def _build_edges(
        self,
        activities: dict[str, dict],
        input_qty: dict[tuple[str, str], str],
        output_qty: dict[tuple[str, str], str],
    ) -> list[LineageEdgeDTO]:
        """Wire bipartite edges (input -> activity, activity -> output).

        Every node has a single centered source/target handle, so edges carry no
        per-handle wiring. Each edge is labelled with its contributed/produced
        quantity when the activity recorded one.
        """
        edges: list[LineageEdgeDTO] = []
        for activity_id, entry in activities.items():
            for source_id in entry["sources"]:
                edges.append(
                    LineageEdgeDTO(
                        id=f"{source_id}__{activity_id}",
                        source_id=source_id,
                        target_id=activity_id,
                        quantity=input_qty.get((activity_id, source_id)),
                    )
                )
            for target_id in entry["targets"]:
                edges.append(
                    LineageEdgeDTO(
                        id=f"{activity_id}__{target_id}",
                        source_id=activity_id,
                        target_id=target_id,
                        quantity=output_qty.get((activity_id, target_id)),
                    )
                )
        return edges

    def _get_item_or_throw(self, item_id: str) -> Item:
        """Validate that an item exists.

        :raises BadRequestException: If the item does not exist.
        """
        item = Item.get_by_id(item_id)
        if not item:
            raise BadRequestException(f"Item with ID '{item_id}' does not exist")
        return item
