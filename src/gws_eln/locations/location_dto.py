"""
Location DTOs for create and update operations.

Defines data transfer objects for LocationService operations.
"""

from gws_core import BaseModelDTO, ModelDTO, UserDTO


class CreateLocationDTO(BaseModelDTO):
    """DTO for creating a new location."""

    name: str
    description: str | None = None


class UpdateLocationDTO(BaseModelDTO):
    """DTO for updating an existing location."""

    name: str
    description: str | None = None


class LocationDTO(ModelDTO):
    """DTO for displaying location information in the frontend."""

    name: str
    description: str | None
    created_by: UserDTO
    last_modified_by: UserDTO
