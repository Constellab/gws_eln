"""
Supplier Service for managing Supplier entities.

Handles CRUD operations, validation, and business logic for suppliers.
Implements Story 3.1 from Epic 3: Service Layer - Suppliers & Locations.
"""

from gws_core import BadRequestException, CurrentUserService

from gws_eln.metarials.metarial import Metarial
from gws_eln.suppliers.supplier import Supplier


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

    def create_supplier(self, name: str, contact_info: str | None = None) -> Supplier:
        """
        Create a new supplier.

        :param name: Supplier name (required, must be unique)
        :type name: str
        :param contact_info: Optional contact information
        :type contact_info: Optional[str]
        :return: The created supplier
        :rtype: Supplier
        :raises BadRequestException: If name is empty or already exists
        """
        # Validate input
        self._validate_supplier_name(name)
        self._check_unique_name(name)

        # Create supplier
        supplier = Supplier()
        supplier.name = name.strip()
        supplier.contact_info = contact_info.strip() if contact_info else None

        # Save (created_by/last_modified_by set automatically by ModelWithUser)
        supplier.save()

        return supplier

    def update_supplier(
        self,
        supplier_id: str,
        name: str,
        contact_info: str | None = None,
    ) -> Supplier:
        """
        Update an existing supplier.

        :param supplier_id: The ID of the supplier to update
        :type supplier_id: str
        :param name: Updated supplier name (required, must be unique)
        :type name: str
        :param contact_info: Updated contact information
        :type contact_info: Optional[str]
        :return: The updated supplier
        :rtype: Supplier
        :raises NotFoundException: If supplier not found
        :raises BadRequestException: If name is empty or duplicates another supplier
        """
        # Get existing supplier
        supplier = self.get_supplier(supplier_id)

        # Validate input
        self._validate_supplier_name(name)

        # Check unique name (only if name changed)
        if supplier.name != name.strip():
            self._check_unique_name(name, exclude_id=supplier_id)

        # Update fields
        supplier.name = name.strip()
        supplier.contact_info = contact_info.strip() if contact_info else None

        # Save (last_modified_by updated automatically by ModelWithUser)
        supplier.save()

        return supplier

    def delete_supplier(self, supplier_id: str) -> bool:
        """
        Delete a supplier if not referenced by any metarials.

        :param supplier_id: The ID of the supplier to delete
        :type supplier_id: str
        :return: True if deletion was successful
        :rtype: bool
        :raises NotFoundException: If supplier not found
        :raises BadRequestException: If supplier is referenced by metarials
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
        Check that supplier is not referenced by any metarials.

        :param supplier: Supplier to check
        :type supplier: Supplier
        :raises BadRequestException: If supplier is referenced
        """
        if Metarial.select().where(Metarial.supplier == supplier).exists():
            raise BadRequestException(
                f"Cannot delete supplier '{supplier.name}' because it is referenced by one or more metarials. "
                "Remove the supplier reference from all metarials first."
            )
