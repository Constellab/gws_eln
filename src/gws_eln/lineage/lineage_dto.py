"""
Lineage DTOs for the item lineage DAG.

The lineage graph is DERIVED from the Activity inputs/outputs (there is no
lineage table). These DTOs are the read-only payload of the lineage route:
a focus item plus the nodes and edges of its ancestor/descendant DAG.
"""

from gws_core import BaseModelDTO

from gws_eln.activities.activity_type import ActivityType
from gws_eln.items.item_status import ItemStatus


class LineageNodeDTO(BaseModelDTO):
    """One item in the lineage DAG.

    :param id: Item id (also used as the React Flow node id).
    :param code: Structured item code (e.g. "ETHA-2026-0007").
    :param label: Free-text human label (optional).
    :param item_sheet_name: Name of the item's catalog sheet.
    :param pretty_quantity: Human-readable current quantity (e.g. "5.0 mL").
    :param status: Current item status (ACTIVE / EXHAUSTED / DISCARDED).
    :param is_focus: True for the item the graph is centered on.
    :param position_x: Layered-layout x position (computed backend).
    :param position_y: Layered-layout y position (computed backend).
    """

    id: str
    code: str
    label: str | None
    item_sheet_name: str
    pretty_quantity: str | None
    status: ItemStatus
    is_focus: bool
    position_x: float
    position_y: float


class LineageEdgeDTO(BaseModelDTO):
    """A directed parent -> child link, derived from one activity.

    :param source_id: Parent item id (an INGREDIENT input of the activity).
    :param target_id: Child item id (an output of the activity).
    :param activity_id: The activity that links them.
    :param activity_type: The activity type, used as the edge label.
    """

    source_id: str
    target_id: str
    activity_id: str
    activity_type: ActivityType


class LineageGraphDTO(BaseModelDTO):
    """The full lineage DAG for a focus item (ancestors + descendants).

    :param focus_item_id: The item the graph is centered on.
    :param nodes: All items in the DAG (deduplicated).
    :param edges: All parent -> child links in the DAG.
    """

    focus_item_id: str
    nodes: list[LineageNodeDTO]
    edges: list[LineageEdgeDTO]
