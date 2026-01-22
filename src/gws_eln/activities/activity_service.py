"""
Activity Service for managing Activity entities.

Handles activity logging and history queries for inventory operations.
Implements Story 7.1 from Epic 7: Activity Service & Audit Log.
"""

from gws_core import BadRequestException, CurrentUserService

from gws_eln.activities.activity import Activity
from gws_eln.activities.activity_dto import CreateActivityDTO
from gws_eln.activities.activity_type import ActivityType
from gws_eln.activities.entity_type import EntityType
from gws_eln.locations.location import Location
from gws_eln.materials.material_batch import MaterialBatch


class ActivityService:
    """
    Service class for managing Activity entities.

    Handles activity logging for all inventory actions and provides
    history queries for audit trail and traceability.

    Activity types supported:
    - RECEIVE: New batch from supplier or additional stock
    - MOVE: Change location of a batch
    - CONSUME: Use consumable material (decrements quantity)
    - USE: Use non-consumable material (reference only)
    - DISCARD: Remove batch with reason
    - ALIQUOT: Create child batch from parent
    - RELABEL: Change label of a batch
    """

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
        entity = self._validate_entity_exists(dto.entity_id)

        # Validate locations if provided
        from_location = None
        to_location = None
        if dto.from_location_id:
            from_location = self._validate_location_exists(dto.from_location_id)
        if dto.to_location_id:
            to_location = self._validate_location_exists(dto.to_location_id)

        # Validate activity-specific requirements
        self._validate_activity_requirements(dto)

        # Create activity
        activity = Activity()
        activity.activity_type = dto.activity_type
        activity.entity_type = EntityType.MATERIAL_BATCH
        activity.entity = entity
        activity.quantity = dto.quantity
        activity.unit_type = dto.unit_type
        activity.from_location = from_location
        activity.to_location = to_location
        activity.reason = dto.reason.strip() if dto.reason else None
        activity.notes = dto.notes.strip() if dto.notes else None
        activity.note_id = dto.note_id
        activity.related_entity_id = dto.related_entity_id

        activity.save()
        return activity

    def get_batch_history(self, batch_id: str) -> list[Activity]:
        """
        Get all activities for a specific batch ordered by created_at DESC.

        :param batch_id: The ID of the batch
        :type batch_id: str
        :return: List of activities for the batch
        :rtype: list[Activity]
        """
        CurrentUserService.get_and_check_current_user()

        # Validate batch exists
        self._validate_entity_exists(batch_id)

        return list(
            Activity.select()
            .where(Activity.entity == batch_id)
            .order_by(Activity.created_at.desc())
        )

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

    def _validate_entity_exists(self, entity_id: str) -> MaterialBatch:
        """
        Validate that a batch entity exists.

        :param entity_id: Batch ID to validate
        :type entity_id: str
        :return: The batch if found
        :rtype: MaterialBatch
        :raises BadRequestException: If batch doesn't exist
        """
        batch = MaterialBatch.get_by_id(entity_id)
        if not batch:
            raise BadRequestException(f"Batch with ID '{entity_id}' does not exist")
        return batch

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
        # DISCARD requires a reason
        if dto.activity_type == ActivityType.DISCARD and not dto.reason:
            raise BadRequestException("Discard activity requires a reason")

        # MOVE requires to_location
        if dto.activity_type == ActivityType.MOVE and not dto.to_location_id:
            raise BadRequestException("Move activity requires a destination location")

        # ALIQUOT requires related_entity_id (the child batch)
        if dto.activity_type == ActivityType.ALIQUOT and not dto.related_entity_id:
            raise BadRequestException(
                "Aliquot activity requires related_entity_id (child batch ID)"
            )
