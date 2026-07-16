"""Custom React Flow node components for the lineage DAG.

Two node types, registered via ``node_types`` on ``react_flow`` and keyed by the
``LineageNodeKind`` values ("item" / "activity"):
- item node: a physical item (code/label/quantity), styled by status/focus.
- activity node: an activity rendered as its colored badge (icon + label).

A node shows a centered target handle (top) only when it has an incoming edge
and a source handle (bottom) only when it has an outgoing edge; all edges on a
side share the single handle.
"""

from typing import TypedDict

import reflex as rx
from gws_eln.lineage.lineage_dto import ACTIVITY_NODE_HEIGHT, ITEM_NODE_HEIGHT

from ..activities.activity_type_component import activity_type_badge
from ..common.react_flow import react_flow_handle


class BatchChip(TypedDict):
    """One lot-number chip: its value, pastel background and same-hue dark text."""

    value: str
    color: str
    text_color: str


class ItemNodeData(TypedDict):
    """Data payload for an item node.

    The visual is carried as plain string fields. ``label`` is the primary line
    and ``code`` the secondary line below; ``quantity`` is a muted suffix on the
    primary line and ``concentration`` on the secondary line (both optional).
    ``has_input`` / ``has_output`` gate the top / bottom handles. ``batches`` are
    the item's lot chips, shown to the right of the node when ``show_batch`` is on.
    """

    code: str
    label: str
    quantity: str
    concentration: str
    background: str
    border: str
    color: str
    has_input: bool
    has_output: bool
    batches: list[BatchChip]
    show_batch: bool


def _batch_chips(data: rx.Var[ItemNodeData]) -> rx.Component:
    """Colored lot-number chips floating to the right of an item node.

    Absolutely positioned so they never affect the fixed node height nor collide
    with the top/bottom edge handles. Same lot -> same color across the graph.
    """
    return rx.cond(
        data["show_batch"] & (data["batches"].length() > 0),
        rx.vstack(
            rx.foreach(
                data["batches"],
                lambda chip: rx.box(
                    chip["value"],
                    background=chip["color"],
                    color=chip["text_color"],
                    style={
                        "fontSize": "9px",
                        "fontWeight": "600",
                        "lineHeight": "1.4",
                        "padding": "1px 7px",
                        "borderRadius": "999px",
                        "whiteSpace": "nowrap",
                        "boxShadow": "0 1px 2px rgba(0,0,0,0.1)",
                    },
                ),
            ),
            spacing="1",
            align="start",
            style={
                "position": "absolute",
                "left": "calc(100% + 6px)",
                "top": "0",
                "maxHeight": f"{ITEM_NODE_HEIGHT}px",
                "flexWrap": "wrap",
            },
        ),
    )


class ActivityNodeData(TypedDict):
    """Data payload for an activity node."""

    activity_type: str
    has_input: bool
    has_output: bool
    highlight: bool


@rx.memo
def item_node(data: rx.Var[ItemNodeData]) -> rx.Component:
    """Custom node for a physical item: label on line 1, code on line 2."""
    return rx.box(
        rx.cond(data["has_input"], react_flow_handle(type="target", position="top")),
        rx.grid(
            # Primary line: the label (always set); code on the secondary line below.
            rx.text(
                data["label"],
                size="1",
                weight="bold",
                style={"white-space": "nowrap"},
                text_align="right",
            ),
            rx.cond(
                data["quantity"] != "",
                rx.text(
                    data["quantity"],
                    size="1",
                    weight="regular",
                    style={"white-space": "nowrap", "opacity": "0.6"},
                    text_align="left",
                ),
                rx.box(),
            ),
            rx.text(
                data["code"],
                size="1",
                weight="regular",
                style={"white-space": "nowrap", "opacity": "0.8"},
                text_align="right",
            ),
            rx.cond(
                data["concentration"] != "",
                rx.text(
                    data["concentration"],
                    size="1",
                    weight="regular",
                    style={"white-space": "nowrap", "opacity": "0.6"},
                    text_align="left",
                ),
                rx.box(),
            ),
            style={"grid-template-columns": "auto auto", "column-gap": "8px", "row-gap": "0"},
            align="center",
            justify="center",
        ),
        rx.cond(data["has_output"], react_flow_handle(type="source", position="bottom")),
        _batch_chips(data),
        background=data["background"],
        border=data["border"],
        color=data["color"],
        padding="8px 12px",
        border_radius="8px",
        font_size="11px",
        min_width="120px",
        height=f"{ITEM_NODE_HEIGHT}px",
        box_sizing="border-box",
        position="relative",
        display="flex",
        flex_direction="column",
        align_items="center",
        justify_content="center",
        text_align="center",
    )


@rx.memo
def activity_node(data: rx.Var[ActivityNodeData]) -> rx.Component:
    """Custom node for an activity, rendered as its colored type badge.

    When ``highlight`` is set (the activity was opened from its list row) the
    badge gets a colored ring so the focused activity stands out on the canvas.
    """
    return rx.box(
        rx.cond(data["has_input"], react_flow_handle(type="target", position="top")),
        activity_type_badge(data["activity_type"]),
        rx.cond(data["has_output"], react_flow_handle(type="source", position="bottom")),
        height=f"{ACTIVITY_NODE_HEIGHT}px",
        box_sizing="border-box",
        border_radius="6px",
        style=rx.cond(
            data["highlight"],
            {
                "display": "flex",
                "align-items": "center",
                "justify-content": "center",
                "outline": "2px solid var(--accent-9)",
                "outline-offset": "3px",
                "box-shadow": "0 0 0 4px var(--accent-4)",
            },
            {"display": "flex", "align-items": "center", "justify-content": "center"},
        ),
    )
