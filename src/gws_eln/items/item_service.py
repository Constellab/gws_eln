"""
Item Service for managing Item entities.

Handles CRUD operations, validation, and business logic for items.
Implements Story 5.1 from Epic 5: Service Layer - Items.
"""

from decimal import Decimal

from gws_core import BadRequestException, CurrentUserService
from gws_eln.activities.activity import Activity
from gws_eln.activities.activity_dto import (
    CreateActivityDTO,
    CreateActivityInputDTO,
    CreateActivityOutputDTO,
)
from gws_eln.activities.activity_input_role import ActivityInputRole
from gws_eln.activities.activity_service import ActivityService
from gws_eln.activities.activity_type import ActivityType
from gws_eln.core.concentration_unit import CONCENTRATION_UNITS, is_valid_concentration_unit
from gws_eln.core.eln_db_manager import ElnDbManager
from gws_eln.items.item import Item
from gws_eln.items.item_activity_dto import ItemActivityResult
from gws_eln.items.item_dto import (
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
        up to the root (original item), ordered from closest to furthest ancestor.

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
        :rtype: ItemActivityResult
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

        # Validate concentration (value + unit) if provided
        self._validate_concentration(dto.concentration, dto.concentration_unit)

        # Validate/get location (default to "labo" if not provided)
        location = LocationService().get_or_default_location(dto.location_id)

        # Get supplier
        supplier = SupplierService().get_supplier(dto.supplier_id) if dto.supplier_id else None

        # Convert quantity from the given unit to base unit for storage
        base_quantity = UnitConverter.to_base_unit(validated_quantity, dto.unit, unit_type)

        # Create item
        item = Item()
        item.item_sheet = item_sheet
        item.item_number = dto.item_number.strip()
        item.quantity = base_quantity
        item.unit_type = unit_type
        item.concentration = dto.concentration
        item.concentration_unit = dto.concentration_unit or None
        item.location = location
        item.expiry_date = dto.expiry_date
        item.label = dto.label.strip() if dto.label else None
        item.notes = dto.notes.strip() if dto.notes else None
        item.parent_item = None  # Original item, not an aliquot
        item.supplier = supplier

        # Save (created_by/last_modified_by set automatically by ModelWithUser)
        item.save()

        # Create 'receive' activity entry using ActivityService
        # Entering an item into inventory (new or existing) is always a RECEIVE.
        activity = self._activity_service.log_activity(
            CreateActivityDTO(
                activity_type=ActivityType.RECEIVE,
                item_id=item.id,
                quantity=base_quantity,
                unit_type=unit_type,
                notes=dto.notes,
                note_id=dto.note_id,
                outputs=[
                    CreateActivityOutputDTO(
                        item_id=item.id,
                        quantity=base_quantity,
                        unit_type=unit_type,
                    )
                ],
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
                item_id=item.id,
                quantity=base_quantity,
                unit_type=item.unit_type,
                notes=dto.notes,
                note_id=dto.note_id,
                outputs=[
                    CreateActivityOutputDTO(
                        item_id=item.id,
                        quantity=base_quantity,
                        unit_type=item.unit_type,
                    )
                ],
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
                item_id=item.id,
                quantity=base_quantity,
                unit_type=item.unit_type,
                notes=dto.notes,
                note_id=dto.note_id,
                inputs=[
                    CreateActivityInputDTO(
                        item_id=item.id,
                        role=ActivityInputRole.INGREDIENT,
                        quantity_contributed=base_quantity,
                        unit_type=item.unit_type,
                    )
                ],
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
                item_id=item.id,
                from_location_id=from_location.id,
                to_location_id=to_location.id,
                note_id=dto.note_id,
                inputs=[
                    CreateActivityInputDTO(
                        item_id=item.id,
                        role=ActivityInputRole.INGREDIENT,
                    )
                ],
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

        # Update concentration (value + unit, None clears them)
        self._validate_concentration(dto.concentration, dto.concentration_unit)
        item.concentration = dto.concentration
        item.concentration_unit = dto.concentration_unit or None

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
                item_id=item_id,
                notes=dto.notes,
                note_id=dto.note_id,
                inputs=[
                    CreateActivityInputDTO(
                        item_id=item_id,
                        role=ActivityInputRole.INSTRUMENT,
                    )
                ],
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
            raise BadRequestException(f"Item '{item.item_number}' is already discarded")

        # Create 'discard' activity entry
        activity = self._activity_service.log_activity(
            CreateActivityDTO(
                activity_type=ActivityType.DISCARD,
                item_id=item.id,
                quantity=item.quantity,
                unit_type=item.unit_type,
                notes=dto.notes or "Item discarded",
                note_id=dto.note_id,
                inputs=[
                    CreateActivityInputDTO(
                        item_id=item.id,
                        role=ActivityInputRole.INGREDIENT,
                        quantity_contributed=item.quantity,
                        unit_type=item.unit_type,
                    )
                ],
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
            old_item_number = item.item_number
            new_item_number = dto.item_number.strip()
            if old_item_number != new_item_number:
                item.item_number = new_item_number
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
                item_id=item.id,
                notes="; ".join(changes),
                note_id=dto.note_id,
                inputs=[
                    CreateActivityInputDTO(
                        item_id=item.id,
                        role=ActivityInputRole.INGREDIENT,
                    )
                ],
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
            raise BadRequestException(f"Item '{item.item_number}' is already discarded")

        # Check for child items (aliquots)
        child_count = (
            Item.select()
            .where(Item.parent_item == item)
            .where(Item.status == ItemStatus.ACTIVE)
            .count()
        )
        if child_count > 0:
            raise BadRequestException(
                f"Cannot delete item '{item.item_number}' because it has {child_count} "
                "active child item(s) (aliquots). Delete all child items first."
            )

        # Count activities for this item
        activity_count = Activity.count_by_item_id(item.id)

        # If only 1 activity (the creation 'create'), hard delete
        if activity_count <= 1:
            # Delete associated activities first
            Activity.delete().where(Activity.item == item).execute()
            # Hard delete the item
            item.delete_instance()
            return DeleteItemResultDTO.DELETED

        # Item has activity history
        if not allow_discard:
            raise BadRequestException(
                f"Cannot delete item '{item.item_number}' because it has activity history."
            )

        # Soft delete (mark as discarded)
        # Create 'discard' activity entry
        self._activity_service.log_activity(
            CreateActivityDTO(
                activity_type=ActivityType.DISCARD,
                item_id=item.id,
                quantity=item.quantity,
                unit_type=item.unit_type,
                notes=notes if notes else "Item discarded",
                note_id=note_id,
                inputs=[
                    CreateActivityInputDTO(
                        item_id=item.id,
                        role=ActivityInputRole.INGREDIENT,
                        quantity_contributed=item.quantity,
                        unit_type=item.unit_type,
                    )
                ],
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

    def _validate_concentration(
        self, concentration: Decimal | None, concentration_unit: str | None
    ) -> None:
        """
        Validate the concentration value and its unit.

        Concentration is optional: both the value and the unit may be omitted
        (None). No conversion is performed for the concentration.

        Rules:
        - The value, if provided, must be strictly positive.
        - The unit, if provided, must be one of the recordable concentration units.
        - The value and the unit go together: either both are provided, or neither.

        :param concentration: Concentration value to validate (or None)
        :type concentration: Decimal | None
        :param concentration_unit: Concentration unit to validate (or None/empty)
        :type concentration_unit: str | None
        :raises BadRequestException: If the value is not positive, the unit is not
                                     in the recordable list, or only one of the two
                                     is provided
        """
        # Normalize empty unit string to None ("no concentration unit")
        unit = concentration_unit or None

        # Both omitted: nothing to validate
        if concentration is None and unit is None:
            return

        # Value and unit must be provided together
        if concentration is None:
            raise BadRequestException(
                "A concentration value is required when a concentration unit is provided."
            )
        if unit is None:
            raise BadRequestException(
                "A concentration unit is required when a concentration value is provided."
            )

        # Value must be strictly positive
        if concentration <= 0:
            raise BadRequestException(f"Concentration must be positive, got: {concentration}")

        # Unit must be in the recordable list
        if not is_valid_concentration_unit(unit):
            valid_units = ", ".join(CONCENTRATION_UNITS)
            raise BadRequestException(
                f"Invalid concentration unit '{unit}'. Valid units: {valid_units}"
            )

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
                f"Invalid unit '{unit}' for item '{item.item_number}' "
                f"(unit type: {unit_type.value}). Valid units: {valid_units}"
            )

        return UnitConverter.to_base_unit(quantity, unit, unit_type)
