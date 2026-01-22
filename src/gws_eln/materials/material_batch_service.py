"""
Material Batch Service for managing MaterialBatch entities.

Handles CRUD operations, validation, and business logic for material batches.
Implements Story 5.1 from Epic 5: Service Layer - Material Batches.
"""

from gws_core import BadRequestException, CurrentUserService

from gws_eln.activities.activity import Activity
from gws_eln.activities.activity_dto import CreateActivityDTO
from gws_eln.activities.activity_service import ActivityService
from gws_eln.activities.activity_type import ActivityType
from gws_eln.core.eln_db_manager import ElnDbManager
from gws_eln.locations.location import Location
from gws_eln.locations.location_service import LocationService
from gws_eln.materials.batch_status import BatchStatus
from gws_eln.materials.material import Material
from gws_eln.materials.material_batch import MaterialBatch
from gws_eln.materials.material_batch_dto import (
    CreateAliquotDTO,
    CreateBatchDTO,
    DecrementQuantityDTO,
    IncrementQuantityDTO,
    MoveBatchDTO,
    ReceiveBatchDTO,
    RelabelBatchDTO,
    UpdateBatchDTO,
)
from gws_eln.suppliers.supplier_service import SupplierService
from gws_eln.utils.units import UnitConverter
from gws_eln.utils.validators import QuantityValidator


