"""
Test suite for MaterialService.

Tests Story 4.2 from Epic 4: Service Layer - Materials.

Tests cover:
- Create consumable material (chemical)
- Create non-consumable material (instrument)
- Create material with supplier reference
- Create material with invalid supplier (fails)
- Update material metadata
- List materials with consumable filter
- Delete unused material (succeeds)
- Delete material with batches (fails)
"""

from decimal import Decimal

from gws_core import BadRequestException, BaseTestCase
from gws_eln.core.unit_type import UnitType
from gws_eln.locations.location import Location
from gws_eln.locations.location_dto import CreateLocationDTO
from gws_eln.locations.location_service import LocationService
from gws_eln.materials.material import Material
from gws_eln.materials.material_batch import MaterialBatch
from gws_eln.materials.material_dto import CreateMaterialDTO, UpdateMaterialDTO
from gws_eln.materials.material_service import MaterialService
from gws_eln.suppliers.supplier import Supplier
from gws_eln.suppliers.supplier_dto import CreateSupplierDTO
from gws_eln.suppliers.supplier_service import SupplierService
from gws_eln.user.eln_user_sync_service import ElnUserSyncService


class TestMaterialService(BaseTestCase):
    """Test suite for MaterialService"""

    @classmethod
    def init_before_test(cls):
        """Setup: sync users from gws_core to gws_eln before tests"""
        super().init_before_test()
        # Sync users so that the current user exists in gws_eln_user table
        sync_service = ElnUserSyncService()
        sync_service.sync_all_users()

    def _create_test_supplier(self, name: str = "Test Supplier") -> Supplier:
        """Helper to create a test supplier."""
        service = SupplierService()
        return service.create_supplier(CreateSupplierDTO(name=name))

    def _create_test_location(self, name: str = "Test Location") -> Location:
        """Helper to create a test location."""
        service = LocationService()
        return service.create_location(CreateLocationDTO(name=name))

    # ============== CREATE TESTS ==============

    def test_create_consumable_material(self):
        """Test creating a consumable material (e.g., chemical)"""
        service = MaterialService()

        # Act
        material = service.create_material(
            CreateMaterialDTO(
                name="Ethanol",
                description="Pure ethanol for laboratory use",
                is_consumable=True,
                default_unit_type=UnitType.VOLUME,
            )
        )

        # Assert
        self.assertIsNotNone(material)
        self.assertIsNotNone(material.id)
        self.assertEqual(material.name, "Ethanol")
        self.assertEqual(material.description, "Pure ethanol for laboratory use")
        self.assertTrue(material.is_consumable)
        self.assertEqual(material.default_unit_type, UnitType.VOLUME)
        self.assertIsNone(material.supplier)
        self.assertIsNotNone(material.created_at)
        self.assertIsNotNone(material.created_by)

        # Verify in database
        db_material = Material.get_by_id(material.id)
        self.assertEqual(db_material.name, "Ethanol")

        # Cleanup
        material.delete_instance()

    def test_create_non_consumable_material(self):
        """Test creating a non-consumable material (e.g., instrument)"""
        service = MaterialService()

        # Act
        material = service.create_material(
            CreateMaterialDTO(
                name="Microscope",
                description="Optical microscope for cell analysis",
                is_consumable=False,
                default_unit_type=UnitType.COUNT,
            )
        )

        # Assert
        self.assertIsNotNone(material)
        self.assertEqual(material.name, "Microscope")
        self.assertFalse(material.is_consumable)
        self.assertEqual(material.default_unit_type, UnitType.COUNT)

        # Cleanup
        material.delete_instance()

    def test_create_material_with_supplier(self):
        """Test creating a material with supplier reference"""
        service = MaterialService()
        supplier = self._create_test_supplier("Sigma-Aldrich")

        # Act
        material = service.create_material(
            CreateMaterialDTO(
                name="Sodium Chloride",
                description="NaCl for buffer preparation",
                supplier_id=supplier.id,
                is_consumable=True,
                default_unit_type=UnitType.MASS,
            )
        )

        # Assert
        self.assertIsNotNone(material)
        self.assertEqual(material.name, "Sodium Chloride")
        self.assertIsNotNone(material.supplier)
        self.assertEqual(material.supplier.id, supplier.id)
        self.assertEqual(material.supplier.name, "Sigma-Aldrich")

        # Cleanup
        material.delete_instance()
        supplier.delete_instance()

    def test_create_material_with_invalid_supplier_fails(self):
        """Test creating a material with non-existent supplier fails"""
        service = MaterialService()

        # Act & Assert
        with self.assertRaises(BadRequestException) as context:
            service.create_material(
                CreateMaterialDTO(
                    name="Test Material",
                    supplier_id="non-existent-supplier-id",
                )
            )

        self.assertIn("does not exist", str(context.exception))

    def test_create_material_name_only(self):
        """Test creating a material with only name (minimal data)"""
        service = MaterialService()

        # Act
        material = service.create_material(CreateMaterialDTO(name="Minimal Material"))

        # Assert
        self.assertIsNotNone(material)
        self.assertEqual(material.name, "Minimal Material")
        self.assertIsNone(material.description)
        self.assertIsNone(material.supplier)
        self.assertTrue(material.is_consumable)  # Default
        self.assertEqual(material.default_unit_type, UnitType.COUNT)  # Default

        # Cleanup
        material.delete_instance()

    def test_create_material_trims_whitespace(self):
        """Test that material name and description are trimmed"""
        service = MaterialService()

        # Act
        material = service.create_material(
            CreateMaterialDTO(
                name="  Trimmed Material  ",
                description="  Trimmed description  ",
            )
        )

        # Assert
        self.assertEqual(material.name, "Trimmed Material")
        self.assertEqual(material.description, "Trimmed description")

        # Cleanup
        material.delete_instance()

    def test_create_material_empty_name_fails(self):
        """Test creating a material with empty name fails"""
        service = MaterialService()

        # Act & Assert
        with self.assertRaises(BadRequestException) as context:
            service.create_material(CreateMaterialDTO(name=""))

        self.assertIn("name is required", str(context.exception))

    def test_create_material_whitespace_name_fails(self):
        """Test creating a material with whitespace-only name fails"""
        service = MaterialService()

        # Act & Assert
        with self.assertRaises(BadRequestException) as context:
            service.create_material(CreateMaterialDTO(name="   "))

        self.assertIn("name is required", str(context.exception))

    def test_create_material_all_unit_types(self):
        """Test creating materials with all unit types"""
        service = MaterialService()
        materials = []

        for unit_type in UnitType:
            material = service.create_material(
                CreateMaterialDTO(
                    name=f"Test {unit_type.value} Material",
                    default_unit_type=unit_type,
                )
            )
            self.assertEqual(material.default_unit_type, unit_type)
            materials.append(material)

        # Cleanup
        for m in materials:
            m.delete_instance()

    # ============== GET TESTS ==============

    def test_get_material(self):
        """Test getting a material by ID"""
        service = MaterialService()

        # Create material
        material = service.create_material(
            CreateMaterialDTO(
                name="Get Test Material",
                description="For get test",
            )
        )

        # Act
        retrieved = service.get_material(material.id)

        # Assert
        self.assertEqual(retrieved.id, material.id)
        self.assertEqual(retrieved.name, "Get Test Material")
        self.assertEqual(retrieved.description, "For get test")

        # Cleanup
        material.delete_instance()

    def test_get_material_not_found(self):
        """Test getting a non-existent material raises NotFoundException"""
        service = MaterialService()

        # Act & Assert
        with self.assertRaises(Exception):  # NotFoundException
            service.get_material("non-existent-id")

    # ============== LIST TESTS ==============

    def test_list_materials(self):
        """Test listing all materials"""
        service = MaterialService()

        # Create multiple materials
        material1 = service.create_material(CreateMaterialDTO(name="Alpha Material"))
        material2 = service.create_material(CreateMaterialDTO(name="Beta Material"))
        material3 = service.create_material(CreateMaterialDTO(name="Gamma Material"))

        # Act
        materials = service.list_materials()

        # Assert (at least our 3 materials)
        material_names = [m.name for m in materials]
        self.assertIn("Alpha Material", material_names)
        self.assertIn("Beta Material", material_names)
        self.assertIn("Gamma Material", material_names)

        # Verify order (should be by name)
        alpha_idx = material_names.index("Alpha Material")
        beta_idx = material_names.index("Beta Material")
        gamma_idx = material_names.index("Gamma Material")
        self.assertLess(alpha_idx, beta_idx)
        self.assertLess(beta_idx, gamma_idx)

        # Cleanup
        material1.delete_instance()
        material2.delete_instance()
        material3.delete_instance()

    def test_list_materials_filter_consumable_true(self):
        """Test listing only consumable materials"""
        service = MaterialService()

        # Create materials
        consumable = service.create_material(
            CreateMaterialDTO(
                name="Consumable Test",
                is_consumable=True,
            )
        )
        non_consumable = service.create_material(
            CreateMaterialDTO(
                name="Non-Consumable Test",
                is_consumable=False,
            )
        )

        # Act
        materials = service.list_materials(filter_consumable=True)

        # Assert
        material_names = [m.name for m in materials]
        self.assertIn("Consumable Test", material_names)
        self.assertNotIn("Non-Consumable Test", material_names)

        # Cleanup
        consumable.delete_instance()
        non_consumable.delete_instance()

    def test_list_materials_filter_consumable_false(self):
        """Test listing only non-consumable materials"""
        service = MaterialService()

        # Create materials
        consumable = service.create_material(
            CreateMaterialDTO(
                name="Consumable Filter Test",
                is_consumable=True,
            )
        )
        non_consumable = service.create_material(
            CreateMaterialDTO(
                name="Non-Consumable Filter Test",
                is_consumable=False,
            )
        )

        # Act
        materials = service.list_materials(filter_consumable=False)

        # Assert
        material_names = [m.name for m in materials]
        self.assertNotIn("Consumable Filter Test", material_names)
        self.assertIn("Non-Consumable Filter Test", material_names)

        # Cleanup
        consumable.delete_instance()
        non_consumable.delete_instance()

    def test_list_materials_filter_consumable_none(self):
        """Test listing all materials with filter_consumable=None"""
        service = MaterialService()

        # Create materials
        consumable = service.create_material(
            CreateMaterialDTO(
                name="Consumable None Test",
                is_consumable=True,
            )
        )
        non_consumable = service.create_material(
            CreateMaterialDTO(
                name="Non-Consumable None Test",
                is_consumable=False,
            )
        )

        # Act
        materials = service.list_materials(filter_consumable=None)

        # Assert - should contain both
        material_names = [m.name for m in materials]
        self.assertIn("Consumable None Test", material_names)
        self.assertIn("Non-Consumable None Test", material_names)

        # Cleanup
        consumable.delete_instance()
        non_consumable.delete_instance()

    # ============== UPDATE TESTS ==============

    def test_update_material(self):
        """Test updating a material"""
        service = MaterialService()

        # Create material
        material = service.create_material(
            CreateMaterialDTO(
                name="Original Name",
                description="Original description",
                is_consumable=True,
                default_unit_type=UnitType.COUNT,
            )
        )
        original_id = material.id

        # Act
        updated = service.update_material(
            material_id=material.id,
            dto=UpdateMaterialDTO(
                name="Updated Name",
                description="Updated description",
                is_consumable=False,
                default_unit_type=UnitType.VOLUME,
            ),
        )

        # Assert
        self.assertEqual(updated.id, original_id)
        self.assertEqual(updated.name, "Updated Name")
        self.assertEqual(updated.description, "Updated description")
        self.assertFalse(updated.is_consumable)
        self.assertEqual(updated.default_unit_type, UnitType.VOLUME)

        # Verify in database
        db_material = Material.get_by_id(original_id)
        self.assertEqual(db_material.name, "Updated Name")
        self.assertEqual(db_material.description, "Updated description")

        # Cleanup
        material.delete_instance()

    def test_update_material_add_supplier(self):
        """Test updating material to add supplier reference"""
        service = MaterialService()
        supplier = self._create_test_supplier("New Supplier")

        # Create material without supplier
        material = service.create_material(CreateMaterialDTO(name="Without Supplier"))
        self.assertIsNone(material.supplier)

        # Act: add supplier
        updated = service.update_material(
            material_id=material.id,
            dto=UpdateMaterialDTO(
                name="Without Supplier",
                supplier_id=supplier.id,
            ),
        )

        # Assert
        self.assertIsNotNone(updated.supplier)
        self.assertEqual(updated.supplier.id, supplier.id)

        # Cleanup
        material.delete_instance()
        supplier.delete_instance()

    def test_update_material_remove_supplier(self):
        """Test updating material to remove supplier reference"""
        service = MaterialService()
        supplier = self._create_test_supplier("To Remove Supplier")

        # Create material with supplier
        material = service.create_material(
            CreateMaterialDTO(
                name="With Supplier",
                supplier_id=supplier.id,
            )
        )
        self.assertIsNotNone(material.supplier)

        # Act: remove supplier (set to None)
        updated = service.update_material(
            material_id=material.id,
            dto=UpdateMaterialDTO(
                name="With Supplier",
                supplier_id=None,
            ),
        )

        # Assert
        self.assertIsNone(updated.supplier)

        # Cleanup
        material.delete_instance()
        supplier.delete_instance()

    def test_update_material_clear_description(self):
        """Test updating material to clear description"""
        service = MaterialService()

        # Create material with description
        material = service.create_material(
            CreateMaterialDTO(
                name="Clear Description",
                description="To be cleared",
            )
        )

        # Act: update with None description
        updated = service.update_material(
            material_id=material.id,
            dto=UpdateMaterialDTO(
                name="Clear Description",
                description=None,
            ),
        )

        # Assert
        self.assertIsNone(updated.description)

        # Cleanup
        material.delete_instance()

    def test_update_material_empty_name_fails(self):
        """Test updating material with empty name fails"""
        service = MaterialService()

        # Create material
        material = service.create_material(CreateMaterialDTO(name="To Update Material"))

        # Act & Assert
        with self.assertRaises(BadRequestException) as context:
            service.update_material(
                material_id=material.id,
                dto=UpdateMaterialDTO(name=""),
            )

        self.assertIn("name is required", str(context.exception))

        # Cleanup
        material.delete_instance()

    def test_update_material_invalid_supplier_fails(self):
        """Test updating material with invalid supplier fails"""
        service = MaterialService()

        # Create material
        material = service.create_material(CreateMaterialDTO(name="Invalid Supplier Update"))

        # Act & Assert
        with self.assertRaises(BadRequestException) as context:
            service.update_material(
                material_id=material.id,
                dto=UpdateMaterialDTO(
                    name="Invalid Supplier Update",
                    supplier_id="non-existent-supplier-id",
                ),
            )

        self.assertIn("does not exist", str(context.exception))

        # Cleanup
        material.delete_instance()

    # ============== DELETE TESTS ==============

    def test_delete_material_unused(self):
        """Test deleting a material that is not referenced"""
        service = MaterialService()

        # Create material
        material = service.create_material(CreateMaterialDTO(name="To Delete Material"))
        material_id = material.id

        # Act
        result = service.delete_material(material_id)

        # Assert
        self.assertTrue(result)
        self.assertFalse(Material.select().where(Material.id == material_id).exists())

    def test_delete_material_with_batches_fails(self):
        """Test deleting a material with existing batches fails"""
        service = MaterialService()
        location = self._create_test_location("Test Delete Location")

        # Create material
        material = service.create_material(CreateMaterialDTO(name="Referenced Material"))

        # Create batch that references the material
        batch = MaterialBatch()
        batch.material = material
        batch.batch_number = "BATCH-001"
        batch.location = location
        batch.quantity = Decimal("100.0")
        batch.unit_type = UnitType.COUNT
        batch.save()

        # Act & Assert
        with self.assertRaises(BadRequestException) as context:
            service.delete_material(material.id)

        self.assertIn("Cannot delete", str(context.exception))
        self.assertIn("batches", str(context.exception).lower())

        # Verify material still exists
        self.assertTrue(Material.select().where(Material.id == material.id).exists())

        # Cleanup
        batch.delete_instance()
        material.delete_instance()
        location.delete_instance()

    def test_delete_material_not_found(self):
        """Test deleting a non-existent material raises NotFoundException"""
        service = MaterialService()

        # Act & Assert
        with self.assertRaises(Exception):  # NotFoundException
            service.delete_material("non-existent-id")

    # ============== AUDIT FIELD TESTS ==============

    def test_audit_fields_on_create(self):
        """Test that audit fields are set on create"""
        service = MaterialService()

        # Act
        material = service.create_material(CreateMaterialDTO(name="Audit Test Material"))

        # Assert
        self.assertIsNotNone(material.created_at)
        self.assertIsNotNone(material.last_modified_at)
        self.assertIsNotNone(material.created_by)
        self.assertIsNotNone(material.last_modified_by)

        # Cleanup
        material.delete_instance()

    def test_audit_fields_on_update(self):
        """Test that audit fields are updated on update"""
        service = MaterialService()

        # Create material
        material = service.create_material(CreateMaterialDTO(name="Audit Update Material"))
        original_created_by_id = material.created_by.id

        # Act: update material
        updated = service.update_material(
            material_id=material.id,
            dto=UpdateMaterialDTO(name="Audit Update Material Modified"),
        )

        # Assert: created_by unchanged, last_modified_by is set
        self.assertEqual(updated.created_by.id, original_created_by_id)
        self.assertIsNotNone(updated.last_modified_at)
        self.assertIsNotNone(updated.last_modified_by)

        # Cleanup
        material.delete_instance()
