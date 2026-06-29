"""Custom React Flow node components for the lineage DAG (Reflex Enterprise).

Two node types, registered via ``node_types`` on ``rxe.flow`` and keyed by the
``LineageNodeKind`` values ("item" / "activity"):
- item node: a physical item (code/label/quantity), styled by status/focus.
- activity node: an activity rendered as its colored badge (icon + label).

Every node has a single centered target handle (top) and source handle
(bottom); all edges share them.
"""

from typing import TypedDict

import reflex as rx
import reflex_enterprise as rxe

from ..activities.activity_type_component import activity_type_badge


class ItemNodeData(TypedDict):
    """Data payload for an item node.

    The visual is carried as plain string fields.
    """

    label: str
    background: str
    border: str
    color: str


class ActivityNodeData(TypedDict):
    """Data payload for an activity node."""

    activity_type: str


@rx.memo
def item_node(data: rx.Var[ItemNodeData]) -> rx.Component:
    """Custom node for a physical item (visual from data string fields)."""
    return rx.box(
        rxe.flow.handle(type="target", position="top"),
        rx.text(
            data["label"],
            size="1",
            weight="medium",
            style={"white-space": "nowrap"},
        ),
        rxe.flow.handle(type="source", position="bottom"),
        background=data["background"],
        border=data["border"],
        color=data["color"],
        padding="8px 12px",
        border_radius="8px",
        font_size="11px",
        min_width="120px",
        text_align="center",
    )


@rx.memo
def activity_node(data: rx.Var[ActivityNodeData]) -> rx.Component:
    """Custom node for an activity, rendered as its colored type badge."""
    return rx.box(
        rxe.flow.handle(type="target", position="top"),
        activity_type_badge(data["activity_type"]),
        rxe.flow.handle(type="source", position="bottom"),
        style={"display": "flex", "align-items": "center", "justify-content": "center"},
    )
