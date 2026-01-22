"""
Test suite for MetarialService.

Tests Story 4.2 from Epic 4: Service Layer - Metarials.

Tests cover:
- Create consumable metarial (chemical)
- Create non-consumable metarial (instrument)
- Create metarial with supplier reference
- Create metarial with invalid supplier (fails)
- Update metarial metadata
- List metarials with consumable filter
- Delete unused metarial (succeeds)
- Delete metarial with batches (fails)
"""

from decimal import Decimal

from gws_core import BadRequestException, BaseTestCase

from gws_eln.core.unit_type import UnitType
from gws_eln.locations.location import Location
from gws_eln.locations.location_dto import CreateLocationDTO
from gws_eln.locations.location_service import LocationService
from gws_eln.metarials.metarial import Metarial
from gws_eln.metarials.metarial_batch import MetarialBatch
from gws_eln.metarials.metarial_dto import CreateMetarialDTO, UpdateMetarialDTO
from gws_eln.metarials.metarial_service import MetarialService
from gws_eln.suppliers.supplier import Supplier
from gws_eln.suppliers.supplier_dto import CreateSupplierDTO
from gws_eln.suppliers.supplier_service import SupplierService
from gws_eln.user.eln_user_sync_service import ElnUserSyncService


class TestMetarialService(BaseTestCase):
    """Test suite for MetarialService"""

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

    def test_create_consumable_metarial(self):
        """Test creating a consumable metarial (e.g., chemical)"""
        service = MetarialService()

        # Act
        metarial = service.create_metarial(CreateMetarialDTO(
            name="Ethanol",
            description="Pure ethanol for laboratory use",
            is_consumable=True,
            default_unit_type=UnitType.VOLUME,
        ))

        # Assert
        self.assertIsNotNone(metarial)
        self.assertIsNotNone(metarial.id)
        self.assertEqual(metarial.name, "Ethanol")
        self.assertEqual(metarial.description, "Pure ethanol for laboratory use")
        self.assertTrue(metarial.is_consumable)
        self.assertEqual(metarial.default_unit_type, UnitType.VOLUME)
        self.assertIsNone(metarial.supplier)
        self.assertIsNotNone(metarial.created_at)
        self.assertIsNotNone(metarial.created_by)

        # Verify in database
        db_metarial = Metarial.get_by_id(metarial.id)
        self.assertEqual(db_metarial.name, "Ethanol")

        # Cleanup
        metarial.delete_instance()

    def test_create_non_consumable_metarial(self):
        """Test creating a non-consumable metarial (e.g., instrument)"""
        service = MetarialService()

        # Act
        metarial = service.create_metarial(CreateMetarialDTO(
            name="Microscope",
            description="Optical microscope for cell analysis",
            is_consumable=False,
            default_unit_type=UnitType.COUNT,
        ))

        # Assert
        self.assertIsNotNone(metarial)
        self.assertEqual(metarial.name, "Microscope")
        self.assertFalse(metarial.is_consumable)
        self.assertEqual(metarial.default_unit_type, UnitType.COUNT)

        # Cleanup
        metarial.delete_instance()

    def test_create_metarial_with_supplier(self):
        """Test creating a metarial with supplier reference"""
        service = MetarialService()
        supplier = self._create_test_supplier("Sigma-Aldrich")

        # Act
        metarial = service.create_metarial(CreateMetarialDTO(
            name="Sodium Chloride",
            description="NaCl for buffer preparation",
            supplier_id=supplier.id,
            is_consumable=True,
            default_unit_type=UnitType.MASS,
        ))

        # Assert
        self.assertIsNotNone(metarial)
        self.assertEqual(metarial.name, "Sodium Chloride")
        self.assertIsNotNone(metarial.supplier)
        self.assertEqual(metarial.supplier.id, supplier.id)
        self.assertEqual(metarial.supplier.name, "Sigma-Aldrich")

        # Cleanup
        metarial.delete_instance()
        supplier.delete_instance()

    def test_create_metarial_with_invalid_supplier_fails(self):
        """Test creating a metarial with non-existent supplier fails"""
        service = MetarialService()

        # Act & Assert
        with self.assertRaises(BadRequestException) as context:
            service.create_metarial(CreateMetarialDTO(
                name="Test Metarial",
                supplier_id="non-existent-supplier-id",
            ))

        self.assertIn("does not exist", str(context.exception))

    def test_create_metarial_name_only(self):
        """Test creating a metarial with only name (minimal data)"""
        service = MetarialService()

        # Act
        metarial = service.create_metarial(CreateMetarialDTO(name="Minimal Metarial"))

        # Assert
        self.assertIsNotNone(metarial)
        self.assertEqual(metarial.name, "Minimal Metarial")
        self.assertIsNone(metarial.description)
        self.assertIsNone(metarial.supplier)
        self.assertTrue(metarial.is_consumable)  # Default
        self.assertEqual(metarial.default_unit_type, UnitType.COUNT)  # Default

        # Cleanup
        metarial.delete_instance()

    def test_create_metarial_trims_whitespace(self):
        """Test that metarial name and description are trimmed"""
        service = MetarialService()

        # Act
        metarial = service.create_metarial(CreateMetarialDTO(
            name="  Trimmed Metarial  ",
            description="  Trimmed description  ",
        ))

        # Assert
        self.assertEqual(metarial.name, "Trimmed Metarial")
        self.assertEqual(metarial.description, "Trimmed description")

        # Cleanup
        metarial.delete_instance()

    def test_create_metarial_empty_name_fails(self):
        """Test creating a metarial with empty name fails"""
        service = MetarialService()

        # Act & Assert
        with self.assertRaises(BadRequestException) as context:
            service.create_metarial(CreateMetarialDTO(name=""))

        self.assertIn("name is required", str(context.exception))

    def test_create_metarial_whitespace_name_fails(self):
        """Test creating a metarial with whitespace-only name fails"""
        service = MetarialService()

        # Act & Assert
        with self.assertRaises(BadRequestException) as context:
            service.create_metarial(CreateMetarialDTO(name="   "))

        self.assertIn("name is required", str(context.exception))

    def test_create_metarial_all_unit_types(self):
        """Test creating metarials with all unit types"""
        service = MetarialService()
        metarials = []

        for unit_type in UnitType:
            metarial = service.create_metarial(CreateMetarialDTO(
                name=f"Test {unit_type.value} Metarial",
                default_unit_type=unit_type,
            ))
            self.assertEqual(metarial.default_unit_type, unit_type)
            metarials.append(metarial)

        # Cleanup
        for m in metarials:
            m.delete_instance()

    # ============== GET TESTS ==============

    def test_get_metarial(self):
        """Test getting a metarial by ID"""
        service = MetarialService()

        # Create metarial
        metarial = service.create_metarial(CreateMetarialDTO(
            name="Get Test Metarial",
            description="For get test",
        ))

        # Act
        retrieved = service.get_metarial(metarial.id)

        # Assert
        self.assertEqual(retrieved.id, metarial.id)
        self.assertEqual(retrieved.name, "Get Test Metarial")
        self.assertEqual(retrieved.description, "For get test")

        # Cleanup
        metarial.delete_instance()

    def test_get_metarial_not_found(self):
        """Test getting a non-existent metarial raises NotFoundException"""
        service = MetarialService()

        # Act & Assert
        with self.assertRaises(Exception):  # NotFoundException
            service.get_metarial("non-existent-id")

    # ============== LIST TESTS ==============

    def test_list_metarials(self):
        """Test listing all metarials"""
        service = MetarialService()

        # Create multiple metarials
        metarial1 = service.create_metarial(CreateMetarialDTO(name="Alpha Metarial"))
        metarial2 = service.create_metarial(CreateMetarialDTO(name="Beta Metarial"))
        metarial3 = service.create_metarial(CreateMetarialDTO(name="Gamma Metarial"))

        # Act
        metarials = service.list_metarials()

        # Assert (at least our 3 metarials)
        metarial_names = [m.name for m in metarials]
        self.assertIn("Alpha Metarial", metarial_names)
        self.assertIn("Beta Metarial", metarial_names)
        self.assertIn("Gamma Metarial", metarial_names)

        # Verify order (should be by name)
        alpha_idx = metarial_names.index("Alpha Metarial")
        beta_idx = metarial_names.index("Beta Metarial")
        gamma_idx = metarial_names.index("Gamma Metarial")
        self.assertLess(alpha_idx, beta_idx)
        self.assertLess(beta_idx, gamma_idx)

        # Cleanup
        metarial1.delete_instance()
        metarial2.delete_instance()
        metarial3.delete_instance()

    def test_list_metarials_filter_consumable_true(self):
        """Test listing only consumable metarials"""
        service = MetarialService()

        # Create metarials
        consumable = service.create_metarial(CreateMetarialDTO(
            name="Consumable Test",
            is_consumable=True,
        ))
        non_consumable = service.create_metarial(CreateMetarialDTO(
            name="Non-Consumable Test",
            is_consumable=False,
        ))

        # Act
        metarials = service.list_metarials(filter_consumable=True)

        # Assert
        metarial_names = [m.name for m in metarials]
        self.assertIn("Consumable Test", metarial_names)
        self.assertNotIn("Non-Consumable Test", metarial_names)

        # Cleanup
        consumable.delete_instance()
        non_consumable.delete_instance()

    def test_list_metarials_filter_consumable_false(self):
        """Test listing only non-consumable metarials"""
        service = MetarialService()

        # Create metarials
        consumable = service.create_metarial(CreateMetarialDTO(
            name="Consumable Filter Test",
            is_consumable=True,
        ))
        non_consumable = service.create_metarial(CreateMetarialDTO(
            name="Non-Consumable Filter Test",
            is_consumable=False,
        ))

        # Act
        metarials = service.list_metarials(filter_consumable=False)

        # Assert
        metarial_names = [m.name for m in metarials]
        self.assertNotIn("Consumable Filter Test", metarial_names)
        self.assertIn("Non-Consumable Filter Test", metarial_names)

        # Cleanup
        consumable.delete_instance()
        non_consumable.delete_instance()

    def test_list_metarials_filter_consumable_none(self):
        """Test listing all metarials with filter_consumable=None"""
        service = MetarialService()

        # Create metarials
        consumable = service.create_metarial(CreateMetarialDTO(
            name="Consumable None Test",
            is_consumable=True,
        ))
        non_consumable = service.create_metarial(CreateMetarialDTO(
            name="Non-Consumable None Test",
            is_consumable=False,
        ))

        # Act
        metarials = service.list_metarials(filter_consumable=None)

        # Assert - should contain both
        metarial_names = [m.name for m in metarials]
        self.assertIn("Consumable None Test", metarial_names)
        self.assertIn("Non-Consumable None Test", metarial_names)

        # Cleanup
        consumable.delete_instance()
        non_consumable.delete_instance()

    # ============== UPDATE TESTS ==============

    def test_update_metarial(self):
        """Test updating a metarial"""
        service = MetarialService()

        # Create metarial
        metarial = service.create_metarial(CreateMetarialDTO(
            name="Original Name",
            description="Original description",
            is_consumable=True,
            default_unit_type=UnitType.COUNT,
        ))
        original_id = metarial.id

        # Act
        updated = service.update_metarial(
            metarial_id=metarial.id,
            dto=UpdateMetarialDTO(
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
        db_metarial = Metarial.get_by_id(original_id)
        self.assertEqual(db_metarial.name, "Updated Name")
        self.assertEqual(db_metarial.description, "Updated description")

        # Cleanup
        metarial.delete_instance()

    def test_update_metarial_add_supplier(self):
        """Test updating metarial to add supplier reference"""
        service = MetarialService()
        supplier = self._create_test_supplier("New Supplier")

        # Create metarial without supplier
        metarial = service.create_metarial(CreateMetarialDTO(name="Without Supplier"))
        self.assertIsNone(metarial.supplier)

        # Act: add supplier
        updated = service.update_metarial(
            metarial_id=metarial.id,
            dto=UpdateMetarialDTO(
                name="Without Supplier",
                supplier_id=supplier.id,
            ),
        )

        # Assert
        self.assertIsNotNone(updated.supplier)
        self.assertEqual(updated.supplier.id, supplier.id)

        # Cleanup
        metarial.delete_instance()
        supplier.delete_instance()

    def test_update_metarial_remove_supplier(self):
        """Test updating metarial to remove supplier reference"""
        service = MetarialService()
        supplier = self._create_test_supplier("To Remove Supplier")

        # Create metarial with supplier
        metarial = service.create_metarial(CreateMetarialDTO(
            name="With Supplier",
            supplier_id=supplier.id,
        ))
        self.assertIsNotNone(metarial.supplier)

        # Act: remove supplier (set to None)
        updated = service.update_metarial(
            metarial_id=metarial.id,
            dto=UpdateMetarialDTO(
                name="With Supplier",
                supplier_id=None,
            ),
        )

        # Assert
        self.assertIsNone(updated.supplier)

        # Cleanup
        metarial.delete_instance()
        supplier.delete_instance()

    def test_update_metarial_clear_description(self):
        """Test updating metarial to clear description"""
        service = MetarialService()

        # Create metarial with description
        metarial = service.create_metarial(CreateMetarialDTO(
            name="Clear Description",
            description="To be cleared",
        ))

        # Act: update with None description
        updated = service.update_metarial(
            metarial_id=metarial.id,
            dto=UpdateMetarialDTO(
                name="Clear Description",
                description=None,
            ),
        )

        # Assert
        self.assertIsNone(updated.description)

        # Cleanup
        metarial.delete_instance()

    def test_update_metarial_empty_name_fails(self):
        """Test updating metarial with empty name fails"""
        service = MetarialService()

        # Create metarial
        metarial = service.create_metarial(CreateMetarialDTO(name="To Update Metarial"))

        # Act & Assert
        with self.assertRaises(BadRequestException) as context:
            service.update_metarial(
                metarial_id=metarial.id,
                dto=UpdateMetarialDTO(name=""),
            )

        self.assertIn("name is required", str(context.exception))

        # Cleanup
        metarial.delete_instance()

    def test_update_metarial_invalid_supplier_fails(self):
        """Test updating metarial with invalid supplier fails"""
        service = MetarialService()

        # Create metarial
        metarial = service.create_metarial(CreateMetarialDTO(name="Invalid Supplier Update"))

        # Act & Assert
        with self.assertRaises(BadRequestException) as context:
            service.update_metarial(
                metarial_id=metarial.id,
                dto=UpdateMetarialDTO(
                    name="Invalid Supplier Update",
                    supplier_id="non-existent-supplier-id",
                ),
            )

        self.assertIn("does not exist", str(context.exception))

        # Cleanup
        metarial.delete_instance()

    # ============== DELETE TESTS ==============

    def test_delete_metarial_unused(self):
        """Test deleting a metarial that is not referenced"""
        service = MetarialService()

        # Create metarial
        metarial = service.create_metarial(CreateMetarialDTO(name="To Delete Metarial"))
        metarial_id = metarial.id

        # Act
        result = service.delete_metarial(metarial_id)

        # Assert
        self.assertTrue(result)
        self.assertFalse(Metarial.select().where(Metarial.id == metarial_id).exists())

    def test_delete_metarial_with_batches_fails(self):
        """Test deleting a metarial with existing batches fails"""
        service = MetarialService()
        location = self._create_test_location("Test Delete Location")

        # Create metarial
        metarial = service.create_metarial(CreateMetarialDTO(name="Referenced Metarial"))

        # Create batch that references the metarial
        batch = MetarialBatch()
        batch.metarial = metarial
        batch.batch_number = "BATCH-001"
        batch.location = location
        batch.quantity = Decimal("100.0")
        batch.unit_type = UnitType.COUNT
        batch.save()

        # Act & Assert
        with self.assertRaises(BadRequestException) as context:
            service.delete_metarial(metarial.id)

        self.assertIn("Cannot delete", str(context.exception))
        self.assertIn("batches", str(context.exception).lower())

        # Verify metarial still exists
        self.assertTrue(Metarial.select().where(Metarial.id == metarial.id).exists())

        # Cleanup
        batch.delete_instance()
        metarial.delete_instance()
        location.delete_instance()

    def test_delete_metarial_not_found(self):
        """Test deleting a non-existent metarial raises NotFoundException"""
        service = MetarialService()

        # Act & Assert
        with self.assertRaises(Exception):  # NotFoundException
            service.delete_metarial("non-existent-id")

    # ============== AUDIT FIELD TESTS ==============

    def test_audit_fields_on_create(self):
        """Test that audit fields are set on create"""
        service = MetarialService()

        # Act
        metarial = service.create_metarial(CreateMetarialDTO(name="Audit Test Metarial"))

        # Assert
        self.assertIsNotNone(metarial.created_at)
        self.assertIsNotNone(metarial.last_modified_at)
        self.assertIsNotNone(metarial.created_by)
        self.assertIsNotNone(metarial.last_modified_by)

        # Cleanup
        metarial.delete_instance()

    def test_audit_fields_on_update(self):
        """Test that audit fields are updated on update"""
        service = MetarialService()

        # Create metarial
        metarial = service.create_metarial(CreateMetarialDTO(name="Audit Update Metarial"))
        original_created_by_id = metarial.created_by.id

        # Act: update metarial
        updated = service.update_metarial(
            metarial_id=metarial.id,
            dto=UpdateMetarialDTO(name="Audit Update Metarial Modified"),
        )

        # Assert: created_by unchanged, last_modified_by is set
        self.assertEqual(updated.created_by.id, original_created_by_id)
        self.assertIsNotNone(updated.last_modified_at)
        self.assertIsNotNone(updated.last_modified_by)

        # Cleanup
        metarial.delete_instance()
