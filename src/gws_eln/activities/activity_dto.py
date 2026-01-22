"""
Activity DTOs for create and query operations.

Defines data transfer objects for ActivityService operations.
"""

from decimal import Decimal

from gws_core import BaseModelDTO

from gws_eln.activities.activity_type import ActivityType
from gws_eln.core.unit_type import UnitType


class CreateActivityDTO(BaseModelDTO):
    """DTO for creating a new activity log entry."""

    activity_type: ActivityType
    entity_id: str  # The batch ID being acted upon
    quantity: Decimal | None = None
    unit_type: UnitType | None = None
    from_location_id: str | None = None
    to_location_id: str | None = None
    notes: str | None = None
    note_id: str | None = None  # Link to Constellab Note
    related_entity_id: str | None = None  # For aliquot: child batch ID
