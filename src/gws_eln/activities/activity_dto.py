"""
Activity DTOs for create and query operations.

Defines data transfer objects for ActivityService operations.
"""

from decimal import Decimal

from gws_core import BaseModelDTO, ModelDTO, UserDTO

from gws_eln.activities.activity_type import ActivityType
from gws_eln.core.unit_type import UnitType
from gws_eln.locations.location_dto import LocationDTO
from gws_eln.materials.material_batch_dto import MaterialBatchSimpleDTO


class CreateActivityDTO(BaseModelDTO):
    """DTO for creating a new activity log entry."""

    activity_type: ActivityType
    batch_id: str  # The batch ID being acted upon
    quantity: Decimal | None = None
    unit_type: UnitType | None = None
    from_location_id: str | None = None
    to_location_id: str | None = None
    notes: str | None = None
    note_id: str | None = None  # Link to Constellab Note
    related_batch_id: str | None = None  # For aliquot: child batch ID


class ActivityDTO(ModelDTO):
    """DTO for displaying activity information in the frontend."""

    activity_type: ActivityType
    batch: MaterialBatchSimpleDTO
    related_batch: MaterialBatchSimpleDTO | None
    quantity: Decimal | None
    unit_type: UnitType | None
    pretty_quantity: str | None
    from_location: LocationDTO | None
    to_location: LocationDTO | None
    notes: str | None
    note_id: str | None
    created_by: UserDTO
    last_modified_by: UserDTO
