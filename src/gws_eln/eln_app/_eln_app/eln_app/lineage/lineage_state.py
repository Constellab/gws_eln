"""State for the item lineage DAG component (React Flow)."""

from typing import Any

import reflex as rx
from gws_core import Logger
from gws_eln.items.item_status import ItemStatus
from gws_eln.lineage.lineage_dto import (
    LineageGraphDTO,
    LineageNodeKind,
)
from gws_eln.lineage.lineage_service import LineageService
from gws_reflex_main import ReflexMainState

from ..common.eln_app_router import ElnAppRouter
from ..common.react_flow import Edge, Node

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

# Batch/lot chips use an HSL color generated from the lot number: only the hue
# varies. Background is a soft pastel; text is a dark same-hue tone for contrast.
_BATCH_SATURATION = 70
_BATCH_LIGHTNESS = 86  # pastel background
_BATCH_TEXT_SATURATION = 55
_BATCH_TEXT_LIGHTNESS = 30  # dark, same-hue text readable on the pastel background
# Golden-angle hue step (~137.5 deg) spreads consecutive/similar lots far apart
# on the color wheel instead of clustering them.
_GOLDEN_ANGLE = 137.508


def _batch_hue(value: str) -> float:
    """Deterministic, process-stable hue (0-360) derived from a lot number.

    Same lot -> same hue across the whole graph, so a lot's descendance is
    visually traceable. Uses a stable polynomial string hash (NOT Python's salted
    ``hash()``); the golden-angle step spreads distinct lots around the wheel.
    """
    hashed = 0
    for char in value:
        hashed = (hashed * 31 + ord(char)) & 0xFFFFFFFF
    return (hashed * _GOLDEN_ANGLE) % 360


def _batch_color(value: str) -> str:
    """Pastel background color for a lot chip."""
    return f"hsl({_batch_hue(value):.0f}, {_BATCH_SATURATION}%, {_BATCH_LIGHTNESS}%)"


def _batch_text_color(value: str) -> str:
    """Dark same-hue text color for a lot chip (readable on its pastel background)."""
    return f"hsl({_batch_hue(value):.0f}, {_BATCH_TEXT_SATURATION}%, {_BATCH_TEXT_LIGHTNESS}%)"


class LineageState(rx.State):
    """Loads the bipartite lineage DAG and maps it to React Flow nodes/edges.

    The backend ``LineageGraphDTO`` already carries the node kind and positions;
    the state only formats them into the rxe Node/Edge dict shape, keeping the
    custom node components thin.
    """

    _item_id: str | None = None
    _has_graph: bool = False
    # Bumped on every (re)load. Used as the React Flow ``key`` so the uncontrolled
    # canvas remounts and picks up fresh nodes/edges after a live refresh.
    _version: int = 0

    _nodes: list[dict] = []
    _edges: list[dict] = []
    is_loading: bool = False
    error_message: str = ""
    # When on, each item node shows its lot number(s) as colored chips so a lot's
    # descendance can be traced down the graph.
    show_batch_numbers: bool = False

    @rx.var
    def graph_key(self) -> str:
        """React Flow key: changes on every reload so the canvas remounts fresh."""
        return f"{self._item_id or ''}:{self._version}"

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
        """Map item + activity nodes to React Flow node dicts (typed by kind).

        A node only gets a top/bottom handle when it actually has an incoming /
        outgoing edge (roots have no input handle, leaves no output handle).
        """
        with_input = {edge.target_id for edge in graph.edges}
        with_output = {edge.source_id for edge in graph.edges}
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
                            "concentration": node.pretty_concentration or "",
                            "background": background,
                            "border": border,
                            "color": color,
                            "has_input": node.id in with_input,
                            "has_output": node.id in with_output,
                            "batches": [
                                {
                                    "value": batch,
                                    "color": _batch_color(batch),
                                    "text_color": _batch_text_color(batch),
                                }
                                for batch in node.batch_numbers
                            ],
                            "show_batch": self.show_batch_numbers,
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
                            "has_input": node.id in with_input,
                            "has_output": node.id in with_output,
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
            # Reload on every mount (like the activities list) so a graph shown
            # again after an activity is always fresh; skip only while a load for
            # this same item is already in flight.
            loading_same = self._item_id == item_id and self.is_loading
        if loading_same:
            return
        await self._load_graph(item_id)

    @rx.event(background=True)
    async def reload_on_navigation(self):
        """Reload the graph after client-side navigation to another item.

        Navigating between ``/items/A`` and ``/items/B`` does not remount the
        lineage component, so ``on_mount`` does not re-fire; the page ``on_load``
        does. Only reload when the graph was already shown for a different item
        (the tab has been opened), keeping the initial load lazy.
        """
        async with self:
            item_id = self.item_id
            skip = not item_id or self._item_id is None or self._item_id == item_id
        if skip:
            return
        await self._load_graph(item_id)

    async def _load_graph(self, item_id: str) -> None:
        """Fetch and build the lineage graph for an item (mount + navigation).

        :param item_id: The focus item ID.
        :type item_id: str
        """
        if not item_id:
            return
        async with self:
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
                self._version += 1
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
    def toggle_batch_numbers(self, value: bool):
        """Show/hide the lot-number chips on every item node.

        The canvas is uncontrolled (``default_nodes``), so the item nodes are
        rebuilt with the new ``show_batch`` flag and the version bumped to remount
        it. Chips (and their colors) are already baked in the node data, so no
        refetch is needed.

        :param value: True to show the lot chips, False to hide them.
        :type value: bool
        """
        self.show_batch_numbers = value
        self._nodes = [
            {**node, "data": {**node["data"], "show_batch": value}}
            if node.get("type") == LineageNodeKind.ITEM.value
            else node
            for node in self._nodes
        ]
        self._version += 1

    @rx.event
    def node_click(self, node: dict[str, Any]):
        """Navigate to the clicked node's item detail page (recenters the DAG).

        ``on_node_click`` forwards the clicked node as its first argument.

        :param node: The clicked React Flow node (carries its item id).
        :type node: dict
        """
        # Activity nodes are not items: ignore clicks on them.
        if node.get("type") == LineageNodeKind.ACTIVITY.value:
            return
        node_id = node.get("id")
        if node_id and node_id != self._item_id:
            return rx.redirect(ElnAppRouter.get_item_detail_url(node_id))
