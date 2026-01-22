"""
Material Batch DTOs for create, receive, and other operations.

Defines data transfer objects for MaterialBatchService operations.
"""

from datetime import date
from decimal import Decimal

from gws_core import BaseModelDTO

from gws_eln.core.unit_type import UnitType


class CreateBatchDTO(BaseModelDTO):
    """DTO for creating a new material batch."""

    material_id: str
    batch_number: str
    quantity: Decimal
    unit_type: UnitType
    location_id: str | None = None  # Default to "labo" if None
    expiry_date: date | None = None
    label: str | None = None
    notes: str | None = None


class ReceiveBatchDTO(BaseModelDTO):
    """DTO for receiving additional stock to an existing batch."""

    quantity: Decimal
    unit_type: UnitType
    notes: str | None = None


class IncrementQuantityDTO(BaseModelDTO):
    """DTO for incrementing batch quantity."""

    quantity: Decimal
    unit_type: UnitType
    reason: str | None = None


class DecrementQuantityDTO(BaseModelDTO):
    """DTO for decrementing batch quantity (consumables only)."""

    quantity: Decimal
    unit_type: UnitType
    reason: str


class MoveBatchDTO(BaseModelDTO):
    """DTO for moving a batch to a different location."""

    to_location_id: str


class UpdateBatchDTO(BaseModelDTO):
    """DTO for updating batch metadata (label, notes, expiry_date)."""

    label: str | None = None
    notes: str | None = None
    expiry_date: date | None = None


class RelabelBatchDTO(BaseModelDTO):
    """DTO for relabeling a batch (changing batch_number or label)."""

    batch_number: str | None = None
    label: str | None = None
