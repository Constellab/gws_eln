"""
Activity DTOs for create and query operations.

Defines data transfer objects for ActivityService operations.
"""

from decimal import Decimal

from gws_core import BaseModelDTO, ModelDTO, UserDTO

from gws_eln.activities.activity_type import ActivityType
from gws_eln.core.unit_type import UnitType
from gws_eln.items.item_dto import ItemSimpleDTO
from gws_eln.locations.location_dto import LocationDTO


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
    created_by: UserDTO
    last_modified_by: UserDTO
