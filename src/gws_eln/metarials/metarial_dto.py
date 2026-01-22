"""
Metarial DTOs for create and update operations.

Defines data transfer objects for MetarialService operations.
"""

from gws_core import BaseModelDTO

from gws_eln.core.unit_type import UnitType


class CreateMetarialDTO(BaseModelDTO):
    """DTO for creating a new metarial."""

    name: str
    description: str | None = None
    supplier_id: str | None = None
    is_consumable: bool = True
    default_unit_type: UnitType = UnitType.COUNT


class UpdateMetarialDTO(BaseModelDTO):
    """DTO for updating an existing metarial."""

    name: str
    description: str | None = None
    supplier_id: str | None = None
    is_consumable: bool = True
    default_unit_type: UnitType = UnitType.COUNT
