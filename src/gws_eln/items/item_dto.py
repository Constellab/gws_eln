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


class CreateAliquotDTO(BaseModelDTO):
    """DTO for creating an aliquot from a parent item.

    Aliquots are derived samples that can either inherit item_sheet_id from
    the parent item or be assigned a different target item sheet (e.g., for
    transformations like extracting a compound from a solution).

    The parent's quantity will be decremented by source_quantity.

    Example 1 (same item sheet): Take 2L from parent (source_quantity=2, source_unit='L')
    to create a 500mL aliquot (aliquot_quantity=500, aliquot_unit='mL').

    Example 2 (different item sheet): Take 100mL from a solution to create 5g of
    extracted compound (target_item_sheet_id points to the compound item sheet).

    Note: source_unit must be compatible with the parent item's unit_type.
    aliquot_unit must be compatible with the target item sheet's unit_type
    (or parent's unit_type if no target item sheet is specified).
    """

    parent_item_id: str
    # Optional target item sheet for the aliquot (if None, inherit from parent)
    target_item_sheet_id: str | None = None
    # Amount to take from parent item (decrements parent)
    source_quantity: Decimal
    source_unit: str  # Exact unit (e.g., 'mL', 'L', 'g') - converted to base unit for storage
    # Amount for the new aliquot (can differ from source due to dilution, processing, etc.)
    aliquot_quantity: Decimal
    aliquot_unit: str  # Exact unit (e.g., 'mL', 'L', 'g') - converted to base unit for storage
    # Optional custom item number for the aliquot (auto-generated if not provided)
    aliquot_item_number: str | None = None
    label: str | None = None
    location_id: str | None = None  # Default to parent's location if None
    notes: str | None = None
    supplier_id: str | None = None  # Default to None
    note_id: str | None = None  # Link to Constellab Note


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
