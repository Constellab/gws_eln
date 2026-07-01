"""Custom React Flow node components for the lineage DAG (Reflex Enterprise).

Two node types, registered via ``node_types`` on ``rxe.flow`` and keyed by the
``LineageNodeKind`` values ("item" / "activity"):
- item node: a physical item (code/label/quantity), styled by status/focus.
- activity node: an activity rendered as its colored badge (icon + label).

A node shows a centered target handle (top) only when it has an incoming edge
and a source handle (bottom) only when it has an outgoing edge; all edges on a
side share the single handle.
"""

from typing import TypedDict

import reflex as rx
import reflex_enterprise as rxe
from gws_eln.lineage.lineage_dto import ACTIVITY_NODE_HEIGHT, ITEM_NODE_HEIGHT

from ..activities.activity_type_component import activity_type_badge


class ItemNodeData(TypedDict):
    """Data payload for an item node.

    The visual is carried as plain string fields. ``code`` and ``label`` are
    rendered on two separate lines; ``quantity`` is an optional muted suffix.
    ``has_input`` / ``has_output`` gate the top / bottom handles.
    """

    code: str
    label: str
    quantity: str
    background: str
    border: str
    color: str
    has_input: bool
    has_output: bool


class ActivityNodeData(TypedDict):
    """Data payload for an activity node."""

    activity_type: str
    has_input: bool
    has_output: bool


@rx.memo
def item_node(data: rx.Var[ItemNodeData]) -> rx.Component:
    """Custom node for a physical item: code on line 1, label on line 2."""
    return rx.box(
        rx.cond(data["has_input"], rxe.flow.handle(type="target", position="top")),
        rx.vstack(
            rx.hstack(
                rx.text(
                    data["code"],
                    size="1",
                    weight="bold",
                    style={"white-space": "nowrap"},
                ),
                rx.cond(
                    data["quantity"] != "",
                    rx.text(
                        data["quantity"],
                        size="1",
                        weight="regular",
                        style={"white-space": "nowrap", "opacity": "0.6"},
                    ),
                ),
                spacing="1",
                align="center",
                justify="center",
            ),
            rx.cond(
                data["label"] != "",
                rx.text(
                    data["label"],
                    size="1",
                    weight="regular",
                    style={"white-space": "nowrap", "opacity": "0.8"},
                ),
            ),
            spacing="0",
            align="center",
        ),
        rx.cond(data["has_output"], rxe.flow.handle(type="source", position="bottom")),
        background=data["background"],
        border=data["border"],
        color=data["color"],
        padding="8px 12px",
        border_radius="8px",
        font_size="11px",
        min_width="120px",
        height=f"{ITEM_NODE_HEIGHT}px",
        box_sizing="border-box",
        display="flex",
        flex_direction="column",
        align_items="center",
        justify_content="center",
        text_align="center",
    )


@rx.memo
def activity_node(data: rx.Var[ActivityNodeData]) -> rx.Component:
    """Custom node for an activity, rendered as its colored type badge."""
    return rx.box(
        rx.cond(data["has_input"], rxe.flow.handle(type="target", position="top")),
        activity_type_badge(data["activity_type"]),
        rx.cond(data["has_output"], rxe.flow.handle(type="source", position="bottom")),
        height=f"{ACTIVITY_NODE_HEIGHT}px",
        box_sizing="border-box",
        style={"display": "flex", "align-items": "center", "justify-content": "center"},
    )
