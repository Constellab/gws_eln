from gws_core import (
    BadRequestException,
    NullableCharField,
    NullableDateField,
    NullableDecimalField,
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
from gws_eln.items.item_dto import ItemDTO, ItemSimpleDTO
from gws_eln.items.item_sheet import ItemSheet
from gws_eln.items.item_status import ItemStatus
from gws_eln.locations.location import Location
from gws_eln.suppliers.supplier import Supplier
from gws_eln.utils.units_converter import UnitConverter


class Item(ModelWithUser):
    """
    Item entity - represents physical inventory.

    Handles: received items, transform outputs, instrument instances, sample instances.

    Key behaviors:
    - Quantity stored in BASE UNITS (L, kg, m, units)
    - Provenance/lineage is NOT stored on the item; it is derived from the
      Activity inputs/outputs.

    Attributes:
        item_sheet: Reference to the item sheet catalog entry (required)
        code: Structured, unique, immutable code (backend-generated)
        label: Custom human-readable label (free text, optional)
        expiry_date: Expiration date
        quantity: Amount in base units (DECIMAL for precision)
        unit_type: Type of unit for quantity
        location: Storage location (required)
        notes: Additional notes
    """

    # Required relationships
    item_sheet = TypedForeignKeyField(ItemSheet, backref="items", on_delete="RESTRICT", index=True)

    location = TypedForeignKeyField(Location, backref="+", on_delete="RESTRICT", index=True)

    # Supplier relationship (optional FK to suppliers table)
    supplier = NullableForeignKeyField(Supplier, backref="items", on_delete="SET NULL", index=True)

    # Item identification
    # Structured, unique, immutable code: "{item_sheet.code}-{year}-{increment}"
    # (e.g. "ETHA-2026-0007"). Backend-generated at creation.
    code = TypedCharField(max_length=50, unique=True, index=True)
    label = NullableCharField(
        max_length=255,
    )

    # Serial number for non-consumable serialized units. Unique lab-wide; the
    # unique index allows multiple NULLs - uniqueness applies only to non-null values.
    serial_number = NullableCharField(max_length=255, unique=True, index=True)

    # Dates
    expiry_date = NullableDateField(index=True)

    # Quantity tracking - stored in base units (L, kg, m, units)
    # DECIMAL(20,12) for high precision
    quantity = TypedDecimalField(max_digits=20, decimal_places=12)
    unit_type = TypedEnumField(choices=UnitType, max_length=20)

    # Concentration tracking. Optional.
    concentration = NullableDecimalField(max_digits=20, decimal_places=12)
    concentration_unit = NullableCharField(max_length=20)

    # Storage condition for the item (free text, e.g. "-20°C"). Inherited from the
    # item sheet's default at creation, can be overridden per item.
    storage_conditions = NullableCharField(max_length=255)

    # Additional information
    notes = NullableTextField()

    # Status for soft delete
    status = TypedEnumField(
        choices=ItemStatus, max_length=20, default=ItemStatus.ACTIVE, index=True
    )

    def _before_insert(self) -> None:
        super()._before_insert()
        self.validate_field_coupling()
        self.recompute_status()

    def _before_update(self) -> None:
        super()._before_update()
        self.validate_field_coupling()
        self.recompute_status()

    def is_consumable(self) -> bool:
        """Check if the item sheet of this item is consumable."""
        return self.item_sheet.is_consumable

    def assert_can_consume(self) -> None:
        """Ensure this item supports quantity-reducing operations.

        Consume, split, combine-from, dilute and concentrate all draw a quantity,
        which only applies to consumable items.

        :raises BadRequestException: If the item is non-consumable.
        """
        if not self.is_consumable():
            raise BadRequestException(
                f"Cannot draw a quantity from non-consumable item '{self.code}' "
                f"(item sheet '{self.item_sheet.name}'). Quantity-reducing operations "
                "(consume, split, combine, dilute, concentrate) only apply to consumable items."
            )

    def assert_can_use(self) -> None:
        """Ensure this item can be recorded as 'used' (instrument reference).

        USE references a non-consumable instrument without changing quantity.
        Consumables must be consumed (quantity drawn) instead.

        :raises BadRequestException: If the item is consumable.
        """
        if self.is_consumable():
            raise BadRequestException(
                f"Cannot 'use' consumable item '{self.code}' "
                f"(item sheet '{self.item_sheet.name}'). Use 'consume' to draw a quantity instead."
            )

    def is_active(self) -> bool:
        """Check if this item is active (not discarded)."""
        return bool(self.status == ItemStatus.ACTIVE)

    def is_discarded(self) -> bool:
        """Check if this item has been discarded."""
        return bool(self.status == ItemStatus.DISCARDED)

    def is_exhausted(self) -> bool:
        """Check if this item is exhausted (consumable fully used up)."""
        return bool(self.status == ItemStatus.EXHAUSTED)

    def recompute_status(self) -> None:
        """Recompute the stored status from the current quantity.

        Rules:
        - DISCARDED is terminal and user-set: never recomputed.
        - Consumable with quantity == 0 -> EXHAUSTED.
        - Otherwise -> ACTIVE. Non-consumable items never become EXHAUSTED.
        """
        if self.status == ItemStatus.DISCARDED:
            return
        if self.is_consumable() and self.quantity == 0:
            self.status = ItemStatus.EXHAUSTED
        else:
            self.status = ItemStatus.ACTIVE

    def validate_field_coupling(self) -> None:
        """Enforce the consumable / non-consumable field coupling on save.

        - Consumable: must not carry a serial number (serials are for serialized
          non-consumable units).
        - Non-consumable: exactly one physical unit per item (quantity == 1);
          received in bulk as N separate items, never as a quantity.
          (Never EXHAUSTED is enforced by recompute_status.)

        :raises BadRequestException: If the coupling is violated.
        """
        if self.is_consumable():
            if self.serial_number:
                raise BadRequestException(
                    f"Consumable item '{self.code}' cannot have a serial number "
                    "(serial numbers are for non-consumable serialized units)."
                )
        elif self.quantity != 1:
            raise BadRequestException(
                f"Non-consumable item '{self.code}' must have quantity 1 "
                "(one item per physical unit); create several units instead of a quantity."
            )

    def validate_sufficient_quantity(self, required_quantity) -> None:
        """Check if the item has sufficient quantity for an operation."""
        if self.quantity < required_quantity:
            raise BadRequestException(
                f"Insufficient quantity in item {self.code}. Available: {self.quantity}, Requested: {required_quantity}"
            )

    def get_pretty_quantity(self) -> str:
        """Get a human-readable string for the quantity and unit type.

        :return: Pretty quantity string (e.g. "5.0 L")
        :rtype: str
        """
        return UnitConverter.format_value(self.quantity, self.unit_type)

    def get_pretty_concentration(self) -> str | None:
        """Get a human-readable string for the concentration, if any.

        :return: Pretty concentration string (e.g. "5 mol/L"), or None if unset.
        :rtype: str | None
        """
        if self.concentration is None:
            return None
        return f"{self.concentration.normalize():f} {self.concentration_unit}"

    def to_simple_dto(self) -> ItemSimpleDTO:
        """Convert the Item model to a ItemSimpleDTO.

        :return: ItemSimpleDTO with the item data
        :rtype: ItemSimpleDTO
        """

        return ItemSimpleDTO(
            id=self.id,
            code=self.code,
            label=self.label,
        )

    def to_dto(self) -> ItemDTO:
        """Convert the Item model to a ItemDTO.

        :return: ItemDTO with the item data
        :rtype: ItemDTO
        """

        return ItemDTO(
            id=self.id,
            code=self.code,
            item_sheet=self.item_sheet.to_dto(),
            location=self.location.to_dto(),
            supplier=self.supplier.to_dto() if self.supplier else None,
            label=self.label,
            serial_number=self.serial_number,
            expiry_date=self.expiry_date,
            quantity=self.quantity,
            pretty_quantity=self.get_pretty_quantity(),
            unit_type=self.unit_type,
            concentration=self.concentration,
            concentration_unit=self.concentration_unit,
            storage_conditions=self.storage_conditions,
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
