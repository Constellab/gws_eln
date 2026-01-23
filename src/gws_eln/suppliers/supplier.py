from peewee import CharField, TextField

from gws_eln.core.eln_db_manager import ElnDbManager
from gws_eln.core.model_with_user import ModelWithUser
from gws_eln.suppliers.supplier_dto import SupplierDTO


class Supplier(ModelWithUser):
    """
    Supplier entity - represents a material supplier/vendor.

    Stores supplier information including name and contact details.
    Materials can optionally reference a supplier.

    Attributes:
        name: Supplier name (required, unique, indexed)
        description: Contact information (email, phone, address, etc.)
    """

    # Required fields
    name = CharField(max_length=255, null=False, unique=True, index=True)

    # Optional fields
    description = TextField(null=True)

    class Meta:
        table_name = "gws_eln_suppliers"
        database = ElnDbManager.get_instance().db
        is_table = True
        db_manager = ElnDbManager.get_instance()

    def to_dto(self) -> SupplierDTO:
        """Convert the Supplier model to a SupplierDTO.

        :return: SupplierDTO with the supplier data
        :rtype: SupplierDTO
        """

        return SupplierDTO(
            id=self.id,
            name=self.name,
            description=self.description,
            created_at=self.created_at,
            last_modified_at=self.last_modified_at,
            created_by=self.created_by.to_dto(),
            last_modified_by=self.last_modified_by.to_dto(),
        )
