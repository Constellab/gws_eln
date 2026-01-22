from gws_core import EnumField
from peewee import CharField, DateField, DecimalField, ForeignKeyField, TextField

from gws_eln.core.eln_db_manager import ElnDbManager
from gws_eln.core.model_with_user import ModelWithUser
from gws_eln.core.unit_type import UnitType
from gws_eln.locations.location import Location
from gws_eln.materials.batch_status import BatchStatus
from gws_eln.materials.material import Material


class MaterialBatch(ModelWithUser):
    """
    MaterialBatch entity - represents physical inventory (batches and aliquots).

    Handles: received batches, aliquots, instrument instances, sample instances.

    Key behaviors:
    - parent_batch_id NULL = original batch/instance
    - parent_batch_id NOT NULL = aliquot/sub-batch (inherits supplier from parent's material)
    - Quantity stored in BASE UNITS (L, kg, m, units)

    Attributes:
        material: Reference to the material catalog entry (required)
        parent_batch: Self-reference for aliquots (NULL for original batches)
        batch_number: Batch number from supplier (NULL for aliquots)
        label: Custom label for aliquots or identification
        expiry_date: Expiration date
        quantity: Amount in base units (DECIMAL for precision)
        unit_type: Type of unit for quantity
        location: Storage location (required)
        notes: Additional notes
    """

    # Required relationships
    material = ForeignKeyField(
        Material, null=False, backref="batches", on_delete="RESTRICT", index=True
    )

    location = ForeignKeyField(Location, null=False, backref="+", on_delete="RESTRICT", index=True)

    # Self-reference for aliquots (parent-child relationship)
    parent_batch = ForeignKeyField(
        "self", null=True, backref="child_batches", on_delete="CASCADE", index=True
    )

    # Batch identification
    batch_number = CharField(max_length=100, null=False, index=True)
    label = CharField(max_length=255, null=True)

    # Dates
    expiry_date = DateField(null=True, index=True)

    # Quantity tracking - stored in base units (L, kg, m, units)
    # DECIMAL(20,12) for high precision
    quantity = DecimalField(max_digits=20, decimal_places=12, null=True)
    unit_type = EnumField(choices=UnitType, max_length=20, null=True)

    # Additional information
    notes = TextField(null=True)

    # Status for soft delete
    status = EnumField(
        choices=BatchStatus, max_length=20, default=BatchStatus.ACTIVE, null=False, index=True
    )

    def is_aliquot(self) -> bool:
        """Check if this batch is an aliquot (has a parent batch)."""
        return self.parent_batch is not None

    def is_original_batch(self) -> bool:
        """Check if this is an original batch (no parent)."""
        return self.parent_batch is None

    def is_consumable(self) -> bool:
        """Check if the material of this batch is consumable."""
        return self.material.is_consumable

    def is_active(self) -> bool:
        """Check if this batch is active (not discarded)."""
        return bool(self.status == BatchStatus.ACTIVE)

    def is_discarded(self) -> bool:
        """Check if this batch has been discarded."""
        return bool(self.status == BatchStatus.DISCARDED)

    class Meta:
        table_name = "gws_eln_material_batches"
        database = ElnDbManager.get_instance().db
        is_table = True
        db_manager = ElnDbManager.get_instance()
