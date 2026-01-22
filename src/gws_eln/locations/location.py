from peewee import CharField, TextField

from gws_eln.core.eln_db_manager import ElnDbManager
from gws_eln.core.model_with_user import ModelWithUser


class Location(ModelWithUser):
    """
    Location entity - represents a storage location in the lab.

    Stores location information for inventory tracking.
    Examples: "labo", "Freezer -80C", "Shelf A1"

    The default location "labo" must be seeded at startup.

    Attributes:
        name: Location name (required, unique, indexed)
        description: Optional description of the location
    """

    # Required fields
    name = CharField(max_length=255, null=False, unique=True, index=True)

    # Optional fields
    description = TextField(null=True)

    class Meta:
        table_name = "gws_eln_locations"
        database = ElnDbManager.get_instance().db
        is_table = True
        db_manager = ElnDbManager.get_instance()

    def to_dto(self) -> "LocationDTO":
        """Convert the Location model to a LocationDTO.

        :return: LocationDTO with the location data
        :rtype: LocationDTO
        """
        from gws_eln.locations.location_dto import LocationDTO

        return LocationDTO(
            id=self.id,
            name=self.name,
            description=self.description,
            created_at=self.created_at,
            last_modified_at=self.last_modified_at,
            created_by=self.created_by.to_dto(),
            last_modified_by=self.last_modified_by.to_dto(),
        )
