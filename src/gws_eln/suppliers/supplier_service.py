"""
Supplier Service for managing Supplier entities.

Handles CRUD operations, validation, and business logic for suppliers.
Implements Story 3.1 from Epic 3: Service Layer - Suppliers & Locations.
"""

from gws_core import BadRequestException, CurrentUserService

from gws_eln.materials.material import Material
from gws_eln.suppliers.supplier import Supplier
from gws_eln.suppliers.supplier_dto import CreateSupplierDTO, UpdateSupplierDTO


class SupplierService:
    """
    Service class for managing Supplier entities.

    Handles CRUD operations, validation, and business logic for suppliers.
    Enforces unique name constraint and prevents deletion of referenced suppliers.
    """

    def get_supplier(self, supplier_id: str) -> Supplier:
        """
        Get a supplier by ID.

        :param supplier_id: The ID of the supplier
        :type supplier_id: str
        :return: The supplier if found
        :rtype: Supplier
        :raises NotFoundException: If supplier not found
        """
        CurrentUserService.get_and_check_current_user()
        return Supplier.get_by_id_and_check(supplier_id)

    def list_suppliers(self) -> list[Supplier]:
        """
        Get all suppliers ordered by name.

        :return: List of all suppliers
        :rtype: list[Supplier]
        """
        CurrentUserService.get_and_check_current_user()
        return list(Supplier.select().order_by(Supplier.name))

    def create_supplier(self, dto: CreateSupplierDTO) -> Supplier:
        """
        Create a new supplier.

        :param dto: DTO containing supplier data
        :type dto: CreateSupplierDTO
        :return: The created supplier
        :rtype: Supplier
        :raises BadRequestException: If name is empty or already exists
        """
        # Validate input
        self._validate_supplier_name(dto.name)
        self._check_unique_name(dto.name)

        # Create supplier
        supplier = Supplier()
        supplier.name = dto.name.strip()
        supplier.contact_info = dto.contact_info.strip() if dto.contact_info else None

        # Save (created_by/last_modified_by set automatically by ModelWithUser)
        supplier.save()

        return supplier

    def update_supplier(self, supplier_id: str, dto: UpdateSupplierDTO) -> Supplier:
        """
        Update an existing supplier.

        :param supplier_id: The ID of the supplier to update
        :type supplier_id: str
        :param dto: DTO containing updated supplier data
        :type dto: UpdateSupplierDTO
        :return: The updated supplier
        :rtype: Supplier
        :raises NotFoundException: If supplier not found
        :raises BadRequestException: If name is empty or duplicates another supplier
        """
        # Get existing supplier
        supplier = self.get_supplier(supplier_id)

        # Validate input
        self._validate_supplier_name(dto.name)

        # Check unique name (only if name changed)
        if supplier.name != dto.name.strip():
            self._check_unique_name(dto.name, exclude_id=supplier_id)

        # Update fields
        supplier.name = dto.name.strip()
        supplier.contact_info = dto.contact_info.strip() if dto.contact_info else None

        # Save (last_modified_by updated automatically by ModelWithUser)
        supplier.save()

        return supplier

    def delete_supplier(self, supplier_id: str) -> bool:
        """
        Delete a supplier if not referenced by any materials.

        :param supplier_id: The ID of the supplier to delete
        :type supplier_id: str
        :return: True if deletion was successful
        :rtype: bool
        :raises NotFoundException: If supplier not found
        :raises BadRequestException: If supplier is referenced by materials
        """
        # Get existing supplier
        supplier = self.get_supplier(supplier_id)

        # Check for references
        self._check_no_references(supplier)

        # Delete
        supplier.delete_instance()

        return True

    def _validate_supplier_name(self, name: str) -> None:
        """
        Validate supplier name is not empty.

        :param name: Supplier name to validate
        :type name: str
        :raises BadRequestException: If name is empty or whitespace only
        """
        if not name or len(name.strip()) == 0:
            raise BadRequestException("Supplier name is required")

    def _check_unique_name(self, name: str, exclude_id: str | None = None) -> None:
        """
        Check that supplier name is unique.

        :param name: Supplier name to check
        :type name: str
        :param exclude_id: Optional supplier ID to exclude from check (for updates)
        :type exclude_id: Optional[str]
        :raises BadRequestException: If name already exists
        """
        query = Supplier.select().where(Supplier.name == name.strip())
        if exclude_id:
            query = query.where(Supplier.id != exclude_id)

        if query.exists():
            raise BadRequestException(f"A supplier with name '{name.strip()}' already exists")

    def _check_no_references(self, supplier: Supplier) -> None:
        """
        Check that supplier is not referenced by any materials.

        :param supplier: Supplier to check
        :type supplier: Supplier
        :raises BadRequestException: If supplier is referenced
        """
        if Material.select().where(Material.default_supplier == supplier).exists():
            raise BadRequestException(
                f"Cannot delete supplier '{supplier.name}' because it is referenced by one or more materials. "
                "Remove the supplier reference from all materials first."
            )
