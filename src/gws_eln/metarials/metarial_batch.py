from gws_core import EnumField
from peewee import CharField, DateField, DecimalField, ForeignKeyField, TextField

from gws_eln.core.eln_db_manager import ElnDbManager
from gws_eln.core.model_with_user import ModelWithUser
from gws_eln.core.unit_type import UnitType
from gws_eln.locations.location import Location
from gws_eln.metarials.metarial import Metarial


class MetarialBatch(ModelWithUser):
    """
    MetarialBatch entity - represents physical inventory (batches and aliquots).

    Handles: received batches, aliquots, instrument instances, sample instances.

    Key behaviors:
    - parent_batch_id NULL = original batch/instance
    - parent_batch_id NOT NULL = aliquot/sub-batch (inherits supplier from parent's metarial)
    - Quantity stored in BASE UNITS (L, kg, m, units)

    Attributes:
        metarial: Reference to the material catalog entry (required)
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
    metarial = ForeignKeyField(
        Metarial, null=False, backref="batches", on_delete="CASCADE", index=True
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

    def is_aliquot(self) -> bool:
        """Check if this batch is an aliquot (has a parent batch)."""
        return self.parent_batch is not None

    def is_original_batch(self) -> bool:
        """Check if this is an original batch (no parent)."""
        return self.parent_batch is None

    def is_consumable(self) -> bool:
        """Check if the metarial of this batch is consumable."""
        return self.metarial.is_consumable

    class Meta:
        table_name = "gws_eln_metarial_batches"
        database = ElnDbManager.get_instance().db
        is_table = True
        db_manager = ElnDbManager.get_instance()
