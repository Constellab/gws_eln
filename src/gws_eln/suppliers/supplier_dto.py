"""
Supplier DTOs for create and update operations.

Defines data transfer objects for SupplierService operations.
"""

from gws_core import BaseModelDTO


class CreateSupplierDTO(BaseModelDTO):
    """DTO for creating a new supplier."""

    name: str
    contact_info: str | None = None


class UpdateSupplierDTO(BaseModelDTO):
    """DTO for updating an existing supplier."""

    name: str
    contact_info: str | None = None
