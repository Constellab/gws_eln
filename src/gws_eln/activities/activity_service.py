"""
Activity Service for managing Activity entities.

Handles activity logging and history queries for inventory operations.
"""

from gws_core import BadRequestException, CurrentUserService

from gws_eln.activities.activity import Activity
from gws_eln.activities.activity_dto import (
    CreateActivityDTO,
    CreateActivityInputDTO,
    CreateActivityOutputDTO,
)
from gws_eln.activities.activity_input import ActivityInput
from gws_eln.activities.activity_input_role import ActivityInputRole
from gws_eln.activities.activity_output import ActivityOutput
from gws_eln.activities.activity_type import ActivityType
from gws_eln.items.item import Item
from gws_eln.locations.location import Location


class ActivityService:
    """
    Service class for managing Activity entities.

    Handles activity logging for all inventory actions and provides
    history queries for audit trail and traceability.

    Activity types supported:
    - RECEIVE: New item from supplier or additional stock
    - MOVE: Change location of an item
    - CONSUME: Use consumable item (decrements quantity)
    - USE: Use non-consumable item (reference only)
    - DISCARD: Remove item
    - RELABEL: Change label of an item
    """

    def get_by_id_and_check(self, activity_id: str) -> Activity:
        """
        Get an activity by ID and check that it exists.

        :param activity_id: The ID of the activity
        :type activity_id: str
        :return: The activity
        :rtype: Activity
        :raises BadRequestException: If activity doesn't exist
        """
        CurrentUserService.get_and_check_current_user()

        return Activity.get_by_id_and_check(activity_id)

    def log_activity(self, dto: CreateActivityDTO) -> Activity:
        """
        Create an activity log entry.

        :param dto: DTO containing activity data
        :type dto: CreateActivityDTO
        :return: The created activity
        :rtype: Activity
        :raises BadRequestException: If validation fails or entity doesn't exist
        """
        CurrentUserService.get_and_check_current_user()

        # Validate entity exists
        entity = self._validate_entity_exists(dto.item_id)

        # Validate locations if provided
        from_location = None
        to_location = None
        if dto.from_location_id:
            from_location = self._validate_location_exists(dto.from_location_id)
        if dto.to_location_id:
            to_location = self._validate_location_exists(dto.to_location_id)

        # Validate related item if provided
        related_item = None
        if dto.related_item_id:
            related_item = self._validate_entity_exists(dto.related_item_id)

        # Validate activity-specific requirements
        self._validate_activity_requirements(dto)

        # Create activity
        activity = Activity()
        activity.activity_type = dto.activity_type
        activity.item = entity
        activity.quantity = dto.quantity
        activity.unit_type = dto.unit_type
        activity.from_location = from_location
        activity.to_location = to_location
        activity.notes = dto.notes.strip() if dto.notes else None
        activity.note_id = dto.note_id
        activity.related_item = related_item
        activity.initial_concentration = dto.initial_concentration
        activity.final_concentration = dto.final_concentration
        activity.concentration_unit = dto.concentration_unit or None
        activity.dilution_factor = dto.dilution_factor

        activity.save()

        # Create the structured lineage rows (items taken from / created)
        for input_dto in dto.inputs:
            self._create_activity_input(activity, input_dto)
        for output_dto in dto.outputs:
            self._create_activity_output(activity, output_dto)

        return activity

    def _create_activity_input(
        self, activity: Activity, input_dto: CreateActivityInputDTO
    ) -> ActivityInput:
        """
        Create an ActivityInput row linking an item the activity took from.

        :param activity: The parent activity
        :type activity: Activity
        :param input_dto: DTO describing the input item, role and contribution
        :type input_dto: CreateActivityInputDTO
        :return: The created activity input
        :rtype: ActivityInput
        :raises BadRequestException: If the input item doesn't exist, is discarded,
                                     or an INSTRUMENT input references a consumable item
        """
        item = self._validate_entity_exists(input_dto.item_id)

        # An activity input (either role) cannot reference a discarded item
        if item.is_discarded():
            raise BadRequestException(
                f"Cannot use discarded item '{item.code}' as an activity input"
            )

        # INSTRUMENT inputs must reference a non-consumable item
        if input_dto.role == ActivityInputRole.INSTRUMENT and item.is_consumable():
            raise BadRequestException(
                f"Item '{item.code}' is consumable and cannot be used as an "
                "INSTRUMENT input. Use a CONSUME activity with a quantity instead."
            )

        activity_input = ActivityInput()
        activity_input.activity = activity
        activity_input.item = item
        activity_input.role = input_dto.role
        activity_input.quantity_contributed = input_dto.quantity_contributed
        activity_input.unit_type = input_dto.unit_type
        activity_input.save()
        return activity_input

    def _create_activity_output(
        self, activity: Activity, output_dto: CreateActivityOutputDTO
    ) -> ActivityOutput:
        """
        Create an ActivityOutput row linking a new item the activity created.

        :param activity: The parent activity
        :type activity: Activity
        :param output_dto: DTO describing the created item and its quantity snapshot
        :type output_dto: CreateActivityOutputDTO
        :return: The created activity output
        :rtype: ActivityOutput
        :raises BadRequestException: If the output item doesn't exist
        """
        item = self._validate_entity_exists(output_dto.item_id)

        activity_output = ActivityOutput()
        activity_output.activity = activity
        activity_output.item = item
        activity_output.quantity = output_dto.quantity
        activity_output.unit_type = output_dto.unit_type
        activity_output.save()
        return activity_output

    def get_item_history(self, item_id: str) -> list[Activity]:
        """
        Get all activities for a specific item ordered by created_at DESC.

        :param item_id: The ID of the item
        :type item_id: str
        :return: List of activities for the item
        :rtype: list[Activity]
        """
        CurrentUserService.get_and_check_current_user()

        # Validate item exists
        self._validate_entity_exists(item_id)

        return Activity.find_by_item_id(item_id)

    def get_note_activities(self, note_id: str) -> list[Activity]:
        """
        Get all activities linked to a specific Constellab Note.

        :param note_id: The ID of the Note
        :type note_id: str
        :return: List of activities linked to the Note
        :rtype: list[Activity]
        """
        CurrentUserService.get_and_check_current_user()

        return list(
            Activity.select()
            .where(Activity.note_id == note_id)
            .order_by(Activity.created_at.desc())
        )

    def list_activities(
        self,
        activity_type: ActivityType | None = None,
        start_date=None,
        end_date=None,
    ) -> list[Activity]:
        """
        Get all activities with optional filters.

        :param activity_type: If provided, filter by activity type
        :type activity_type: Optional[ActivityType]
        :param start_date: If provided, filter activities created on or after this date
        :param end_date: If provided, filter activities created on or before this date
        :return: List of activities
        :rtype: list[Activity]
        """
        CurrentUserService.get_and_check_current_user()

        query = Activity.select()

        if activity_type is not None:
            query = query.where(Activity.activity_type == activity_type)

        if start_date is not None:
            query = query.where(Activity.created_at >= start_date)

        if end_date is not None:
            query = query.where(Activity.created_at <= end_date)

        return list(query.order_by(Activity.created_at.desc()))

    def _validate_entity_exists(self, entity_id: str) -> Item:
        """
        Validate that an item entity exists.

        :param entity_id: Item ID to validate
        :type entity_id: str
        :return: The item if found
        :rtype: Item
        :raises BadRequestException: If item doesn't exist
        """
        item = Item.get_by_id(entity_id)
        if not item:
            raise BadRequestException(f"Item with ID '{entity_id}' does not exist")
        return item

    def _validate_location_exists(self, location_id: str) -> Location:
        """
        Validate that a location exists.

        :param location_id: Location ID to validate
        :type location_id: str
        :return: The location if found
        :rtype: Location
        :raises BadRequestException: If location doesn't exist
        """
        location = Location.get_by_id(location_id)
        if not location:
            raise BadRequestException(f"Location with ID '{location_id}' does not exist")
        return location

    def _validate_activity_requirements(self, dto: CreateActivityDTO) -> None:
        """
        Validate activity-specific requirements.

        :param dto: Activity DTO to validate
        :type dto: CreateActivityDTO
        :raises BadRequestException: If validation fails
        """
        # DISCARD requires a notes
        if dto.activity_type == ActivityType.DISCARD and not dto.notes:
            raise BadRequestException("Discard activity requires a notes")

        # MOVE requires to_location
        if dto.activity_type == ActivityType.MOVE and not dto.to_location_id:
            raise BadRequestException("Move activity requires a destination location")
