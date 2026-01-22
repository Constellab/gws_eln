"""
Material Service for managing Material entities.

Handles CRUD operations, validation, and business logic for materials.
Implements Story 4.1 from Epic 4: Service Layer - Materials.
"""

from gws_core import BadRequestException, CurrentUserService

from gws_eln.materials.material import Material
from gws_eln.materials.material_batch import MaterialBatch
from gws_eln.materials.material_dto import CreateMaterialDTO, UpdateMaterialDTO
from gws_eln.suppliers.supplier import Supplier


class MaterialService:
    """
    Service class for managing Material entities.

    Handles CRUD operations, validation, and business logic for materials.
    Supports both consumable (chemicals, reagents, samples) and non-consumable
    (instruments, equipment) materials.
    """

    def get_material(self, material_id: str) -> Material:
        """
        Get a material by ID.

        :param material_id: The ID of the material
        :type material_id: str
        :return: The material if found
        :rtype: Material
        :raises NotFoundException: If material not found
        """
        CurrentUserService.get_and_check_current_user()
        return Material.get_by_id_and_check(material_id)

    def list_materials(self, filter_consumable: bool | None = None) -> list[Material]:
        """
        Get all materials, optionally filtered by consumable flag.

        :param filter_consumable: If provided, filter by is_consumable value.
                                  None returns all materials.
        :type filter_consumable: Optional[bool]
        :return: List of materials
        :rtype: list[Material]
        """
        CurrentUserService.get_and_check_current_user()

        query = Material.select()

        if filter_consumable is not None:
            query = query.where(Material.is_consumable == filter_consumable)

        return list(query.order_by(Material.name))

    def create_material(self, dto: CreateMaterialDTO) -> Material:
        """
        Create a new material.

        :param dto: DTO containing material data
        :type dto: CreateMaterialDTO
        :return: The created material
        :rtype: Material
        :raises BadRequestException: If validation fails or supplier doesn't exist
        """
        # Validate input
        self._validate_material_name(dto.name)

        # Validate supplier exists if provided
        supplier = None
        if dto.supplier_id:
            supplier = self._validate_supplier_exists(dto.supplier_id)

        # Create material
        material = Material()
        material.name = dto.name.strip()
        material.description = dto.description.strip() if dto.description else None
        material.supplier = supplier
        material.is_consumable = dto.is_consumable
        material.default_unit_type = dto.default_unit_type

        # Save (created_by/last_modified_by set automatically by ModelWithUser)
        material.save()

        return material

    def update_material(self, material_id: str, dto: UpdateMaterialDTO) -> Material:
        """
        Update an existing material.

        :param material_id: The ID of the material to update
        :type material_id: str
        :param dto: DTO containing updated material data
        :type dto: UpdateMaterialDTO
        :return: The updated material
        :rtype: Material
        :raises NotFoundException: If material not found
        :raises BadRequestException: If validation fails or supplier doesn't exist
        """
        # Get existing material
        material = self.get_material(material_id)

        # Validate input
        self._validate_material_name(dto.name)

        # Validate supplier exists if provided
        supplier = None
        if dto.supplier_id:
            supplier = self._validate_supplier_exists(dto.supplier_id)

        # Update fields
        material.name = dto.name.strip()
        material.description = dto.description.strip() if dto.description else None
        material.supplier = supplier
        material.is_consumable = dto.is_consumable
        material.default_unit_type = dto.default_unit_type

        # Save (last_modified_by updated automatically by ModelWithUser)
        material.save()

        return material

    def delete_material(self, material_id: str) -> bool:
        """
        Delete a material if not referenced by any batches.

        :param material_id: The ID of the material to delete
        :type material_id: str
        :return: True if deletion was successful
        :rtype: bool
        :raises NotFoundException: If material not found
        :raises BadRequestException: If material is referenced by batches
        """
        # Get existing material
        material = self.get_material(material_id)

        # Check for references
        self._check_no_batch_references(material)

        # Delete
        material.delete_instance()

        return True

    def _validate_material_name(self, name: str) -> None:
        """
        Validate material name is not empty.

        :param name: Material name to validate
        :type name: str
        :raises BadRequestException: If name is empty or whitespace only
        """
        if not name or len(name.strip()) == 0:
            raise BadRequestException("Material name is required")

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

    def _check_no_batch_references(self, material: Material) -> None:
        """
        Check that material is not referenced by any batches.

        :param material: Material to check
        :type material: Material
        :raises BadRequestException: If material is referenced
        """
        if MaterialBatch.select().where(MaterialBatch.material == material).exists():
            raise BadRequestException(
                f"Cannot delete material '{material.name}' because it has existing batches. "
                "Delete all batches first."
            )
