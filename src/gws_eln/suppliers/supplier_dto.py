"""
Supplier DTOs for create and update operations.

Defines data transfer objects for SupplierService operations.
"""

from gws_core import BaseModelDTO, ModelDTO, UserDTO


class CreateSupplierDTO(BaseModelDTO):
    """DTO for creating a new supplier."""

    name: str
    description: str | None = None


class UpdateSupplierDTO(BaseModelDTO):
    """DTO for updating an existing supplier."""

    name: str
    description: str | None = None


class SupplierDTO(ModelDTO):
    """DTO for displaying supplier information in the frontend."""

    name: str
    description: str | None
    created_by: UserDTO
    last_modified_by: UserDTO
