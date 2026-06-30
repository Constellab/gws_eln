"""State for the item lineage DAG component (Reflex Enterprise React Flow)."""

from typing import Any, TypeAlias

import reflex as rx
import reflex_enterprise as rxe
from gws_core import Logger
from gws_eln.items.item_status import ItemStatus
from gws_eln.lineage.lineage_dto import (
    LineageGraphDTO,
    LineageNodeKind,
)
from gws_eln.lineage.lineage_service import LineageService
from gws_reflex_main import ReflexMainState

from ..common.eln_app_router import ElnAppRouter

# React Flow node/edge TypedDict shapes (Reflex Enterprise), used to type the
# computed vars so they satisfy the rxe.flow `nodes`/`edges` prop types.
Node: TypeAlias = rxe.flow.util.Node
Edge: TypeAlias = rxe.flow.util.Edge

# Item node visual (background / border / text color) per status. Focus is a
# border + background override on top. Carried as plain strings (see
# ItemNodeData) rather than a style dict.
_DEFAULT_COLOR = "#1f2937"
_FOCUS_BACKGROUND = "#eff6ff"
_FOCUS_BORDER = "2px solid #2563eb"
_STATUS_VISUAL = {
    ItemStatus.ACTIVE.value: ("#ffffff", "1px solid #d1d5db", _DEFAULT_COLOR),
    ItemStatus.EXHAUSTED.value: ("#f9fafb", "1px dashed #9ca3af", "#6b7280"),
    ItemStatus.DISCARDED.value: ("#fef2f2", "1px solid #dc2626", "#991b1b"),
}


class LineageState(rx.State):
    """Loads the bipartite lineage DAG and maps it to React Flow nodes/edges.

    The backend ``LineageGraphDTO`` already carries the node kind and positions;
    the state only formats them into the rxe Node/Edge dict shape, keeping the
    custom node components thin.
    """

    _item_id: str | None = None
    _has_graph: bool = False

    _nodes: list[dict] = []
    _edges: list[dict] = []
    is_loading: bool = False
    error_message: str = ""

    @rx.var
    def has_graph(self) -> bool:
        """Whether a graph has been loaded and contains at least one node."""
        return self._has_graph

    @rx.var
    def rf_nodes(self) -> list[Node]:
        """The React Flow nodes (item + activity)."""
        return self._nodes

    @rx.var
    def rf_edges(self) -> list[Edge]:
        """The React Flow edges."""
        return self._edges

    def _build_rf_nodes(self, graph: LineageGraphDTO) -> list[dict]:
        """Map item + activity nodes to React Flow node dicts (typed by kind)."""
        nodes: list[dict] = []
        for node in graph.nodes:
            if node.kind == LineageNodeKind.ITEM:
                background, border, color = self._item_visual(node.status, node.is_focus)
                nodes.append(
                    {
                        "id": node.id,
                        "type": node.kind.value,
                        "position": {"x": node.position_x, "y": node.position_y},
                        "data": {
                            "code": node.code or "",
                            "label": node.label or "",
                            "quantity": node.pretty_quantity or "",
                            "background": background,
                            "border": border,
                            "color": color,
                        },
                    }
                )
            else:
                nodes.append(
                    {
                        "id": node.id,
                        "type": node.kind.value,
                        "position": {"x": node.position_x, "y": node.position_y},
                        "data": {
                            "activity_type": node.activity_type.value,
                        },
                    }
                )
        return nodes

    def _build_rf_edges(self, graph: LineageGraphDTO) -> list[dict]:
        """Map bipartite edges to React Flow edge dicts, with a quantity label.

        The input -> activity edge shows the contributed quantity (e.g. ``-5 L``)
        and each activity -> output edge the produced quantity (e.g. ``+2 L``).
        """
        edges: list[dict] = []
        for edge in graph.edges:
            rf_edge: dict = {
                "id": edge.id,
                "source": edge.source_id,
                "target": edge.target_id,
                "markerEnd": {"type": "arrowclosed"},
            }
            if edge.quantity:
                rf_edge["label"] = edge.quantity
                rf_edge["labelBgPadding"] = [4, 2]
                rf_edge["labelBgBorderRadius"] = 4
                rf_edge["labelBgStyle"] = {"fill": "#ffffff", "fillOpacity": 0.75}
                rf_edge["labelStyle"] = {"fontSize": 10, "fill": "#374151"}
            edges.append(rf_edge)
        return edges

    def _item_visual(self, status: ItemStatus, is_focus: bool) -> tuple[str, str, str]:
        """Resolve (background, border, color) strings from status and focus."""
        background, border, color = _STATUS_VISUAL.get(
            status.value, _STATUS_VISUAL[ItemStatus.ACTIVE.value]
        )
        if is_focus:
            background, border = _FOCUS_BACKGROUND, _FOCUS_BORDER
        return background, border, color

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
            if self._item_id == item_id and self._has_graph:
                return
            self._item_id = item_id
            self._nodes = []
            self._edges = []
            self._has_graph = False
            self.is_loading = True
            self.error_message = ""
            main_state = await self.get_state(ReflexMainState)

        try:
            with await main_state.authenticate_user():
                graph = LineageService().get_lineage_graph(item_id)
            async with self:
                self._nodes = self._build_rf_nodes(graph)
                self._edges = self._build_rf_edges(graph)
                self._has_graph = len(graph.nodes) > 0
                self.is_loading = False
        except Exception as e:
            Logger.error(f"Error loading lineage for item {item_id}: {e}")
            Logger.log_exception_stack_trace(e)
            async with self:
                self._nodes = []
                self._edges = []
                self._has_graph = False
                self.is_loading = False
                self.error_message = "Failed to load lineage"

    @rx.event
    def node_click(self, node: dict[str, Any]):
        """Navigate to the clicked node's item detail page (recenters the DAG).

        The Enterprise ``on_node_click`` passes the node as the first argument.

        :param node: The clicked React Flow node (carries its item id).
        :type node: dict
        """
        # Activity nodes are not items: ignore clicks on them.
        if node.get("type") == LineageNodeKind.ACTIVITY.value:
            return
        node_id = node.get("id")
        if node_id and node_id != self._item_id:
            return rx.redirect(ElnAppRouter.get_item_detail_url(node_id))
