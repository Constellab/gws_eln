"""
Material DTOs for create and update operations.

Defines data transfer objects for MaterialService operations.
"""

from gws_core import BaseModelDTO, ModelDTO, UserDTO

from gws_eln.core.unit_type import UnitType
from gws_eln.suppliers.supplier_dto import SupplierDTO


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


class MaterialDTO(ModelDTO):
    """DTO for displaying material information in the frontend."""

    name: str
    description: str | None
    default_supplier: SupplierDTO | None
    is_consumable: bool
    default_unit_type: UnitType
    created_by: UserDTO
    last_modified_by: UserDTO
