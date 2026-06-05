"""
ItemSheet Service for managing ItemSheet entities.

Handles CRUD operations, validation, and business logic for item sheets.
"""

from gws_core import BadRequestException, CurrentUserService
from gws_eln.items.item import Item
from gws_eln.items.item_sheet import ItemSheet
from gws_eln.items.item_sheet_dto import CreateItemSheetDTO, UpdateItemSheetDTO
from gws_eln.suppliers.supplier import Supplier


class ItemSheetService:
    """
    Service class for managing ItemSheet entities.

    Handles CRUD operations, validation, and business logic for item sheets.
    Supports both consumable (chemicals, reagents, samples) and non-consumable
    (instruments, equipment) item sheets.
    """

    def get_item_sheet(self, item_sheet_id: str) -> ItemSheet:
        """
        Get an item sheet by ID.

        :param item_sheet_id: The ID of the item sheet
        :type item_sheet_id: str
        :return: The item sheet if found
        :rtype: ItemSheet
        :raises NotFoundException: If item sheet not found
        """
        CurrentUserService.get_and_check_current_user()
        return ItemSheet.get_by_id_and_check(item_sheet_id)

    def list_item_sheets(self, filter_consumable: bool | None = None) -> list[ItemSheet]:
        """
        Get all item sheets, optionally filtered by consumable flag.

        :param filter_consumable: If provided, filter by is_consumable value.
                                  None returns all item sheets.
        :type filter_consumable: Optional[bool]
        :return: List of item sheets
        :rtype: list[ItemSheet]
        """
        CurrentUserService.get_and_check_current_user()

        query = ItemSheet.select()

        if filter_consumable is not None:
            query = query.where(ItemSheet.is_consumable == filter_consumable)

        return list(query.order_by(ItemSheet.name))

    def create_item_sheet(self, dto: CreateItemSheetDTO) -> ItemSheet:
        """
        Create a new item sheet.

        :param dto: DTO containing item sheet data
        :type dto: CreateItemSheetDTO
        :return: The created item sheet
        :rtype: ItemSheet
        :raises BadRequestException: If validation fails or supplier doesn't exist
        """
        # Validate input
        self._validate_item_sheet_name(dto.name)

        # Validate supplier exists if provided
        supplier = None
        if dto.supplier_id:
            supplier = self._validate_supplier_exists(dto.supplier_id)

        # Create item sheet
        item_sheet = ItemSheet()
        item_sheet.name = dto.name.strip()
        item_sheet.description = dto.description.strip() if dto.description else None
        item_sheet.default_supplier = supplier
        item_sheet.is_consumable = dto.is_consumable
        item_sheet.default_unit_type = dto.default_unit_type

        # Save (created_by/last_modified_by set automatically by ModelWithUser)
        item_sheet.save()

        return item_sheet

    def update_item_sheet(self, item_sheet_id: str, dto: UpdateItemSheetDTO) -> ItemSheet:
        """
        Update an existing item sheet.

        :param item_sheet_id: The ID of the item sheet to update
        :type item_sheet_id: str
        :param dto: DTO containing updated item sheet data
        :type dto: UpdateItemSheetDTO
        :return: The updated item sheet
        :rtype: ItemSheet
        :raises NotFoundException: If item sheet not found
        :raises BadRequestException: If validation fails or supplier doesn't exist
        """
        # Get existing item sheet
        item_sheet = self.get_item_sheet(item_sheet_id)

        # Validate input
        self._validate_item_sheet_name(dto.name)

        # Validate supplier exists if provided
        supplier = None
        if dto.supplier_id:
            supplier = self._validate_supplier_exists(dto.supplier_id)

        # Update fields
        item_sheet.name = dto.name.strip()
        item_sheet.description = dto.description.strip() if dto.description else None
        item_sheet.default_supplier = supplier
        item_sheet.default_unit_type = dto.default_unit_type

        # Save (last_modified_by updated automatically by ModelWithUser)
        item_sheet.save()

        return item_sheet

    def delete_item_sheet(self, item_sheet_id: str) -> bool:
        """
        Delete an item sheet if not referenced by any items.

        :param item_sheet_id: The ID of the item sheet to delete
        :type item_sheet_id: str
        :return: True if deletion was successful
        :rtype: bool
        :raises NotFoundException: If item sheet not found
        :raises BadRequestException: If item sheet is referenced by items
        """
        # Get existing item sheet
        item_sheet = self.get_item_sheet(item_sheet_id)

        # Check for references
        self._check_no_item_references(item_sheet)

        # Delete
        item_sheet.delete_instance()

        return True

    def _validate_item_sheet_name(self, name: str) -> None:
        """
        Validate item sheet name is not empty.

        :param name: Item sheet name to validate
        :type name: str
        :raises BadRequestException: If name is empty or whitespace only
        """
        if not name or len(name.strip()) == 0:
            raise BadRequestException("Item sheet name is required")

    def _validate_supplier_exists(self, supplier_id: str) -> Supplier:
        """
        Validate that a supplier exists.

        :param supplier_id: Supplier ID to validate
        :type supplier_id: str
        :return: The supplier if found
        :rtype: Supplier
        :raises BadRequestException: If supplier doesn't exist
        """
        supplier = Supplier.get_by_id(supplier_id)
        if not supplier:
            raise BadRequestException(f"Supplier with ID '{supplier_id}' does not exist")
        return supplier

    def _check_no_item_references(self, item_sheet: ItemSheet) -> None:
        """
        Check that item sheet is not referenced by any items.

        :param item_sheet: Item sheet to check
        :type item_sheet: ItemSheet
        :raises BadRequestException: If item sheet is referenced
        """
        if Item.select().where(Item.item_sheet == item_sheet).exists():
            raise BadRequestException(
                f"Cannot delete item sheet '{item_sheet.name}' because it has existing items. "
                "Delete all items first."
            )
