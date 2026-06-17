"""
ItemSheet Service for managing ItemSheet entities.

Handles CRUD operations, validation, and business logic for item sheets.
"""

import re
import string
import unicodedata

from gws_core import BadRequestException, CurrentUserService
from gws_eln.items.item import Item
from gws_eln.items.item_sheet import ItemSheet
from gws_eln.items.item_sheet_dto import CreateItemSheetDTO, UpdateItemSheetDTO
from gws_eln.suppliers.supplier import Supplier

# A sheet code is exactly 4 characters using A-Z and 0-9.
ITEM_SHEET_CODE_PATTERN = re.compile(r"^[A-Z0-9]{4}$")
ITEM_SHEET_CODE_ALPHABET = string.ascii_uppercase + string.digits


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

    def has_items(self, item_sheet_id: str) -> bool:
        """Whether at least one Item references the given item sheet.

        Used by the frontend to lock the immutable ``unit_type`` field once
        items exist.

        :param item_sheet_id: The ID of the item sheet to check
        :type item_sheet_id: str
        :return: True if any item references the sheet
        :rtype: bool
        """
        return self._has_items(self.get_item_sheet(item_sheet_id))

    def is_code_available(self, code: str) -> bool:
        """Whether a normalized 4-char code is not yet used by any sheet.

        :param code: The (already uppercased) code to check
        :type code: str
        :return: True if free, False if taken
        :rtype: bool
        """
        return not ItemSheet.select().where(ItemSheet.code == code).exists()

    def suggest_code(self, name: str) -> str:
        """Suggest an available 4-char code derived from a name.

        Accents are stripped and the name reduced to ``[A-Z0-9]`` (e.g.
        "Éthanol 99%" -> "ETHA"); the first 4 chars form the base, padded with
        ``0`` if shorter (and "ITEM" if the name has no alphanumerics). If that
        base is taken, the trailing character(s) are varied until a free code is
        found. Always returns a valid, available code - editable before saving.

        :param name: The item sheet name to derive a code from
        :type name: str
        :return: An available 4-char [A-Z0-9] code
        :rtype: str
        """
        CurrentUserService.get_and_check_current_user()

        # "Éthanol 99%" -> "ETHA"
        base = (self._slug_code(name)[:4] or "ITEM").ljust(4, "0")

        if self.is_code_available(base):
            return base

        # Vary the last character, then the last two, to find a free code.
        for char in ITEM_SHEET_CODE_ALPHABET:
            candidate = base[:3] + char
            if self.is_code_available(candidate):
                return candidate
        for first in ITEM_SHEET_CODE_ALPHABET:
            for second in ITEM_SHEET_CODE_ALPHABET:
                candidate = base[:2] + first + second
                if self.is_code_available(candidate):
                    return candidate

        return base  # all variants exhausted (practically impossible)

    def _slug_code(self, name: str) -> str:
        """Reduce a name to uppercase ``[A-Z0-9]`` only, stripping accents."""
        decomposed = unicodedata.normalize("NFKD", name or "")
        ascii_only = decomposed.encode("ascii", "ignore").decode("ascii")
        return "".join(char for char in ascii_only.upper() if char in ITEM_SHEET_CODE_ALPHABET)

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
        code = self._validate_code(dto.code)

        # Validate supplier exists if provided
        supplier = None
        if dto.supplier_id:
            supplier = self._validate_supplier_exists(dto.supplier_id)

        # Create item sheet
        item_sheet = ItemSheet()
        item_sheet.name = dto.name.strip()
        item_sheet.code = code
        item_sheet.description = dto.description.strip() if dto.description else None
        item_sheet.default_supplier = supplier
        item_sheet.is_consumable = dto.is_consumable
        item_sheet.unit_type = dto.unit_type
        item_sheet.storage_conditions = (
            dto.storage_conditions.strip() if dto.storage_conditions else None
        )

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
        :raises BadRequestException: If validation fails, supplier doesn't exist,
                                     or the unit_type is changed while items exist
        """
        # Get existing item sheet
        item_sheet = self.get_item_sheet(item_sheet_id)

        # Validate input
        self._validate_item_sheet_name(dto.name)

        # The unit_type is immutable once any Item references this sheet.
        if dto.unit_type != item_sheet.unit_type and self._has_items(item_sheet):
            raise BadRequestException(
                "Cannot change the unit type of item sheet "
                f"'{item_sheet.name}' because it already has items."
            )

        # Validate supplier exists if provided
        supplier = None
        if dto.supplier_id:
            supplier = self._validate_supplier_exists(dto.supplier_id)

        # Update fields
        item_sheet.name = dto.name.strip()
        item_sheet.description = dto.description.strip() if dto.description else None
        item_sheet.default_supplier = supplier
        item_sheet.unit_type = dto.unit_type
        item_sheet.storage_conditions = (
            dto.storage_conditions.strip() if dto.storage_conditions else None
        )

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

    def _validate_code(self, code: str) -> str:
        """Validate and normalize a sheet code.

        The code is uppercased, then must be exactly 4 characters [A-Z0-9] and
        not already used by another sheet (it is the unique prefix of item codes).
        It is immutable once the sheet is created.

        :param code: The raw code to validate
        :type code: str
        :return: The normalized (uppercased) code
        :rtype: str
        :raises BadRequestException: If the code is missing, malformed or taken
        """
        if not code or not code.strip():
            raise BadRequestException("Item sheet code is required")

        normalized = code.strip().upper()
        if not ITEM_SHEET_CODE_PATTERN.match(normalized):
            raise BadRequestException(
                "Item sheet code must be exactly 4 characters using A-Z and 0-9 only"
            )

        if ItemSheet.select().where(ItemSheet.code == normalized).exists():
            raise BadRequestException(f"Item sheet code '{normalized}' is already in use")

        return normalized

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

    def _has_items(self, item_sheet: ItemSheet) -> bool:
        """Whether at least one Item references this item sheet.

        :param item_sheet: Item sheet to check
        :type item_sheet: ItemSheet
        :return: True if any item references the sheet
        :rtype: bool
        """
        return Item.select().where(Item.item_sheet == item_sheet).exists()

    def _check_no_item_references(self, item_sheet: ItemSheet) -> None:
        """
        Check that item sheet is not referenced by any items.

        :param item_sheet: Item sheet to check
        :type item_sheet: ItemSheet
        :raises BadRequestException: If item sheet is referenced
        """
        if self._has_items(item_sheet):
            raise BadRequestException(
                f"Cannot delete item sheet '{item_sheet.name}' because it has existing items. "
                "Delete all items first."
            )
