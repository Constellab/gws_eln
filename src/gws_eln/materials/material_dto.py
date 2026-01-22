"""
Material DTOs for create and update operations.

Defines data transfer objects for MaterialService operations.
"""

from gws_core import BaseModelDTO

from gws_eln.core.unit_type import UnitType


class CreateMaterialDTO(BaseModelDTO):
    """DTO for creating a new material."""

    name: str
    description: str | None = None
    supplier_id: str | None = None
    is_consumable: bool = True
    default_unit_type: UnitType = UnitType.COUNT


class UpdateMaterialDTO(BaseModelDTO):
    """DTO for updating an existing material."""

    name: str
    description: str | None = None
    supplier_id: str | None = None
    is_consumable: bool = True
    default_unit_type: UnitType = UnitType.COUNT
