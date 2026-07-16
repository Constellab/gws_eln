"""Minimal wrapper around the ``@xyflow/react`` (React Flow) library.

Replaces the previously used ``reflex_enterprise`` ``rxe.flow``, exposing only
the subset of React Flow the lineage DAG needs: the ``ReactFlow`` canvas, the
``Background`` and ``Controls`` widgets and the node ``Handle``, plus the
``Node`` / ``Edge`` dict shapes used to type the state vars.

React Flow renders as an uncontrolled flow here (``default_nodes`` /
``default_edges``), so no ``ReactFlowProvider`` is required.
"""

from collections.abc import Mapping, Sequence
from typing import Any, Literal, TypedDict

import reflex as rx
from typing_extensions import NotRequired

# Same pinned version reflex_enterprise used, so the npm dependency is unchanged.
LIBRARY = "@xyflow/react@12.8.4"

Position = Literal["top", "right", "bottom", "left"]


class XYPosition(TypedDict):
    """Position of a node on the pane."""

    x: float
    y: float


class Node(TypedDict):
    """A React Flow node (only the fields the lineage state sets)."""

    id: str
    position: XYPosition
    type: NotRequired[str]
    data: NotRequired[dict[str, Any]]


class Edge(TypedDict):
    """A React Flow edge (only the fields the lineage state sets)."""

    id: str
    source: str
    target: str
    label: NotRequired[Any]
    markerEnd: NotRequired[dict[str, Any]]
    labelBgPadding: NotRequired[tuple[float, float]]
    labelBgBorderRadius: NotRequired[float]
    labelBgStyle: NotRequired[dict[str, Any]]
    labelStyle: NotRequired[dict[str, Any]]


def _on_node_click_spec(event: rx.Var, node: rx.Var[Node]) -> tuple[rx.Var[Node]]:
    """React Flow calls ``onNodeClick(event, node)``; forward only the node."""
    return (node,)


class ReactFlow(rx.Component):
    """The ``<ReactFlow />`` canvas: renders nodes and edges and handles interaction."""

    library = LIBRARY
    tag = "ReactFlow"
    is_default = False

    nodes: rx.Var[Sequence[Node]]
    """Nodes to render in a controlled flow."""

    edges: rx.Var[Sequence[Edge]]
    """Edges to render in a controlled flow."""

    default_nodes: rx.Var[Sequence[Node]]
    """Initial nodes for an uncontrolled flow."""

    default_edges: rx.Var[Sequence[Edge]]
    """Initial edges for an uncontrolled flow."""

    node_types: rx.Var[Mapping[str, Any]]
    """Maps a node ``type`` string to the component that renders it."""

    fit_view: rx.Var[bool]
    """Zoom/pan to fit all nodes on the initial render."""

    fit_view_options: rx.Var[Mapping[str, Any]]
    """Options for the initial ``fit_view`` (e.g. ``nodes`` to fit a subset, ``padding``, ``maxZoom``)."""

    nodes_draggable: rx.Var[bool]
    """Whether nodes can be dragged."""

    nodes_connectable: rx.Var[bool]
    """Whether nodes can be connected by the user."""

    on_node_click: rx.EventHandler[_on_node_click_spec]
    """Called with the clicked node when a user clicks on a node."""

    def add_imports(self) -> rx.ImportDict:
        """Import the React Flow stylesheet (required for the canvas to render)."""
        return {"": "@xyflow/react/dist/style.css"}


class ReactFlowBackground(rx.Component):
    """The ``<Background />`` widget (dots / lines / cross pattern)."""

    library = LIBRARY
    tag = "Background"
    is_default = False

    color: rx.Var[str]
    gap: rx.Var[float | tuple[float, float]]
    size: rx.Var[float]
    variant: rx.Var[Literal["lines", "dots", "cross"]]


class ReactFlowControls(rx.Component):
    """The ``<Controls />`` widget (zoom in/out, fit view, lock)."""

    library = LIBRARY
    tag = "Controls"
    is_default = False


class ReactFlowHandle(rx.Component):
    """The ``<Handle />`` connection point used inside custom node components."""

    library = LIBRARY
    tag = "Handle"
    is_default = False

    type: rx.Var[Literal["source", "target"]]
    position: rx.Var[Position]
    is_connectable: rx.Var[bool]


react_flow = ReactFlow.create
react_flow_background = ReactFlowBackground.create
react_flow_controls = ReactFlowControls.create
react_flow_handle = ReactFlowHandle.create
