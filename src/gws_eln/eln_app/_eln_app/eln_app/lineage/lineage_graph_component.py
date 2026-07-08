"""Item lineage DAG component (React Flow)."""

import reflex as rx
from gws_eln.lineage.lineage_dto import LineageNodeKind

from ..common.react_flow import react_flow, react_flow_background, react_flow_controls
from .lineage_nodes import activity_node, item_node
from .lineage_state import LineageState


def _graph_canvas() -> rx.Component:
    """The React Flow canvas wired to the lineage state."""
    return rx.box(
        react_flow(
            react_flow_background(gap=16, size=1),
            react_flow_controls(),
            default_nodes=LineageState.rf_nodes,
            default_edges=LineageState.rf_edges,
            node_types={
                LineageNodeKind.ITEM.value: item_node,
                LineageNodeKind.ACTIVITY.value: activity_node,
            },
            fit_view=True,
            nodes_draggable=True,
            nodes_connectable=False,
            on_node_click=LineageState.node_click,
            # Remount the uncontrolled canvas when the graph reloads (new version)
            # so fresh nodes/edges are picked up without leaving the page.
            key=LineageState.graph_key,
        ),
        width="100%",
        height="70vh",
        border="1px solid var(--gray-5)",
        border_radius="8px",
        overflow="hidden",
    )


def _empty_state() -> rx.Component:
    """Shown when the item has no lineage (no ancestors, no descendants)."""
    return rx.center(
        rx.vstack(
            rx.icon("git-fork", size=48, color="gray"),
            rx.text("No lineage for this item", size="4", color="gray", margin_top="1rem"),
            rx.text(
                "This item was not derived from, nor used to create, other items.",
                size="2",
                color="gray",
            ),
            spacing="2",
            align="center",
        ),
        padding="3rem",
        width="100%",
    )


def lineage_graph_component(item_id: rx.Var[str]) -> rx.Component:
    """Create the lineage DAG component for a specific item.

    Renders an interactive React Flow graph centered on the item, with its
    ancestors above and descendants below. Loads lazily on mount and remounts
    when the item changes (``key=item_id``).

    :param item_id: The ID of the focus item.
    :type item_id: rx.Var[str]
    :return: The lineage graph component.
    :rtype: rx.Component
    """
    return rx.box(
        rx.cond(
            LineageState.error_message != "",
            rx.callout(
                LineageState.error_message,
                icon="triangle_alert",
                color_scheme="red",
                role="alert",
            ),
            rx.cond(
                LineageState.is_loading,
                rx.center(rx.spinner(size="3"), padding="3rem", width="100%"),
                rx.cond(
                    LineageState.has_graph,
                    _graph_canvas(),
                    _empty_state(),
                ),
            ),
        ),
        width="100%",
        on_mount=LineageState.fetch_lineage_on_mount(item_id),
        key=item_id,
    )
