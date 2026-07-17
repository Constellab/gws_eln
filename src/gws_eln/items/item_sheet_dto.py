"""
ItemSheet DTOs for create and update operations.

Defines data transfer objects for ItemSheetService operations.
"""

from enum import Enum

from gws_core import BaseModelDTO, ModelDTO, UserDTO
from gws_eln.core.unit_type import UnitType
from gws_eln.suppliers.supplier_dto import SupplierDTO


class DeleteItemSheetMode(Enum):
    """How deleting an item sheet will resolve, given its items.

    - DELETE: no items at all -> hard delete, no reason needed.
    - DISCARD: only discarded items -> soft delete, a reason is required.
    - BLOCKED: at least one non-discarded item -> deletion refused.
    """

    DELETE = "delete"
    DISCARD = "discard"
    BLOCKED = "blocked"


class CreateItemSheetDTO(BaseModelDTO):
    """DTO for creating a new item sheet."""

    name: str
    code: str  # Exactly 4 chars [A-Z0-9], unique, immutable
    description: str | None = None
    supplier_id: str | None = None
    is_consumable: bool = True
    unit_type: UnitType = UnitType.COUNT
    storage_conditions: str | None = None


class UpdateItemSheetDTO(BaseModelDTO):
    """DTO for updating an existing item sheet."""

    name: str
    description: str | None = None
    supplier_id: str | None = None
    is_consumable: bool = True
    unit_type: UnitType = UnitType.COUNT
    storage_conditions: str | None = None


class ItemSheetDTO(ModelDTO):
    """DTO for displaying item sheet information in the frontend."""

    name: str
    code: str
    description: str | None
    default_supplier: SupplierDTO | None
    is_consumable: bool
    unit_type: UnitType
    storage_conditions: str | None
    discard_reason: str | None = None  # Justification, set when the sheet is discarded
    is_discarded: bool = False  # True once the sheet is discarded (locks all actions)
    created_by: UserDTO
    last_modified_by: UserDTO