class MaterialBatchService:
    """
    Service class for managing MaterialBatch entities.

    Handles CRUD operations, validation, and business logic for material batches.
    Supports batch creation, receiving stock, and tracking inventory.
    """

    def __init__(self):
        """Initialize the service with dependencies."""
        self._activity_service = ActivityService()

    def get_batch(self, batch_id: str) -> MaterialBatch:
        """
        Get a batch by ID.

        :param batch_id: The ID of the batch
        :type batch_id: str
        :return: The batch if found
        :rtype: MaterialBatch
        :raises NotFoundException: If batch not found
        """
        CurrentUserService.get_and_check_current_user()
        return MaterialBatch.get_by_id_and_check(batch_id)

    def list_batches(
        self,
        material_id: str | None = None,
        location_id: str | None = None,
        include_discarded: bool = False,
    ) -> list[MaterialBatch]:
        """
        Get all batches, optionally filtered by material or location.

        :param material_id: If provided, filter by material ID
        :type material_id: Optional[str]
        :param location_id: If provided, filter by location ID
        :type location_id: Optional[str]
        :param include_discarded: If True, include discarded batches (default: False)
        :type include_discarded: bool
        :return: List of batches
        :rtype: list[MaterialBatch]
        """
        CurrentUserService.get_and_check_current_user()

        query = MaterialBatch.select()

        # By default, only show active batches
        if not include_discarded:
            query = query.where(MaterialBatch.status == BatchStatus.ACTIVE)

        if material_id is not None:
            query = query.where(MaterialBatch.material == material_id)

        if location_id is not None:
            query = query.where(MaterialBatch.location == location_id)

        return list(query.order_by(MaterialBatch.created_at.desc()))

    @ElnDbManager.transaction()
    def create_batch(self, dto: CreateBatchDTO) -> MaterialBatch:
        """
        Create a new material batch.

        :param dto: DTO containing batch data
        :type dto: CreateBatchDTO
        :return: The created batch
        :rtype: MaterialBatch
        :raises BadRequestException: If validation fails or references don't exist
        """
        # Validate input
        self._validate_batch_number(dto.batch_number)

        # Validate quantity is positive
        validated_quantity = QuantityValidator.validate_quantity(dto.quantity)

        # Validate unit is valid for the unit type
        base_unit = UnitConverter.get_base_unit(dto.unit_type)
        QuantityValidator.validate_unit(base_unit, dto.unit_type)

        # Validate material exists
        material = self._validate_material_exists(dto.material_id)

        # Validate/get location (default to "labo" if not provided)
        location = LocationService().get_or_default_location(dto.location_id)

        # Get supplier
        supplier = SupplierService().get_supplier(dto.supplier_id) if dto.supplier_id else None

        # Convert quantity to base units (input is already in base unit for the type)
        # No conversion needed since we're using base units directly
        base_quantity = validated_quantity

        # Create batch
        batch = MaterialBatch()
        batch.material = material
        batch.batch_number = dto.batch_number.strip()
        batch.quantity = base_quantity
        batch.unit_type = dto.unit_type
        batch.location = location
        batch.expiry_date = dto.expiry_date
        batch.label = dto.label.strip() if dto.label else None
        batch.notes = dto.notes.strip() if dto.notes else None
        batch.parent_batch = None  # Original batch, not an aliquot
        batch.supplier = supplier

        # Save (created_by/last_modified_by set automatically by ModelWithUser)
        batch.save()

        # Create 'receive' activity entry using ActivityService
        self._activity_service.log_activity(
            CreateActivityDTO(
                activity_type=ActivityType.RECEIVE,
                entity_id=batch.id,
                quantity=base_quantity,
                unit_type=dto.unit_type,
                to_location_id=location.id,
                notes=dto.notes,
            )
        )

        return batch

    @ElnDbManager.transaction()
    def receive_batch(self, batch_id: str, dto: ReceiveBatchDTO) -> MaterialBatch:
        """
        Receive additional stock to an existing batch (increments quantity).

        :param batch_id: The ID of the batch to receive stock for
        :type batch_id: str
        :param dto: DTO containing receive data
        :type dto: ReceiveBatchDTO
        :return: The updated batch
        :rtype: MaterialBatch
        :raises NotFoundException: If batch not found
        :raises BadRequestException: If validation fails
        """
        # Get existing batch
        batch = self.get_batch(batch_id)

        # Validate quantity is positive
        validated_quantity = QuantityValidator.validate_quantity(dto.quantity)

        # Validate unit type matches batch's unit type
        if dto.unit_type != batch.unit_type:
            raise BadRequestException(
                f"Unit type mismatch. Batch uses '{batch.unit_type.value}' "
                f"but received '{dto.unit_type.value}'"
            )

        # Add quantity to existing (both in base units)
        batch.quantity = batch.quantity + validated_quantity

        # Save (last_modified_by updated automatically by ModelWithUser)
        batch.save()

        # Create 'receive' activity entry using ActivityService
        self._activity_service.log_activity(
            CreateActivityDTO(
                activity_type=ActivityType.RECEIVE,
                entity_id=batch.id,
                quantity=validated_quantity,
                unit_type=dto.unit_type,
                to_location_id=batch.location.id,
                notes=dto.notes,
            )
        )

        return batch

    @ElnDbManager.transaction()
    def increment_quantity(self, batch_id: str, dto: IncrementQuantityDTO) -> MaterialBatch:
        """
        Increment batch quantity.

        :param batch_id: The ID of the batch
        :type batch_id: str
        :param dto: DTO containing increment data
        :type dto: IncrementQuantityDTO
        :return: The updated batch
        :rtype: MaterialBatch
        :raises NotFoundException: If batch not found
        :raises BadRequestException: If validation fails
        """
        # Get existing batch
        batch = self.get_batch(batch_id)

        # Validate quantity is positive
        validated_quantity = QuantityValidator.validate_quantity(dto.quantity)

        # Validate unit type matches batch's unit type
        if dto.unit_type != batch.unit_type:
            raise BadRequestException(
                f"Unit type mismatch. Batch uses '{batch.unit_type.value}' "
                f"but received '{dto.unit_type.value}'"
            )

        # Add quantity to existing (both in base units)
        batch.quantity = batch.quantity + validated_quantity

        # Save (last_modified_by updated automatically by ModelWithUser)
        batch.save()

        # Create 'receive' activity entry (increment is like receiving more stock)
        self._activity_service.log_activity(
            CreateActivityDTO(
                activity_type=ActivityType.RECEIVE,
                entity_id=batch.id,
                quantity=validated_quantity,
                unit_type=dto.unit_type,
                to_location_id=batch.location.id,
                notes=dto.notes,
            )
        )

        return batch

    @ElnDbManager.transaction()
    def decrement_quantity(self, batch_id: str, dto: DecrementQuantityDTO) -> MaterialBatch:
        """
        Decrement batch quantity (consumables only).

        :param batch_id: The ID of the batch
        :type batch_id: str
        :param dto: DTO containing decrement data
        :type dto: DecrementQuantityDTO
        :return: The updated batch
        :rtype: MaterialBatch
        :raises NotFoundException: If batch not found
        :raises BadRequestException: If validation fails, batch is non-consumable,
                                     or would result in negative stock
        """
        # Get existing batch
        batch = self.get_batch(batch_id)

        # Validate batch is consumable
        if not batch.is_consumable():
            raise BadRequestException(
                f"Cannot decrement non-consumable material '{batch.material.name}'. "
                "Non-consumable items cannot have their quantity reduced."
            )

        # Validate quantity is positive
        validated_quantity = QuantityValidator.validate_quantity(dto.quantity)

        # Validate unit type matches batch's unit type
        if dto.unit_type != batch.unit_type:
            raise BadRequestException(
                f"Unit type mismatch. Batch uses '{batch.unit_type.value}' "
                f"but received '{dto.unit_type.value}'"
            )

        batch.validate_sufficient_quantity(validated_quantity)

        # Subtract quantity
        batch.quantity = batch.quantity - validated_quantity

        # Save (last_modified_by updated automatically by ModelWithUser)
        batch.save()

        # Create 'consume' activity entry
        self._activity_service.log_activity(
            CreateActivityDTO(
                activity_type=ActivityType.CONSUME,
                entity_id=batch.id,
                quantity=validated_quantity,
                unit_type=dto.unit_type,
                notes=dto.notes,
            )
        )

        return batch

    @ElnDbManager.transaction()
    def move_batch(self, batch_id: str, dto: MoveBatchDTO) -> MaterialBatch:
        """
        Move a batch to a different location.

        :param batch_id: The ID of the batch to move
        :type batch_id: str
        :param dto: DTO containing move data
        :type dto: MoveBatchDTO
        :return: The updated batch
        :rtype: MaterialBatch
        :raises NotFoundException: If batch not found
        :raises BadRequestException: If destination location doesn't exist
        """
        # Get existing batch
        batch = self.get_batch(batch_id)

        # Validate destination location exists
        to_location = Location.get_by_id_and_check(dto.to_location_id)

        # Store from_location before updating
        from_location = batch.location

        # Update batch location
        batch.location = to_location

        # Save (last_modified_by updated automatically by ModelWithUser)
        batch.save()

        # Create 'move' activity entry
        self._activity_service.log_activity(
            CreateActivityDTO(
                activity_type=ActivityType.MOVE,
                entity_id=batch.id,
                from_location_id=from_location.id,
                to_location_id=to_location.id,
            )
        )

        return batch

    def update_batch(self, batch_id: str, dto: UpdateBatchDTO) -> MaterialBatch:
        """
        Update batch metadata (label, notes, expiry_date).

        Note: To change batch_number or label with activity logging, use relabel_batch().

        :param batch_id: The ID of the batch to update
        :type batch_id: str
        :param dto: DTO containing update data
        :type dto: UpdateBatchDTO
        :return: The updated batch
        :rtype: MaterialBatch
        :raises NotFoundException: If batch not found
        """
        # Get existing batch
        batch = self.get_batch(batch_id)

        # Update notes if provided (can be set to empty string to clear)
        batch.notes = dto.notes.strip() if dto.notes else None

        if dto.supplier_id is not None:
            batch.supplier = SupplierService().get_supplier(dto.supplier_id)
        else:
            batch.supplier = None

        # Update expiry_date (can be None to clear)
        # Only update if the key is explicitly provided
        batch.expiry_date = dto.expiry_date

        # Save (last_modified_by updated automatically by ModelWithUser)
        batch.save()

        return batch

    @ElnDbManager.transaction()
    def relabel_batch(self, batch_id: str, dto: RelabelBatchDTO) -> MaterialBatch:
        """
        Relabel a batch (change batch_number and/or label) with activity logging.

        :param batch_id: The ID of the batch to relabel
        :type batch_id: str
        :param dto: DTO containing relabel data
        :type dto: RelabelBatchDTO
        :return: The updated batch
        :rtype: MaterialBatch
        :raises NotFoundException: If batch not found
        :raises BadRequestException: If validation fails or no changes provided
        """
        # Get existing batch
        batch = self.get_batch(batch_id)

        # Validate at least one field is provided
        if dto.batch_number is None and dto.label is None:
            raise BadRequestException(
                "At least one of batch_number or label must be provided for relabeling"
            )

        # Track what changed for activity notes
        changes = []

        # Update batch_number if provided
        if dto.batch_number is not None:
            self._validate_batch_number(dto.batch_number)
            old_batch_number = batch.batch_number
            new_batch_number = dto.batch_number.strip()
            if old_batch_number != new_batch_number:
                batch.batch_number = new_batch_number
                changes.append(f"batch_number: '{old_batch_number}' -> '{new_batch_number}'")

        # Update label if provided
        if dto.label is not None:
            old_label = batch.label
            new_label = dto.label.strip() if dto.label else None
            if old_label != new_label:
                batch.label = new_label
                changes.append(f"label: '{old_label}' -> '{new_label}'")

        # If no actual changes, return batch as-is
        if not changes:
            return batch

        # Save (last_modified_by updated automatically by ModelWithUser)
        batch.save()

        # Create 'relabel' activity entry
        self._activity_service.log_activity(
            CreateActivityDTO(
                activity_type=ActivityType.RELABEL,
                entity_id=batch.id,
                notes="; ".join(changes),
            )
        )

        return batch

    @ElnDbManager.transaction()
    def delete_batch(self, batch_id: str, notes: str | None = None) -> dict:
        """
        Delete or discard a batch if it has no child batches (aliquots).

        - If batch only has the initial 'receive' activity from creation: hard delete
        - If batch has other activities (usage history): soft delete (set status to DISCARDED)

        :param batch_id: The ID of the batch to delete
        :type batch_id: str
        :param notes: Optional notes for discarding the batch
        :type notes: Optional[str]
        :return: Dict with 'deleted' (bool) and 'hard_deleted' (bool) keys
        :rtype: dict
        :raises NotFoundException: If batch not found
        :raises BadRequestException: If batch has child batches or is already discarded
        """
        # Get existing batch
        batch = self.get_batch(batch_id)

        # Check if already discarded
        if batch.is_discarded():
            raise BadRequestException(f"Batch '{batch.batch_number}' is already discarded")

        # Check for child batches (aliquots)
        child_count = (
            MaterialBatch.select()
            .where(MaterialBatch.parent_batch == batch)
            .where(MaterialBatch.status == BatchStatus.ACTIVE)
            .count()
        )
        if child_count > 0:
            raise BadRequestException(
                f"Cannot delete batch '{batch.batch_number}' because it has {child_count} "
                "active child batch(es) (aliquots). Delete all child batches first."
            )

        # Count activities for this batch
        activity_count = Activity.count_by_batch_id(batch.id)

        # If only 1 activity (the creation 'receive'), hard delete
        if activity_count <= 1:
            # Delete associated activities first
            Activity.delete().where(Activity.entity == batch).execute()
            # Hard delete the batch
            batch.delete_instance()
            return {"deleted": True, "hard_deleted": True}

        # Otherwise, soft delete (mark as discarded)
        # Create 'discard' activity entry
        self._activity_service.log_activity(
            CreateActivityDTO(
                activity_type=ActivityType.DISCARD,
                entity_id=batch.id,
                quantity=batch.quantity,
                unit_type=batch.unit_type,
                notes=notes if notes else "Batch discarded",
            )
        )

        # Update status to DISCARDED
        batch.status = BatchStatus.DISCARDED
        batch.save()

        return {"deleted": True, "hard_deleted": False}

    def _validate_batch_number(self, batch_number: str) -> None:
        """
        Validate batch number is not empty.

        :param batch_number: Batch number to validate
        :type batch_number: str
        :raises BadRequestException: If batch number is empty or whitespace only
        """
        if not batch_number or len(batch_number.strip()) == 0:
            raise BadRequestException("Batch number is required")

    def _validate_material_exists(self, material_id: str) -> Material:
        """
        Validate that a material exists.

        :param material_id: Material ID to validate
        :type material_id: str
        :return: The material if found
        :rtype: Material
        :raises BadRequestException: If material doesn't exist
        """
        material = Material.get_by_id(material_id)
        if not material:
            raise BadRequestException(f"Material with ID '{material_id}' does not exist")
        return material

    ########################## ALIQUOTS ##############################

    @ElnDbManager.transaction()
    def create_aliquot(self, dto: CreateAliquotDTO) -> MaterialBatch:
        """
        Create an aliquot from a parent batch.

        Aliquots are derived samples that:
        - Inherit material_id from the parent
        - Inherit supplier_id from the parent's material
        - Have a reference to the parent batch (parent_batch_id)
        - Can have their own quantity, label, and location

        The parent batch is decremented by source_quantity, while the aliquot
        is created with aliquot_quantity. These can differ (e.g., dilution,
        processing loss, etc.).

        Example: Take 2L from parent to create a 500mL aliquot after dilution.

        :param dto: DTO containing aliquot data
        :type dto: CreateAliquotDTO
        :return: The created aliquot batch
        :rtype: MaterialBatch
        :raises BadRequestException: If validation fails, parent doesn't exist,
                                     or insufficient quantity in parent
        """
        # Validate both quantities are positive
        validated_source_quantity = QuantityValidator.validate_quantity(dto.source_quantity)
        validated_aliquot_quantity = QuantityValidator.validate_quantity(dto.aliquot_quantity)

        # Validate parent batch exists
        parent_batch = self.get_batch(dto.parent_batch_id)

        # Validate parent is active (not discarded)
        if parent_batch.is_discarded():
            raise BadRequestException(
                f"Cannot create aliquot from discarded batch '{parent_batch.batch_number}'"
            )

        # Validate parent material is consumable (aliquots only make sense for consumables)
        if not parent_batch.is_consumable():
            raise BadRequestException(
                f"Cannot create aliquot from non-consumable material '{parent_batch.material.name}'. "
                "Aliquots can only be created from consumable materials (chemicals, reagents, samples)."
            )

        # Validate source unit type matches parent's unit type
        if dto.source_unit_type != parent_batch.unit_type:
            raise BadRequestException(
                f"Source unit type mismatch. Parent batch uses '{parent_batch.unit_type.value}' "
                f"but source specifies '{dto.source_unit_type.value}'"
            )

        # Validate aliquot unit type matches parent's unit type
        if dto.aliquot_unit_type != parent_batch.unit_type:
            raise BadRequestException(
                f"Aliquot unit type mismatch. Parent batch uses '{parent_batch.unit_type.value}' "
                f"but aliquot specifies '{dto.aliquot_unit_type.value}'"
            )

        # Validate sufficient quantity in parent and decrement
        parent_batch.validate_sufficient_quantity(validated_source_quantity)

        # Decrement parent quantity by source_quantity
        parent_batch.quantity = parent_batch.quantity - validated_source_quantity
        parent_batch.save()

        # Determine location (default to parent's location if not provided)
        location = (
            LocationService().get_or_default_location(dto.location_id)
            if dto.location_id
            else parent_batch.location
        )

        # Determine batch number: use provided or auto-generate
        if dto.aliquot_batch_number:
            self._validate_batch_number(dto.aliquot_batch_number)
            aliquot_batch_number = dto.aliquot_batch_number.strip()
        else:
            # Auto-generate batch number based on parent
            aliquot_count = (
                MaterialBatch.select().where(MaterialBatch.parent_batch == parent_batch).count()
            )
            aliquot_batch_number = f"{parent_batch.batch_number}-A{aliquot_count + 1}"

        # Create aliquot batch with aliquot_quantity
        aliquot = MaterialBatch()
        aliquot.material = parent_batch.material  # Inherit material from parent
        aliquot.parent_batch = parent_batch  # Set parent reference
        aliquot.batch_number = aliquot_batch_number
        aliquot.label = dto.label.strip() if dto.label else None
        aliquot.quantity = validated_aliquot_quantity  # Aliquot's own quantity
        aliquot.unit_type = dto.aliquot_unit_type
        aliquot.location = location
        aliquot.notes = dto.notes.strip() if dto.notes else None
        aliquot.expiry_date = parent_batch.expiry_date  # Inherit expiry from parent
        aliquot.supplier = (
            SupplierService().get_supplier(dto.supplier_id) if dto.supplier_id else None
        )

        # Save (created_by/last_modified_by set automatically by ModelWithUser)
        aliquot.save()

        # Create activity on PARENT batch (ALIQUOT type)
        # Documents that quantity was taken from parent to create the aliquot
        self._activity_service.log_activity(
            CreateActivityDTO(
                activity_type=ActivityType.ALIQUOT,
                entity_id=parent_batch.id,
                quantity=validated_source_quantity,  # Amount taken from parent
                unit_type=dto.source_unit_type,
                from_location_id=parent_batch.location.id,
                to_location_id=location.id,
                related_entity_id=aliquot.id,  # Reference to the child aliquot
                notes=dto.notes.strip() if dto.notes else None,
            )
        )

        # Create activity on CHILD aliquot (ALIQUOT_CREATED type)
        # Documents the origin/creation of the aliquot for traceability
        self._activity_service.log_activity(
            CreateActivityDTO(
                activity_type=ActivityType.ALIQUOT_CREATED,
                entity_id=aliquot.id,
                quantity=validated_aliquot_quantity,  # Aliquot's quantity
                unit_type=dto.aliquot_unit_type,
                to_location_id=location.id,
                related_entity_id=parent_batch.id,  # Reference to the parent batch
                notes=dto.notes.strip() if dto.notes else None,
            )
        )

        return aliquot
