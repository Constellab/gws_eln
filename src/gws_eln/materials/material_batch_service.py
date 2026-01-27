"""
Material Batch Service for managing MaterialBatch entities.

Handles CRUD operations, validation, and business logic for material batches.
Implements Story 5.1 from Epic 5: Service Layer - Material Batches.
"""

import re
from typing import cast

from gws_core import BadRequestException, CurrentUserService

from gws_eln.activities.activity import Activity
from gws_eln.activities.activity_dto import CreateActivityDTO
from gws_eln.activities.activity_service import ActivityService
from gws_eln.activities.activity_type import ActivityType
from gws_eln.core.eln_db_manager import ElnDbManager
from gws_eln.locations.location import Location
from gws_eln.locations.location_service import LocationService
from gws_eln.materials.batch_activity_dto import BatchActivityResult
from gws_eln.materials.batch_status import BatchStatus
from gws_eln.materials.material import Material
from gws_eln.materials.material_batch import MaterialBatch
from gws_eln.materials.material_batch_dto import (
    CreateAliquotDTO,
    CreateBatchDTO,
    DecrementQuantityDTO,
    DeleteBatchResultDTO,
    DiscardBatchDTO,
    HierarchyObjectDTO,
    MoveBatchDTO,
    ReceiveBatchDTO,
    RelabelBatchDTO,
    UpdateBatchDTO,
    UseBatchDTO,
)
from gws_eln.suppliers.supplier_service import SupplierService
from gws_eln.utils.units_converter import UnitConverter
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

    def get_parent_hierarchy(
        self,
        batch_id: str,
        include_self: bool = False,
        include_material: bool = False,
    ) -> list[HierarchyObjectDTO]:
        """
        Get the full hierarchy of parent batches for a given batch.

        Returns a list of all parent batches from the immediate parent
        up to the root (original batch), ordered from closest to furthest ancestor.

        :param batch_id: The ID of the batch to get parent hierarchy for
        :type batch_id: str
        :param include_self: If True, include the current batch at the beginning.
        :type include_self: bool
        :param include_material: If True, include the material at the end.
        :type include_material: bool
        :return: List as HierarchyObjectDTO, ordered from current batch (if include_self)
                 -> immediate parent -> root -> material (if include_material).
        :rtype: list[HierarchyObjectDTO]
        :raises NotFoundException: If batch not found
        """
        return self.get_batch(batch_id).get_parent_hierarchy(
            include_self=include_self,
            include_material=include_material,
        )

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
    def create_batch(self, dto: CreateBatchDTO) -> BatchActivityResult:
        """
        Create a new material batch.

        :param dto: DTO containing batch data
        :type dto: CreateBatchDTO
        :return: The created batch and its receive activity
        :rtype: BatchActivityResult
        :raises BadRequestException: If validation fails or references don't exist
        """
        # Validate input
        self._validate_batch_number(dto.batch_number)

        # Validate quantity is positive
        validated_quantity = QuantityValidator.validate_quantity(dto.quantity)

        # Validate material exists
        material = self._validate_material_exists(dto.material_id)

        # Get unit_type from the material's default_unit_type
        unit_type = material.default_unit_type

        # Validate unit is valid for the material's unit type
        if not UnitConverter.is_valid_unit(dto.unit, unit_type):
            valid_units = ", ".join(UnitConverter.get_valid_units(unit_type))
            raise BadRequestException(
                f"Invalid unit '{dto.unit}' for material '{material.name}' "
                f"(unit type: {unit_type.value}). Valid units: {valid_units}"
            )

        # Validate/get location (default to "labo" if not provided)
        location = LocationService().get_or_default_location(dto.location_id)

        # Get supplier
        supplier = SupplierService().get_supplier(dto.supplier_id) if dto.supplier_id else None

        # Convert quantity from the given unit to base unit for storage
        base_quantity = UnitConverter.to_base_unit(validated_quantity, dto.unit, unit_type)

        # Create batch
        batch = MaterialBatch()
        batch.material = material
        batch.batch_number = dto.batch_number.strip()
        batch.quantity = base_quantity
        batch.unit_type = unit_type
        batch.location = location
        batch.expiry_date = dto.expiry_date
        batch.label = dto.label.strip() if dto.label else None
        batch.notes = dto.notes.strip() if dto.notes else None
        batch.parent_batch = None  # Original batch, not an aliquot
        batch.supplier = supplier

        # Save (created_by/last_modified_by set automatically by ModelWithUser)
        batch.save()

        # Create 'receive' activity entry using ActivityService
        activity = self._activity_service.log_activity(
            CreateActivityDTO(
                activity_type=ActivityType.RECEIVE,
                batch_id=batch.id,
                quantity=base_quantity,
                unit_type=unit_type,
                notes=dto.notes,
                note_id=dto.note_id,
            )
        )

        return BatchActivityResult(batch=batch, activity=activity)

    @ElnDbManager.transaction()
    def receive_batch(self, batch_id: str, dto: ReceiveBatchDTO) -> BatchActivityResult:
        """
        Receive additional stock to an existing batch (increments quantity).

        :param batch_id: The ID of the batch to receive stock for
        :type batch_id: str
        :param dto: DTO containing receive data
        :type dto: ReceiveBatchDTO
        :return: The updated batch and the created activity
        :rtype: BatchActivityResult
        :raises NotFoundException: If batch not found
        :raises BadRequestException: If validation fails
        """
        # Get existing batch
        batch = self.get_batch(batch_id)

        # Validate quantity is positive
        validated_quantity = QuantityValidator.validate_quantity(dto.quantity)

        # Validate unit and convert to base unit
        base_quantity = self._validate_and_convert_quantity(batch, validated_quantity, dto.unit)

        # Add quantity to existing (both in base units)
        batch.quantity = batch.quantity + base_quantity

        # Save (last_modified_by updated automatically by ModelWithUser)
        batch.save()

        # Create 'receive' activity entry using ActivityService
        activity = self._activity_service.log_activity(
            CreateActivityDTO(
                activity_type=ActivityType.RECEIVE,
                batch_id=batch.id,
                quantity=base_quantity,
                unit_type=batch.unit_type,
                notes=dto.notes,
                note_id=dto.note_id,
            )
        )

        return BatchActivityResult(batch=batch, activity=activity)

    @ElnDbManager.transaction()
    def consume_quantity(self, batch_id: str, dto: DecrementQuantityDTO) -> BatchActivityResult:
        """
        Decrement batch quantity (consumables only).

        :param batch_id: The ID of the batch
        :type batch_id: str
        :param dto: DTO containing decrement data
        :type dto: DecrementQuantityDTO
        :return: The updated batch and the created activity
        :rtype: BatchActivityResult
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

        # Validate unit and convert to base unit
        base_quantity = self._validate_and_convert_quantity(batch, validated_quantity, dto.unit)

        batch.validate_sufficient_quantity(base_quantity)

        # Subtract quantity
        batch.quantity = batch.quantity - base_quantity

        # Save (last_modified_by updated automatically by ModelWithUser)
        batch.save()

        # Create 'consume' activity entry
        activity = self._activity_service.log_activity(
            CreateActivityDTO(
                activity_type=ActivityType.CONSUME,
                batch_id=batch.id,
                quantity=base_quantity,
                unit_type=batch.unit_type,
                notes=dto.notes,
                note_id=dto.note_id,
            )
        )

        return BatchActivityResult(batch=batch, activity=activity)

    @ElnDbManager.transaction()
    def move_batch(self, batch_id: str, dto: MoveBatchDTO) -> BatchActivityResult:
        """
        Move a batch to a different location.

        :param batch_id: The ID of the batch to move
        :type batch_id: str
        :param dto: DTO containing move data
        :type dto: MoveBatchDTO
        :return: The updated batch and the created activity
        :rtype: BatchActivityResult
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
        activity = self._activity_service.log_activity(
            CreateActivityDTO(
                activity_type=ActivityType.MOVE,
                batch_id=batch.id,
                from_location_id=from_location.id,
                to_location_id=to_location.id,
                note_id=dto.note_id,
            )
        )

        return BatchActivityResult(batch=batch, activity=activity)

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

    def use_batch(self, batch_id: str, dto: UseBatchDTO) -> BatchActivityResult:
        """
        Record a USE activity on a batch (reference only, no state change).

        USE is for non-consumable materials or when you just want to log
        that a batch was used without changing its quantity.

        :param batch_id: The ID of the batch
        :type batch_id: str
        :param dto: DTO containing use data
        :type dto: UseBatchDTO
        :return: The batch and the created activity
        :rtype: BatchActivityResult
        """
        # Validate batch exists
        batch = self.get_batch(batch_id)

        activity = self._activity_service.log_activity(
            CreateActivityDTO(
                activity_type=ActivityType.USE,
                batch_id=batch_id,
                notes=dto.notes,
                note_id=dto.note_id,
            )
        )

        return BatchActivityResult(batch=batch, activity=activity)

    @ElnDbManager.transaction()
    def discard_batch(self, batch_id: str, dto: DiscardBatchDTO) -> BatchActivityResult:
        """
        Discard a batch (soft delete with activity logging).

        :param batch_id: The ID of the batch to discard
        :type batch_id: str
        :param dto: DTO containing discard data
        :type dto: DiscardBatchDTO
        :return: The updated batch and the created activity
        :rtype: BatchActivityResult
        :raises NotFoundException: If batch not found
        :raises BadRequestException: If batch is already discarded
        """
        batch = self.get_batch(batch_id)

        if batch.is_discarded():
            raise BadRequestException(f"Batch '{batch.batch_number}' is already discarded")

        # Create 'discard' activity entry
        activity = self._activity_service.log_activity(
            CreateActivityDTO(
                activity_type=ActivityType.DISCARD,
                batch_id=batch.id,
                quantity=batch.quantity,
                unit_type=batch.unit_type,
                notes=dto.notes or "Batch discarded",
                note_id=dto.note_id,
            )
        )

        batch.status = BatchStatus.DISCARDED
        batch.save()

        return BatchActivityResult(batch=batch, activity=activity)

    @ElnDbManager.transaction()
    def relabel_batch(self, batch_id: str, dto: RelabelBatchDTO) -> BatchActivityResult:
        """
        Relabel a batch (change batch_number and/or label) with activity logging.

        :param batch_id: The ID of the batch to relabel
        :type batch_id: str
        :param dto: DTO containing relabel data
        :type dto: RelabelBatchDTO
        :return: The updated batch and the created activity (activity is None if no changes)
        :rtype: BatchActivityResult
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

        # If no actual changes, return batch as-is with no activity
        if not changes:
            return BatchActivityResult(batch=batch, activity=None)

        # Save (last_modified_by updated automatically by ModelWithUser)
        batch.save()

        # Create 'relabel' activity entry
        activity = self._activity_service.log_activity(
            CreateActivityDTO(
                activity_type=ActivityType.RELABEL,
                batch_id=batch.id,
                notes="; ".join(changes),
                note_id=dto.note_id,
            )
        )

        return BatchActivityResult(batch=batch, activity=activity)

    @ElnDbManager.transaction()
    def delete_batch(
        self, batch_id: str, notes: str | None = None, note_id: str | None = None
    ) -> DeleteBatchResultDTO:
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
            Activity.delete().where(Activity.batch == batch).execute()
            # Hard delete the batch
            batch.delete_instance()
            return DeleteBatchResultDTO.DELETED

        # Otherwise, soft delete (mark as discarded)
        # Create 'discard' activity entry
        self._activity_service.log_activity(
            CreateActivityDTO(
                activity_type=ActivityType.DISCARD,
                batch_id=batch.id,
                quantity=batch.quantity,
                unit_type=batch.unit_type,
                notes=notes if notes else "Batch discarded",
                note_id=note_id,
            )
        )

        # Update status to DISCARDED
        batch.status = BatchStatus.DISCARDED
        batch.save()

        return DeleteBatchResultDTO.DISCARDED

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

    def _validate_and_convert_quantity(self, batch: MaterialBatch, quantity, unit: str):
        """
        Validate that the unit is valid for the batch's unit type and convert to base unit.

        :param batch: The batch to validate against
        :type batch: MaterialBatch
        :param quantity: The quantity to convert (already validated as positive)
        :param unit: The unit string (e.g., 'mL', 'g', 'kg')
        :type unit: str
        :return: Quantity converted to base unit
        :raises BadRequestException: If unit is not valid for the batch's unit type
        """
        unit_type = batch.unit_type

        if not UnitConverter.is_valid_unit(unit, unit_type):
            valid_units = ", ".join(UnitConverter.get_valid_units(unit_type))
            raise BadRequestException(
                f"Invalid unit '{unit}' for batch '{batch.batch_number}' "
                f"(unit type: {unit_type.value}). Valid units: {valid_units}"
            )

        return UnitConverter.to_base_unit(quantity, unit, unit_type)

    ########################## REVERSE ACTIVITY ##############################

    @ElnDbManager.transaction()
    def reverse_activity(self, activity_id: str) -> None:
        """Reverse an activity: undo its effect on the batch and delete the activity record.

        This is called when a materialActivity block is removed from a note.
        The batch state is restored to what it was before the activity.

        :param activity_id: The ID of the activity to reverse
        :type activity_id: str
        :raises BadRequestException: If activity not found, or reversal is not possible
        """
        CurrentUserService.get_and_check_current_user()

        activity = Activity.get_by_id(activity_id)
        if not activity:
            raise BadRequestException(f"Activity with ID '{activity_id}' does not exist")

        batch = cast(MaterialBatch, activity.batch)
        activity_type = activity.activity_type

        if activity_type == ActivityType.RECEIVE:
            self._reverse_receive(activity, batch)
        elif activity_type == ActivityType.CONSUME:
            self._reverse_consume(activity, batch)
        elif activity_type == ActivityType.MOVE:
            self._reverse_move(activity, batch)
        elif activity_type == ActivityType.USE:
            self._reverse_use(activity, batch)
        elif activity_type == ActivityType.DISCARD:
            self._reverse_discard(activity, batch)
        elif activity_type == ActivityType.ALIQUOT:
            self._reverse_aliquot(activity, batch)
        elif activity_type == ActivityType.ALIQUOT_CREATED:
            raise BadRequestException(
                "Cannot reverse ALIQUOT_CREATED directly. "
                "Reverse the parent ALIQUOT activity instead."
            )
        elif activity_type == ActivityType.RELABEL:
            self._reverse_relabel(activity, batch)
        else:
            raise BadRequestException(f"Unknown activity type: {activity_type}")

        # Delete the activity record
        activity.delete_instance()

    def _reverse_receive(self, activity: Activity, batch: MaterialBatch) -> None:
        """Reverse RECEIVE: decrement quantity that was added.

        Original effect: batch.quantity += activity.quantity
        Reversal: batch.quantity -= activity.quantity
        """
        if activity.quantity is None:
            raise BadRequestException("Cannot reverse RECEIVE activity without quantity")

        if batch.quantity < activity.quantity:
            raise BadRequestException(
                f"Cannot reverse RECEIVE: batch '{batch.batch_number}' current quantity "
                f"({batch.quantity}) is less than the received quantity ({activity.quantity}). "
                f"The batch may have been consumed since this receive."
            )

        batch.quantity = batch.quantity - activity.quantity
        batch.save()

    def _reverse_consume(self, activity: Activity, batch: MaterialBatch) -> None:
        """Reverse CONSUME: re-add quantity that was consumed.

        Original effect: batch.quantity -= activity.quantity
        Reversal: batch.quantity += activity.quantity
        """
        if activity.quantity is None:
            raise BadRequestException("Cannot reverse CONSUME activity without quantity")

        batch.quantity = batch.quantity + activity.quantity
        batch.save()

    def _reverse_move(self, activity: Activity, batch: MaterialBatch) -> None:
        """Reverse MOVE: restore original location.

        Original effect: batch.location = activity.to_location
        Reversal: batch.location = activity.from_location
        """
        if activity.from_location is None:
            raise BadRequestException(
                "Cannot reverse MOVE activity: original location (from_location) is not recorded"
            )

        batch.location = activity.from_location
        batch.save()

    def _reverse_use(self, activity: Activity, batch: MaterialBatch) -> None:
        """Reverse USE: no batch state change needed.

        USE is reference-only (no quantity/location change).
        Just delete the activity record (done in reverse_activity).
        """
        pass

    def _reverse_discard(self, activity: Activity, batch: MaterialBatch) -> None:
        """Reverse DISCARD: reactivate the batch.

        Original effect: batch.status = DISCARDED
        Reversal: batch.status = ACTIVE
        """
        if not batch.is_discarded():
            raise BadRequestException(
                f"Cannot reverse DISCARD: batch '{batch.batch_number}' is not discarded"
            )

        batch.status = BatchStatus.ACTIVE
        batch.save()

    def _reverse_aliquot(self, activity: Activity, batch: MaterialBatch) -> None:
        """Reverse ALIQUOT: restore parent quantity, delete child batch and its ALIQUOT_CREATED activity.

        Original effect:
        - parent.quantity -= source_quantity (recorded in activity.quantity)
        - child batch created (referenced by activity.related_batch)
        - ALIQUOT_CREATED activity created on child batch

        Reversal:
        - Verify child batch has no active children (sub-aliquots)
        - Delete ALIQUOT_CREATED activity on child batch
        - Delete child batch
        - parent.quantity += activity.quantity
        """
        child_batch = activity.related_batch
        if child_batch is None:
            raise BadRequestException(
                "Cannot reverse ALIQUOT activity: related child batch not found"
            )

        # Check child batch has no active children
        active_children_count = (
            MaterialBatch.select()
            .where(MaterialBatch.parent_batch == child_batch)
            .where(MaterialBatch.status == BatchStatus.ACTIVE)
            .count()
        )
        if active_children_count > 0:
            raise BadRequestException(
                f"Cannot reverse ALIQUOT: child batch '{child_batch.batch_number}' has "
                f"{active_children_count} active sub-aliquot(s). Delete them first."
            )

        # Delete ALIQUOT_CREATED activity on the child batch
        Activity.delete().where(
            (Activity.batch == child_batch)
            & (Activity.activity_type == ActivityType.ALIQUOT_CREATED)
        ).execute()

        # Delete all activities on the child batch (there should only be the ALIQUOT_CREATED)
        Activity.delete().where(Activity.batch == child_batch).execute()

        # Delete child batch
        child_batch.delete_instance()

        # Restore parent quantity
        if activity.quantity is not None:
            batch.quantity = batch.quantity + activity.quantity
            batch.save()

    def _reverse_relabel(self, activity: Activity, batch: MaterialBatch) -> None:
        """Reverse RELABEL: restore original batch_number and/or label.

        The original values are stored in activity.notes with format:
        "batch_number: 'old_value' -> 'new_value'; label: 'old_value' -> 'new_value'"

        Parse this string to extract and restore original values.
        """
        if not activity.notes:
            raise BadRequestException(
                "Cannot reverse RELABEL activity: no change details recorded in notes"
            )

        # Parse batch_number change
        batch_number_match = re.search(r"batch_number: '(.+?)' -> '(.+?)'", activity.notes)
        if batch_number_match:
            old_batch_number = batch_number_match.group(1)
            batch.batch_number = old_batch_number

        # Parse label change
        label_match = re.search(r"label: '(.+?)' -> '(.+?)'", activity.notes)
        if label_match:
            old_label = label_match.group(1)
            batch.label = None if old_label == "None" else old_label

        batch.save()

    ########################## ALIQUOTS ##############################

    @ElnDbManager.transaction()
    def create_aliquot(self, dto: CreateAliquotDTO) -> BatchActivityResult:
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
        :return: The created aliquot batch and the ALIQUOT activity (on the parent)
        :rtype: BatchActivityResult
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

        # Get unit_type from parent batch
        unit_type = parent_batch.unit_type

        # Validate source unit and convert to base unit
        base_source_quantity = self._validate_and_convert_quantity(
            parent_batch, validated_source_quantity, dto.source_unit
        )

        # Validate aliquot unit and convert to base unit
        if not UnitConverter.is_valid_unit(dto.aliquot_unit, unit_type):
            valid_units = ", ".join(UnitConverter.get_valid_units(unit_type))
            raise BadRequestException(
                f"Invalid aliquot unit '{dto.aliquot_unit}' for batch '{parent_batch.batch_number}' "
                f"(unit type: {unit_type.value}). Valid units: {valid_units}"
            )
        base_aliquot_quantity = UnitConverter.to_base_unit(
            validated_aliquot_quantity, dto.aliquot_unit, unit_type
        )

        # Validate sufficient quantity in parent (using base units)
        parent_batch.validate_sufficient_quantity(base_source_quantity)

        # Decrement parent quantity by source_quantity (in base units)
        parent_batch.quantity = parent_batch.quantity - base_source_quantity
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

        # Create aliquot batch with aliquot_quantity (in base units)
        aliquot = MaterialBatch()
        aliquot.material = parent_batch.material  # Inherit material from parent
        aliquot.parent_batch = parent_batch  # Set parent reference
        aliquot.batch_number = aliquot_batch_number
        aliquot.label = dto.label.strip() if dto.label else None
        aliquot.quantity = base_aliquot_quantity  # Aliquot's own quantity in base units
        aliquot.unit_type = unit_type  # Inherit unit_type from parent
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
        aliquot_activity = self._activity_service.log_activity(
            CreateActivityDTO(
                activity_type=ActivityType.ALIQUOT,
                batch_id=parent_batch.id,
                quantity=base_source_quantity,  # Amount taken from parent (base units)
                unit_type=unit_type,
                from_location_id=parent_batch.location.id,
                to_location_id=location.id,
                related_batch_id=aliquot.id,  # Reference to the child aliquot
                notes=dto.notes.strip() if dto.notes else None,
                note_id=dto.note_id,
            )
        )

        # Create activity on CHILD aliquot (ALIQUOT_CREATED type)
        # Documents the origin/creation of the aliquot for traceability
        self._activity_service.log_activity(
            CreateActivityDTO(
                activity_type=ActivityType.ALIQUOT_CREATED,
                batch_id=aliquot.id,
                quantity=base_aliquot_quantity,  # Aliquot's quantity (base units)
                unit_type=unit_type,
                to_location_id=location.id,
                related_batch_id=parent_batch.id,  # Reference to the parent batch
                notes=dto.notes.strip() if dto.notes else None,
                note_id=dto.note_id,
            )
        )

        return BatchActivityResult(batch=aliquot, activity=aliquot_activity)
