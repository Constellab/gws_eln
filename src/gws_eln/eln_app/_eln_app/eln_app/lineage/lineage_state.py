"""State for the item lineage DAG component (Reflex Enterprise React Flow)."""

from collections import defaultdict
from typing import Any, TypeAlias

import reflex as rx
import reflex_enterprise as rxe
from gws_core import Logger
from gws_eln.items.item_status import ItemStatus
from gws_eln.lineage.lineage_dto import LineageGraphDTO
from gws_eln.lineage.lineage_service import LineageService
from gws_reflex_main import ReflexMainState

from ..common.eln_app_router import ElnAppRouter

# React Flow node/edge TypedDict shapes (Reflex Enterprise), used to type the
# computed vars so they satisfy the rxe.flow `nodes`/`edges` prop types.
Node: TypeAlias = rxe.flow.util.Node
Edge: TypeAlias = rxe.flow.util.Edge

# Prefix for the synthetic activity-junction node ids (distinguishes them from
# real item ids, which are clickable for navigation).
_ACTIVITY_NODE_PREFIX = "activity-"

# Node visual styles per status (focus overrides everything).
_FOCUS_STYLE = {"border": "2px solid #2563eb", "background": "#eff6ff"}
_STATUS_STYLE = {
    ItemStatus.ACTIVE.value: {"border": "1px solid #d1d5db", "background": "#ffffff"},
    ItemStatus.EXHAUSTED.value: {
        "border": "1px dashed #9ca3af",
        "background": "#f9fafb",
        "color": "#6b7280",
    },
    ItemStatus.DISCARDED.value: {
        "border": "1px solid #dc2626",
        "background": "#fef2f2",
        "color": "#991b1b",
    },
}
_BASE_NODE_STYLE = {
    "padding": "8px 12px",
    "border-radius": "8px",
    "font-size": "11px",
    "width": 180,
    "text-align": "center",
}
# A small pill for the activity-junction node: one activity = one label, shared
# by all the lines fanning out (split 1->N) or in (combine N->1).
_ACTIVITY_NODE_STYLE = {
    "padding": "3px 10px",
    "border-radius": "12px",
    "font-size": "10px",
    "background": "#eef2ff",
    "border": "1px solid #c7d2fe",
    "color": "#3730a3",
    "text-align": "center",
}


