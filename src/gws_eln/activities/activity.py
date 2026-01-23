from gws_core import EnumField
from peewee import CharField, DecimalField, ForeignKeyField, TextField

from gws_eln.activities.activity_dto import ActivityDTO
from gws_eln.activities.activity_type import ActivityType
from gws_eln.core.eln_db_manager import ElnDbManager
from gws_eln.core.model_with_user import ModelWithUser
from gws_eln.core.unit_type import UnitType
from gws_eln.locations.location import Location
from gws_eln.materials.material_batch import MaterialBatch


class Activity(ModelWithUser):
    """
    Activity entity - audit log for all inventory actions.

    Tracks all inventory operations for complete audit trail and traceability.

    Activity types:
    - receive: New batch from supplier
    - move: Change location
    - consume: Use consumable (decrements quantity)
    - use: Use non-consumable (reference only)
    - discard: Remove
    - aliquot: Create child batch
    - relabel: Change label only

    Attributes:
        activity_type: Type of activity (required)
        entity_type: Type of entity being acted upon (always 'material_batch' in MVP)
        entity: The batch being acted upon (required)
        related_entity_id: For lineage - child aliquot ID, related batch ID
        quantity: For quantity-based actions (stored in base units)
        unit_type: Unit type for quantity
        from_location: Source location for move actions
        to_location: Destination location for move actions
        notes: Additional notes
        note_id: Link to Constellab Note for Note-linked actions
    """

    # Activity classification
    activity_type = EnumField(choices=ActivityType, max_length=20, null=False, index=True)

    # Entity being acted upon
    entity = ForeignKeyField(
        MaterialBatch, null=False, backref="activities", on_delete="CASCADE", index=True
    )

    # Related entity (for aliquot creation - points to child batch)
    related_entity_id = CharField(max_length=36, null=True, index=True)

    # Quantity information (for consume, aliquot actions)
    # Stored in base units (L, kg, m, units)
    quantity = DecimalField(max_digits=20, decimal_places=12, null=True)
    unit_type = EnumField(choices=UnitType, max_length=20, null=True)

    # Location tracking (for move actions)
    from_location = ForeignKeyField(Location, null=True, backref="+", on_delete="SET NULL")

    to_location = ForeignKeyField(Location, null=True, backref="+", on_delete="SET NULL")

    # Additional information
    notes = TextField(null=True)

    # Link to Constellab Note (for Note-linked actions)
    note_id = CharField(max_length=255, null=True, index=True)

    @classmethod
    def find_by_batch_id(cls, batch_id: str) -> list["Activity"]:
        """
        Find all activities for a given batch ID.

        :param batch_id: The ID of the batch
        :type batch_id: str
        :return: List of activities for the batch
        :rtype: list[Activity]
        """
        return list(cls.select().where(cls.entity == batch_id).order_by(cls.created_at.desc()))

    @classmethod
    def count_by_batch_id(cls, batch_id: str) -> int:
        """
        Count all activities for a given batch ID.

        :param batch_id: The ID of the batch
        :type batch_id: str
        :return: Count of activities for the batch
        :rtype: int
        """
        return cls.select().where(cls.entity == batch_id).count()

    class Meta:
        table_name = "gws_eln_activities"
        database = ElnDbManager.get_instance().db
        is_table = True
        db_manager = ElnDbManager.get_instance()

    def to_dto(self) -> ActivityDTO:
        """Convert the Activity model to an ActivityDTO.

        :return: ActivityDTO with the activity data
        :rtype: ActivityDTO
        """
        return ActivityDTO(
            id=self.id,
            activity_type=self.activity_type,
            entity_id=self.entity.id,
            entity_batch_number=self.entity.batch_number,
            entity_material_name=self.entity.material.name,
            related_entity_id=self.related_entity_id,
            quantity=self.quantity,
            unit_type=self.unit_type,
            from_location=self.from_location.to_dto() if self.from_location else None,
            to_location=self.to_location.to_dto() if self.to_location else None,
            notes=self.notes,
            note_id=self.note_id,
            created_at=self.created_at,
            last_modified_at=self.last_modified_at,
            created_by=self.created_by.to_dto(),
            last_modified_by=self.last_modified_by.to_dto(),
        )
