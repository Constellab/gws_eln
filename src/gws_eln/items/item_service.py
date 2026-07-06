"""
Item Service for managing Item entities.

Handles CRUD operations, validation, and business logic for items.
"""

from decimal import Decimal

from gws_core import BadRequestException, CurrentUserService
from gws_eln.activities.activity import Activity
from gws_eln.activities.activity_dto import (
    CreateActivityDTO,
    CreateActivityInputDTO,
    CreateActivityOutputDTO,
)
from gws_eln.activities.activity_input import ActivityInput
from gws_eln.activities.activity_input_role import ActivityInputRole
from gws_eln.activities.activity_service import ActivityService
from gws_eln.activities.activity_type import ActivityType
from gws_eln.core.concentration_unit import CONCENTRATION_UNITS, is_valid_concentration_unit
from gws_eln.core.eln_db_manager import ElnDbManager
from gws_eln.core.unit_type import UnitType
from gws_eln.items.item import Item
from gws_eln.items.item_activity_dto import ItemActivityResult, TransformResult
from gws_eln.items.item_dto import (
    CombineItemDTO,
    ConcentrateItemDTO,
    CreateItemDTO,
    CreateItemsBulkDTO,
    DecrementQuantityDTO,
    DeleteItemResultDTO,
    DiluteItemDTO,
    DiscardItemDTO,
    MoveItemDTO,
    ReceiveItemDTO,
    RelabelItemDTO,
    SplitItemDTO,
    TransformItemsDTO,
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
from peewee import IntegrityError

# A combine merges several items, so it needs at least this many ingredient inputs.
MIN_COMBINE_INGREDIENTS = 2


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

        # By default, hide only discarded (soft-deleted) items.
        # Exhausted items still exist physically and remain visible.
        if not include_discarded:
            query = query.where(Item.status != ItemStatus.DISCARDED)

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
        # Validate quantity is positive
        validated_quantity = QuantityValidator.validate_quantity(dto.quantity)

        # Validate item sheet exists
        item_sheet = self._validate_item_sheet_exists(dto.item_sheet_id)

        # Get unit_type from the item sheet's unit_type
        unit_type = item_sheet.unit_type

        # Validate unit is valid for the item sheet's unit type
        if not UnitConverter.is_valid_unit(dto.unit, unit_type):
            valid_units = ", ".join(UnitConverter.get_valid_units(unit_type))
            raise BadRequestException(
                f"Invalid unit '{dto.unit}' for item sheet '{item_sheet.name}' "
                f"(unit type: {unit_type.value}). Valid units: {valid_units}"
            )

        # Validate concentration (value + unit) if provided
        self._validate_concentration(dto.concentration, dto.concentration_unit)

        # Normalize and validate the serial number (unique lab-wide when set)
        serial_number = dto.serial_number.strip() if dto.serial_number else None
        self._validate_serial_number_unique(serial_number)

        # Validate/get location (default to "labo" if not provided)
        location = LocationService().get_or_default_location(dto.location_id)

        # Get supplier
        supplier = SupplierService().get_supplier(dto.supplier_id) if dto.supplier_id else None

        # Convert quantity from the given unit to base unit for storage
        base_quantity = UnitConverter.to_base_unit(validated_quantity, dto.unit, unit_type)

        # Create item
        item = Item()
        item.item_sheet = item_sheet
        item.quantity = base_quantity
        item.unit_type = unit_type
        item.concentration = dto.concentration
        item.concentration_unit = dto.concentration_unit or None
        item.location = location
        item.expiry_date = dto.expiry_date
        item.label = self._normalize_required_label(dto.label)
        item.serial_number = serial_number
        item.storage_conditions = self._resolve_storage_conditions(
            dto.storage_conditions, item_sheet
        )
        item.notes = dto.notes.strip() if dto.notes else None
        item.supplier = supplier

        # Save with a unique code (created_by/last_modified_by set by ModelWithUser)
        self._save_with_unique_code(item, item_sheet)

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
    def create_items_bulk(self, dto: CreateItemsBulkDTO) -> list[Item]:
        """Create several serialized non-consumable items in one atomic action.

        One Item is created per entry in ``dto.serial_numbers`` (quantity 1 each,
        unit type from the sheet), with sequential codes (MAX+1, MAX+2, ...). Each
        unit gets its own RECEIVE activity so it has an independent history.

        :param dto: Shared fields + one serial number per unit (None/empty allowed)
        :type dto: CreateItemsBulkDTO
        :return: The created items
        :rtype: list[Item]
        :raises BadRequestException: If the sheet is consumable, no unit is requested,
                                     or a serial is duplicated (in the batch or lab-wide)
        """
        CurrentUserService.get_and_check_current_user()

        item_sheet = self._validate_item_sheet_exists(dto.item_sheet_id)
        if item_sheet.is_consumable:
            raise BadRequestException(
                f"Bulk creation is only for non-consumable (serialized) items; "
                f"'{item_sheet.name}' is consumable. Create a single item with a quantity instead."
            )

        if not dto.serial_numbers:
            raise BadRequestException("At least one unit is required")

        # Normalize serials (strip, empty -> None) and reject duplicates within the
        # batch and against existing items (lab-wide uniqueness).
        serials: list[str | None] = []
        seen: set[str] = set()
        for raw in dto.serial_numbers:
            serial = raw.strip() if raw else None
            if serial:
                if serial in seen:
                    raise BadRequestException(f"Duplicate serial number '{serial}' in the batch")
                seen.add(serial)
                self._validate_serial_number_unique(serial)
            serials.append(serial)

        self._validate_concentration(dto.concentration, dto.concentration_unit)

        # Shared fields resolved once for every created unit
        location = LocationService().get_or_default_location(dto.location_id)
        supplier = SupplierService().get_supplier(dto.supplier_id) if dto.supplier_id else None
        label = self._normalize_required_label(dto.label)
        storage_conditions = self._resolve_storage_conditions(dto.storage_conditions, item_sheet)
        notes = dto.notes.strip() if dto.notes else None
        unit_type = item_sheet.unit_type

        created: list[Item] = []
        for serial in serials:
            item = Item()
            item.item_sheet = item_sheet
            item.quantity = Decimal(1)
            item.unit_type = unit_type
            item.concentration = dto.concentration
            item.concentration_unit = dto.concentration_unit or None
            item.location = location
            item.expiry_date = dto.expiry_date
            item.label = label
            item.serial_number = serial
            item.storage_conditions = storage_conditions
            item.notes = notes
            item.supplier = supplier
            self._save_with_unique_code(item, item_sheet)

            # One RECEIVE activity per unit (0 inputs, 1 output) so each unit has
            # its own history.
            self._activity_service.log_activity(
                CreateActivityDTO(
                    activity_type=ActivityType.RECEIVE,
                    item_id=item.id,
                    quantity=Decimal(1),
                    unit_type=unit_type,
                    notes=dto.notes,
                    note_id=dto.note_id,
                    outputs=[
                        CreateActivityOutputDTO(
                            item_id=item.id,
                            quantity=Decimal(1),
                            unit_type=unit_type,
                        )
                    ],
                )
            )
            created.append(item)

        return created

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
        item.assert_can_consume()

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
                    ),
                    *self._build_instrument_inputs(dto.instrument_item_ids),
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
        Correct/complete item metadata (notes, expiry_date, supplier, storage).

        Note: to change the label with activity logging, use relabel_item().

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

        # Update storage condition (free text, None/empty clears it)
        item.storage_conditions = dto.storage_conditions.strip() if dto.storage_conditions else None

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

        USE references a non-consumable instrument without changing its quantity.

        :param item_id: The ID of the item
        :type item_id: str
        :param dto: DTO containing use data
        :type dto: UseItemDTO
        :return: The item and the created activity
        :rtype: ItemActivityResult
        :raises BadRequestException: If the item is consumable or discarded
        """
        # Validate item exists and is usable (non-consumable)
        item = self.get_item(item_id)
        item.assert_can_use()

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
            raise BadRequestException(f"Item '{item.code}' is already discarded")

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
        Relabel an item (change its label) with activity logging.

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

        # Label is mandatory: reject a missing or blank value
        new_label = self._normalize_required_label(dto.label)

        # Track what changed for activity notes
        changes = []

        # Update label
        old_label = item.label
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

    def _build_instrument_inputs(
        self, instrument_item_ids: list[str]
    ) -> list[CreateActivityInputDTO]:
        """Build INSTRUMENT activity inputs from a list of item ids.

        Each id is recorded as an INSTRUMENT input (no quantity). The activity
        layer validates that every referenced item is a non-consumable,
        non-discarded item.
        """
        return [
            CreateActivityInputDTO(item_id=instrument_id, role=ActivityInputRole.INSTRUMENT)
            for instrument_id in instrument_item_ids
        ]

    @ElnDbManager.transaction()
    def split_item(self, item_id: str, dto: SplitItemDTO) -> TransformResult:
        """
        Split one source item into 1..N new output items.

        The source is reduced in place by ``quantity_contributed`` (the amount
        drawn from it). The output quantities must sum to at most that amount;
        any remainder is consumed as loss (the leftover does not stay in the
        source). Each output is a brand new item that inherits the source's item
        sheet, unit_type and concentration; only quantity/location/label/expiry
        are per-output. A single SPLIT activity records the source as one
        INGREDIENT input and every created item as an output, capturing the lineage.

        :param item_id: The ID of the source item to split
        :type item_id: str
        :param dto: DTO containing the consumed quantity and the output items
        :type dto: SplitItemDTO
        :return: The mutated source item and the created output items + activity
        :rtype: TransformResult
        :raises NotFoundException: If the source item not found
        :raises BadRequestException: If validation fails (no outputs, discarded
                                     or non-consumable source, bad unit,
                                     insufficient quantity, or outputs exceeding
                                     the consumed quantity)
        """
        # Get and guard the source item
        source = self.get_item(item_id)

        if source.is_discarded():
            raise BadRequestException(f"Cannot split discarded item '{source.code}'")

        source.assert_can_consume()

        if not dto.outputs:
            raise BadRequestException("Split requires at least one output item")

        unit_type = source.unit_type

        # The amount drawn from the source (reduces it, bounds the outputs).
        validated_contributed = QuantityValidator.validate_quantity(dto.quantity_contributed)
        contributed_base_quantity = self._validate_and_convert_quantity(
            source, validated_contributed, dto.unit
        )

        # Validate every output and convert its quantity to base units, while
        # accumulating the total that ends up in the outputs.
        total_output_base_quantity = Decimal(0)
        prepared_outputs = []
        for output_dto in dto.outputs:
            validated_quantity = QuantityValidator.validate_quantity(output_dto.quantity)
            base_quantity = self._validate_and_convert_quantity(
                source, validated_quantity, output_dto.unit
            )
            total_output_base_quantity += base_quantity
            prepared_outputs.append((output_dto, base_quantity))

        # Outputs cannot amount to more than what was drawn from the source.
        if total_output_base_quantity > contributed_base_quantity:
            raise BadRequestException(
                "The total output quantity cannot exceed the consumed quantity "
                f"({UnitConverter.format_value(contributed_base_quantity, unit_type)})"
            )

        # Cannot draw more than the source holds (no negative stock)
        source.validate_sufficient_quantity(contributed_base_quantity)

        # Reduce the source in place by the full consumed amount (loss included)
        source.quantity = source.quantity - contributed_base_quantity
        source.save()

        # Create the new output items. Each code is generated just before the
        # item is saved, so the next iteration sees this increment (sequential
        # MAX+1, MAX+2, ... within this one action).
        output_items = []
        activity_outputs = []
        for output_dto, base_quantity in prepared_outputs:
            if output_dto.location_id:
                location = Location.get_by_id_and_check(output_dto.location_id)
            else:
                location = source.location

            item = Item()
            item.item_sheet = source.item_sheet
            item.quantity = base_quantity
            item.unit_type = unit_type
            # Concentration is intensive: children inherit it unchanged
            item.concentration = source.concentration
            item.concentration_unit = source.concentration_unit
            item.location = location
            item.expiry_date = (
                output_dto.expiry_date if output_dto.expiry_date is not None else source.expiry_date
            )
            item.label = self._normalize_required_label(output_dto.label)
            # Storage condition inherits the output's own sheet default
            item.storage_conditions = source.item_sheet.storage_conditions
            item.notes = output_dto.notes.strip() if output_dto.notes else None
            item.supplier = source.supplier
            # Lineage (source -> output) is recorded in the activity inputs/outputs
            self._save_with_unique_code(item, source.item_sheet)

            output_items.append(item)
            activity_outputs.append(
                CreateActivityOutputDTO(
                    item_id=item.id,
                    quantity=base_quantity,
                    unit_type=unit_type,
                )
            )

        # One split activity: 1 ingredient input (source) + optional INSTRUMENTs -> N outputs
        split_inputs = [
            CreateActivityInputDTO(
                item_id=source.id,
                role=ActivityInputRole.INGREDIENT,
                quantity_contributed=contributed_base_quantity,
                unit_type=unit_type,
            )
        ]
        split_inputs.extend(self._build_instrument_inputs(dto.instrument_item_ids))

        activity = self._activity_service.log_activity(
            CreateActivityDTO(
                activity_type=ActivityType.SPLIT,
                item_id=source.id,
                quantity=contributed_base_quantity,
                unit_type=unit_type,
                notes=dto.notes,
                note_id=dto.note_id,
                inputs=split_inputs,
                outputs=activity_outputs,
            )
        )

        return TransformResult(activity=activity, inputs=[source], outputs=output_items)

    @ElnDbManager.transaction()
    def combine_items(self, dto: CombineItemDTO) -> TransformResult:
        """
        Combine 2..N ingredient items into one new output item.

        Each ingredient is reduced in place by its contribution (bounded by the
        non-negative stock check); inputs may be of any dimension. A
        brand new output item is created on the caller-provided output item
        sheet - its dimension/quantity come from the sheet + user input,
        never from summing the inputs. The output concentration is
        user-entered or null. Optional instrument inputs (non-consumable)
        are recorded for traceability. A single combine activity records every
        ingredient as an ingredient input and the new item as the sole output.

        :param dto: DTO describing the ingredient inputs and the output item
        :type dto: CombineItemDTO
        :return: The mutated ingredient items and the created output + activity
        :rtype: TransformResult
        :raises NotFoundException: If an input item or the output sheet not found
        :raises BadRequestException: If validation fails (<2 ingredients, a
                                     discarded or non-consumable ingredient, bad
                                     unit, or insufficient quantity)
        """
        # Combine needs at least two ingredients to merge
        if len(dto.inputs) < MIN_COMBINE_INGREDIENTS:
            raise BadRequestException(
                f"Combine requires at least {MIN_COMBINE_INGREDIENTS} ingredient inputs"
            )

        # Validate the output item definition up front
        output_sheet = self._validate_item_sheet_exists(dto.output_item_sheet_id)
        output_unit_type = output_sheet.unit_type

        if not UnitConverter.is_valid_unit(dto.output_unit, output_unit_type):
            valid_units = ", ".join(UnitConverter.get_valid_units(output_unit_type))
            raise BadRequestException(
                f"Invalid unit '{dto.output_unit}' for output item sheet "
                f"'{output_sheet.name}' (unit type: {output_unit_type.value}). "
                f"Valid units: {valid_units}"
            )

        validated_output_quantity = QuantityValidator.validate_quantity(dto.output_quantity)
        output_base_quantity = UnitConverter.to_base_unit(
            validated_output_quantity, dto.output_unit, output_unit_type
        )

        self._validate_concentration(dto.output_concentration, dto.output_concentration_unit)

        # Resolve and reduce each ingredient in place
        mutated_inputs = []
        activity_inputs = []
        for input_dto in dto.inputs:
            item = self.get_item(input_dto.item_id)

            if item.is_discarded():
                raise BadRequestException(f"Cannot combine discarded item '{item.code}'")

            item.assert_can_consume()

            validated_quantity = QuantityValidator.validate_quantity(input_dto.quantity)
            base_quantity = self._validate_and_convert_quantity(
                item, validated_quantity, input_dto.unit
            )
            item.validate_sufficient_quantity(base_quantity)

            item.quantity = item.quantity - base_quantity
            item.save()

            mutated_inputs.append(item)
            activity_inputs.append(
                CreateActivityInputDTO(
                    item_id=item.id,
                    role=ActivityInputRole.INGREDIENT,
                    quantity_contributed=base_quantity,
                    unit_type=item.unit_type,
                )
            )

        # Optional instrument inputs (non-consumable; validated by ActivityService)
        activity_inputs.extend(self._build_instrument_inputs(dto.instrument_item_ids))

        # Create the new output item.
        # Lineage lives entirely in the activity inputs/outputs.
        location = LocationService().get_or_default_location(dto.output_location_id)
        output = Item()
        output.item_sheet = output_sheet
        output.quantity = output_base_quantity
        output.unit_type = output_unit_type
        output.concentration = dto.output_concentration
        output.concentration_unit = dto.output_concentration_unit or None
        output.location = location
        output.expiry_date = dto.output_expiry_date
        output.label = self._normalize_required_label(dto.output_label)
        # Storage condition inherits the output's own sheet default
        output.storage_conditions = output_sheet.storage_conditions
        output.notes = dto.notes.strip() if dto.notes else None
        output.supplier = None
        self._save_with_unique_code(output, output_sheet)

        # One combine activity: N ingredient inputs (+ optional INSTRUMENTs) -> 1 output
        activity = self._activity_service.log_activity(
            CreateActivityDTO(
                activity_type=ActivityType.COMBINE,
                item_id=output.id,
                quantity=output_base_quantity,
                unit_type=output_unit_type,
                notes=dto.notes,
                note_id=dto.note_id,
                inputs=activity_inputs,
                outputs=[
                    CreateActivityOutputDTO(
                        item_id=output.id,
                        quantity=output_base_quantity,
                        unit_type=output_unit_type,
                    )
                ],
            )
        )

        return TransformResult(activity=activity, inputs=mutated_inputs, outputs=[output])

    def _create_concentration_output(
        self,
        reference_item: Item,
        output_quantity: Decimal,
        output_unit: str,
        concentration: Decimal | None,
        concentration_unit: str | None,
        location_id: str | None,
        label: str | None,
        expiry_date,
    ) -> tuple[Item, Decimal]:
        """Create the new output item of a dilute/concentrate.

        The output lives on the reference item's own sheet (same substance, new
        concentration - concentration is identity-defining). Its quantity is
        user-entered (never computed). Returns the saved item and its base quantity.
        """
        self._validate_concentration(concentration, concentration_unit)

        validated_quantity = QuantityValidator.validate_quantity(output_quantity)
        output_base_quantity = self._validate_and_convert_quantity(
            reference_item, validated_quantity, output_unit
        )

        if location_id:
            location = Location.get_by_id_and_check(location_id)
        else:
            location = reference_item.location

        output = Item()
        output.item_sheet = reference_item.item_sheet
        output.quantity = output_base_quantity
        output.unit_type = reference_item.unit_type
        output.concentration = concentration
        output.concentration_unit = concentration_unit or None
        output.location = location
        output.expiry_date = expiry_date if expiry_date is not None else reference_item.expiry_date
        output.label = self._normalize_required_label(label)
        # Storage condition inherits the output's own sheet default
        output.storage_conditions = reference_item.item_sheet.storage_conditions
        output.notes = None
        output.supplier = reference_item.supplier
        self._save_with_unique_code(output, reference_item.item_sheet)

        return output, output_base_quantity

    @ElnDbManager.transaction()
    def concentrate_item(self, item_id: str, dto: ConcentrateItemDTO) -> TransformResult:
        """
        Concentrate a source item into a new, more concentrated item.

        The source is reduced in place by its contribution; a brand new output
        item is created on the source's own sheet at the user-entered (higher)
        concentration. The CONCENTRATE activity records the source as one
        INGREDIENT input, the new item as the output, and the initial/final
        concentration + dilution factor as store-only audit.

        :param item_id: The ID of the source item to concentrate
        :type item_id: str
        :param dto: DTO describing the draw from the source and the output item
        :type dto: ConcentrateItemDTO
        :return: The mutated source and the created output + activity
        :rtype: TransformResult
        :raises NotFoundException: If the source item not found
        :raises BadRequestException: If validation fails (discarded/non-consumable
                                     source, bad unit, or insufficient quantity)
        """
        source = self.get_item(item_id)

        if source.is_discarded():
            raise BadRequestException(f"Cannot concentrate discarded item '{source.code}'")

        source.assert_can_consume()
        self._assert_has_concentration(source, "concentrate")

        # Reduce the source by the drawn amount
        validated_quantity = QuantityValidator.validate_quantity(dto.quantity_contributed)
        base_drawn = self._validate_and_convert_quantity(source, validated_quantity, dto.unit)
        source.validate_sufficient_quantity(base_drawn)

        # Concentration before the operation (the source keeps its own concentration)
        initial_concentration = source.concentration

        source.quantity = source.quantity - base_drawn
        source.save()

        # Create the new, more concentrated output item
        output, output_base_quantity = self._create_concentration_output(
            reference_item=source,
            output_quantity=dto.output_quantity,
            output_unit=dto.output_unit,
            concentration=dto.output_concentration,
            concentration_unit=dto.output_concentration_unit,
            location_id=dto.output_location_id,
            label=dto.output_label,
            expiry_date=dto.output_expiry_date,
        )

        activity = self._activity_service.log_activity(
            CreateActivityDTO(
                activity_type=ActivityType.CONCENTRATE,
                item_id=output.id,
                quantity=output_base_quantity,
                unit_type=source.unit_type,
                notes=dto.notes,
                note_id=dto.note_id,
                initial_concentration=initial_concentration,
                final_concentration=dto.output_concentration,
                concentration_unit=dto.output_concentration_unit,
                dilution_factor=dto.dilution_factor,
                concentration_method=dto.concentration_method,
                inputs=[
                    CreateActivityInputDTO(
                        item_id=source.id,
                        role=ActivityInputRole.INGREDIENT,
                        quantity_contributed=base_drawn,
                        unit_type=source.unit_type,
                    ),
                    *self._build_instrument_inputs(dto.instrument_item_ids),
                ],
                outputs=[
                    CreateActivityOutputDTO(
                        item_id=output.id,
                        quantity=output_base_quantity,
                        unit_type=source.unit_type,
                    )
                ],
            )
        )

        return TransformResult(activity=activity, inputs=[source], outputs=[output])

    @ElnDbManager.transaction()
    def dilute_item(self, item_id: str, dto: DiluteItemDTO) -> TransformResult:
        """
        Dilute a target item with one or more diluents into a new, less
        concentrated item.

        The target and EVERY diluent are reduced in place. A brand new
        output item is created on the target's own sheet at the user-entered
        concentration; its quantity is user-entered, never computed by summing
        target+diluents. Diluents may be of any dimension. The
        DILUTE activity records the target and each diluent as INGREDIENT inputs,
        the new item as the output, and the initial/final concentration +
        dilution factor as store-only audit.

        :param item_id: The ID of the target item being diluted
        :type item_id: str
        :param dto: DTO describing the draws (target + diluent) and the output item
        :type dto: DiluteItemDTO
        :return: The mutated target and diluent, and the created output + activity
        :rtype: TransformResult
        :raises NotFoundException: If the target or diluent item not found
        :raises BadRequestException: If validation fails (discarded/non-consumable
                                     input, bad unit, or insufficient quantity)
        """
        if not dto.diluents:
            raise BadRequestException("Dilute requires at least one diluent")

        target = self.get_item(item_id)
        if target.is_discarded():
            raise BadRequestException(f"Cannot dilute discarded item '{target.code}'")
        target.assert_can_consume()
        self._assert_has_concentration(target, "dilute")

        # Concentration of the target before the operation
        initial_concentration = target.concentration

        # Reduce the target
        target_quantity = QuantityValidator.validate_quantity(dto.quantity_contributed)
        base_target = self._validate_and_convert_quantity(target, target_quantity, dto.unit)
        target.validate_sufficient_quantity(base_target)
        target.quantity = target.quantity - base_target
        target.save()

        # Reduce each diluent in place (each of its own dimension - not enforced)
        diluent_items: list[Item] = []
        diluent_activity_inputs: list[CreateActivityInputDTO] = []
        for diluent_dto in dto.diluents:
            diluent = self.get_item(diluent_dto.item_id)
            if diluent.is_discarded():
                raise BadRequestException(
                    f"Cannot use discarded item '{diluent.code}' as a diluent"
                )
            diluent.assert_can_consume()
            if diluent.unit_type != UnitType.VOLUME:
                raise BadRequestException(
                    f"Diluent '{diluent.code}' must be expressed in volume "
                    f"(its quantity is in {diluent.unit_type.value}). Only volume "
                    "items can be used as diluents."
                )

            diluent_quantity = QuantityValidator.validate_quantity(
                diluent_dto.quantity_contributed
            )
            base_diluent = self._validate_and_convert_quantity(
                diluent, diluent_quantity, diluent_dto.unit
            )
            diluent.validate_sufficient_quantity(base_diluent)
            diluent.quantity = diluent.quantity - base_diluent
            diluent.save()

            diluent_items.append(diluent)
            diluent_activity_inputs.append(
                CreateActivityInputDTO(
                    item_id=diluent.id,
                    role=ActivityInputRole.INGREDIENT,
                    quantity_contributed=base_diluent,
                    unit_type=diluent.unit_type,
                )
            )

        # Create the new, diluted output item (on the target's sheet)
        output, output_base_quantity = self._create_concentration_output(
            reference_item=target,
            output_quantity=dto.output_quantity,
            output_unit=dto.output_unit,
            concentration=dto.output_concentration,
            concentration_unit=dto.output_concentration_unit,
            location_id=dto.output_location_id,
            label=dto.output_label,
            expiry_date=dto.output_expiry_date,
        )

        activity = self._activity_service.log_activity(
            CreateActivityDTO(
                activity_type=ActivityType.DILUTE,
                item_id=output.id,
                quantity=output_base_quantity,
                unit_type=target.unit_type,
                notes=dto.notes,
                note_id=dto.note_id,
                initial_concentration=initial_concentration,
                final_concentration=dto.output_concentration,
                concentration_unit=dto.output_concentration_unit,
                dilution_factor=dto.dilution_factor,
                inputs=[
                    CreateActivityInputDTO(
                        item_id=target.id,
                        role=ActivityInputRole.INGREDIENT,
                        quantity_contributed=base_target,
                        unit_type=target.unit_type,
                    ),
                    *diluent_activity_inputs,
                    *self._build_instrument_inputs(dto.instrument_item_ids),
                ],
                outputs=[
                    CreateActivityOutputDTO(
                        item_id=output.id,
                        quantity=output_base_quantity,
                        unit_type=target.unit_type,
                    )
                ],
            )
        )

        return TransformResult(
            activity=activity, inputs=[target, *diluent_items], outputs=[output]
        )

    @ElnDbManager.transaction()
    def transform_items(self, dto: TransformItemsDTO) -> TransformResult:
        """
        Generic transform: consume N inputs into M new output items.

        Each consumable input is reduced in place by its contribution (bounded by
        the non-negative stock check) and recorded as an INGREDIENT; each
        non-consumable input is recorded as an INSTRUMENT (no quantity effect).
        Each output is a brand new item created on its chosen item sheet - its
        quantity/unit come from the sheet + user input, never from the inputs, and
        its concentration is user-entered or null. A single TRANSFORM activity
        records every input and every created output; lineage lives entirely in
        the activity inputs/outputs.

        :param dto: DTO describing the inputs consumed and the outputs created
        :type dto: TransformItemsDTO
        :return: The mutated input items and the created outputs + activity
        :rtype: TransformResult
        :raises NotFoundException: If an input item or an output sheet not found
        :raises BadRequestException: If validation fails (no input, no output, a
                                     discarded input, bad unit, or insufficient
                                     quantity)
        """
        if not dto.inputs:
            raise BadRequestException("A transform requires at least one input")
        if not dto.outputs:
            raise BadRequestException("A transform requires at least one output")

        # Resolve every input: reduce consumables in place, record instruments.
        mutated_inputs: list[Item] = []
        activity_inputs: list[CreateActivityInputDTO] = []
        for input_dto in dto.inputs:
            item = self.get_item(input_dto.item_id)

            if item.is_discarded():
                raise BadRequestException(f"Cannot transform discarded item '{item.code}'")

            if item.is_consumable():
                if input_dto.quantity is None or not input_dto.unit:
                    raise BadRequestException(
                        f"Input '{item.code}' is consumable and requires a quantity and unit"
                    )
                validated_quantity = QuantityValidator.validate_quantity(input_dto.quantity)
                base_quantity = self._validate_and_convert_quantity(
                    item, validated_quantity, input_dto.unit
                )
                item.validate_sufficient_quantity(base_quantity)
                item.quantity = item.quantity - base_quantity
                item.save()

                mutated_inputs.append(item)
                activity_inputs.append(
                    CreateActivityInputDTO(
                        item_id=item.id,
                        role=ActivityInputRole.INGREDIENT,
                        quantity_contributed=base_quantity,
                        unit_type=item.unit_type,
                    )
                )
            else:
                # Non-consumable -> INSTRUMENT input (no quantity, not decremented)
                mutated_inputs.append(item)
                activity_inputs.append(
                    CreateActivityInputDTO(
                        item_id=item.id,
                        role=ActivityInputRole.INSTRUMENT,
                    )
                )

        # Create every output item on its chosen sheet.
        output_items: list[Item] = []
        activity_outputs: list[CreateActivityOutputDTO] = []
        for output_dto in dto.outputs:
            output_sheet = self._validate_item_sheet_exists(output_dto.output_item_sheet_id)
            output_unit_type = output_sheet.unit_type

            if not UnitConverter.is_valid_unit(output_dto.unit, output_unit_type):
                valid_units = ", ".join(UnitConverter.get_valid_units(output_unit_type))
                raise BadRequestException(
                    f"Invalid unit '{output_dto.unit}' for output item sheet "
                    f"'{output_sheet.name}' (unit type: {output_unit_type.value}). "
                    f"Valid units: {valid_units}"
                )

            validated_quantity = QuantityValidator.validate_quantity(output_dto.quantity)
            output_base_quantity = UnitConverter.to_base_unit(
                validated_quantity, output_dto.unit, output_unit_type
            )

            self._validate_concentration(output_dto.concentration, output_dto.concentration_unit)

            location = LocationService().get_or_default_location(output_dto.location_id)

            output = Item()
            output.item_sheet = output_sheet
            output.quantity = output_base_quantity
            output.unit_type = output_unit_type
            output.concentration = output_dto.concentration
            output.concentration_unit = output_dto.concentration_unit or None
            output.location = location
            output.expiry_date = output_dto.expiry_date
            output.label = self._normalize_required_label(output_dto.label)
            # Storage condition inherits the output's own sheet default
            output.storage_conditions = output_sheet.storage_conditions
            output.notes = None
            output.supplier = None
            self._save_with_unique_code(output, output_sheet)

            output_items.append(output)
            activity_outputs.append(
                CreateActivityOutputDTO(
                    item_id=output.id,
                    quantity=output_base_quantity,
                    unit_type=output_unit_type,
                )
            )

        # One TRANSFORM activity: N inputs -> M outputs. The activity's own
        # item_id points at the first created output for the chronological log.
        activity = self._activity_service.log_activity(
            CreateActivityDTO(
                activity_type=ActivityType.TRANSFORM,
                item_id=output_items[0].id,
                notes=dto.notes,
                note_id=dto.note_id,
                inputs=activity_inputs,
                outputs=activity_outputs,
            )
        )

        return TransformResult(activity=activity, inputs=mutated_inputs, outputs=output_items)

    def cancel_creation(self, item_id: str) -> None:
        """
        Cancel the creation of an item by deleting it if it is deletable.

        An item is deletable if:
        - It only has the initial 'create' activity (no other activities)
        - It has not contributed to any other item's lineage

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
        Delete or discard an item.

        - If item only has the initial 'create' activity and fed no lineage: hard delete
        - If item has other activities (usage history): soft delete (set status to DISCARDED)
        - Descendants never block a discard - they remain intact

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
        :raises BadRequestException: If item is already discarded, or has activity
                                     history when allow_discard=False
        """
        # Get existing item
        item = self.get_item(item_id)

        # Check if already discarded
        if item.is_discarded():
            raise BadRequestException(f"Item '{item.code}' is already discarded")

        # Count activities where this item is the primary subject.
        activity_count = Activity.count_by_item_id(item.id)

        # An item that fed another item's lineage (an INGREDIENT input of some other
        # activity, e.g. a combine/dilute/concentrate source) must never be hard-deleted.
        contributed_to_lineage = (
            ActivityInput.select()
            .join(Activity)
            .where(
                (ActivityInput.item == item)
                & (ActivityInput.role == ActivityInputRole.INGREDIENT)
                & (Activity.item != item.id)
            )
            .count()
            > 0
        )

        # If it only has the initial 'create' activity and fed no lineage, hard delete.
        # (Descendants do NOT block a discard - they stay intact.)
        if activity_count <= 1 and not contributed_to_lineage:
            # Delete associated activities first
            Activity.delete().where(Activity.item == item).execute()
            # Hard delete the item
            item.delete_instance()
            return DeleteItemResultDTO.DELETED

        # Item has activity history
        if not allow_discard:
            raise BadRequestException(
                f"Cannot delete item '{item.code}' because it has activity history."
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

    @staticmethod
    def _assert_has_concentration(item: Item, action: str) -> None:
        """Ensure an item carries a concentration before a dilute/concentrate.

        Dilute/concentrate operate on the item's concentration, so the source/
        target must already have one (set at creation). An item expressed only as
        a quantity, with no concentration, cannot be diluted or concentrated.

        :param item: The source (concentrate) or target (dilute) item
        :type item: Item
        :param action: The action name, for the error message ("dilute"/"concentrate")
        :type action: str
        :raises BadRequestException: If the item has no recorded concentration
        """
        if item.concentration is None:
            raise BadRequestException(
                f"Cannot {action} item '{item.code}': it has no recorded concentration. "
                f"Only items with a concentration can be diluted or concentrated."
            )

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

    @staticmethod
    def _resolve_storage_conditions(value: str | None, item_sheet: ItemSheet) -> str | None:
        """Resolve an item's storage condition.

        Uses the explicit per-item value when given, otherwise inherits the
        item sheet's default.

        :param value: The per-item storage condition override (may be None/empty)
        :type value: str | None
        :param item_sheet: The item sheet to inherit the default from
        :type item_sheet: ItemSheet
        :return: The resolved storage condition
        :rtype: str | None
        """
        return value.strip() if value else item_sheet.storage_conditions

    @staticmethod
    def _normalize_required_label(label: str | None) -> str:
        """Strip and validate a required item label.

        The label is mandatory on every item (duplicates are allowed). Empty or
        whitespace-only values are rejected.

        :param label: The raw label from the DTO
        :type label: str | None
        :return: The stripped, non-empty label
        :rtype: str
        :raises BadRequestException: If the label is missing or blank
        """
        normalized = label.strip() if label else ""
        if not normalized:
            raise BadRequestException("A label is required")
        return normalized

    def _validate_serial_number_unique(self, serial_number: str | None) -> None:
        """Validate that a serial number is not already used by another item.

        A serial number identifies one physical unit lab-wide; it must be unique
        across all items. NULL serials are exempt.
        The DB unique index is the concurrency backstop; this check gives a clean
        error message.

        :param serial_number: The serial number to check (None is always valid)
        :type serial_number: str | None
        :raises BadRequestException: If the serial number is already in use
        """
        if not serial_number:
            return
        if Item.select().where(Item.serial_number == serial_number).exists():
            raise BadRequestException(
                f"Serial number '{serial_number}' is already used by another item"
            )

    def _save_with_unique_code(
        self, item: Item, item_sheet: ItemSheet, max_attempts: int = 5
    ) -> None:
        """Save a new item, (re)generating its code until it is unique.

        The code is ``MAX + 1`` over existing items of the sheet. Under
        concurrency two inserts can pick the same code; the unique index rejects the
        loser, which then recomputes ``MAX + 1`` and retries.

        :param item: The new item to save (its ``code`` is assigned here)
        :type item: Item
        :param item_sheet: The sheet whose code prefixes the generated code
        :type item_sheet: ItemSheet
        :param max_attempts: Maximum number of code (re)generation attempts
        :type max_attempts: int
        :raises IntegrityError: If a unique code cannot be assigned within
            ``max_attempts``, or for any non-code integrity violation.
        """
        for attempt in range(1, max_attempts + 1):
            item.code = self._generate_item_code(item_sheet)
            try:
                item.save()
                return
            except IntegrityError as err:
                if attempt >= max_attempts or not self._is_duplicate_code_error(err):
                    raise

    @staticmethod
    def _is_duplicate_code_error(error: Exception) -> bool:
        """Whether an IntegrityError is a duplicate on the item code column.

        Distinguishes a code collision (which we recover from by recomputing the
        code) from other unique violations (e.g. serial number), which must surface.

        :param error: The integrity error raised by the database
        :type error: Exception
        :return: True if the error is a duplicate-entry on the code
        :rtype: bool
        """
        message = str(error).lower()
        return "duplicate" in message and "code" in message

    def _generate_item_code(self, item_sheet: ItemSheet) -> str:
        """Generate one unique item code for the sheet.

        Format ``{item_sheet.code}-{increment}`` (e.g. ``ETHA-0007``). The
        increment is the *numeric* ``MAX + 1`` over existing items of that sheet.
        It is zero-padded to a minimum width of 4 and overflows naturally past 9999.

        For bulk creation (split), call this once per item *after saving the
        previous one*, so each call sees the prior increment in the database. The
        DB unique constraint on ``Item.code`` is the concurrency backstop.

        :param item_sheet: The sheet whose code prefixes the generated code
        :type item_sheet: ItemSheet
        :return: A unique item code
        :rtype: str
        """
        prefix = f"{item_sheet.code}-"

        max_increment = 0
        for item in Item.select(Item.code).where(
            (Item.item_sheet == item_sheet) & (Item.code.startswith(prefix))
        ):
            suffix = item.code[len(prefix) :]
            if suffix.isdigit():
                max_increment = max(max_increment, int(suffix))

        return f"{prefix}{max_increment + 1:04d}"

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
                f"Invalid unit '{unit}' for item '{item.code}' "
                f"(unit type: {unit_type.value}). Valid units: {valid_units}"
            )

        return UnitConverter.to_base_unit(quantity, unit, unit_type)
