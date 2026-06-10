from gws_core import (
    NullableDecimalField,
    NullableEnumField,
    TypedForeignKeyField,
)

from gws_eln.activities.activity import Activity
from gws_eln.core.eln_db_manager import ElnDbManager
from gws_eln.core.model_with_user import ModelWithUser
from gws_eln.core.unit_type import UnitType
from gws_eln.items.item import Item


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

    class Meta:
        table_name = "gws_eln_activity_outputs"
        database = ElnDbManager.get_instance().db
        is_table = True
        db_manager = ElnDbManager.get_instance()
