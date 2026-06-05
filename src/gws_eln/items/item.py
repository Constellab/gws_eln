from gws_core import (
    BadRequestException,
    NullableCharField,
    NullableDateField,
    NullableForeignKeyField,
    NullableTextField,
    TypedCharField,
    TypedDecimalField,
    TypedEnumField,
    TypedForeignKeyField,
)
from gws_eln.core.eln_db_manager import ElnDbManager
from gws_eln.core.model_with_user import ModelWithUser
from gws_eln.core.unit_type import UnitType
from gws_eln.items.item_dto import HierarchyObjectDTO, ItemDTO, ItemSimpleDTO
from gws_eln.items.item_sheet import ItemSheet
from gws_eln.items.item_status import ItemStatus
from gws_eln.locations.location import Location
from gws_eln.suppliers.supplier import Supplier
from gws_eln.utils.units_converter import UnitConverter


class Item(ModelWithUser):
    """
    Item entity - represents physical inventory (batches and aliquots).

    Handles: received batches, aliquots, instrument instances, sample instances.

    Key behaviors:
    - parent_item_id NULL = original batch/instance
    - parent_item_id NOT NULL = aliquot/sub-batch (inherits supplier from parent's item sheet)
    - Quantity stored in BASE UNITS (L, kg, m, units)

    Attributes:
        item_sheet: Reference to the item sheet catalog entry (required)
        parent_item: Self-reference for aliquots (NULL for original batches)
        batch_number: Batch number from supplier (NULL for aliquots)
        label: Custom label for aliquots or identification
        expiry_date: Expiration date
        quantity: Amount in base units (DECIMAL for precision)
        unit_type: Type of unit for quantity
        location: Storage location (required)
        notes: Additional notes
    """

    # Required relationships
    item_sheet = TypedForeignKeyField(ItemSheet, backref="items", on_delete="RESTRICT", index=True)

    location = TypedForeignKeyField(Location, backref="+", on_delete="RESTRICT", index=True)

    # Self-reference for aliquots (parent-child relationship)
    parent_item = NullableForeignKeyField["Item"](
        "self", backref="child_items", on_delete="CASCADE", index=True
    )

    # Supplier relationship (optional FK to suppliers table)
    supplier = NullableForeignKeyField(Supplier, backref="items", on_delete="SET NULL", index=True)

    # Batch identification
    batch_number = TypedCharField(max_length=100, index=True)
    label = NullableCharField(
        max_length=255,
    )

    # Dates
    expiry_date = NullableDateField(index=True)

    # Quantity tracking - stored in base units (L, kg, m, units)
    # DECIMAL(20,12) for high precision
    quantity = TypedDecimalField(max_digits=20, decimal_places=12)
    unit_type = TypedEnumField(choices=UnitType, max_length=20)

    # Additional information
    notes = NullableTextField()

    # Status for soft delete
    status = TypedEnumField(
        choices=ItemStatus, max_length=20, default=ItemStatus.ACTIVE, index=True
    )

    def is_aliquot(self) -> bool:
        """Check if this item is an aliquot (has a parent item)."""
        return self.parent_item is not None

    def is_original_batch(self) -> bool:
        """Check if this is an original batch (no parent)."""
        return self.parent_item is None

    def is_consumable(self) -> bool:
        """Check if the item sheet of this item is consumable."""
        return self.item_sheet.is_consumable

    def is_active(self) -> bool:
        """Check if this item is active (not discarded)."""
        return bool(self.status == ItemStatus.ACTIVE)

    def is_discarded(self) -> bool:
        """Check if this item has been discarded."""
        return bool(self.status == ItemStatus.DISCARDED)

    def validate_sufficient_quantity(self, required_quantity) -> None:
        """Check if the item has sufficient quantity for an operation."""
        if self.quantity < required_quantity:
            raise BadRequestException(
                f"Insufficient quantity in item {self.batch_number}. Available: {self.quantity}, Requested: {required_quantity}"
            )

    def get_pretty_quantity(self) -> str:
        """Get a human-readable string for the quantity and unit type.

        :return: Pretty quantity string (e.g. "5.0 L")
        :rtype: str
        """
        return UnitConverter.format_value(self.quantity, self.unit_type)

    def to_simple_dto(self) -> ItemSimpleDTO:
        """Convert the Item model to a ItemSimpleDTO.

        :return: ItemSimpleDTO with the item data
        :rtype: ItemSimpleDTO
        """

        return ItemSimpleDTO(
            id=self.id,
            item_number=self.batch_number,
            label=self.label,
        )

    def get_parent_hierarchy(
        self,
        include_self: bool = False,
        include_item_sheet: bool = False,
    ) -> list[HierarchyObjectDTO]:
        """Get the full hierarchy of parent items.

        Returns a list of all parent items from the immediate parent
        up to the root (original batch), ordered from closest to furthest ancestor.

        :param include_self: If True, include the current item at the beginning of the list.
        :type include_self: bool
        :param include_item_sheet: If True, include the item sheet at the end of the hierarchy.
        :type include_item_sheet: bool
        :return: List of parent items as HierarchyObjectDTO, ordered from
                 current item (if include_self) -> immediate parent -> root -> item sheet (if include_item_sheet).
        :rtype: list[HierarchyObjectDTO]
        """
        hierarchy: list[HierarchyObjectDTO] = []

        if include_self:
            hierarchy.append(
                HierarchyObjectDTO(
                    id=self.id,
                    name=self.batch_number,
                    sub_name=self.label,
                )
            )

        current = self.parent_item
        while current is not None:
            hierarchy.append(
                HierarchyObjectDTO(
                    id=current.id,
                    name=current.batch_number,
                    sub_name=current.label,
                )
            )
            current = current.parent_item

        if include_item_sheet:
            hierarchy.append(
                HierarchyObjectDTO(
                    id=self.item_sheet.id,
                    name=self.item_sheet.name,
                    sub_name=None,
                )
            )

        return hierarchy

    def to_dto(self) -> ItemDTO:
        """Convert the Item model to a ItemDTO.

        :return: ItemDTO with the item data
        :rtype: ItemDTO
        """

        return ItemDTO(
            id=self.id,
            item_sheet=self.item_sheet.to_dto(),
            location=self.location.to_dto(),
            parent_item=self.parent_item.to_simple_dto() if self.parent_item else None,
            supplier=self.supplier.to_dto() if self.supplier else None,
            item_number=self.batch_number,
            label=self.label,
            expiry_date=self.expiry_date,
            quantity=self.quantity,
            pretty_quantity=self.get_pretty_quantity(),
            unit_type=self.unit_type,
            notes=self.notes,
            status=self.status,
            created_at=self.created_at,
            last_modified_at=self.last_modified_at,
            created_by=self.created_by.to_dto(),
            last_modified_by=self.last_modified_by.to_dto(),
        )

    class Meta:
        table_name = "gws_eln_items"
        database = ElnDbManager.get_instance().db
        is_table = True
        db_manager = ElnDbManager.get_instance()
