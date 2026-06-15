from gws_core import (
    NullableCharField,
    NullableDecimalField,
    NullableEnumField,
    NullableForeignKeyField,
    NullableTextField,
    TypedEnumField,
    TypedForeignKeyField,
)

from gws_eln.activities.activity_dto import ActivityDTO
from gws_eln.activities.activity_type import ActivityType
from gws_eln.core.eln_db_manager import ElnDbManager
from gws_eln.core.model_with_user import ModelWithUser
from gws_eln.core.unit_type import UnitType
from gws_eln.items.item import Item
from gws_eln.locations.location import Location
from gws_eln.utils.units_converter import UnitConverter


class Activity(ModelWithUser):
    """
    Activity entity - audit log for all inventory actions.

    Tracks all inventory operations for complete audit trail and traceability.

    Activity types:
    - receive: New item received from supplier
    - consume: Use consumable item (decrements quantity)
    - use: Use non-consumable item (reference only, no decrement)
    - move: Change location of an item
    - relabel: Change label of an item
    - discard: Remove item
    - split: Split an item into multiple items
    - combine: Combine multiple items into one
    - dilute: Dilute an item (change quantity and concentration)
    - concentrate: Concentrate an item (change quantity and concentration)

    Attributes:
        activity_type: Type of activity (required)
        item: The item being acted upon (required)
        related_item: For lineage - related item ID (for split/combine)
        quantity: For quantity-based actions (stored in base units)
        unit_type: Unit type for quantity
        from_location: Source location for move actions
        to_location: Destination location for move actions
        notes: Additional notes
        note_id: Link to Constellab Note for Note-linked actions
    """

    # Activity classification
    activity_type = TypedEnumField(choices=ActivityType, max_length=20, index=True)

    # Entity being acted upon
    item = TypedForeignKeyField(Item, backref="activities", on_delete="CASCADE", index=True)

    # Related entity for lineage (for split/combine operations)
    related_item = NullableForeignKeyField(Item, backref="+", on_delete="CASCADE", index=True)

    # Quantity information (for consume and quantity-based actions)
    # Stored in base units (L, kg, m, units)
    quantity = NullableDecimalField(max_digits=20, decimal_places=12)
    unit_type = NullableEnumField(choices=UnitType, max_length=20)

    # Location tracking (for move actions)
    from_location = NullableForeignKeyField(Location, backref="+", on_delete="SET NULL")

    to_location = NullableForeignKeyField(Location, backref="+", on_delete="SET NULL")

    # Additional information
    notes = NullableTextField()

    # Link to Constellab Note (for Note-linked actions)
    note_id = NullableCharField(max_length=36)

    # Concentration audit (dilute / concentrate only) - store-only, not derivable.
    initial_concentration = NullableDecimalField(max_digits=20, decimal_places=12)
    final_concentration = NullableDecimalField(max_digits=20, decimal_places=12)
    concentration_unit = NullableCharField(max_length=20)
    dilution_factor = NullableDecimalField(max_digits=20, decimal_places=12)

    @classmethod
    def find_by_item_id(cls, item_id: str) -> list["Activity"]:
        """
        Find all activities for a given item ID.

        :param item_id: The ID of the item
        :type item_id: str
        :return: List of activities for the item
        :rtype: list[Activity]
        """
        return list(cls.select().where(cls.item == item_id).order_by(cls.created_at.desc()))

    @classmethod
    def count_by_item_id(cls, item_id: str) -> int:
        """
        Count all activities for a given item ID.

        :param item_id: The ID of the item
        :type item_id: str
        :return: Count of activities for the item
        :rtype: int
        """
        return cls.select().where(cls.item == item_id).count()

    def get_pretty_quantity(self) -> str | None:
        """Get a human-readable string for the quantity and unit type.

        :return: Pretty quantity string (e.g. "5.0 L") or None if no quantity
        :rtype: str | None
        """
        if self.quantity is not None and self.unit_type is not None:
            return UnitConverter.format_value(self.quantity, self.unit_type)
        return None

    def to_dto(self) -> ActivityDTO:
        """Convert the Activity model to an ActivityDTO.

        :return: ActivityDTO with the activity data
        :rtype: ActivityDTO
        """
        return ActivityDTO(
            id=self.id,
            activity_type=self.activity_type,
            item=self.item.to_dto(),
            related_item=self.related_item.to_dto() if self.related_item else None,
            quantity=self.quantity,
            unit_type=self.unit_type,
            pretty_quantity=self.get_pretty_quantity(),
            from_location=self.from_location.to_dto() if self.from_location else None,
            to_location=self.to_location.to_dto() if self.to_location else None,
            notes=self.notes,
            note_id=self.note_id,
            initial_concentration=self.initial_concentration,
            final_concentration=self.final_concentration,
            concentration_unit=self.concentration_unit,
            dilution_factor=self.dilution_factor,
            inputs=[activity_input.to_dto() for activity_input in self.inputs],
            outputs=[activity_output.to_dto() for activity_output in self.outputs],
            created_at=self.created_at,
            last_modified_at=self.last_modified_at,
            created_by=self.created_by.to_dto(),
            last_modified_by=self.last_modified_by.to_dto(),
        )

    class Meta:
        table_name = "gws_eln_activities"
        database = ElnDbManager.get_instance().db
        is_table = True
        db_manager = ElnDbManager.get_instance()
