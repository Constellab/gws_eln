"""
Lineage DTOs for the item lineage DAG.

The lineage graph is DERIVED from the Activity inputs/outputs (there is no
lineage table). It is rendered as a BIPARTITE graph: item nodes and activity
nodes, alternating in rows, with edges item -> activity -> item. Every node has
a single centered source handle (bottom) and target handle (top); all edges
share them.
"""

from enum import Enum

from gws_core import BaseModelDTO

from gws_eln.activities.activity_type import ActivityType
from gws_eln.items.item_status import ItemStatus

# Fixed node heights (px), shared by the backend layout (lineage_service) and the
# React Flow node components (lineage_nodes).
ITEM_NODE_HEIGHT = 52
ACTIVITY_NODE_HEIGHT = 24
# Minimum item-node width (px), shared so the backend width-aware spacing matches
# the node component's own min width.
ITEM_NODE_MIN_WIDTH = 120


class LineageNodeKind(Enum):
    """Kind of lineage node: a physical item or an activity (the junction)."""

    ITEM = "item"
    ACTIVITY = "activity"


class LineageNodeDTO(BaseModelDTO):
    """One node in the lineage DAG: an item or an activity.

    :param id: The item id (item nodes) or the activity id (activity nodes).
    :param kind: ITEM or ACTIVITY.
    :param position_x: Layered-layout x position (computed backend).
    :param position_y: Layered-layout y position (computed backend).
    :param is_focus: True for the item the graph is centered on (items only).
    :param code: Item code (item nodes only).
    :param label: Item free-text label (item nodes only).
    :param item_sheet_name: Item's catalog sheet name (item nodes only).
    :param pretty_quantity: Item human-readable quantity (item nodes only).
    :param pretty_concentration: Item human-readable concentration (item nodes only, optional).
    :param status: Item status (item nodes only).
    :param batch_numbers: Item lot numbers = union of its ancestors' lots (item nodes only).
    :param activity_type: The activity type (activity nodes only).
    """

    id: str
    kind: LineageNodeKind
    position_x: float
    position_y: float
    is_focus: bool
    # item-only
    code: str | None = None
    label: str | None = None
    item_sheet_name: str | None = None
    pretty_quantity: str | None = None
    pretty_concentration: str | None = None
    status: ItemStatus | None = None
    batch_numbers: list[str] = []
    # activity-only
    activity_type: ActivityType | None = None


class LineageEdgeDTO(BaseModelDTO):
    """A directed link in the bipartite graph (item->activity or activity->item).

    :param id: Unique edge id.
    :param source_id: Source node id.
    :param target_id: Target node id.
    :param quantity: Human-readable signed quantity flowing on this edge
        (input contribution ``-5 L`` or output production ``+2 L``).
    """

    id: str
    source_id: str
    target_id: str
    quantity: str | None = None


class LineageGraphDTO(BaseModelDTO):
    """The full lineage DAG for a focus item (item + activity nodes).

    :param focus_item_id: The item the graph is centered on.
    :param nodes: All nodes (items + activities).
    :param edges: All bipartite links (item -> activity -> item).
    """

    focus_item_id: str
    nodes: list[LineageNodeDTO]
    edges: list[LineageEdgeDTO]
