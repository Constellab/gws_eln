"""
Material Batch DTOs for create, receive, and other operations.

Defines data transfer objects for MaterialBatchService operations.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from gws_core import BaseModelDTO, UserDTO

from gws_eln.core.unit_type import UnitType
from gws_eln.locations.location_dto import LocationDTO
from gws_eln.materials.batch_status import BatchStatus
from gws_eln.materials.material_dto import MaterialDTO
from gws_eln.suppliers.supplier_dto import SupplierDTO


class CreateBatchDTO(BaseModelDTO):
    """DTO for creating a new material batch.

    The unit field accepts any valid unit string (e.g., 'mL', 'g', 'kg').
    The unit_type is automatically determined from the material's default_unit_type.
    The quantity is converted from the given unit to the base unit for storage.
    """

    material_id: str
    batch_number: str
    quantity: Decimal
    unit: str  # Exact unit (e.g., 'mL', 'g', 'kg') - converted to base unit for storage
    location_id: str | None = None  # Default to "labo" if None
    supplier_id: str | None = None
    expiry_date: date | None = None
    label: str | None = None
    notes: str | None = None


class ReceiveBatchDTO(BaseModelDTO):
    """DTO for receiving additional stock to an existing batch.

    The unit field accepts any valid unit string (e.g., 'mL', 'g', 'kg').
    The quantity is converted from the given unit to the base unit for storage.
    """

    quantity: Decimal
    unit: str  # Exact unit (e.g., 'mL', 'g', 'kg') - converted to base unit for storage
    notes: str | None = None


class IncrementQuantityDTO(BaseModelDTO):
    """DTO for incrementing batch quantity.

    The unit field accepts any valid unit string (e.g., 'mL', 'g', 'kg').
    The quantity is converted from the given unit to the base unit for storage.
    """

    quantity: Decimal
    unit: str  # Exact unit (e.g., 'mL', 'g', 'kg') - converted to base unit for storage
    notes: str | None = None


class DecrementQuantityDTO(BaseModelDTO):
    """DTO for decrementing batch quantity (consumables only).

    The unit field accepts any valid unit string (e.g., 'mL', 'g', 'kg').
    The quantity is converted from the given unit to the base unit for storage.
    """

    quantity: Decimal
    unit: str  # Exact unit (e.g., 'mL', 'g', 'kg') - converted to base unit for storage
    notes: str | None = None


class MoveBatchDTO(BaseModelDTO):
    """DTO for moving a batch to a different location."""

    to_location_id: str


class UpdateBatchDTO(BaseModelDTO):
    """DTO for updating batch metadata (label, notes, expiry_date)."""

    notes: str | None = None
    expiry_date: date | None = None
    supplier_id: str | None = None


class RelabelBatchDTO(BaseModelDTO):
    """DTO for relabeling a batch (changing batch_number or label)."""

    batch_number: str | None = None
    label: str | None = None


class DeleteBatchResultDTO(Enum):
    """Enum for delete batch operation results."""

    DELETED = "deleted"
    DISCARDED = "discarded"


class CreateAliquotDTO(BaseModelDTO):
    """DTO for creating an aliquot from a parent batch.

    Aliquots are derived samples that inherit material_id and supplier
    from the parent batch. The parent's quantity will be decremented
    by source_quantity.

    Example: Take 2L from parent (source_quantity=2, source_unit='L')
    to create a 500mL aliquot (aliquot_quantity=500, aliquot_unit='mL').

    Note: Both units must be compatible with the parent batch's unit_type.
    The quantities are converted from the given units to base units for storage.
    """

    parent_batch_id: str
    # Amount to take from parent batch (decrements parent)
    source_quantity: Decimal
    source_unit: str  # Exact unit (e.g., 'mL', 'L', 'g') - converted to base unit for storage
    # Amount for the new aliquot (can differ from source due to dilution, processing, etc.)
    aliquot_quantity: Decimal
    aliquot_unit: str  # Exact unit (e.g., 'mL', 'L', 'g') - converted to base unit for storage
    # Optional custom batch number for the aliquot (auto-generated if not provided)
    aliquot_batch_number: str | None = None
    label: str | None = None
    location_id: str | None = None  # Default to parent's location if None
    notes: str | None = None
    supplier_id: str | None = None  # Default to None


class MaterialBatchSimpleDTO(BaseModelDTO):
    """Simple DTO for material batch with minimal fields."""

    id: str
    batch_number: str
    label: str | None


class MaterialBatchDTO(MaterialBatchSimpleDTO):
    """DTO for displaying material batch information in the frontend."""

    quantity: Decimal
    unit_type: UnitType
    pretty_quantity: str  # Pre-formatted quantity string for display
    material: MaterialDTO
    location: LocationDTO
    parent_batch: MaterialBatchSimpleDTO | None
    supplier: SupplierDTO | None
    expiry_date: date | None
    notes: str | None
    status: BatchStatus
    created_at: datetime
    last_modified_at: datetime
    created_by: UserDTO
    last_modified_by: UserDTO


class HierarchyObjectDTO(BaseModelDTO):
    """DTO for representing a batch in a hierarchy view."""

    id: str
    name: str
    sub_name: str | None
