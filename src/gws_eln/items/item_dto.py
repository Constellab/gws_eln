"""
Item DTOs for create, receive, and other operations.

Defines data transfer objects for ItemService operations.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from gws_core import BaseModelDTO, UserDTO
from gws_eln.core.unit_type import UnitType
from gws_eln.items.item_sheet_dto import ItemSheetDTO
from gws_eln.items.item_status import ItemStatus
from gws_eln.locations.location_dto import LocationDTO
from gws_eln.suppliers.supplier_dto import SupplierDTO


class CreateItemDTO(BaseModelDTO):
    """DTO for creating a new item.

    The unit field accepts any valid unit string (e.g., 'mL', 'g', 'kg').
    The unit_type is automatically determined from the item sheet's default_unit_type.
    The quantity is converted from the given unit to the base unit for storage.
    """

    item_sheet_id: str
    item_number: str
    quantity: Decimal
    unit: str  # Exact unit (e.g., 'mL', 'g', 'kg') - converted to base unit for storage
    concentration: Decimal | None = None
    concentration_unit: str | None = None
    location_id: str | None = None  # Default to "labo" if None
    supplier_id: str | None = None
    expiry_date: date | None = None
    label: str | None = None
    notes: str | None = None
    note_id: str | None = None  # Link to Constellab Note


class ReceiveItemDTO(BaseModelDTO):
    """DTO for receiving additional stock to an existing item.

    The unit field accepts any valid unit string (e.g., 'mL', 'g', 'kg').
    The quantity is converted from the given unit to the base unit for storage.
    """

    quantity: Decimal
    unit: str  # Exact unit (e.g., 'mL', 'g', 'kg') - converted to base unit for storage
    notes: str | None = None
    note_id: str | None = None  # Link to Constellab Note


class IncrementQuantityDTO(BaseModelDTO):
    """DTO for incrementing item quantity.

    The unit field accepts any valid unit string (e.g., 'mL', 'g', 'kg').
    The quantity is converted from the given unit to the base unit for storage.
    """

    quantity: Decimal
    unit: str  # Exact unit (e.g., 'mL', 'g', 'kg') - converted to base unit for storage
    notes: str | None = None


class DecrementQuantityDTO(BaseModelDTO):
    """DTO for decrementing item quantity (consumables only).

    The unit field accepts any valid unit string (e.g., 'mL', 'g', 'kg').
    The quantity is converted from the given unit to the base unit for storage.
    """

    quantity: Decimal
    unit: str  # Exact unit (e.g., 'mL', 'g', 'kg') - converted to base unit for storage
    notes: str | None = None
    note_id: str | None = None  # Link to Constellab Note


class MoveItemDTO(BaseModelDTO):
    """DTO for moving an item to a different location."""

    to_location_id: str
    note_id: str | None = None  # Link to Constellab Note


class UpdateItemDTO(BaseModelDTO):
    """DTO for updating item metadata (label, notes, expiry_date)."""

    notes: str | None = None
    expiry_date: date | None = None
    supplier_id: str | None = None
    concentration: Decimal | None = None
    concentration_unit: str | None = None  # Recorded verbatim, no conversion (e.g. 'mM', 'ng/µL')
    note_id: str | None = None  # Link to Constellab Note


class UseItemDTO(BaseModelDTO):
    """DTO for recording a USE activity on an item (reference only, no state change)."""

    notes: str | None = None
    note_id: str | None = None  # Link to Constellab Note


class DiscardItemDTO(BaseModelDTO):
    """DTO for discarding an item."""

    notes: str | None = None
    note_id: str | None = None  # Link to Constellab Note


class RelabelItemDTO(BaseModelDTO):
    """DTO for relabeling an item (changing item_number or label)."""

    item_number: str | None = None
    label: str | None = None
    note_id: str | None = None  # Link to Constellab Note


class DeleteItemResultDTO(Enum):
    """Enum for delete item operation results."""

    DELETED = "deleted"
    DISCARDED = "discarded"


class ItemSimpleDTO(BaseModelDTO):
    """Simple DTO for item with minimal fields."""

    id: str
    item_number: str
    label: str | None


class ItemDTO(ItemSimpleDTO):
    """DTO for displaying item information in the frontend."""

    quantity: Decimal
    unit_type: UnitType
    pretty_quantity: str  # Pre-formatted quantity string for display
    concentration: Decimal | None
    concentration_unit: str | None
    item_sheet: ItemSheetDTO
    location: LocationDTO
    parent_item: ItemSimpleDTO | None
    supplier: SupplierDTO | None
    expiry_date: date | None
    notes: str | None
    status: ItemStatus
    created_at: datetime
    last_modified_at: datetime
    created_by: UserDTO
    last_modified_by: UserDTO


class HierarchyObjectDTO(BaseModelDTO):
    """DTO for representing an item in a hierarchy view."""

    id: str
    name: str
    sub_name: str | None
