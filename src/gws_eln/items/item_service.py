"""
Item Service for managing Item entities.

Handles CRUD operations, validation, and business logic for items.
Implements Story 5.1 from Epic 5: Service Layer - Items.
"""

import re
from typing import cast

from gws_core import BadRequestException, CurrentUserService
from gws_eln.activities.activity import Activity
from gws_eln.activities.activity_dto import CreateActivityDTO
from gws_eln.activities.activity_service import ActivityService
from gws_eln.activities.activity_type import ActivityType
from gws_eln.core.eln_db_manager import ElnDbManager
from gws_eln.items.item import Item
from gws_eln.items.item_activity_dto import ItemActivityResult
from gws_eln.items.item_dto import (
    CreateAliquotDTO,
    CreateItemDTO,
    DecrementQuantityDTO,
    DeleteItemResultDTO,
    DiscardItemDTO,
    HierarchyObjectDTO,
    MoveItemDTO,
    ReceiveItemDTO,
    RelabelItemDTO,
    UpdateItemDTO,
    UseItemDTO,
)
from gws_eln.items.item_sheet import ItemSheet
from gws_eln.items.item_status import ItemStatus
from gws_eln.locations.location import Location
from gws_eln.locations.location_service import LocationService
from gws_eln.suppliers.supplier_service import SupplierService
from gws_eln.utils.units_converter import UnitConverter
from gws_eln.utils.validators import QuantityValidator


