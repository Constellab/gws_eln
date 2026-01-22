from peewee import CharField, TextField

from gws_eln.core.eln_db_manager import ElnDbManager
from gws_eln.core.model_with_user import ModelWithUser


class Supplier(ModelWithUser):
    """
    Supplier entity - represents a material supplier/vendor.

    Stores supplier information including name and contact details.
    Materials can optionally reference a supplier.

    Attributes:
        name: Supplier name (required, unique, indexed)
        contact_info: Contact information (email, phone, address, etc.)
    """

    # Required fields
    name = CharField(max_length=255, null=False, unique=True, index=True)

    # Optional fields
    contact_info = TextField(null=True)

    class Meta:
        table_name = "gws_eln_suppliers"
        database = ElnDbManager.get_instance().db
        is_table = True
        db_manager = ElnDbManager.get_instance()
