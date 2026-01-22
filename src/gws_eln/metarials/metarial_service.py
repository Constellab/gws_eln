"""
Metarial Service for managing Metarial entities.

Handles CRUD operations, validation, and business logic for metarials.
Implements Story 4.1 from Epic 4: Service Layer - Metarials.
"""

from gws_core import BadRequestException, CurrentUserService

from gws_eln.metarials.metarial import Metarial
from gws_eln.metarials.metarial_batch import MetarialBatch
from gws_eln.metarials.metarial_dto import CreateMetarialDTO, UpdateMetarialDTO
from gws_eln.suppliers.supplier import Supplier


class MetarialService:
    """
    Service class for managing Metarial entities.

    Handles CRUD operations, validation, and business logic for metarials.
    Supports both consumable (chemicals, reagents, samples) and non-consumable
    (instruments, equipment) materials.
    """

    def get_metarial(self, metarial_id: str) -> Metarial:
        """
        Get a metarial by ID.

        :param metarial_id: The ID of the metarial
        :type metarial_id: str
        :return: The metarial if found
        :rtype: Metarial
        :raises NotFoundException: If metarial not found
        """
        CurrentUserService.get_and_check_current_user()
        return Metarial.get_by_id_and_check(metarial_id)

    def list_metarials(self, filter_consumable: bool | None = None) -> list[Metarial]:
        """
        Get all metarials, optionally filtered by consumable flag.

        :param filter_consumable: If provided, filter by is_consumable value.
                                  None returns all metarials.
        :type filter_consumable: Optional[bool]
        :return: List of metarials
        :rtype: list[Metarial]
        """
        CurrentUserService.get_and_check_current_user()

        query = Metarial.select()

        if filter_consumable is not None:
            query = query.where(Metarial.is_consumable == filter_consumable)

        return list(query.order_by(Metarial.name))

    def create_metarial(self, dto: CreateMetarialDTO) -> Metarial:
        """
        Create a new metarial.

        :param dto: DTO containing metarial data
        :type dto: CreateMetarialDTO
        :return: The created metarial
        :rtype: Metarial
        :raises BadRequestException: If validation fails or supplier doesn't exist
        """
        # Validate input
        self._validate_metarial_name(dto.name)

        # Validate supplier exists if provided
        supplier = None
        if dto.supplier_id:
            supplier = self._validate_supplier_exists(dto.supplier_id)

        # Create metarial
        metarial = Metarial()
        metarial.name = dto.name.strip()
        metarial.description = dto.description.strip() if dto.description else None
        metarial.supplier = supplier
        metarial.is_consumable = dto.is_consumable
        metarial.default_unit_type = dto.default_unit_type

        # Save (created_by/last_modified_by set automatically by ModelWithUser)
        metarial.save()

        return metarial

    def update_metarial(self, metarial_id: str, dto: UpdateMetarialDTO) -> Metarial:
        """
        Update an existing metarial.

        :param metarial_id: The ID of the metarial to update
        :type metarial_id: str
        :param dto: DTO containing updated metarial data
        :type dto: UpdateMetarialDTO
        :return: The updated metarial
        :rtype: Metarial
        :raises NotFoundException: If metarial not found
        :raises BadRequestException: If validation fails or supplier doesn't exist
        """
        # Get existing metarial
        metarial = self.get_metarial(metarial_id)

        # Validate input
        self._validate_metarial_name(dto.name)

        # Validate supplier exists if provided
        supplier = None
        if dto.supplier_id:
            supplier = self._validate_supplier_exists(dto.supplier_id)

        # Update fields
        metarial.name = dto.name.strip()
        metarial.description = dto.description.strip() if dto.description else None
        metarial.supplier = supplier
        metarial.is_consumable = dto.is_consumable
        metarial.default_unit_type = dto.default_unit_type

        # Save (last_modified_by updated automatically by ModelWithUser)
        metarial.save()

        return metarial

    def delete_metarial(self, metarial_id: str) -> bool:
        """
        Delete a metarial if not referenced by any batches.

        :param metarial_id: The ID of the metarial to delete
        :type metarial_id: str
        :return: True if deletion was successful
        :rtype: bool
        :raises NotFoundException: If metarial not found
        :raises BadRequestException: If metarial is referenced by batches
        """
        # Get existing metarial
        metarial = self.get_metarial(metarial_id)

        # Check for references
        self._check_no_batch_references(metarial)

        # Delete
        metarial.delete_instance()

        return True

    def _validate_metarial_name(self, name: str) -> None:
        """
        Validate metarial name is not empty.

        :param name: Metarial name to validate
        :type name: str
        :raises BadRequestException: If name is empty or whitespace only
        """
        if not name or len(name.strip()) == 0:
            raise BadRequestException("Metarial name is required")

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

    def _check_no_batch_references(self, metarial: Metarial) -> None:
        """
        Check that metarial is not referenced by any batches.

        :param metarial: Metarial to check
        :type metarial: Metarial
        :raises BadRequestException: If metarial is referenced
        """
        if MetarialBatch.select().where(MetarialBatch.metarial == metarial).exists():
            raise BadRequestException(
                f"Cannot delete metarial '{metarial.name}' because it has existing batches. "
                "Delete all batches first."
            )