class ItemService:
    """
    Service class for managing Item entities.

    Handles CRUD operations, validation, and business logic for items.
    Supports item creation, receiving stock, and tracking inventory.
    """

    def __init__(self):
        """Initialize the service with dependencies."""
        self._activity_service = ActivityService()

    def get_item(self, item_id: str) -> Item:
        """
        Get an item by ID.

        :param item_id: The ID of the item
        :type item_id: str
        :return: The item if found
        :rtype: Item
        :raises NotFoundException: If item not found
        """
        CurrentUserService.get_and_check_current_user()
        return Item.get_by_id_and_check(item_id)

    def get_parent_hierarchy(
        self,
        item_id: str,
        include_self: bool = False,
        include_item_sheet: bool = False,
    ) -> list[HierarchyObjectDTO]:
        """
        Get the full hierarchy of parent items for a given item.

        Returns a list of all parent items from the immediate parent
        up to the root (original batch), ordered from closest to furthest ancestor.

        :param item_id: The ID of the item to get parent hierarchy for
        :type item_id: str
        :param include_self: If True, include the current item at the beginning.
        :type include_self: bool
        :param include_item_sheet: If True, include the item sheet at the end.
        :type include_item_sheet: bool
        :return: List as HierarchyObjectDTO, ordered from current item (if include_self)
                 -> immediate parent -> root -> item sheet (if include_item_sheet).
        :rtype: list[HierarchyObjectDTO]
        :raises NotFoundException: If item not found
        """
        return self.get_item(item_id).get_parent_hierarchy(
            include_self=include_self,
            include_item_sheet=include_item_sheet,
        )

    def list_items(
        self,
        item_sheet_id: str | None = None,
        location_id: str | None = None,
        include_discarded: bool = False,
    ) -> list[Item]:
        """
        Get all items, optionally filtered by item sheet or location.

        :param item_sheet_id: If provided, filter by item sheet ID
        :type item_sheet_id: Optional[str]
        :param location_id: If provided, filter by location ID
        :type location_id: Optional[str]
        :param include_discarded: If True, include discarded items (default: False)
        :type include_discarded: bool
        :return: List of items
        :rtype: list[Item]
        """
        CurrentUserService.get_and_check_current_user()

        query = Item.select()

        # By default, only show active items
        if not include_discarded:
            query = query.where(Item.status == ItemStatus.ACTIVE)

        if item_sheet_id is not None:
            query = query.where(Item.item_sheet == item_sheet_id)

        if location_id is not None:
            query = query.where(Item.location == location_id)

        return list(query.order_by(Item.created_at.desc()))

    @ElnDbManager.transaction()
    def create_item(self, dto: CreateItemDTO) -> ItemActivityResult:
        """
        Create a new item.

        :param dto: DTO containing item data
        :type dto: CreateItemDTO
        :return: The created item and its receive activity
        :rtype: BatchActivityResult
        :raises BadRequestException: If validation fails or references don't exist
        """
        # Validate input
        self._validate_item_number(dto.item_number)

        # Validate quantity is positive
        validated_quantity = QuantityValidator.validate_quantity(dto.quantity)

        # Validate item sheet exists
        item_sheet = self._validate_item_sheet_exists(dto.item_sheet_id)

        # Get unit_type from the item sheet's default_unit_type
        unit_type = item_sheet.default_unit_type

        # Validate unit is valid for the item sheet's unit type
        if not UnitConverter.is_valid_unit(dto.unit, unit_type):
            valid_units = ", ".join(UnitConverter.get_valid_units(unit_type))
            raise BadRequestException(
                f"Invalid unit '{dto.unit}' for item sheet '{item_sheet.name}' "
                f"(unit type: {unit_type.value}). Valid units: {valid_units}"
            )

        # Validate/get location (default to "labo" if not provided)
        location = LocationService().get_or_default_location(dto.location_id)

        # Get supplier
        supplier = SupplierService().get_supplier(dto.supplier_id) if dto.supplier_id else None

        # Convert quantity from the given unit to base unit for storage
        base_quantity = UnitConverter.to_base_unit(validated_quantity, dto.unit, unit_type)

        # Create item
        item = Item()
        item.item_sheet = item_sheet
        item.batch_number = dto.item_number.strip()
        item.quantity = base_quantity
        item.unit_type = unit_type
        item.location = location
        item.expiry_date = dto.expiry_date
        item.label = dto.label.strip() if dto.label else None
        item.notes = dto.notes.strip() if dto.notes else None
        item.parent_item = None  # Original batch, not an aliquot
        item.supplier = supplier

        # Save (created_by/last_modified_by set automatically by ModelWithUser)
        item.save()

        # Create 'receive' activity entry using ActivityService
        activity = self._activity_service.log_activity(
            CreateActivityDTO(
                activity_type=ActivityType.CREATE,
                batch_id=item.id,
                quantity=base_quantity,
                unit_type=unit_type,
                notes=dto.notes,
                note_id=dto.note_id,
            )
        )

        return ItemActivityResult(item=item, activity=activity)

    @ElnDbManager.transaction()
    def receive_item(self, item_id: str, dto: ReceiveItemDTO) -> ItemActivityResult:
        """
        Receive additional stock to an existing item (increments quantity).

        :param item_id: The ID of the item to receive stock for
        :type item_id: str
        :param dto: DTO containing receive data
        :type dto: ReceiveItemDTO
        :return: The updated item and the created activity
        :rtype: ItemActivityResult
        :raises NotFoundException: If item not found
        :raises BadRequestException: If validation fails
        """
        # Get existing item
        item = self.get_item(item_id)

        # Validate quantity is positive
        validated_quantity = QuantityValidator.validate_quantity(dto.quantity)

        # Validate unit and convert to base unit
        base_quantity = self._validate_and_convert_quantity(item, validated_quantity, dto.unit)

        # Add quantity to existing (both in base units)
        item.quantity = item.quantity + base_quantity

        # Save (last_modified_by updated automatically by ModelWithUser)
        item.save()

        # Create 'receive' activity entry using ActivityService
        activity = self._activity_service.log_activity(
            CreateActivityDTO(
                activity_type=ActivityType.RECEIVE,
                batch_id=item.id,
                quantity=base_quantity,
                unit_type=item.unit_type,
                notes=dto.notes,
                note_id=dto.note_id,
            )
        )

        return ItemActivityResult(item=item, activity=activity)

    @ElnDbManager.transaction()
    def consume_quantity(self, item_id: str, dto: DecrementQuantityDTO) -> ItemActivityResult:
        """
        Decrement item quantity (consumables only).

        :param item_id: The ID of the item
        :type item_id: str
        :param dto: DTO containing decrement data
        :type dto: DecrementQuantityDTO
        :return: The updated item and the created activity
        :rtype: ItemActivityResult
        :raises NotFoundException: If item not found
        :raises BadRequestException: If validation fails, item is non-consumable,
                                     or would result in negative stock
        """
        # Get existing item
        item = self.get_item(item_id)

        # Validate item is consumable
        if not item.is_consumable():
            raise BadRequestException(
                f"Cannot decrement non-consumable item sheet '{item.item_sheet.name}'. "
                "Non-consumable items cannot have their quantity reduced."
            )

        # Validate quantity is positive
        validated_quantity = QuantityValidator.validate_quantity(dto.quantity)

        # Validate unit and convert to base unit
        base_quantity = self._validate_and_convert_quantity(item, validated_quantity, dto.unit)

        item.validate_sufficient_quantity(base_quantity)

        # Subtract quantity
        item.quantity = item.quantity - base_quantity

        # Save (last_modified_by updated automatically by ModelWithUser)
        item.save()

        # Create 'consume' activity entry
        activity = self._activity_service.log_activity(
            CreateActivityDTO(
                activity_type=ActivityType.CONSUME,
                batch_id=item.id,
                quantity=base_quantity,
                unit_type=item.unit_type,
                notes=dto.notes,
                note_id=dto.note_id,
            )
        )

        return ItemActivityResult(item=item, activity=activity)

    @ElnDbManager.transaction()
    def move_item(self, item_id: str, dto: MoveItemDTO) -> ItemActivityResult:
        """
        Move an item to a different location.

        :param item_id: The ID of the item to move
        :type item_id: str
        :param dto: DTO containing move data
        :type dto: MoveItemDTO
        :return: The updated item and the created activity
        :rtype: ItemActivityResult
        :raises NotFoundException: If item not found
        :raises BadRequestException: If destination location doesn't exist
        """
        # Get existing item
        item = self.get_item(item_id)

        # Validate destination location exists
        to_location = Location.get_by_id_and_check(dto.to_location_id)

        # Store from_location before updating
        from_location = item.location

        # Update item location
        item.location = to_location

        # Save (last_modified_by updated automatically by ModelWithUser)
        item.save()

        # Create 'move' activity entry
        activity = self._activity_service.log_activity(
            CreateActivityDTO(
                activity_type=ActivityType.MOVE,
                batch_id=item.id,
                from_location_id=from_location.id,
                to_location_id=to_location.id,
                note_id=dto.note_id,
            )
        )

        return ItemActivityResult(item=item, activity=activity)

    def update_item(self, item_id: str, dto: UpdateItemDTO) -> Item:
        """
        Update item metadata (label, notes, expiry_date).

        Note: To change item_number or label with activity logging, use relabel_item().

        :param item_id: The ID of the item to update
        :type item_id: str
        :param dto: DTO containing update data
        :type dto: UpdateItemDTO
        :return: The updated item
        :rtype: Item
        :raises NotFoundException: If item not found
        """
        # Get existing item
        item = self.get_item(item_id)

        # Update notes if provided (can be set to empty string to clear)
        item.notes = dto.notes.strip() if dto.notes else None

        if dto.supplier_id is not None:
            item.supplier = SupplierService().get_supplier(dto.supplier_id)
        else:
            item.supplier = None

        # Update expiry_date (can be None to clear)
        # Only update if the key is explicitly provided
        item.expiry_date = dto.expiry_date

        # Save (last_modified_by updated automatically by ModelWithUser)
        item.save()

        return item

    def use_item(self, item_id: str, dto: UseItemDTO) -> ItemActivityResult:
        """
        Record a USE activity on an item (reference only, no state change).

        USE is for non-consumable item sheets or when you just want to log
        that an item was used without changing its quantity.

        :param item_id: The ID of the item
        :type item_id: str
        :param dto: DTO containing use data
        :type dto: UseItemDTO
        :return: The item and the created activity
        :rtype: ItemActivityResult
        """
        # Validate item exists
        item = self.get_item(item_id)

        activity = self._activity_service.log_activity(
            CreateActivityDTO(
                activity_type=ActivityType.USE,
                batch_id=item_id,
                notes=dto.notes,
                note_id=dto.note_id,
            )
        )

        return ItemActivityResult(item=item, activity=activity)

    @ElnDbManager.transaction()
    def discard_item(self, item_id: str, dto: DiscardItemDTO) -> ItemActivityResult:
        """
        Discard an item (soft delete with activity logging).

        :param item_id: The ID of the item to discard
        :type item_id: str
        :param dto: DTO containing discard data
        :type dto: DiscardItemDTO
        :return: The updated item and the created activity
        :rtype: ItemActivityResult
        :raises NotFoundException: If item not found
        :raises BadRequestException: If item is already discarded
        """
        item = self.get_item(item_id)

        if item.is_discarded():
            raise BadRequestException(f"Item '{item.batch_number}' is already discarded")

        # Create 'discard' activity entry
        activity = self._activity_service.log_activity(
            CreateActivityDTO(
                activity_type=ActivityType.DISCARD,
                batch_id=item.id,
                quantity=item.quantity,
                unit_type=item.unit_type,
                notes=dto.notes or "Item discarded",
                note_id=dto.note_id,
            )
        )

        item.status = ItemStatus.DISCARDED
        item.save()

        return ItemActivityResult(item=item, activity=activity)

    @ElnDbManager.transaction()
    def relabel_item(self, item_id: str, dto: RelabelItemDTO) -> ItemActivityResult:
        """
        Relabel an item (change item_number and/or label) with activity logging.

        :param item_id: The ID of the item to relabel
        :type item_id: str
        :param dto: DTO containing relabel data
        :type dto: RelabelItemDTO
        :return: The updated item and the created activity (activity is None if no changes)
        :rtype: ItemActivityResult
        :raises NotFoundException: If item not found
        :raises BadRequestException: If validation fails or no changes provided
        """
        # Get existing item
        item = self.get_item(item_id)

        # Validate at least one field is provided
        if dto.item_number is None and dto.label is None:
            raise BadRequestException(
                "At least one of item_number or label must be provided for relabeling"
            )

        # Track what changed for activity notes
        changes = []

        # Update item_number if provided
        if dto.item_number is not None:
            self._validate_item_number(dto.item_number)
            old_item_number = item.batch_number
            new_item_number = dto.item_number.strip()
            if old_item_number != new_item_number:
                item.batch_number = new_item_number
                changes.append(f"item_number: '{old_item_number}' -> '{new_item_number}'")

        # Update label if provided
        if dto.label is not None:
            old_label = item.label
            new_label = dto.label.strip() if dto.label else None
            if old_label != new_label:
                item.label = new_label
                changes.append(f"label: '{old_label}' -> '{new_label}'")

        # If no actual changes, return item as-is with no activity
        if not changes:
            return ItemActivityResult(item=item, activity=None)

        # Save (last_modified_by updated automatically by ModelWithUser)
        item.save()

        # Create 'relabel' activity entry
        activity = self._activity_service.log_activity(
            CreateActivityDTO(
                activity_type=ActivityType.RELABEL,
                batch_id=item.id,
                notes="; ".join(changes),
                note_id=dto.note_id,
            )
        )

        return ItemActivityResult(item=item, activity=activity)

    def cancel_creation(self, item_id: str) -> None:
        """
        Cancel the creation of an item by deleting it if it is deletable.

        An item is deletable if:
        - It only has the initial 'create' activity (no other activities)
        - It has no active child items (aliquots)

        This is intended for canceling an item creation that was started but
        should be discarded (e.g., user changed their mind, made an error, etc.).

        :param item_id: The ID of the item to cancel
        :type item_id: str
        :raises NotFoundException: If item not found
        :raises BadRequestException: If item is not deletable
        """
        result = self.delete_item(item_id, allow_discard=False)
        if result != DeleteItemResultDTO.DELETED:
            raise BadRequestException(
                "Cannot cancel item because it has activity history. "
                "Use delete_item or discard_item instead."
            )

    @ElnDbManager.transaction()
    def delete_item(
        self,
        item_id: str,
        notes: str | None = None,
        note_id: str | None = None,
        allow_discard: bool = True,
    ) -> DeleteItemResultDTO:
        """
        Delete or discard an item if it has no child items (aliquots).

        - If item only has the initial 'create' activity from creation: hard delete
        - If item has other activities (usage history): soft delete (set status to DISCARDED)

        :param item_id: The ID of the item to delete
        :type item_id: str
        :param notes: Optional notes for discarding the item
        :type notes: Optional[str]
        :param note_id: Optional note ID to link the discard activity
        :type note_id: Optional[str]
        :param allow_discard: If False, raise an error instead of soft-deleting
                              when item has activity history (default: True)
        :type allow_discard: bool
        :return: Result indicating whether item was deleted or discarded
        :rtype: DeleteItemResultDTO
        :raises NotFoundException: If item not found
        :raises BadRequestException: If item has child items, is already discarded,
                                     or has activity history when allow_discard=False
        """
        # Get existing item
        item = self.get_item(item_id)

        # Check if already discarded
        if item.is_discarded():
            raise BadRequestException(f"Item '{item.batch_number}' is already discarded")

        # Check for child items (aliquots)
        child_count = (
            Item.select()
            .where(Item.parent_item == item)
            .where(Item.status == ItemStatus.ACTIVE)
            .count()
        )
        if child_count > 0:
            raise BadRequestException(
                f"Cannot delete item '{item.batch_number}' because it has {child_count} "
                "active child item(s) (aliquots). Delete all child items first."
            )

        # Count activities for this item
        activity_count = Activity.count_by_batch_id(item.id)

        # If only 1 activity (the creation 'create'), hard delete
        if activity_count <= 1:
            # Delete associated activities first
            Activity.delete().where(Activity.batch == item).execute()
            # Hard delete the item
            item.delete_instance()
            return DeleteItemResultDTO.DELETED

        # Item has activity history
        if not allow_discard:
            raise BadRequestException(
                f"Cannot delete item '{item.batch_number}' because it has activity history."
            )

        # Soft delete (mark as discarded)
        # Create 'discard' activity entry
        self._activity_service.log_activity(
            CreateActivityDTO(
                activity_type=ActivityType.DISCARD,
                batch_id=item.id,
                quantity=item.quantity,
                unit_type=item.unit_type,
                notes=notes if notes else "Item discarded",
                note_id=note_id,
            )
        )

        # Update status to DISCARDED
        item.status = ItemStatus.DISCARDED
        item.save()

        return DeleteItemResultDTO.DISCARDED

    def _validate_item_number(self, item_number: str) -> None:
        """
        Validate item number is not empty.

        :param item_number: Item number to validate
        :type item_number: str
        :raises BadRequestException: If item number is empty or whitespace only
        """
        if not item_number or len(item_number.strip()) == 0:
            raise BadRequestException("Item number is required")

    def _validate_item_sheet_exists(self, item_sheet_id: str) -> ItemSheet:
        """
        Validate that an item sheet exists.

        :param item_sheet_id: Item sheet ID to validate
        :type item_sheet_id: str
        :return: The item sheet if found
        :rtype: ItemSheet
        :raises BadRequestException: If item sheet doesn't exist
        """
        item_sheet = ItemSheet.get_by_id(item_sheet_id)
        if not item_sheet:
            raise BadRequestException(f"Item sheet with ID '{item_sheet_id}' does not exist")
        return item_sheet

    def _validate_and_convert_quantity(self, item: Item, quantity, unit: str):
        """
        Validate that the unit is valid for the item's unit type and convert to base unit.

        :param item: The item to validate against
        :type item: Item
        :param quantity: The quantity to convert (already validated as positive)
        :param unit: The unit string (e.g., 'mL', 'g', 'kg')
        :type unit: str
        :return: Quantity converted to base unit
        :raises BadRequestException: If unit is not valid for the item's unit type
        """
        unit_type = item.unit_type

        if not UnitConverter.is_valid_unit(unit, unit_type):
            valid_units = ", ".join(UnitConverter.get_valid_units(unit_type))
            raise BadRequestException(
                f"Invalid unit '{unit}' for item '{item.batch_number}' "
                f"(unit type: {unit_type.value}). Valid units: {valid_units}"
            )

        return UnitConverter.to_base_unit(quantity, unit, unit_type)

    ########################## REVERSE ACTIVITY ##############################

    @ElnDbManager.transaction()
    def reverse_activity(self, activity_id: str) -> None:
        """Reverse an activity: undo its effect on the item and delete the activity record.

        This is called when a materialActivity block is removed from a note.
        The item state is restored to what it was before the activity.

        :param activity_id: The ID of the activity to reverse
        :type activity_id: str
        :raises BadRequestException: If activity not found, or reversal is not possible
        """
        CurrentUserService.get_and_check_current_user()

        activity = Activity.get_by_id(activity_id)
        if not activity:
            raise BadRequestException(f"Activity with ID '{activity_id}' does not exist")

        item = cast(Item, activity.batch)
        activity_type = activity.activity_type

        if activity_type == ActivityType.CREATE:
            self._reverse_create(activity, item)
        elif activity_type == ActivityType.RECEIVE:
            self._reverse_receive(activity, item)
        elif activity_type == ActivityType.CONSUME:
            self._reverse_consume(activity, item)
        elif activity_type == ActivityType.MOVE:
            self._reverse_move(activity, item)
        elif activity_type == ActivityType.USE:
            self._reverse_use(activity, item)
        elif activity_type == ActivityType.DISCARD:
            self._reverse_discard(activity, item)
        elif activity_type == ActivityType.ALIQUOT:
            self._reverse_aliquot(activity, item)
        elif activity_type == ActivityType.ALIQUOT_CREATED:
            raise BadRequestException(
                "Cannot reverse ALIQUOT_CREATED directly. "
                "Reverse the parent ALIQUOT activity instead."
            )
        elif activity_type == ActivityType.RELABEL:
            self._reverse_relabel(activity, item)
        else:
            raise BadRequestException(f"Unknown activity type: {activity_type}")

        # Delete the activity record (except for CREATE which deletes the item)
        if activity_type != ActivityType.CREATE:
            activity.delete_instance()

    def _reverse_create(self, activity: Activity, item: Item) -> None:
        """Reverse CREATE: delete the item if it is deletable.

        Original effect: item created with initial quantity
        Reversal: hard delete the item and its CREATE activity

        An item can only be reversed if it has no other activities and no child items.
        """
        # Use cancel_creation logic via delete_item with allow_discard=False
        # But we need to handle the activity deletion ourselves since we're in reverse_activity
        # Check for active child items
        child_count = (
            Item.select()
            .where(Item.parent_item == item)
            .where(Item.status == ItemStatus.ACTIVE)
            .count()
        )
        if child_count > 0:
            raise BadRequestException(
                f"Cannot reverse CREATE: item '{item.batch_number}' has {child_count} "
                "active child item(s) (aliquots). Delete them first."
            )

        # Check activity count (should be exactly 1 - the CREATE activity)
        activity_count = Activity.count_by_batch_id(item.id)
        if activity_count > 1:
            raise BadRequestException(
                f"Cannot reverse CREATE: item '{item.batch_number}' has additional activities. "
                "Reverse those activities first."
            )

        # Delete the CREATE activity
        activity.delete_instance()

        # Hard delete the item
        item.delete_instance()

    def _reverse_receive(self, activity: Activity, item: Item) -> None:
        """Reverse RECEIVE: decrement quantity that was added.

        Original effect: item.quantity += activity.quantity
        Reversal: item.quantity -= activity.quantity
        """
        if activity.quantity is None:
            raise BadRequestException("Cannot reverse RECEIVE activity without quantity")

        if item.quantity < activity.quantity:
            raise BadRequestException(
                f"Cannot reverse RECEIVE: item '{item.batch_number}' current quantity "
                f"({item.quantity}) is less than the received quantity ({activity.quantity}). "
                f"The item may have been consumed since this receive."
            )

        item.quantity = item.quantity - activity.quantity
        item.save()

    def _reverse_consume(self, activity: Activity, item: Item) -> None:
        """Reverse CONSUME: re-add quantity that was consumed.

        Original effect: item.quantity -= activity.quantity
        Reversal: item.quantity += activity.quantity
        """
        if activity.quantity is None:
            raise BadRequestException("Cannot reverse CONSUME activity without quantity")

        item.quantity = item.quantity + activity.quantity
        item.save()

    def _reverse_move(self, activity: Activity, item: Item) -> None:
        """Reverse MOVE: restore original location.

        Original effect: item.location = activity.to_location
        Reversal: item.location = activity.from_location
        """
        if activity.from_location is None:
            raise BadRequestException(
                "Cannot reverse MOVE activity: original location (from_location) is not recorded"
            )

        item.location = activity.from_location
        item.save()

    def _reverse_use(self, activity: Activity, item: Item) -> None:
        """Reverse USE: no item state change needed.

        USE is reference-only (no quantity/location change).
        Just delete the activity record (done in reverse_activity).
        """
        pass

    def _reverse_discard(self, activity: Activity, item: Item) -> None:
        """Reverse DISCARD: reactivate the item.

        Original effect: item.status = DISCARDED
        Reversal: item.status = ACTIVE
        """
        if not item.is_discarded():
            raise BadRequestException(
                f"Cannot reverse DISCARD: item '{item.batch_number}' is not discarded"
            )

        item.status = ItemStatus.ACTIVE
        item.save()

    def _reverse_aliquot(self, activity: Activity, item: Item) -> None:
        """Reverse ALIQUOT: restore parent quantity, delete child item and its ALIQUOT_CREATED activity.

        Original effect:
        - parent.quantity -= source_quantity (recorded in activity.quantity)
        - child item created (referenced by activity.related_batch)
        - ALIQUOT_CREATED activity created on child item

        Reversal:
        - Verify child item has no active children (sub-aliquots)
        - Delete ALIQUOT_CREATED activity on child item
        - Delete child item
        - parent.quantity += activity.quantity
        """
        child_item = activity.related_batch
        if child_item is None:
            raise BadRequestException(
                "Cannot reverse ALIQUOT activity: related child item not found"
            )

        # Check child item has no active children
        active_children_count = (
            Item.select()
            .where(Item.parent_item == child_item)
            .where(Item.status == ItemStatus.ACTIVE)
            .count()
        )
        if active_children_count > 0:
            raise BadRequestException(
                f"Cannot reverse ALIQUOT: child item '{child_item.batch_number}' has "
                f"{active_children_count} active sub-aliquot(s). Delete them first."
            )

        # Delete ALIQUOT_CREATED activity on the child item
        Activity.delete().where(
            (Activity.batch == child_item)
            & (Activity.activity_type == ActivityType.ALIQUOT_CREATED)
        ).execute()

        # Delete all activities on the child item (there should only be the ALIQUOT_CREATED)
        Activity.delete().where(Activity.batch == child_item).execute()

        # Delete child item
        child_item.delete_instance()

        # Restore parent quantity
        if activity.quantity is not None:
            item.quantity = item.quantity + activity.quantity
            item.save()

    def _reverse_relabel(self, activity: Activity, item: Item) -> None:
        """Reverse RELABEL: restore original item_number and/or label.

        The original values are stored in activity.notes with format:
        "item_number: 'old_value' -> 'new_value'; label: 'old_value' -> 'new_value'"

        Parse this string to extract and restore original values.
        """
        if not activity.notes:
            raise BadRequestException(
                "Cannot reverse RELABEL activity: no change details recorded in notes"
            )

        # Parse item_number change
        item_number_match = re.search(r"item_number: '(.+?)' -> '(.+?)'", activity.notes)
        if item_number_match:
            old_item_number = item_number_match.group(1)
            item.batch_number = old_item_number

        # Parse label change
        label_match = re.search(r"label: '(.+?)' -> '(.+?)'", activity.notes)
        if label_match:
            old_label = label_match.group(1)
            item.label = None if old_label == "None" else old_label

        item.save()

    ########################## ALIQUOTS ##############################

    @ElnDbManager.transaction()
    def create_aliquot(self, dto: CreateAliquotDTO) -> ItemActivityResult:
        """
        Create an aliquot from a parent item.

        Aliquots are derived samples that:
        - Can inherit item_sheet_id from the parent OR use a different target item sheet
        - Have a reference to the parent item (parent_item_id)
        - Can have their own quantity, label, and location

        The parent item is decremented by source_quantity, while the aliquot
        is created with aliquot_quantity. These can differ (e.g., dilution,
        processing loss, material transformation, etc.).

        Example 1: Take 2L from parent to create a 500mL aliquot after dilution.
        Example 2: Take 100mL from a solution to extract 5g of a different compound.

        :param dto: DTO containing aliquot data
        :type dto: CreateAliquotDTO
        :return: The created aliquot item and the ALIQUOT activity (on the parent)
        :rtype: BatchActivityResult
        :raises BadRequestException: If validation fails, parent doesn't exist,
                                     or insufficient quantity in parent
        """
        # Validate both quantities are positive
        validated_source_quantity = QuantityValidator.validate_quantity(dto.source_quantity)
        validated_aliquot_quantity = QuantityValidator.validate_quantity(dto.aliquot_quantity)

        # Validate parent item exists
        parent_item = self.get_item(dto.parent_item_id)

        # Validate parent is active (not discarded)
        if parent_item.is_discarded():
            raise BadRequestException(
                f"Cannot create aliquot from discarded item '{parent_item.batch_number}'"
            )

        # Validate parent item sheet is consumable (aliquots only make sense for consumables)
        if not parent_item.is_consumable():
            raise BadRequestException(
                f"Cannot create aliquot from non-consumable item sheet '{parent_item.item_sheet.name}'. "
                "Aliquots can only be created from consumable item sheets (chemicals, reagents, samples)."
            )

        # Determine target item sheet: use provided or inherit from parent
        if dto.target_item_sheet_id:
            target_item_sheet = self._validate_item_sheet_exists(dto.target_item_sheet_id)
            # Validate target item sheet is consumable
            if not target_item_sheet.is_consumable:
                raise BadRequestException(
                    f"Cannot create aliquot with non-consumable item sheet '{target_item_sheet.name}'. "
                    "Aliquots can only be created with consumable item sheets."
                )
            aliquot_unit_type = target_item_sheet.default_unit_type
        else:
            target_item_sheet = parent_item.item_sheet
            aliquot_unit_type = parent_item.unit_type

        # Get unit_type from parent item for source quantity validation
        parent_unit_type = parent_item.unit_type

        # Validate source unit and convert to base unit (against parent's unit_type)
        base_source_quantity = self._validate_and_convert_quantity(
            parent_item, validated_source_quantity, dto.source_unit
        )

        # Validate aliquot unit and convert to base unit (against target item sheet's unit_type)
        if not UnitConverter.is_valid_unit(dto.aliquot_unit, aliquot_unit_type):
            valid_units = ", ".join(UnitConverter.get_valid_units(aliquot_unit_type))
            raise BadRequestException(
                f"Invalid aliquot unit '{dto.aliquot_unit}' for item sheet '{target_item_sheet.name}' "
                f"(unit type: {aliquot_unit_type.value}). Valid units: {valid_units}"
            )
        base_aliquot_quantity = UnitConverter.to_base_unit(
            validated_aliquot_quantity, dto.aliquot_unit, aliquot_unit_type
        )

        # Validate sufficient quantity in parent (using base units)
        parent_item.validate_sufficient_quantity(base_source_quantity)

        # Decrement parent quantity by source_quantity (in base units)
        parent_item.quantity = parent_item.quantity - base_source_quantity
        parent_item.save()

        # Determine location (default to parent's location if not provided)
        location = (
            LocationService().get_or_default_location(dto.location_id)
            if dto.location_id
            else parent_item.location
        )

        # Determine item number: use provided or auto-generate
        if dto.aliquot_item_number:
            self._validate_item_number(dto.aliquot_item_number)
            aliquot_item_number = dto.aliquot_item_number.strip()
        else:
            # Auto-generate item number based on parent
            aliquot_count = Item.select().where(Item.parent_item == parent_item).count()
            aliquot_item_number = f"{parent_item.batch_number}-A{aliquot_count + 1}"

        # Create aliquot item with aliquot_quantity (in base units)
        aliquot = Item()
        aliquot.item_sheet = target_item_sheet  # Use target item sheet (may differ from parent)
        aliquot.parent_item = parent_item  # Set parent reference
        aliquot.batch_number = aliquot_item_number
        aliquot.label = dto.label.strip() if dto.label else None
        aliquot.quantity = base_aliquot_quantity  # Aliquot's own quantity in base units
        aliquot.unit_type = aliquot_unit_type  # Use target item sheet's unit_type
        aliquot.location = location
        aliquot.notes = dto.notes.strip() if dto.notes else None
        aliquot.expiry_date = parent_item.expiry_date  # Inherit expiry from parent
        aliquot.supplier = (
            SupplierService().get_supplier(dto.supplier_id) if dto.supplier_id else None
        )

        # Save (created_by/last_modified_by set automatically by ModelWithUser)
        aliquot.save()

        # Create activity on PARENT item (ALIQUOT type)
        # Documents that quantity was taken from parent to create the aliquot
        aliquot_activity = self._activity_service.log_activity(
            CreateActivityDTO(
                activity_type=ActivityType.ALIQUOT,
                batch_id=parent_item.id,
                quantity=base_source_quantity,  # Amount taken from parent (base units)
                unit_type=parent_unit_type,  # Use parent's unit_type
                from_location_id=parent_item.location.id,
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
                unit_type=aliquot_unit_type,  # Use aliquot's unit_type (from target item sheet)
                to_location_id=location.id,
                related_batch_id=parent_item.id,  # Reference to the parent item
                notes=dto.notes.strip() if dto.notes else None,
                note_id=dto.note_id,
            )
        )

        return ItemActivityResult(item=aliquot, activity=aliquot_activity)
