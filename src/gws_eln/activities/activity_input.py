from gws_core import (
    NullableDecimalField,
    NullableEnumField,
    TypedEnumField,
    TypedForeignKeyField,
)

from gws_eln.activities.activity import Activity
from gws_eln.activities.activity_input_role import ActivityInputRole
from gws_eln.core.eln_db_manager import ElnDbManager
from gws_eln.core.model_with_user import ModelWithUser
from gws_eln.core.unit_type import UnitType
from gws_eln.items.item import Item


class ActivityInput(ModelWithUser):
    """
    ActivityInput entity - item(s) the activity took from.

    Junction between an Activity and an input Item. An activity has 0..N inputs.
    INGREDIENT inputs contribute mass/volume and form the lineage; INSTRUMENT
    inputs are equipment references only (no quantity, excluded from lineage).

    Attributes:
        activity: The parent activity (required)
        item: The input item (required)
        role: INGREDIENT or INSTRUMENT (required)
        quantity_contributed: Amount drawn from the item, in base units
            (null for INSTRUMENT inputs and for move/relabel)
        unit_type: Unit type for the contributed quantity
    """

    # Parent activity
    activity = TypedForeignKeyField(Activity, backref="inputs", on_delete="CASCADE", index=True)

    # The input item
    item = TypedForeignKeyField(Item, backref="+", on_delete="CASCADE", index=True)

    # Whether the item is an ingredient or an instrument
    role = TypedEnumField(choices=ActivityInputRole, max_length=20)

    # Amount drawn from the item, stored in base units (L, kg, m, units)
    # Null for INSTRUMENT inputs and for move/relabel
    quantity_contributed = NullableDecimalField(max_digits=20, decimal_places=12)
    unit_type = NullableEnumField(choices=UnitType, max_length=20)

    class Meta:
        table_name = "gws_eln_activity_inputs"
        database = ElnDbManager.get_instance().db
        is_table = True
        db_manager = ElnDbManager.get_instance()
