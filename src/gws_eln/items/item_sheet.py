from gws_core import (
    NullableForeignKeyField,
    NullableTextField,
    TypedBooleanField,
    TypedCharField,
    TypedEnumField,
)
from gws_eln.core.eln_db_manager import ElnDbManager
from gws_eln.core.model_with_user import ModelWithUser
from gws_eln.core.unit_type import UnitType
from gws_eln.items.item_sheet_dto import ItemSheetDTO
from gws_eln.suppliers.supplier import Supplier


class ItemSheet(ModelWithUser):
    """
    ItemSheet entity - represents a catalog entry for lab item sheets.

    Handles ALL item sheet types: chemicals, reagents, instruments, equipment, samples.
    The is_consumable flag determines behavior:
    - TRUE: consumables (chemicals, reagents, samples) - quantity decrements on use
    - FALSE: non-consumables (instruments, equipment) - usage reference only

    Attributes:
        name: ItemSheet name (required, indexed)
        description: Optional description text
        default_supplier: Optional reference to supplier (FK to gws_eln_suppliers)
        is_consumable: Whether the item sheet is consumable (affects quantity behavior)
        default_unit_type: Default unit type for items of this item sheet
    """

    # Required fields
    name = TypedCharField(max_length=255, index=True)

    # Optional fields
    description = NullableTextField()

    # Default supplier relationship (optional FK to suppliers table)
    # This is to prefill the front form when receiving new items
    default_supplier = NullableForeignKeyField(
        Supplier, backref="item_sheets", on_delete="SET NULL", index=True
    )

    # Behavior flag
    is_consumable = TypedBooleanField(default=True, index=True)

    # Default unit type for this item sheet
    default_unit_type = TypedEnumField(choices=UnitType, max_length=20, default=UnitType.COUNT)

    class Meta:
        table_name = "gws_eln_item_sheets"
        database = ElnDbManager.get_instance().db
        is_table = True
        db_manager = ElnDbManager.get_instance()

    def to_dto(self) -> ItemSheetDTO:
        """Convert the ItemSheet model to a ItemSheetDTO.

        :return: ItemSheetDTO with the item sheet data
        :rtype: ItemSheetDTO
        """

        return ItemSheetDTO(
            id=self.id,
            name=self.name,
            description=self.description,
            default_supplier=self.default_supplier.to_dto() if self.default_supplier else None,
            is_consumable=self.is_consumable,
            default_unit_type=self.default_unit_type,
            created_at=self.created_at,
            last_modified_at=self.last_modified_at,
            created_by=self.created_by.to_dto(),
            last_modified_by=self.last_modified_by.to_dto(),
        )
