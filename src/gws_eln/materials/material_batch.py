from gws_core import BadRequestException, EnumField
from peewee import CharField, DateField, DecimalField, ForeignKeyField, TextField

from gws_eln.core.eln_db_manager import ElnDbManager
from gws_eln.core.model_with_user import ModelWithUser
from gws_eln.core.unit_type import UnitType
from gws_eln.locations.location import Location
from gws_eln.materials.batch_status import BatchStatus
from gws_eln.materials.material import Material
from gws_eln.materials.material_batch_dto import MaterialBatchDTO
from gws_eln.suppliers.supplier import Supplier
from gws_eln.utils.units_converter import UnitConverter


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

    # Supplier relationship (optional FK to suppliers table)
    supplier = ForeignKeyField(
        Supplier, null=True, backref="materials", on_delete="SET NULL", index=True
    )

    # Batch identification
    batch_number = CharField(max_length=100, null=False, index=True)
    label = CharField(max_length=255, null=True)

    # Dates
    expiry_date = DateField(null=True, index=True)

    # Quantity tracking - stored in base units (L, kg, m, units)
    # DECIMAL(20,12) for high precision
    quantity = DecimalField(max_digits=20, decimal_places=12)
    unit_type = EnumField(choices=UnitType, max_length=20)

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

    def validate_sufficient_quantity(self, required_quantity) -> None:
        """Check if the batch has sufficient quantity for an operation."""
        if self.quantity < required_quantity:
            raise BadRequestException(
                f"Insufficient quantity in batch {self.batch_number}. Available: {self.quantity}, Requested: {required_quantity}"
            )

    class Meta:
        table_name = "gws_eln_material_batches"
        database = ElnDbManager.get_instance().db
        is_table = True
        db_manager = ElnDbManager.get_instance()

    def to_dto(self) -> MaterialBatchDTO:
        """Convert the MaterialBatch model to a MaterialBatchDTO.

        :return: MaterialBatchDTO with the batch data
        :rtype: MaterialBatchDTO
        """

        return MaterialBatchDTO(
            id=self.id,
            material_id=self.material.id,
            material_name=self.material.name,
            location=self.location.to_dto(),
            parent_batch_id=self.parent_batch.id if self.parent_batch else None,
            supplier=self.supplier.to_dto() if self.supplier else None,
            batch_number=self.batch_number,
            label=self.label,
            expiry_date=self.expiry_date,
            quantity=self.quantity,
            pretty_quantity=UnitConverter.format_value(self.quantity, self.unit_type),
            unit_type=self.unit_type,
            notes=self.notes,
            status=self.status,
            created_at=self.created_at,
            last_modified_at=self.last_modified_at,
            created_by=self.created_by.to_dto(),
            last_modified_by=self.last_modified_by.to_dto(),
        )
