from gws_core import EnumField
from peewee import BooleanField, CharField, ForeignKeyField, TextField

from gws_eln.core.eln_db_manager import ElnDbManager
from gws_eln.core.model_with_user import ModelWithUser
from gws_eln.core.unit_type import UnitType
from gws_eln.suppliers.supplier import Supplier


class Metarial(ModelWithUser):
    """
    Metarial entity - represents a catalog entry for lab materials.

    Handles ALL material types: chemicals, reagents, instruments, equipment, samples.
    The is_consumable flag determines behavior:
    - TRUE: consumables (chemicals, reagents, samples) - quantity decrements on use
    - FALSE: non-consumables (instruments, equipment) - usage reference only

    Attributes:
        name: Material name (required, indexed)
        description: Optional description text
        supplier: Optional reference to supplier (FK to gws_eln_suppliers)
        is_consumable: Whether the material is consumable (affects quantity behavior)
        default_unit_type: Default unit type for batches of this material
    """

    # Required fields
    name = CharField(max_length=255, null=False, index=True)

    # Optional fields
    description = TextField(null=True)

    # Supplier relationship (optional FK to suppliers table)
    supplier = ForeignKeyField(
        Supplier, null=True, backref="metarials", on_delete="SET NULL", index=True
    )

    # Behavior flag
    is_consumable = BooleanField(default=True, null=False, index=True)

    # Default unit type for this material
    default_unit_type = EnumField(
        choices=UnitType, max_length=20, default=UnitType.COUNT, null=False
    )

    class Meta:
        table_name = "gws_eln_metarials"
        database = ElnDbManager.get_instance().db
        is_table = True
        db_manager = ElnDbManager.get_instance()
