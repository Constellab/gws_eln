"""
Activity DTOs for create and query operations.

Defines data transfer objects for ActivityService operations.
"""

from decimal import Decimal

from gws_core import BaseModelDTO, ModelDTO, UserDTO

from gws_eln.activities.activity_input_role import ActivityInputRole
from gws_eln.activities.activity_type import ActivityType
from gws_eln.core.unit_type import UnitType
from gws_eln.items.item_dto import ItemSimpleDTO
from gws_eln.locations.location_dto import LocationDTO


class CreateActivityInputDTO(BaseModelDTO):
    """DTO for an input item the activity took from (ingredient or instrument)."""

    item_id: str  # The input item ID
    role: ActivityInputRole
    quantity_contributed: Decimal | None = None  # Null for INSTRUMENT and move/relabel
    unit_type: UnitType | None = None


class CreateActivityOutputDTO(BaseModelDTO):
    """DTO for a new item created by the activity."""

    item_id: str  # The created item ID
    quantity: Decimal | None = None  # Snapshot of the output quantity at creation
    unit_type: UnitType | None = None


class CreateActivityDTO(BaseModelDTO):
    """DTO for creating a new activity log entry."""

    activity_type: ActivityType
    item_id: str  # The item ID being acted upon
    quantity: Decimal | None = None
    unit_type: UnitType | None = None
    from_location_id: str | None = None
    to_location_id: str | None = None
    notes: str | None = None
    note_id: str | None = None  # Link to Constellab Note
    related_item_id: str | None = None  # For lineage: related item ID

    # Structured lineage: items the activity took from / created
    inputs: list[CreateActivityInputDTO] = []
    outputs: list[CreateActivityOutputDTO] = []


class ActivityInputDTO(ModelDTO):
    """DTO for displaying an activity input (item the activity took from)."""

    item: ItemSimpleDTO
    role: ActivityInputRole
    quantity_contributed: Decimal | None
    unit_type: UnitType | None
    pretty_quantity: str | None


class ActivityOutputDTO(ModelDTO):
    """DTO for displaying an activity output (new item the activity created)."""

    item: ItemSimpleDTO
    quantity: Decimal | None
    unit_type: UnitType | None
    pretty_quantity: str | None


class ActivityDTO(ModelDTO):
    """DTO for displaying activity information in the frontend."""

    activity_type: ActivityType
    item: ItemSimpleDTO
    related_item: ItemSimpleDTO | None
    quantity: Decimal | None
    unit_type: UnitType | None
    pretty_quantity: str | None
    from_location: LocationDTO | None
    to_location: LocationDTO | None
    notes: str | None
    note_id: str | None
    inputs: list[ActivityInputDTO]
    outputs: list[ActivityOutputDTO]
    created_by: UserDTO
    last_modified_by: UserDTO
