from gws_core import (
    NullableDecimalField,
    NullableEnumField,
    NullableTextField,
    TypedForeignKeyField,
)

from gws_eln.activities.activity import Activity
from gws_eln.activities.activity_dto import ActivityOutputDTO
from gws_eln.core.eln_db_manager import ElnDbManager
from gws_eln.core.model_with_user import ModelWithUser
from gws_eln.core.unit_type import UnitType
from gws_eln.items.item import Item
from gws_eln.utils.units_converter import UnitConverter


class ActivityOutput(ModelWithUser):
    """
    ActivityOutput entity - new item(s) the activity created.

    Junction between an Activity and an output Item. An activity has 0..N outputs
    (only receive/split/combine/dilute/concentrate create outputs). The quantity
    here is an immutable snapshot at creation time; item.quantity is the source
    of truth.

    Attributes:
        activity: The parent activity (required)
        item: The created item (required)
        quantity: Snapshot of the output quantity at creation, in base units
        unit_type: Unit type for the quantity
    """

    # Parent activity
    activity = TypedForeignKeyField(Activity, backref="outputs", on_delete="CASCADE", index=True)

    # The created item
    item = TypedForeignKeyField(Item, backref="+", on_delete="CASCADE", index=True)

    # Snapshot of the output quantity at creation, in base units (L, kg, m, units)
    # Audit only; item.quantity is the source of truth
    quantity = NullableDecimalField(max_digits=20, decimal_places=12)
    unit_type = NullableEnumField(choices=UnitType, max_length=20)

    # Justification the user gave to proceed past a warning when this output was
    # created (e.g. a split output whose label diverges from its source). Store-only
    # audit; surfaced as a warning hint on the output item's activity timeline.
    override_reason = NullableTextField()

    def get_pretty_quantity(self) -> str | None:
        """Get a human-readable string for the output quantity and unit type.

        An output is an addition, so the sign is intrinsically positive
        (e.g. "+10 mL"). Null when the output carries no quantity.

        :return: Signed pretty quantity string (e.g. "+5.0 L") or None if no quantity
        :rtype: str | None
        """
        if self.quantity is not None and self.unit_type is not None:
            return f"+{UnitConverter.format_value(self.quantity, self.unit_type)}"
        return None

    def to_dto(self) -> ActivityOutputDTO:
        """Convert the ActivityOutput model to an ActivityOutputDTO.

        :return: ActivityOutputDTO with the output data
        :rtype: ActivityOutputDTO
        """
        return ActivityOutputDTO(
            id=self.id,
            item=self.item.to_simple_dto(),
            quantity=self.quantity,
            unit_type=self.unit_type,
            pretty_quantity=self.get_pretty_quantity(),
            override_reason=self.override_reason,
            created_at=self.created_at,
            last_modified_at=self.last_modified_at,
        )

    class Meta:
        table_name = "gws_eln_activity_outputs"
        database = ElnDbManager.get_instance().db
        is_table = True
        db_manager = ElnDbManager.get_instance()
