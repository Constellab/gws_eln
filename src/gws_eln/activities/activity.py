from gws_core import EnumField
from peewee import CharField, DecimalField, ForeignKeyField, TextField

from gws_eln.activities.activity_type import ActivityType
from gws_eln.activities.entity_type import EntityType
from gws_eln.core.eln_db_manager import ElnDbManager
from gws_eln.core.model_with_user import ModelWithUser
from gws_eln.locations.location import Location
from gws_eln.metarials.metarial_batch import MetarialBatch
from gws_eln.metarials.unit_type import UnitType


class Activity(ModelWithUser):
    """
    Activity entity - audit log for all inventory actions.

    Tracks all inventory operations for complete audit trail and traceability.

    Activity types:
    - receive: New batch from supplier
    - move: Change location
    - consume: Use consumable (decrements quantity)
    - use: Use non-consumable (reference only)
    - discard: Remove with reason
    - aliquot: Create child batch
    - relabel: Change label only

    Attributes:
        activity_type: Type of activity (required)
        entity_type: Type of entity being acted upon (always 'metarial_batch' in MVP)
        entity: The batch being acted upon (required)
        related_entity_id: For lineage - child aliquot ID, related batch ID
        quantity: For quantity-based actions (stored in base units)
        unit_type: Unit type for quantity
        from_location: Source location for move actions
        to_location: Destination location for move actions
        reason: Reason for discard actions (required for discard)
        notes: Additional notes
        note_id: Link to Constellab Note for Note-linked actions
    """

    # Activity classification
    activity_type = EnumField(
        choices=ActivityType,
        max_length=20,
        null=False,
        index=True
    )

    entity_type = EnumField(
        choices=EntityType,
        max_length=20,
        default=EntityType.METARIAL_BATCH,
        null=False
    )

    # Entity being acted upon
    entity = ForeignKeyField(
        MetarialBatch,
        null=False,
        backref="activities",
        on_delete="CASCADE",
        index=True
    )

    # Related entity (for aliquot creation - points to child batch)
    related_entity_id = CharField(max_length=36, null=True, index=True)

    # Quantity information (for consume, aliquot actions)
    # Stored in base units (L, kg, m, units)
    quantity = DecimalField(max_digits=20, decimal_places=12, null=True)
    unit_type = EnumField(choices=UnitType, max_length=20, null=True)

    # Location tracking (for move actions)
    from_location = ForeignKeyField(
        Location,
        null=True,
        backref="+",
        on_delete="SET NULL"
    )

    to_location = ForeignKeyField(
        Location,
        null=True,
        backref="+",
        on_delete="SET NULL"
    )

    # Additional information
    reason = TextField(null=True)
    notes = TextField(null=True)

    # Link to Constellab Note (for Note-linked actions)
    note_id = CharField(max_length=255, null=True, index=True)

    class Meta:
        table_name = "gws_eln_activities"
        database = ElnDbManager.get_instance().db
        is_table = True
        db_manager = ElnDbManager.get_instance()
