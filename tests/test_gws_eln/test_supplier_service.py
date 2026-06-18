"""
Test suite for SupplierService.

Tests Story 3.2 from Epic 3: Service Layer - Suppliers & Locations.

Tests cover:
- Create supplier with valid data
- Create supplier with duplicate name (fails)
- Update supplier
- Delete unused supplier (succeeds)
- Delete referenced supplier (fails)
- List all suppliers
"""

from gws_core import BadRequestException, BaseTestCase, NotFoundException
from gws_eln.items.item_sheet_dto import CreateItemSheetDTO
from gws_eln.items.item_sheet_service import ItemSheetService
from gws_eln.suppliers.supplier import Supplier
from gws_eln.suppliers.supplier_dto import CreateSupplierDTO, UpdateSupplierDTO
from gws_eln.suppliers.supplier_service import SupplierService
from gws_eln.user.eln_user_sync_service import ElnUserSyncService


class TestSupplierService(BaseTestCase):
    """Test suite for SupplierService"""

    @classmethod
    def init_before_test(cls):
        """Setup: sync users from gws_core to gws_eln before tests"""
        super().init_before_test()
        # Sync users so that the current user exists in gws_eln_user table
        sync_service = ElnUserSyncService()
        sync_service.sync_all_users()

    def test_create_supplier_valid_data(self):
        """Test creating a supplier with valid data"""
        service = SupplierService()

        # Act
        supplier = service.create_supplier(
            CreateSupplierDTO(name="Test Supplier", description="Supplier description")
        )

        # Assert
        self.assertIsNotNone(supplier)
        self.assertIsNotNone(supplier.id)
        self.assertEqual(supplier.name, "Test Supplier")
        self.assertEqual(supplier.description, "Supplier description")
        self.assertIsNotNone(supplier.created_at)
        self.assertIsNotNone(supplier.created_by)

        # Verify in database
        db_supplier = Supplier.get_by_id(supplier.id)
        self.assertEqual(db_supplier.name, "Test Supplier")

        # Cleanup
        supplier.delete_instance()

    def test_create_supplier_name_only(self):
        """Test creating a supplier with only name (no description)"""
        service = SupplierService()

        # Act
        supplier = service.create_supplier(CreateSupplierDTO(name="Minimal Supplier"))

        # Assert
        self.assertIsNotNone(supplier)
        self.assertEqual(supplier.name, "Minimal Supplier")
        self.assertIsNone(supplier.description)

        # Cleanup
        supplier.delete_instance()

    def test_create_supplier_trims_whitespace(self):
        """Test that supplier name and description are trimmed"""
        service = SupplierService()

        # Act
        supplier = service.create_supplier(
            CreateSupplierDTO(name="  Trimmed Supplier  ", description="  info@test.com  ")
        )

        # Assert
        self.assertEqual(supplier.name, "Trimmed Supplier")
        self.assertEqual(supplier.description, "info@test.com")

        # Cleanup
        supplier.delete_instance()

    def test_create_supplier_duplicate_name_fails(self):
        """Test creating a supplier with duplicate name fails"""
        service = SupplierService()

        # Create first supplier
        supplier1 = service.create_supplier(CreateSupplierDTO(name="Unique Supplier"))

        # Act & Assert: duplicate name should fail
        with self.assertRaises(BadRequestException) as context:
            service.create_supplier(CreateSupplierDTO(name="Unique Supplier"))

        self.assertIn("already exists", str(context.exception))
        self.assertIn("Unique Supplier", str(context.exception))

        # Cleanup
        supplier1.delete_instance()

    def test_create_supplier_empty_name_fails(self):
        """Test creating a supplier with empty name fails"""
        service = SupplierService()

        # Act & Assert
        with self.assertRaises(BadRequestException) as context:
            service.create_supplier(CreateSupplierDTO(name=""))

        self.assertIn("name is required", str(context.exception))

    def test_create_supplier_whitespace_name_fails(self):
        """Test creating a supplier with whitespace-only name fails"""
        service = SupplierService()

        # Act & Assert
        with self.assertRaises(BadRequestException) as context:
            service.create_supplier(CreateSupplierDTO(name="   "))

        self.assertIn("name is required", str(context.exception))

    def test_get_supplier(self):
        """Test getting a supplier by ID"""
        service = SupplierService()

        # Create supplier
        supplier = service.create_supplier(
            CreateSupplierDTO(name="Get Test Supplier", description="get@test.com")
        )

        # Act
        retrieved = service.get_supplier(supplier.id)

        # Assert
        self.assertEqual(retrieved.id, supplier.id)
        self.assertEqual(retrieved.name, "Get Test Supplier")
        self.assertEqual(retrieved.description, "get@test.com")

        # Cleanup
        supplier.delete_instance()

    def test_get_supplier_not_found(self):
        """Test getting a non-existent supplier raises NotFoundException"""
        service = SupplierService()

        # Act & Assert
        with self.assertRaises(NotFoundException):
            service.get_supplier("non-existent-id")

    def test_list_suppliers(self):
        """Test listing all suppliers"""
        service = SupplierService()

        # Create multiple suppliers
        supplier1 = service.create_supplier(CreateSupplierDTO(name="Alpha Supplier"))
        supplier2 = service.create_supplier(CreateSupplierDTO(name="Beta Supplier"))
        supplier3 = service.create_supplier(CreateSupplierDTO(name="Gamma Supplier"))

        # Act
        suppliers = service.list_suppliers()

        # Assert (at least our 3 suppliers)
        supplier_names = [s.name for s in suppliers]
        self.assertIn("Alpha Supplier", supplier_names)
        self.assertIn("Beta Supplier", supplier_names)
        self.assertIn("Gamma Supplier", supplier_names)

        # Verify order (should be by name)
        alpha_idx = supplier_names.index("Alpha Supplier")
        beta_idx = supplier_names.index("Beta Supplier")
        gamma_idx = supplier_names.index("Gamma Supplier")
        self.assertLess(alpha_idx, beta_idx)
        self.assertLess(beta_idx, gamma_idx)

        # Cleanup
        supplier1.delete_instance()
        supplier2.delete_instance()
        supplier3.delete_instance()

    def test_update_supplier(self):
        """Test updating a supplier"""
        service = SupplierService()

        # Create supplier
        supplier = service.create_supplier(
            CreateSupplierDTO(name="Original Name", description="original@test.com")
        )
        original_id = supplier.id

        # Act
        updated = service.update_supplier(
            supplier_id=supplier.id,
            dto=UpdateSupplierDTO(name="Updated Name", description="updated@test.com"),
        )

        # Assert
        self.assertEqual(updated.id, original_id)
        self.assertEqual(updated.name, "Updated Name")
        self.assertEqual(updated.description, "updated@test.com")

        # Verify in database
        db_supplier = Supplier.get_by_id(original_id)
        self.assertEqual(db_supplier.name, "Updated Name")
        self.assertEqual(db_supplier.description, "updated@test.com")

        # Cleanup
        supplier.delete_instance()

    def test_update_supplier_clear_description(self):
        """Test updating supplier to clear description"""
        service = SupplierService()

        # Create supplier with description
        supplier = service.create_supplier(
            CreateSupplierDTO(
                name="Clear Description Supplier", description="to-be-cleared description"
            )
        )

        # Act: update with None description
        updated = service.update_supplier(
            supplier_id=supplier.id,
            dto=UpdateSupplierDTO(name="Clear Description Supplier", description=None),
        )

        # Assert
        self.assertIsNone(updated.description)

        # Cleanup
        supplier.delete_instance()

    def test_update_supplier_same_name(self):
        """Test updating supplier keeping the same name"""
        service = SupplierService()

        # Create supplier
        supplier = service.create_supplier(
            CreateSupplierDTO(name="Same Name Supplier", description="original description")
        )

        # Act: update description only, keep same name
        updated = service.update_supplier(
            supplier_id=supplier.id,
            dto=UpdateSupplierDTO(name="Same Name Supplier", description="new description"),
        )

        # Assert
        self.assertEqual(updated.name, "Same Name Supplier")
        self.assertEqual(updated.description, "new description")

        # Cleanup
        supplier.delete_instance()

    def test_update_supplier_duplicate_name_fails(self):
        """Test updating supplier to a name that already exists fails"""
        service = SupplierService()

        # Create two suppliers
        supplier1 = service.create_supplier(CreateSupplierDTO(name="Supplier One"))
        supplier2 = service.create_supplier(CreateSupplierDTO(name="Supplier Two"))

        # Act & Assert: try to rename supplier2 to supplier1's name
        with self.assertRaises(BadRequestException) as context:
            service.update_supplier(
                supplier_id=supplier2.id, dto=UpdateSupplierDTO(name="Supplier One")
            )

        self.assertIn("already exists", str(context.exception))

        # Cleanup
        supplier1.delete_instance()
        supplier2.delete_instance()

    def test_update_supplier_empty_name_fails(self):
        """Test updating supplier with empty name fails"""
        service = SupplierService()

        # Create supplier
        supplier = service.create_supplier(CreateSupplierDTO(name="To Update Supplier"))

        # Act & Assert
        with self.assertRaises(BadRequestException) as context:
            service.update_supplier(supplier_id=supplier.id, dto=UpdateSupplierDTO(name=""))

        self.assertIn("name is required", str(context.exception))

        # Cleanup
        supplier.delete_instance()

    def test_delete_supplier_unused(self):
        """Test deleting a supplier that is not referenced"""
        service = SupplierService()

        # Create supplier
        supplier = service.create_supplier(CreateSupplierDTO(name="To Delete Supplier"))
        supplier_id = supplier.id

        # Act
        result = service.delete_supplier(supplier_id)

        # Assert
        self.assertTrue(result)
        self.assertFalse(Supplier.select().where(Supplier.id == supplier_id).exists())

    def test_delete_supplier_referenced_fails(self):
        """Test deleting a supplier referenced by materials fails"""
        service = SupplierService()

        # Create supplier
        supplier = service.create_supplier(CreateSupplierDTO(name="Referenced Supplier"))

        # Create an item sheet that references the supplier
        ItemSheetService().create_item_sheet(
            CreateItemSheetDTO(name="Sheet SUPR", code="SUPR", supplier_id=supplier.id)
        )

        # Act & Assert
        with self.assertRaises(BadRequestException) as context:
            service.delete_supplier(supplier.id)

        self.assertIn("Cannot delete", str(context.exception))
        self.assertIn("sheet", str(context.exception).lower())

        # Verify supplier still exists
        self.assertTrue(Supplier.select().where(Supplier.id == supplier.id).exists())

    def test_delete_supplier_not_found(self):
        """Test deleting a non-existent supplier raises NotFoundException"""
        service = SupplierService()

        # Act & Assert
        with self.assertRaises(NotFoundException):
            service.delete_supplier("non-existent-id")

    def test_audit_fields_on_create(self):
        """Test that audit fields are set on create"""
        service = SupplierService()

        # Act
        supplier = service.create_supplier(CreateSupplierDTO(name="Audit Test Supplier"))

        # Assert
        self.assertIsNotNone(supplier.created_at)
        self.assertIsNotNone(supplier.last_modified_at)
        self.assertIsNotNone(supplier.created_by)
        self.assertIsNotNone(supplier.last_modified_by)

        # Cleanup
        supplier.delete_instance()

    def test_audit_fields_on_update(self):
        """Test that audit fields are updated on update"""
        service = SupplierService()

        # Create supplier
        supplier = service.create_supplier(CreateSupplierDTO(name="Audit Update Supplier"))
        original_created_by_id = supplier.created_by.id

        # Act: update supplier
        updated = service.update_supplier(
            supplier_id=supplier.id, dto=UpdateSupplierDTO(name="Audit Update Supplier Modified")
        )

        # Assert: created_by unchanged, last_modified_by is set
        self.assertEqual(updated.created_by.id, original_created_by_id)
        self.assertIsNotNone(updated.last_modified_at)
        self.assertIsNotNone(updated.last_modified_by)

        # Cleanup
        supplier.delete_instance()
