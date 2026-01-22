"""
Location DTOs for create and update operations.

Defines data transfer objects for LocationService operations.
"""

from gws_core import BaseModelDTO


class CreateLocationDTO(BaseModelDTO):
    """DTO for creating a new location."""

    name: str
    description: str | None = None


class UpdateLocationDTO(BaseModelDTO):
    """DTO for updating an existing location."""

    name: str
    description: str | None = None