class LineageState(rx.State):
    """Loads and exposes the lineage DAG for the current item.

    The backend ``LineageGraphDTO`` is mapped to React Flow node/edge dicts (the
    ``rxe.flow.util`` Node/Edge shape) in computed vars, keeping the component a
    thin renderer.
    """

    _item_id: str | None = None
    _graph: LineageGraphDTO | None = None
    is_loading: bool = False
    error_message: str = ""

    @rx.var
    def has_graph(self) -> bool:
        """Whether a graph has been loaded and contains at least one node."""
        return self._graph is not None and len(self._graph.nodes) > 0

    @rx.var
    def rf_nodes(self) -> list[Node]:
        """React Flow nodes: item nodes + activity-junction nodes."""
        return self._build_flow()[0]

    @rx.var
    def rf_edges(self) -> list[Edge]:
        """React Flow edges, routed through activity-junction nodes when an
        activity fans out (split) or in (combine)."""
        return self._build_flow()[1]

    def _build_flow(self) -> tuple[list[Node], list[Edge]]:
        """Build the React Flow nodes and edges from the lineage graph.

        An activity that links more than one pair (a split fanning out to many
        outputs, a combine fanning in from many inputs) is rendered as a single
        **junction node** carrying the activity name once: edges go
        ``input(s) -> [activity] -> output(s)`` so the lines share one label
        instead of repeating it on every line. A plain 1->1 activity stays a
        single labelled item-to-item edge.
        """
        if not self._graph:
            return [], []

        nodes: list[Node] = []
        position_by_id: dict[str, tuple[float, float]] = {}
        for node in self._graph.nodes:
            position_by_id[node.id] = (node.position_x, node.position_y)
            label = node.code if not node.label else f"{node.code} · {node.label}"
            if node.pretty_quantity:
                label = f"{label} ({node.pretty_quantity})"
            nodes.append(
                {
                    "id": node.id,
                    "position": {"x": node.position_x, "y": node.position_y},
                    "data": {"label": label},
                    "style": self._node_style(node.status, node.is_focus),
                }
            )

        # Group edges by the activity that produced them.
        groups: dict[str, list] = defaultdict(list)
        for edge in self._graph.edges:
            groups[edge.activity_id].append(edge)

        edges: list[Edge] = []
        for activity_id, group in groups.items():
            if len(group) == 1:
                edge = group[0]
                edges.append(
                    {
                        "id": f"{edge.source_id}-{edge.target_id}-{activity_id}",
                        "source": edge.source_id,
                        "target": edge.target_id,
                        "label": edge.activity_type.value,
                        "markerEnd": {"type": "arrowclosed"},
                    }
                )
                continue

            # Multi-edge activity -> insert a shared junction node.
            sources = list(dict.fromkeys(e.source_id for e in group))
            targets = list(dict.fromkeys(e.target_id for e in group))
            junction_id = f"{_ACTIVITY_NODE_PREFIX}{activity_id}"
            nodes.append(
                {
                    "id": junction_id,
                    "position": self._junction_position(sources + targets, position_by_id),
                    "data": {"label": group[0].activity_type.value},
                    "style": dict(_ACTIVITY_NODE_STYLE),
                }
            )
            for source_id in sources:
                edges.append(
                    {
                        "id": f"{source_id}-{junction_id}",
                        "source": source_id,
                        "target": junction_id,
                        "markerEnd": {"type": "arrowclosed"},
                    }
                )
            for target_id in targets:
                edges.append(
                    {
                        "id": f"{junction_id}-{target_id}",
                        "source": junction_id,
                        "target": target_id,
                        "markerEnd": {"type": "arrowclosed"},
                    }
                )

        return nodes, edges

    def _junction_position(
        self, item_ids: list[str], position_by_id: dict[str, tuple[float, float]]
    ) -> dict[str, float]:
        """Place the activity-junction node at the centroid of the items it links."""
        points = [position_by_id[i] for i in item_ids if i in position_by_id]
        if not points:
            return {"x": 0.0, "y": 0.0}
        return {
            "x": sum(x for x, _ in points) / len(points),
            "y": sum(y for _, y in points) / len(points),
        }

    def _node_style(self, status: ItemStatus, is_focus: bool) -> dict[str, Any]:
        """Build the inline style for one node based on status and focus."""
        style = dict(_BASE_NODE_STYLE)
        style.update(_STATUS_STYLE.get(status.value, {}))
        if is_focus:
            style.update(_FOCUS_STYLE)
        return style

    @rx.event(background=True)
    async def fetch_lineage_on_mount(self, item_id: str):
        """Lazily load the lineage graph when the lineage tab is mounted.

        :param item_id: The focus item ID.
        :type item_id: str
        """
        async with self:
            if not item_id:
                return
            # Already loaded for this item: keep it (re-fetch happens on remount).
            if self._item_id == item_id and self._graph is not None:
                return
            self._item_id = item_id
            self._graph = None
            self.is_loading = True
            self.error_message = ""
            main_state = await self.get_state(ReflexMainState)

        try:
            with await main_state.authenticate_user():
                graph = LineageService().get_lineage_graph(item_id)
            async with self:
                self._graph = graph
                self.is_loading = False
        except Exception as e:
            Logger.error(f"Error loading lineage for item {item_id}: {e}")
            Logger.log_exception_stack_trace(e)
            async with self:
                self._graph = None
                self.is_loading = False
                self.error_message = "Failed to load lineage"

    @rx.event
    def node_click(self, node: dict[str, Any]):
        """Navigate to the clicked node's item detail page (recenters the DAG).

        The Enterprise ``on_node_click`` passes the node as the first argument.

        :param node: The clicked React Flow node (carries its item id).
        :type node: dict
        """
        node_id = node.get("id")
        # Activity-junction nodes are not items: ignore clicks on them.
        if not node_id or node_id.startswith(_ACTIVITY_NODE_PREFIX):
            return
        if node_id != self._item_id:
            return rx.redirect(ElnAppRouter.get_item_detail_url(node_id))
