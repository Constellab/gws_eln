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
    ACTIVITY_NODE_HEIGHT,
    ITEM_NODE_HEIGHT,
    ITEM_NODE_MIN_WIDTH,
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
# Minimum horizontal gap (px) kept between the EDGES of two sibling item cards.
# Sibling spacing is width-aware (see _distribute_x), so a long label pushes its
# neighbours further apart instead of overlapping them.
_X_GAP = 80
# Item-node width estimation (the node is a 2-column grid, see lineage_nodes):
# col1 = max(label, code), col2 = max(quantity, concentration).
_CHAR_WIDTH = 7.0  # approx px per character at the node font size
_NODE_COL_GAP = 8  # grid column-gap in the node
_NODE_PADDING_X = 12  # node horizontal padding (each side)
# Minimum center-to-center distance between two activity badges on the same row.
_ACTIVITY_MIN_GAP = 150
# Shift the activity down by half the node-height difference so its in/out edges
# stay equal length (nodes are top-anchored).
_ACTIVITY_Y_OFFSET = (ITEM_NODE_HEIGHT - ACTIVITY_NODE_HEIGHT) / 2

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

        # Lot numbers per item (own + inherited from ancestors), reusing the same
        # cache. Displayed on the graph when the "batch numbers" toggle is on.
        batch_by_item = self._batch_numbers_by_item(repo, [item.id for item in items])

        # 2. Item layers (longest path), then items ordered/positioned by the
        # activity they belong to (siblings grouped to reduce edge crossings).
        item_layer = self._compute_item_layers(item_id, raw)
        activities = self._group_activities(raw)
        item_nodes = self._build_item_nodes(
            items, item_layer, activities, batch_by_item, focus_id=item_id
        )
        position_by_id: dict[str, tuple[float, float]] = {
            node.id: (node.position_x, node.position_y) for node in item_nodes
        }

        # 3. One activity node per activity, centered over its output items.
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

    def get_batch_numbers(self, item_id: str) -> list[str]:
        """Return the batch/lot numbers attached to an item, sorted and de-duplicated.

        A batch number is set once at creation on an origin item (a single lot).
        A derived item carries none of its own; its batch numbers are the union
        of all its ancestors' batch numbers, collected by walking the lineage up.
        An origin item (no ancestors) yields at most its own single lot number.

        :param item_id: The item whose lot numbers to resolve.
        :type item_id: str
        :return: Sorted, de-duplicated lot numbers (own + inherited from ancestors).
        :rtype: list[str]
        """
        return self._batch_numbers_by_item(LineageRepo(), [item_id])[item_id]

    def _batch_numbers_by_item(
        self, repo: LineageRepo, item_ids: list[str]
    ) -> dict[str, list[str]]:
        """Resolve the lot numbers of several items at once (own + inherited).

        Each item's lots are the union of the own ``batch_number`` of itself and
        all its ancestors. The ancestor walks share ``repo`` so their overlapping
        adjacency/activity lookups are cached, and every own lot is resolved in a
        single item query.

        :param repo: Shared lineage cache (reused across the per-item up-walks).
        :param item_ids: The items to resolve.
        :return: ``{item_id: sorted, de-duplicated lot numbers}`` for each item.
        """
        closure_by_item: dict[str, set[str]] = {}
        all_ids: set[str] = set()
        for item_id in item_ids:
            closure: set[str] = {item_id}
            self._walk(repo, item_id, "up", closure, {})
            closure_by_item[item_id] = closure
            all_ids |= closure

        own_batch: dict[str, str] = {
            row.id: row.batch_number
            for row in Item.select(Item.id, Item.batch_number).where(
                Item.id.in_(list(all_ids)) & Item.batch_number.is_null(False)
            )
        }
        return {
            item_id: sorted({own_batch[a] for a in closure if a in own_batch})
            for item_id, closure in closure_by_item.items()
        }

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

        Processes the whole BFS frontier level by level: every level resolves
        its adjacency and loads its activities in one batched query each (via the
        repo), so the query count scales with graph depth, not item count.

        Accumulates reached item ids into ``node_ids`` and raw item->item links
        into ``raw_edges`` (keyed by (source, target, activity) to dedup).

        :param repo: Request-scoped DB cache.
        :param start_id: Item id to start from.
        :param direction: "up" (ancestors) or "down" (descendants).
        :param node_ids: Mutated in place with every reached item id.
        :param raw_edges: Mutated in place with every discovered link.
        """
        visited_ids: set[str] = set()
        next_level: set[str] = {start_id}

        while next_level:
            level = next_level - visited_ids
            if not level:
                break
            visited_ids |= level
            next_level = self._expand_level(repo, direction, level, node_ids, raw_edges)

    def _expand_level(
        self,
        repo: LineageRepo,
        direction: str,
        level: set[str],
        node_ids: set[str],
        raw_edges: _RawEdges,
    ) -> set[str]:
        """Expand a whole BFS level in one hop, recording its raw item->item links.

        Down: children are the outputs of activities where a level item is an
        INGREDIENT input. Up: parents are the INGREDIENT inputs of activities that
        output a level item.

        :return: The next level (the set of reached item ids).
        """
        if direction == "down":
            activity_ids_by_item = repo.activity_ids_by_input_items(level)
        else:
            activity_ids_by_item = repo.activity_ids_by_output_items(level)

        activity_ids = [
            activity_id for activity_ids in activity_ids_by_item.values() for activity_id in activity_ids
        ]
        if not activity_ids:
            return set()
        repo.load_activities(activity_ids)

        # For each level item, route through its activities to the items on the
        # other side (outputs when going down, ingredient inputs when going up).
        # Each becomes a raw input->output edge and feeds the next level.
        next_level: set[str] = set()
        for current_id in level:
            for activity_id in activity_ids_by_item[current_id]:
                activity_type = repo.activity_type(activity_id)
                if direction == "down":
                    for out in repo.outputs(activity_id):
                        raw_edges[(current_id, out.item_id, activity_id)] = activity_type
                        node_ids.add(out.item_id)
                        next_level.add(out.item_id)
                else:
                    for inp in repo.ingredient_inputs(activity_id):
                        raw_edges[(inp.item_id, current_id, activity_id)] = activity_type
                        node_ids.add(inp.item_id)
                        next_level.add(inp.item_id)
        return next_level

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
        self,
        items: list[Item],
        item_layer: dict[str, int],
        activities: dict[str, dict],
        batch_by_item: dict[str, list[str]],
        focus_id: str,
    ) -> list[LineageNodeDTO]:
        """Build item nodes on even rows (y = layer * 2 * ROW_GAP).

        Layers are placed from the focus outward; each item is ordered by the
        barycenter of its already-placed neighbours toward the focus, which keeps
        same-activity siblings contiguous under their activity and reduces edge
        crossings.
        """
        producers, consumers = self._producers_and_consumers(activities)
        by_layer: dict[int, list[Item]] = defaultdict(list)
        for item in items:
            by_layer[item_layer.get(item.id, 0)].append(item)

        item_x: dict[str, float] = {}
        nodes: list[LineageNodeDTO] = []
        for level in sorted(by_layer, key=abs):
            ordered = self._order_layer(by_layer[level], level, activities, producers, consumers, item_x)
            # Space siblings by their estimated width so a long label pushes its
            # neighbours apart instead of overlapping them.
            widths = [self._estimate_item_width(item) for item in ordered]
            positions = self._distribute_x(widths)
            for item, position_x in zip(ordered, positions, strict=True):
                item_x[item.id] = position_x
                nodes.append(
                    LineageNodeDTO(
                        id=item.id,
                        kind=LineageNodeKind.ITEM,
                        position_x=position_x,
                        position_y=level * 2 * _ROW_GAP,
                        is_focus=item.id == focus_id,
                        code=item.code,
                        label=item.label,
                        item_sheet_name=item.item_sheet.name,
                        pretty_quantity=item.get_pretty_quantity(),
                        pretty_concentration=item.get_pretty_concentration(),
                        status=item.status,
                        batch_numbers=batch_by_item.get(item.id, []),
                    )
                )
        return nodes

    def _estimate_item_width(self, item: Item) -> float:
        """Estimate an item node's rendered width (px) from its text.

        The node is a 2-column grid (see ``lineage_nodes.item_node``): the left
        column holds the label (row 1) and code (row 2), the right column the
        quantity and concentration. Column widths are the widest of their two
        rows; the total is both columns plus the grid gap and the node padding,
        floored at the node's min width. Used to space siblings without overlap.

        :param item: The item whose node width to estimate.
        :type item: Item
        :return: Estimated node width in pixels.
        :rtype: float
        """
        col1 = max(len(item.label or ""), len(item.code or ""))
        col2 = max(
            len(item.get_pretty_quantity() or ""),
            len(item.get_pretty_concentration() or ""),
        )
        content = col1 * _CHAR_WIDTH
        if col2:
            content += _NODE_COL_GAP + col2 * _CHAR_WIDTH
        return max(ITEM_NODE_MIN_WIDTH, content + 2 * _NODE_PADDING_X)

    def _distribute_x(self, widths: list[float]) -> list[float]:
        """Center x positions for a row of cards, spaced by their widths.

        Cards are laid left to right so adjacent ones keep ``_X_GAP`` between
        their edges (center-to-center = half each width + gap), then the whole
        row is shifted so it stays centered on x=0 (like the previous fixed grid).

        :param widths: Each card's width, in placement order.
        :type widths: list[float]
        :return: The centered center-x of each card, same order.
        :rtype: list[float]
        """
        if not widths:
            return []
        positions = [0.0]
        for index in range(1, len(widths)):
            gap = widths[index - 1] / 2 + widths[index] / 2 + _X_GAP
            positions.append(positions[-1] + gap)
        shift = -(positions[0] + positions[-1]) / 2
        return [position + shift for position in positions]

    def _producers_and_consumers(
        self, activities: dict[str, dict]
    ) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
        """Map each item to the activities that produce it / consume it."""
        producers: dict[str, list[str]] = defaultdict(list)
        consumers: dict[str, list[str]] = defaultdict(list)
        for activity_id, entry in activities.items():
            for target_id in entry["targets"]:
                producers[target_id].append(activity_id)
            for source_id in entry["sources"]:
                consumers[source_id].append(activity_id)
        return producers, consumers

    def _order_layer(
        self,
        layer_items: list[Item],
        level: int,
        activities: dict[str, dict],
        producers: dict[str, list[str]],
        consumers: dict[str, list[str]],
        item_x: dict[str, float],
    ) -> list[Item]:
        """Order a layer by each item's neighbour barycenter toward the focus.

        The anchor is the producing activity (descendants) or consuming activity
        (ancestors); an item's neighbours toward the focus are the other side of
        that activity. Same-activity siblings share a barycenter and anchor, so
        they stay contiguous. The focus layer is ordered by id.
        """
        if level == 0:
            return sorted(layer_items, key=lambda item: item.id)
        anchors = producers if level > 0 else consumers

        def sort_key(item: Item) -> tuple:
            anchor = min(anchors.get(item.id, ()), default=None)
            if anchor is None:
                return (0.0, "", item.id)
            side = activities[anchor]["sources"] if level > 0 else activities[anchor]["targets"]
            xs = [item_x[n] for n in side if n in item_x]
            barycenter = sum(xs) / len(xs) if xs else 0.0
            return (barycenter, anchor, item.id)

        return sorted(layer_items, key=sort_key)

    def _build_activity_nodes(
        self,
        activities: dict[str, dict],
        item_layer: dict[str, int],
        position_by_id: dict[str, tuple[float, float]],
    ) -> list[LineageNodeDTO]:
        """Build one node per activity, on the odd row just above its outputs and
        horizontally centered over all its items (inputs + outputs). Activities
        sharing a row are kept at least ``_ACTIVITY_MIN_GAP`` apart so their badges
        never overlap. Updates ``position_by_id``."""
        # Group activities by row, with their barycenter over all connected items.
        by_row: dict[int, list[tuple[str, dict, float]]] = defaultdict(list)
        for activity_id, entry in activities.items():
            output_layers = [item_layer.get(t, 0) for t in entry["targets"]] or [0]
            row = min(output_layers) * 2 - 1
            xs = [position_by_id[i][0] for i in entry["sources"] + entry["targets"] if i in position_by_id]
            by_row[row].append((activity_id, entry, sum(xs) / len(xs) if xs else 0.0))

        nodes: list[LineageNodeDTO] = []
        for row, row_activities in by_row.items():
            position_y = row * _ROW_GAP + _ACTIVITY_Y_OFFSET
            row_activities.sort(key=lambda activity: (activity[2], activity[0]))
            spaced_xs = self._space_out([activity[2] for activity in row_activities], _ACTIVITY_MIN_GAP)
            for (activity_id, entry, _centroid_x), position_x in zip(row_activities, spaced_xs, strict=True):
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

    def _space_out(self, xs: list[float], min_gap: float) -> list[float]:
        """Push sorted x positions apart to keep ``min_gap`` between neighbours,
        then recenter so the group keeps its original mean."""
        if not xs:
            return []
        spaced = [xs[0]]
        for x in xs[1:]:
            spaced.append(max(x, spaced[-1] + min_gap))
        shift = sum(xs) / len(xs) - sum(spaced) / len(spaced)
        return [x + shift for x in spaced]

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
