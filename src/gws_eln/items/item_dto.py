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
    The unit_type is automatically determined from the item sheet's unit_type.
    The quantity is converted from the given unit to the base unit for storage.
    """

    item_sheet_id: str
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
    """DTO for relabeling an item (changing its label)."""

    label: str | None = None
    note_id: str | None = None  # Link to Constellab Note


class SplitOutputDTO(BaseModelDTO):
    """DTO for one output item produced by a split.

    The output inherits the source item's item sheet, unit_type and
    concentration; only the fields below are user-entered per output.
    The quantity unit is validated against the source item's unit type.
    """

    quantity: Decimal
    unit: str  # Exact unit (e.g., 'mL', 'g') - validated against the source's unit type
    location_id: str | None = None  # Defaults to the source item's location if None
    label: str | None = None
    expiry_date: date | None = None  # Defaults to the source item's expiry_date if None
    notes: str | None = None


class SplitItemDTO(BaseModelDTO):
    """DTO for splitting one source item into 1..N new output items.

    The source quantity is reduced in place by the sum of the output
    quantities; the leftover stays in the source item. Each output is a
    new item that inherits the source's sheet/unit_type/concentration.
    """

    outputs: list[SplitOutputDTO]
    notes: str | None = None
    note_id: str | None = None  # Link to Constellab Note


class CombineInputDTO(BaseModelDTO):
    """DTO for one ingredient consumed by a combine.

    The given quantity is drawn from the item (reduced in place), bounded by
    the non-negative stock check. Inputs may be of any dimension.
    """

    item_id: str
    quantity: Decimal
    unit: str  # Exact unit - validated against this input item's own unit type


class CombineItemDTO(BaseModelDTO):
    """DTO for combining 2..N ingredient items into one new output item.

    Each ingredient is reduced in place by its contribution; a brand new output
    item is created on the caller-provided `output_item_sheet_id`. The
    output concentration is user-entered or null - never computed.
    Optional instrument inputs (non-consumable) can be recorded alongside.
    """

    inputs: list[CombineInputDTO]
    output_item_sheet_id: str
    output_quantity: Decimal
    output_unit: str  # Validated against the output item sheet's default unit type
    instrument_item_ids: list[str] = []  # Optional instrument inputs (non-consumable)
    output_location_id: str | None = None  # Default to "labo" if None
    output_label: str | None = None
    output_expiry_date: date | None = None
    output_concentration: Decimal | None = None
    output_concentration_unit: str | None = None
    notes: str | None = None
    note_id: str | None = None  # Link to Constellab Note


class ConcentrateItemDTO(BaseModelDTO):
    """DTO for concentrating one source item into a new, more concentrated item.

    The source is reduced in place by `quantity_contributed`; a brand new output
    item is created on the source's own sheet at the user-entered (higher)
    concentration. Concentration is store-only - the activity records the
    initial/final concentration + dilution factor as audit.
    """

    quantity_contributed: Decimal  # Amount drawn from the source (reduces it)
    unit: str  # Validated against the source item's unit type
    output_quantity: Decimal
    output_unit: str  # Validated against the source item's unit type (same sheet)
    output_concentration: Decimal | None = None
    output_concentration_unit: str | None = None
    dilution_factor: Decimal | None = None  # Store-only audit
    output_location_id: str | None = None  # Defaults to the source's location if None
    output_label: str | None = None
    output_expiry_date: date | None = None  # Defaults to the source's expiry_date if None
    notes: str | None = None
    note_id: str | None = None  # Link to Constellab Note


class DiluteItemDTO(BaseModelDTO):
    """DTO for diluting one target item with a diluent into a new, less
    concentrated item.

    BOTH the target (acted on) and the diluent are reduced in place. A brand new
    output item is created on the target's own sheet at the user-entered
    concentration; its quantity is user-entered, never computed by summing
    target+diluent. The diluent may be of any dimension. Concentration
    is store-only - the activity records initial/final concentration + dilution
    factor as audit.
    """

    quantity_contributed: Decimal  # Amount drawn from the target (reduces it)
    unit: str  # Validated against the target item's unit type
    diluent_item_id: str
    diluent_quantity_contributed: Decimal  # Amount drawn from the diluent (reduces it)
    diluent_unit: str  # Validated against the diluent item's own unit type (any dimension)
    output_quantity: Decimal
    output_unit: str  # Validated against the target item's unit type (same sheet)
    output_concentration: Decimal | None = None
    output_concentration_unit: str | None = None
    dilution_factor: Decimal | None = None  # Store-only audit
    output_location_id: str | None = None  # Defaults to the target's location if None
    output_label: str | None = None
    output_expiry_date: date | None = None  # Defaults to the target's expiry_date if None
    notes: str | None = None
    note_id: str | None = None  # Link to Constellab Note


class DeleteItemResultDTO(Enum):
    """Enum for delete item operation results."""

    DELETED = "deleted"
    DISCARDED = "discarded"


class ItemSimpleDTO(BaseModelDTO):
    """Simple DTO for item with minimal fields."""

    id: str
    code: str  # Structured "{sheet.code}-{year}-{incr}", unique, immutable.
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
