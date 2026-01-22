"""
Location Service for managing Location entities.

Handles CRUD operations, validation, and business logic for locations.
Implements Story 3.3 from Epic 3: Service Layer - Suppliers & Locations.
"""

from gws_core import BadRequestException, CurrentUserService

from gws_eln.locations.location import Location
from gws_eln.locations.location_dto import CreateLocationDTO, UpdateLocationDTO
from gws_eln.materials.material_batch import MaterialBatch

# Default location name that cannot be deleted
DEFAULT_LOCATION_NAME = "labo"


class LocationService:
    """
    Service class for managing Location entities.

    Handles CRUD operations, validation, and business logic for locations.
    Enforces unique name constraint and prevents deletion of referenced locations.
    The default "labo" location cannot be deleted.
    """

    def get_location(self, location_id: str) -> Location:
        """
        Get a location by ID.

        :param location_id: The ID of the location
        :type location_id: str
        :return: The location if found
        :rtype: Location
        :raises NotFoundException: If location not found
        """
        CurrentUserService.get_and_check_current_user()
        return Location.get_by_id_and_check(location_id)

    def get_default_location(self) -> Location:
        """
        Get the default "labo" location.

        Creates it if it doesn't exist.

        :return: The default "labo" location
        :rtype: Location
        :raises NotFoundException: If default location doesn't exist and cannot be created
        """
        CurrentUserService.get_and_check_current_user()
        return self._ensure_default_location()

    def list_locations(self) -> list[Location]:
        """
        Get all locations ordered by name.

        :return: List of all locations
        :rtype: list[Location]
        """
        CurrentUserService.get_and_check_current_user()
        return list(Location.select().order_by(Location.name))

    def create_location(self, dto: CreateLocationDTO) -> Location:
        """
        Create a new location.

        :param dto: DTO containing location data
        :type dto: CreateLocationDTO
        :return: The created location
        :rtype: Location
        :raises BadRequestException: If name is empty or already exists
        """
        # Validate input
        self._validate_location_name(dto.name)
        self._check_unique_name(dto.name)

        # Create location
        location = Location()
        location.name = dto.name.strip()
        location.description = dto.description.strip() if dto.description else None

        # Save (created_by/last_modified_by set automatically by ModelWithUser)
        location.save()

        return location

    def update_location(self, location_id: str, dto: UpdateLocationDTO) -> Location:
        """
        Update an existing location.

        :param location_id: The ID of the location to update
        :type location_id: str
        :param dto: DTO containing updated location data
        :type dto: UpdateLocationDTO
        :return: The updated location
        :rtype: Location
        :raises NotFoundException: If location not found
        :raises BadRequestException: If name is empty or duplicates another location
        """
        # Get existing location
        location = self.get_location(location_id)

        # Validate input
        self._validate_location_name(dto.name)

        # Check unique name (only if name changed)
        if location.name != dto.name.strip():
            self._check_unique_name(dto.name, exclude_id=location_id)

        # Update fields
        location.name = dto.name.strip()
        location.description = dto.description.strip() if dto.description else None

        # Save (last_modified_by updated automatically by ModelWithUser)
        location.save()

        return location

    def delete_location(self, location_id: str) -> bool:
        """
        Delete a location if not referenced by any batches and not the default "labo" location.

        :param location_id: The ID of the location to delete
        :type location_id: str
        :return: True if deletion was successful
        :rtype: bool
        :raises NotFoundException: If location not found
        :raises BadRequestException: If location is referenced by batches or is the default location
        """
        # Get existing location
        location = self.get_location(location_id)

        # Check if it's the default location
        if location.name == DEFAULT_LOCATION_NAME:
            raise BadRequestException(
                f"Cannot delete the default location '{DEFAULT_LOCATION_NAME}'. "
                "This location is required for system operation."
            )

        # Check for references
        self._check_no_references(location)

        # Delete
        location.delete_instance()

        return True

    def _ensure_default_location(self) -> Location:
        """
        Ensure the default "labo" location exists, creating it if necessary.

        :return: The default "labo" location
        :rtype: Location
        """
        location = Location.select().where(Location.name == DEFAULT_LOCATION_NAME).first()
        if location is None:
            # Create default location
            location = Location()
            location.name = DEFAULT_LOCATION_NAME
            location.description = "Default laboratory location"
            location.save()
        return location

    def _validate_location_name(self, name: str) -> None:
        """
        Validate location name is not empty.

        :param name: Location name to validate
        :type name: str
        :raises BadRequestException: If name is empty or whitespace only
        """
        if not name or len(name.strip()) == 0:
            raise BadRequestException("Location name is required")

    def _check_unique_name(self, name: str, exclude_id: str | None = None) -> None:
        """
        Check that location name is unique.

        :param name: Location name to check
        :type name: str
        :param exclude_id: Optional location ID to exclude from check (for updates)
        :type exclude_id: Optional[str]
        :raises BadRequestException: If name already exists
        """
        query = Location.select().where(Location.name == name.strip())
        if exclude_id:
            query = query.where(Location.id != exclude_id)

        if query.exists():
            raise BadRequestException(f"A location with name '{name.strip()}' already exists")

    def _check_no_references(self, location: Location) -> None:
        """
        Check that location is not referenced by any batches.

        :param location: Location to check
        :type location: Location
        :raises BadRequestException: If location is referenced
        """
        if MaterialBatch.select().where(MaterialBatch.location == location).exists():
            raise BadRequestException(
                f"Cannot delete location '{location.name}' because it is referenced by one or more batches. "
                "Move all batches to a different location first."
            )
