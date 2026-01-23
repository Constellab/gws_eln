"""
Test suite for MaterialBatchService.

Tests Story 5.5 from Epic 5: Service Layer - Material Batches.

Tests cover:
- Create batch with valid material and location
- Create batch with default "labo" location
- Receive batch (increment quantity)
- List batches by material and location
- Validation errors for invalid data
- Activity logging for create and receive operations
"""

from datetime import date
from decimal import Decimal

from gws_core import BadRequestException, BaseTestCase, NotFoundException
from gws_eln.activities.activity import Activity
from gws_eln.activities.activity_type import ActivityType
from gws_eln.core.unit_type import UnitType
from gws_eln.locations.location import Location
from gws_eln.locations.location_dto import CreateLocationDTO
from gws_eln.locations.location_service import DEFAULT_LOCATION_NAME, LocationService
from gws_eln.materials.material import Material
from gws_eln.materials.material_batch import MaterialBatch
from gws_eln.materials.material_batch_dto import (
    CreateAliquotDTO,
    CreateBatchDTO,
    DecrementQuantityDTO,
    DeleteBatchResultDTO,
    MoveBatchDTO,
    ReceiveBatchDTO,
    RelabelBatchDTO,
    UpdateBatchDTO,
)
from gws_eln.materials.material_batch_service import MaterialBatchService
from gws_eln.materials.material_dto import CreateMaterialDTO
from gws_eln.materials.material_service import MaterialService
from gws_eln.user.eln_user_sync_service import ElnUserSyncService


class TestMaterialBatchService(BaseTestCase):
    """Test suite for MaterialBatchService"""

    @classmethod
    def init_before_test(cls):
        """Setup: sync users from gws_core to gws_eln before tests"""
        super().init_before_test()
        # Sync users so that the current user exists in gws_eln_user table
        sync_service = ElnUserSyncService()
        sync_service.sync_all_users()

    def _create_test_material(
        self,
        name: str = "Test Material",
        is_consumable: bool = True,
        unit_type: UnitType = UnitType.VOLUME,
    ) -> Material:
        """Helper to create a test material."""
        service = MaterialService()
        return service.create_material(
            CreateMaterialDTO(
                name=name,
                is_consumable=is_consumable,
                default_unit_type=unit_type,
            )
        )

    def _create_test_location(self, name: str = "Test Location") -> Location:
        """Helper to create a test location."""
        service = LocationService()
        return service.create_location(CreateLocationDTO(name=name))

    def _ensure_default_location(self) -> Location:
        """Helper to ensure the default labo location exists."""
        service = LocationService()
        return service.get_default_location()

    # ============== CREATE BATCH TESTS ==============

    def test_create_batch_with_valid_data(self):
        """Test creating a batch with valid material and location"""
        service = MaterialBatchService()
        material = self._create_test_material("Ethanol", True, UnitType.VOLUME)
        location = self._create_test_location("Cold Storage")

        # Act
        batch = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="BATCH-001",
                quantity=Decimal("1500"),
                unit="mL",  # 1500 mL = 1.5 L (base unit)
                location_id=location.id,
                expiry_date=date(2027, 12, 31),
                label="Ethanol Batch 1",
                notes="Initial stock received",
            )
        )

        # Assert
        self.assertIsNotNone(batch)
        self.assertIsNotNone(batch.id)
        self.assertEqual(batch.material.id, material.id)
        self.assertEqual(batch.batch_number, "BATCH-001")
        self.assertEqual(batch.quantity, Decimal("1.500000000000"))  # Stored in base unit (L)
        self.assertEqual(batch.unit_type, UnitType.VOLUME)
        self.assertEqual(batch.location.id, location.id)
        self.assertEqual(batch.expiry_date, date(2027, 12, 31))
        self.assertEqual(batch.label, "Ethanol Batch 1")
        self.assertEqual(batch.notes, "Initial stock received")
        self.assertIsNone(batch.parent_batch)  # Original batch
        self.assertTrue(batch.is_original_batch())
        self.assertFalse(batch.is_aliquot())
        self.assertIsNotNone(batch.created_at)
        self.assertIsNotNone(batch.created_by)

        # Verify in database
        db_batch = MaterialBatch.get_by_id(batch.id)
        self.assertEqual(db_batch.batch_number, "BATCH-001")

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()
        material.delete_instance()
        location.delete_instance()

    def test_create_batch_with_default_location(self):
        """Test creating a batch with default 'labo' location when none provided"""
        service = MaterialBatchService()
        material = self._create_test_material("Test Chemical", True, UnitType.MASS)
        default_location = self._ensure_default_location()

        # Act - no location_id provided
        batch = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="BATCH-DEFAULT",
                quantity=Decimal("500"),
                unit="g",  # grams (base unit for MASS)
            )
        )

        # Assert
        self.assertIsNotNone(batch)
        self.assertEqual(batch.location.name, DEFAULT_LOCATION_NAME)
        self.assertEqual(batch.location.id, default_location.id)

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()
        material.delete_instance()

    def test_create_batch_minimal_data(self):
        """Test creating a batch with only required fields"""
        service = MaterialBatchService()
        material = self._create_test_material("Minimal Material", unit_type=UnitType.COUNT)
        self._ensure_default_location()

        # Act
        batch = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="MIN-001",
                quantity=Decimal("10"),
                unit="units",
            )
        )

        # Assert
        self.assertIsNotNone(batch)
        self.assertEqual(batch.batch_number, "MIN-001")
        self.assertEqual(batch.quantity, Decimal("10"))
        self.assertIsNone(batch.expiry_date)
        self.assertIsNone(batch.label)
        self.assertIsNone(batch.notes)
        self.assertEqual(batch.location.name, DEFAULT_LOCATION_NAME)

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()
        material.delete_instance()

    def test_create_batch_trims_whitespace(self):
        """Test that batch number, label, and notes are trimmed"""
        service = MaterialBatchService()
        material = self._create_test_material("Trim Test Material", unit_type=UnitType.COUNT)
        self._ensure_default_location()

        # Act
        batch = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="  BATCH-TRIM  ",
                quantity=Decimal("1"),
                unit="units",
                label="  Trimmed Label  ",
                notes="  Trimmed Notes  ",
            )
        )

        # Assert
        self.assertEqual(batch.batch_number, "BATCH-TRIM")
        self.assertEqual(batch.label, "Trimmed Label")
        self.assertEqual(batch.notes, "Trimmed Notes")

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()
        material.delete_instance()

    def test_create_batch_creates_activity(self):
        """Test that creating a batch logs a 'receive' activity"""
        service = MaterialBatchService()
        material = self._create_test_material("Activity Test Material", unit_type=UnitType.COUNT)
        location = self._create_test_location("Activity Test Location")

        # Act
        batch = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="ACT-001",
                quantity=Decimal("100"),
                unit="units",
                location_id=location.id,
                notes="Test activity creation",
            )
        )

        # Assert - check activity was created
        activities = Activity.find_by_batch_id(batch.id)
        self.assertEqual(len(activities), 1)

        activity = activities[0]
        self.assertEqual(activity.activity_type, ActivityType.RECEIVE)
        self.assertEqual(activity.batch.id, batch.id)
        self.assertEqual(activity.quantity, Decimal("100"))
        self.assertEqual(activity.unit_type, UnitType.COUNT)
        self.assertEqual(activity.notes, "Test activity creation")

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()
        material.delete_instance()
        location.delete_instance()

    # ============== CREATE BATCH VALIDATION TESTS ==============

    def test_create_batch_invalid_material_fails(self):
        """Test creating a batch with non-existent material fails"""
        service = MaterialBatchService()
        self._ensure_default_location()

        # Act & Assert
        with self.assertRaises(BadRequestException) as context:
            service.create_batch(
                CreateBatchDTO(
                    material_id="non-existent-id",
                    batch_number="BATCH-FAIL",
                    quantity=Decimal("1"),
                    unit="units",
                )
            )

        self.assertIn("does not exist", str(context.exception))

    def test_create_batch_invalid_location_fails(self):
        """Test creating a batch with non-existent location fails"""
        service = MaterialBatchService()
        material = self._create_test_material("Location Fail Material", unit_type=UnitType.COUNT)

        # Act & Assert
        with self.assertRaises(BadRequestException) as context:
            service.create_batch(
                CreateBatchDTO(
                    material_id=material.id,
                    batch_number="BATCH-FAIL",
                    quantity=Decimal("1"),
                    unit="units",
                    location_id="non-existent-location-id",
                )
            )

        self.assertIn("does not exist", str(context.exception))

        # Cleanup
        material.delete_instance()

    def test_create_batch_empty_batch_number_fails(self):
        """Test creating a batch with empty batch number fails"""
        service = MaterialBatchService()
        material = self._create_test_material(
            "Empty Batch Number Material", unit_type=UnitType.COUNT
        )
        self._ensure_default_location()

        # Act & Assert
        with self.assertRaises(BadRequestException) as context:
            service.create_batch(
                CreateBatchDTO(
                    material_id=material.id,
                    batch_number="",
                    quantity=Decimal("1"),
                    unit="units",
                )
            )

        self.assertIn("Batch number is required", str(context.exception))

        # Cleanup
        material.delete_instance()

    def test_create_batch_whitespace_batch_number_fails(self):
        """Test creating a batch with whitespace-only batch number fails"""
        service = MaterialBatchService()
        material = self._create_test_material(
            "Whitespace Batch Number Material", unit_type=UnitType.COUNT
        )
        self._ensure_default_location()

        # Act & Assert
        with self.assertRaises(BadRequestException) as context:
            service.create_batch(
                CreateBatchDTO(
                    material_id=material.id,
                    batch_number="   ",
                    quantity=Decimal("1"),
                    unit="units",
                )
            )

        self.assertIn("Batch number is required", str(context.exception))

        # Cleanup
        material.delete_instance()

    def test_create_batch_negative_quantity_fails(self):
        """Test creating a batch with negative quantity fails"""
        service = MaterialBatchService()
        material = self._create_test_material(
            "Negative Quantity Material", unit_type=UnitType.COUNT
        )
        self._ensure_default_location()

        # Act & Assert
        with self.assertRaises(BadRequestException) as context:
            service.create_batch(
                CreateBatchDTO(
                    material_id=material.id,
                    batch_number="NEG-001",
                    quantity=Decimal("-10"),
                    unit="units",
                )
            )

        self.assertIn("positive", str(context.exception).lower())

        # Cleanup
        material.delete_instance()

    def test_create_batch_zero_quantity_fails(self):
        """Test creating a batch with zero quantity fails"""
        service = MaterialBatchService()
        material = self._create_test_material("Zero Quantity Material", unit_type=UnitType.COUNT)
        self._ensure_default_location()

        # Act & Assert
        with self.assertRaises(BadRequestException) as context:
            service.create_batch(
                CreateBatchDTO(
                    material_id=material.id,
                    batch_number="ZERO-001",
                    quantity=Decimal("0"),
                    unit="units",
                )
            )

        self.assertIn("positive", str(context.exception).lower())

        # Cleanup
        material.delete_instance()

    # ============== RECEIVE BATCH TESTS ==============

    def test_receive_batch_increments_quantity(self):
        """Test receiving stock increments batch quantity"""
        service = MaterialBatchService()
        material = self._create_test_material("Receive Test Material", True, UnitType.VOLUME)
        self._ensure_default_location()

        # Create initial batch (100 L)
        batch = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="RCV-001",
                quantity=Decimal("100"),
                unit="L",
            )
        )
        original_quantity = batch.quantity

        # Act - receive additional stock (50 L)
        updated_batch = service.receive_batch(
            batch_id=batch.id,
            dto=ReceiveBatchDTO(
                quantity=Decimal("50"),
                unit="L",
                notes="Additional stock received",
            ),
        )

        # Assert
        self.assertEqual(updated_batch.id, batch.id)
        self.assertEqual(updated_batch.quantity, Decimal("150"))  # 100 + 50
        self.assertEqual(updated_batch.quantity, original_quantity + Decimal("50"))

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()
        material.delete_instance()

    def test_receive_batch_creates_activity(self):
        """Test receiving stock logs a 'receive' activity"""
        service = MaterialBatchService()
        material = self._create_test_material("Receive Activity Material", True, UnitType.MASS)
        location = self._create_test_location("Receive Activity Location")

        # Create initial batch (200 g)
        batch = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="RCV-ACT",
                quantity=Decimal("200"),
                unit="g",
                location_id=location.id,
            )
        )

        # Clear initial activity
        initial_activities_count = Activity.count_by_batch_id(batch.id)

        # Act - receive additional stock
        service.receive_batch(
            batch_id=batch.id,
            dto=ReceiveBatchDTO(
                quantity=Decimal("100"),
                unit="g",
                notes="Receive activity test",
            ),
        )

        # Assert - check new activity was created
        activities = Activity.find_by_batch_id(batch.id)
        self.assertEqual(len(activities), initial_activities_count + 1)

        # Find the receive activity with the specific notes
        receive_activities = [a for a in activities if a.notes == "Receive activity test"]
        self.assertEqual(len(receive_activities), 1)

        receive_activity = receive_activities[0]
        self.assertEqual(receive_activity.activity_type, ActivityType.RECEIVE)
        self.assertEqual(receive_activity.quantity, Decimal("100"))
        self.assertEqual(receive_activity.unit_type, UnitType.MASS)

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()
        material.delete_instance()
        location.delete_instance()

    def test_receive_batch_multiple_times(self):
        """Test receiving stock multiple times accumulates quantity"""
        service = MaterialBatchService()
        material = self._create_test_material("Multi Receive Material", True, UnitType.COUNT)
        self._ensure_default_location()

        # Create initial batch
        batch = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="MULTI-RCV",
                quantity=Decimal("100"),
                unit="units",
            )
        )

        # Act - receive multiple times
        service.receive_batch(
            batch.id,
            ReceiveBatchDTO(
                quantity=Decimal("25"),
                unit="units",
            ),
        )
        service.receive_batch(
            batch.id,
            ReceiveBatchDTO(
                quantity=Decimal("50"),
                unit="units",
            ),
        )
        updated_batch = service.receive_batch(
            batch.id,
            ReceiveBatchDTO(
                quantity=Decimal("75"),
                unit="units",
            ),
        )

        # Assert
        self.assertEqual(updated_batch.quantity, Decimal("250"))  # 100 + 25 + 50 + 75

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()
        material.delete_instance()

    def test_receive_batch_invalid_unit_fails(self):
        """Test receiving stock with invalid unit for batch's unit type fails"""
        service = MaterialBatchService()
        material = self._create_test_material("Unit Mismatch Material", True, UnitType.VOLUME)
        self._ensure_default_location()

        # Create batch with VOLUME unit type
        batch = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="UNIT-MIS",
                quantity=Decimal("100"),
                unit="L",
            )
        )

        # Act & Assert - try to receive with mass unit (invalid for volume batch)
        with self.assertRaises(BadRequestException) as context:
            service.receive_batch(
                batch.id,
                ReceiveBatchDTO(
                    quantity=Decimal("50"),
                    unit="g",  # Invalid: mass unit for volume batch
                ),
            )

        self.assertIn("Invalid unit 'g'", str(context.exception))

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()
        material.delete_instance()

    def test_receive_batch_negative_quantity_fails(self):
        """Test receiving with negative quantity fails"""
        service = MaterialBatchService()
        material = self._create_test_material("Negative Receive Material", True, UnitType.COUNT)
        self._ensure_default_location()

        # Create batch
        batch = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="NEG-RCV",
                quantity=Decimal("100"),
                unit="units",
            )
        )

        # Act & Assert
        with self.assertRaises(BadRequestException) as context:
            service.receive_batch(
                batch.id,
                ReceiveBatchDTO(
                    quantity=Decimal("-50"),
                    unit="units",
                ),
            )

        self.assertIn("positive", str(context.exception).lower())

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()
        material.delete_instance()

    def test_receive_batch_not_found_fails(self):
        """Test receiving stock for non-existent batch fails"""
        service = MaterialBatchService()

        # Act & Assert
        with self.assertRaises(Exception):  # NotFoundException
            service.receive_batch(
                "non-existent-id",
                ReceiveBatchDTO(
                    quantity=Decimal("100"),
                    unit="units",
                ),
            )

    # ============== LIST BATCHES TESTS ==============

    def test_list_batches(self):
        """Test listing all batches"""
        service = MaterialBatchService()
        material = self._create_test_material("List Test Material", unit_type=UnitType.COUNT)
        self._ensure_default_location()

        # Create multiple batches
        batch1 = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="LIST-001",
                quantity=Decimal("10"),
                unit="units",
            )
        )
        batch2 = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="LIST-002",
                quantity=Decimal("20"),
                unit="units",
            )
        )

        # Act
        batches = service.list_batches()

        # Assert - at least our 2 batches
        batch_numbers = [b.batch_number for b in batches]
        self.assertIn("LIST-001", batch_numbers)
        self.assertIn("LIST-002", batch_numbers)

        # Cleanup
        Activity.delete().where(Activity.batch == batch1).execute()
        Activity.delete().where(Activity.batch == batch2).execute()
        batch1.delete_instance()
        batch2.delete_instance()
        material.delete_instance()

    def test_list_batches_by_material(self):
        """Test listing batches filtered by material"""
        service = MaterialBatchService()
        material1 = self._create_test_material("Filter Material 1", unit_type=UnitType.COUNT)
        material2 = self._create_test_material("Filter Material 2", unit_type=UnitType.COUNT)
        self._ensure_default_location()

        # Create batches for different materials
        batch1 = service.create_batch(
            CreateBatchDTO(
                material_id=material1.id,
                batch_number="FILT-M1",
                quantity=Decimal("10"),
                unit="units",
            )
        )
        batch2 = service.create_batch(
            CreateBatchDTO(
                material_id=material2.id,
                batch_number="FILT-M2",
                quantity=Decimal("20"),
                unit="units",
            )
        )

        # Act - filter by material1
        batches = service.list_batches(material_id=material1.id)

        # Assert
        batch_numbers = [b.batch_number for b in batches]
        self.assertIn("FILT-M1", batch_numbers)
        self.assertNotIn("FILT-M2", batch_numbers)

        # Cleanup
        Activity.delete().where(Activity.batch == batch1).execute()
        Activity.delete().where(Activity.batch == batch2).execute()
        batch1.delete_instance()
        batch2.delete_instance()
        material1.delete_instance()
        material2.delete_instance()

    def test_list_batches_by_location(self):
        """Test listing batches filtered by location"""
        service = MaterialBatchService()
        material = self._create_test_material("Location Filter Material", unit_type=UnitType.COUNT)
        location1 = self._create_test_location("Filter Location 1")
        location2 = self._create_test_location("Filter Location 2")

        # Create batches in different locations
        batch1 = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="FILT-L1",
                quantity=Decimal("10"),
                unit="units",
                location_id=location1.id,
            )
        )
        batch2 = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="FILT-L2",
                quantity=Decimal("20"),
                unit="units",
                location_id=location2.id,
            )
        )

        # Act - filter by location1
        batches = service.list_batches(location_id=location1.id)

        # Assert
        batch_numbers = [b.batch_number for b in batches]
        self.assertIn("FILT-L1", batch_numbers)
        self.assertNotIn("FILT-L2", batch_numbers)

        # Cleanup
        Activity.delete().where(Activity.batch == batch1).execute()
        Activity.delete().where(Activity.batch == batch2).execute()
        batch1.delete_instance()
        batch2.delete_instance()
        material.delete_instance()
        location1.delete_instance()
        location2.delete_instance()

    # ============== GET BATCH TESTS ==============

    def test_get_batch(self):
        """Test getting a batch by ID"""
        service = MaterialBatchService()
        material = self._create_test_material("Get Test Material", unit_type=UnitType.COUNT)
        self._ensure_default_location()

        # Create batch
        batch = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="GET-001",
                quantity=Decimal("100"),
                unit="units",
            )
        )

        # Act
        retrieved = service.get_batch(batch.id)

        # Assert
        self.assertEqual(retrieved.id, batch.id)
        self.assertEqual(retrieved.batch_number, "GET-001")
        self.assertEqual(retrieved.quantity, Decimal("100"))

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()
        material.delete_instance()

    def test_get_batch_not_found(self):
        """Test getting a non-existent batch raises NotFoundException"""
        service = MaterialBatchService()

        # Act & Assert
        with self.assertRaises(Exception):  # NotFoundException
            service.get_batch("non-existent-id")

    # ============== AUDIT FIELD TESTS ==============

    def test_audit_fields_on_create(self):
        """Test that audit fields are set on batch creation"""
        service = MaterialBatchService()
        material = self._create_test_material("Audit Create Material", unit_type=UnitType.COUNT)
        self._ensure_default_location()

        # Act
        batch = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="AUDIT-001",
                quantity=Decimal("10"),
                unit="units",
            )
        )

        # Assert
        self.assertIsNotNone(batch.created_at)
        self.assertIsNotNone(batch.last_modified_at)
        self.assertIsNotNone(batch.created_by)
        self.assertIsNotNone(batch.last_modified_by)

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()
        material.delete_instance()

    def test_audit_fields_on_receive(self):
        """Test that audit fields are updated on receive"""
        service = MaterialBatchService()
        material = self._create_test_material("Audit Receive Material", unit_type=UnitType.COUNT)
        self._ensure_default_location()

        # Create batch
        batch = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="AUDIT-RCV",
                quantity=Decimal("100"),
                unit="units",
            )
        )
        original_created_at = batch.created_at

        # Act
        updated = service.receive_batch(
            batch.id,
            ReceiveBatchDTO(
                quantity=Decimal("50"),
                unit="units",
            ),
        )

        # Assert - created_by should remain unchanged
        self.assertEqual(updated.created_by.id, batch.created_by.id)
        self.assertIsNotNone(updated.last_modified_at)
        self.assertIsNotNone(updated.last_modified_by)

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()
        material.delete_instance()

    # ============== ALL UNIT TYPES TESTS ==============

    def test_create_batch_all_unit_types(self):
        """Test creating batches with all unit types"""
        from gws_eln.utils.units_converter import UnitConverter

        service = MaterialBatchService()
        self._ensure_default_location()
        batches = []
        materials = []

        for unit_type in UnitType:
            material = self._create_test_material(
                f"Test {unit_type.value} Material",
                is_consumable=True,
                unit_type=unit_type,
            )
            materials.append(material)

            # Get default unit for this unit type
            unit = UnitConverter.get_default_unit(unit_type)

            batch = service.create_batch(
                CreateBatchDTO(
                    material_id=material.id,
                    batch_number=f"UNIT-{unit_type.value.upper()}",
                    quantity=Decimal("10"),
                    unit=unit,
                )
            )
            batches.append(batch)

            self.assertEqual(batch.unit_type, unit_type)

        # Cleanup
        for batch in batches:
            Activity.delete().where(Activity.batch == batch).execute()
            batch.delete_instance()
        for material in materials:
            material.delete_instance()

    def test_create_batch_converts_unit_to_base(self):
        """Test that creating a batch converts the quantity from the given unit to base unit"""
        service = MaterialBatchService()
        self._ensure_default_location()

        # Create material with VOLUME unit type (base unit = L)
        material = self._create_test_material("Volume Conversion Material", True, UnitType.VOLUME)

        # Act - create batch with 500 mL (should be stored as 0.5 L)
        batch = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="CONV-001",
                quantity=Decimal("500"),
                unit="mL",  # Input in milliliters
            )
        )

        # Assert - quantity should be stored in base unit (L)
        self.assertEqual(batch.quantity, Decimal("0.500000000000"))  # 500 mL = 0.5 L
        self.assertEqual(batch.unit_type, UnitType.VOLUME)

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()
        material.delete_instance()

    def test_create_batch_invalid_unit_for_material_fails(self):
        """Test that creating a batch with an invalid unit for the material's unit type fails"""
        service = MaterialBatchService()
        self._ensure_default_location()

        # Create material with VOLUME unit type
        material = self._create_test_material("Volume Only Material", True, UnitType.VOLUME)

        # Act & Assert - try to create batch with mass unit (g) for volume material
        with self.assertRaises(BadRequestException) as context:
            service.create_batch(
                CreateBatchDTO(
                    material_id=material.id,
                    batch_number="INV-UNIT",
                    quantity=Decimal("100"),
                    unit="g",  # Invalid: mass unit for volume material
                )
            )

        self.assertIn("Invalid unit 'g'", str(context.exception))
        self.assertIn("volume", str(context.exception).lower())

        # Cleanup
        material.delete_instance()

    # ============== DECREMENT QUANTITY TESTS (Story 5.2) ==============

    def test_decrement_quantity_consumable(self):
        """Test decrementing consumable batch quantity"""
        service = MaterialBatchService()
        material = self._create_test_material("Dec Consumable Material", True, UnitType.VOLUME)
        self._ensure_default_location()

        # Create initial batch (100 L)
        batch = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="DEC-001",
                quantity=Decimal("100"),
                unit="L",
            )
        )

        # Act - decrement quantity
        updated_batch = service.consume_quantity(
            batch_id=batch.id,
            dto=DecrementQuantityDTO(
                quantity=Decimal("30"),
                unit="L",
                notes="Used in experiment",
            ),
        )

        # Assert
        self.assertEqual(updated_batch.id, batch.id)
        self.assertEqual(updated_batch.quantity, Decimal("70"))  # 100 - 30

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()
        material.delete_instance()

    def test_decrement_quantity_creates_consume_activity(self):
        """Test that decrementing quantity logs a 'consume' activity"""
        service = MaterialBatchService()
        material = self._create_test_material("Dec Activity Material", True, UnitType.COUNT)
        self._ensure_default_location()

        # Create initial batch
        batch = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="DEC-ACT",
                quantity=Decimal("100"),
                unit="units",
            )
        )
        initial_activity_count = Activity.count_by_batch_id(batch.id)

        # Act - decrement quantity
        service.consume_quantity(
            batch_id=batch.id,
            dto=DecrementQuantityDTO(
                quantity=Decimal("25"),
                unit="units",
                notes="Test decrement note",
            ),
        )

        # Assert - new activity created
        activities = Activity.find_by_batch_id(batch.id)
        self.assertEqual(len(activities), initial_activity_count + 1)

        # Find the consume activity by notes
        consume_activities = [a for a in activities if a.notes == "Test decrement note"]
        self.assertEqual(len(consume_activities), 1)
        self.assertEqual(consume_activities[0].activity_type, ActivityType.CONSUME)
        self.assertEqual(consume_activities[0].quantity, Decimal("25"))

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()
        material.delete_instance()

    def test_decrement_quantity_non_consumable_fails(self):
        """Test decrementing non-consumable batch fails"""
        service = MaterialBatchService()
        material = self._create_test_material("Non-Consumable Material", False, UnitType.COUNT)
        self._ensure_default_location()

        # Create batch for non-consumable material
        batch = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="DEC-NONCON",
                quantity=Decimal("10"),
                unit="units",
            )
        )

        # Act & Assert - try to decrement non-consumable
        with self.assertRaises(BadRequestException) as context:
            service.consume_quantity(
                batch.id,
                DecrementQuantityDTO(
                    quantity=Decimal("5"),
                    unit="units",
                    notes="Should fail",
                ),
            )

        self.assertIn("non-consumable", str(context.exception).lower())

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()
        material.delete_instance()

    def test_decrement_quantity_below_zero_fails(self):
        """Test decrementing below zero fails"""
        service = MaterialBatchService()
        material = self._create_test_material("Dec Below Zero Material", True, UnitType.COUNT)
        self._ensure_default_location()

        # Create batch with limited quantity
        batch = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="DEC-ZERO",
                quantity=Decimal("50"),
                unit="units",
            )
        )

        # Act & Assert - try to decrement more than available
        with self.assertRaises(BadRequestException) as context:
            service.consume_quantity(
                batch.id,
                DecrementQuantityDTO(
                    quantity=Decimal("100"),  # More than available (50)
                    unit="units",
                    notes="Should fail",
                ),
            )

        self.assertIn("Insufficient quantity", str(context.exception))

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()
        material.delete_instance()

    def test_decrement_quantity_invalid_unit_fails(self):
        """Test decrementing with invalid unit for batch's unit type fails"""
        service = MaterialBatchService()
        material = self._create_test_material("Dec Mismatch Material", True, UnitType.VOLUME)
        self._ensure_default_location()

        batch = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="DEC-MIS",
                quantity=Decimal("100"),
                unit="L",
            )
        )

        # Act & Assert - try to decrement with mass unit (invalid for volume batch)
        with self.assertRaises(BadRequestException) as context:
            service.consume_quantity(
                batch.id,
                DecrementQuantityDTO(
                    quantity=Decimal("50"),
                    unit="g",  # Invalid: mass unit for volume batch
                    notes="Should fail",
                ),
            )

        self.assertIn("Invalid unit 'g'", str(context.exception))

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()
        material.delete_instance()

    def test_decrement_quantity_to_zero(self):
        """Test decrementing to exactly zero succeeds"""
        service = MaterialBatchService()
        material = self._create_test_material("Dec To Zero Material", True, UnitType.COUNT)
        self._ensure_default_location()

        batch = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="DEC-TOZERO",
                quantity=Decimal("100"),
                unit="units",
            )
        )

        # Act - decrement to exactly zero
        updated_batch = service.consume_quantity(
            batch.id,
            DecrementQuantityDTO(
                quantity=Decimal("100"),
                unit="units",
                notes="Used all stock",
            ),
        )

        # Assert
        self.assertEqual(updated_batch.quantity, Decimal("0"))

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()
        material.delete_instance()

    def test_decrement_multiple_times(self):
        """Test decrementing multiple times accumulates correctly"""
        service = MaterialBatchService()
        material = self._create_test_material("Multi Dec Material", True, UnitType.COUNT)
        self._ensure_default_location()

        batch = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="DEC-MULTI",
                quantity=Decimal("100"),
                unit="units",
            )
        )

        # Act - decrement multiple times
        service.consume_quantity(
            batch.id,
            DecrementQuantityDTO(
                quantity=Decimal("20"),
                unit="units",
                notes="First use",
            ),
        )
        service.consume_quantity(
            batch.id,
            DecrementQuantityDTO(
                quantity=Decimal("30"),
                unit="units",
                notes="Second use",
            ),
        )
        updated_batch = service.consume_quantity(
            batch.id,
            DecrementQuantityDTO(
                quantity=Decimal("10"),
                unit="units",
                notes="Third use",
            ),
        )

        # Assert: 100 - 20 - 30 - 10 = 40
        self.assertEqual(updated_batch.quantity, Decimal("40"))

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()
        material.delete_instance()

    def test_decrement_quantity_without_notes(self):
        """Test decrementing quantity without notes (notes is optional)"""
        service = MaterialBatchService()
        material = self._create_test_material("Dec No Notes Material", True, UnitType.COUNT)
        self._ensure_default_location()

        batch = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="DEC-NONOTES",
                quantity=Decimal("100"),
                unit="units",
            )
        )

        # Act - decrement without notes
        updated_batch = service.consume_quantity(
            batch.id,
            DecrementQuantityDTO(
                quantity=Decimal("25"),
                unit="units",
                # notes is optional, not provided
            ),
        )

        # Assert
        self.assertEqual(updated_batch.quantity, Decimal("75"))  # 100 - 25

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()
        material.delete_instance()

    # ============== MOVE BATCH TESTS (Story 5.3) ==============

    def test_move_batch(self):
        """Test moving a batch to a different location"""
        service = MaterialBatchService()
        material = self._create_test_material("Move Test Material", True, UnitType.COUNT)
        location1 = self._create_test_location("Location A")
        location2 = self._create_test_location("Location B")

        # Create batch at location1
        batch = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="MOVE-001",
                quantity=Decimal("100"),
                unit="units",
                location_id=location1.id,
            )
        )
        self.assertEqual(batch.location.id, location1.id)

        # Act - move to location2
        updated_batch = service.move_batch(
            batch_id=batch.id,
            dto=MoveBatchDTO(to_location_id=location2.id),
        )

        # Assert
        self.assertEqual(updated_batch.id, batch.id)
        self.assertEqual(updated_batch.location.id, location2.id)

        # Verify in database
        db_batch = MaterialBatch.get_by_id(batch.id)
        self.assertEqual(db_batch.location.id, location2.id)

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()
        material.delete_instance()
        location1.delete_instance()
        location2.delete_instance()

    def test_move_batch_creates_activity(self):
        """Test that moving a batch logs a 'move' activity"""
        service = MaterialBatchService()
        material = self._create_test_material("Move Activity Material", True, UnitType.COUNT)
        location1 = self._create_test_location("Move From Location")
        location2 = self._create_test_location("Move To Location")

        # Create batch at location1
        batch = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="MOVE-ACT",
                quantity=Decimal("100"),
                unit="units",
                location_id=location1.id,
            )
        )
        initial_activity_count = Activity.count_by_batch_id(batch.id)

        # Act - move to location2
        service.move_batch(
            batch_id=batch.id,
            dto=MoveBatchDTO(to_location_id=location2.id),
        )

        # Assert - new activity created
        activity_count = Activity.count_by_batch_id(batch.id)
        self.assertEqual(activity_count, initial_activity_count + 1)

        # Find the move activity by type - select specific columns to avoid NULL enum issue
        move_activity = (
            Activity.select(
                Activity.id,
                Activity.activity_type,
                Activity.from_location,
                Activity.to_location,
            )
            .where(Activity.batch == batch)
            .where(Activity.activity_type == ActivityType.MOVE)
            .first()
        )
        self.assertIsNotNone(move_activity)
        self.assertEqual(move_activity.from_location.id, location1.id)
        self.assertEqual(move_activity.to_location.id, location2.id)

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()
        material.delete_instance()
        location1.delete_instance()
        location2.delete_instance()

    def test_move_batch_invalid_location_fails(self):
        """Test moving a batch to non-existent location fails"""
        service = MaterialBatchService()
        material = self._create_test_material("Move Invalid Material", True, UnitType.COUNT)
        location = self._create_test_location("Move Valid Location")

        batch = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="MOVE-INV",
                quantity=Decimal("100"),
                unit="units",
                location_id=location.id,
            )
        )

        # Act & Assert - try to move to non-existent location
        with self.assertRaises(NotFoundException) as context:
            service.move_batch(
                batch.id,
                MoveBatchDTO(
                    to_location_id="non-existent-location-id",
                ),
            )

        self.assertIn("Location with id", str(context.exception))

        # Verify batch location unchanged
        db_batch = MaterialBatch.get_by_id(batch.id)
        self.assertEqual(db_batch.location.id, location.id)

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()
        material.delete_instance()
        location.delete_instance()

    def test_move_batch_to_same_location(self):
        """Test moving a batch to its current location succeeds (no-op)"""
        service = MaterialBatchService()
        material = self._create_test_material("Move Same Material", True, UnitType.COUNT)
        location = self._create_test_location("Same Location")

        batch = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="MOVE-SAME",
                quantity=Decimal("100"),
                unit="units",
                location_id=location.id,
            )
        )

        # Act - move to same location
        updated_batch = service.move_batch(
            batch_id=batch.id,
            dto=MoveBatchDTO(to_location_id=location.id),
        )

        # Assert - location unchanged (still valid)
        self.assertEqual(updated_batch.location.id, location.id)

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()
        material.delete_instance()
        location.delete_instance()

    def test_move_batch_not_found_fails(self):
        """Test moving a non-existent batch fails"""
        service = MaterialBatchService()
        location = self._create_test_location("Move Target Location")

        # Act & Assert
        with self.assertRaises(Exception):  # NotFoundException
            service.move_batch(
                "non-existent-batch-id",
                MoveBatchDTO(
                    to_location_id=location.id,
                ),
            )

        # Cleanup
        location.delete_instance()

    # ============== UPDATE BATCH TESTS (Story 5.4) ==============

    def test_update_batch_label(self):
        """Test updating batch label"""
        service = MaterialBatchService()
        material = self._create_test_material("Update Label Material", True, UnitType.COUNT)
        self._ensure_default_location()

        batch = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="UPD-LBL",
                quantity=Decimal("100"),
                unit="units",
                label="Original Label",
            )
        )
        self.assertEqual(batch.label, "Original Label")

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()
        material.delete_instance()

    def test_update_batch_notes(self):
        """Test updating batch notes"""
        service = MaterialBatchService()
        material = self._create_test_material("Update Notes Material", True, UnitType.COUNT)
        self._ensure_default_location()

        batch = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="UPD-NOTES",
                quantity=Decimal("100"),
                unit="units",
                notes="Original notes",
            )
        )

        # Act - update notes
        updated_batch = service.update_batch(
            batch_id=batch.id,
            dto=UpdateBatchDTO(notes="Updated notes"),
        )

        # Assert
        self.assertEqual(updated_batch.notes, "Updated notes")

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()
        material.delete_instance()

    def test_update_batch_expiry_date(self):
        """Test updating batch expiry date"""
        service = MaterialBatchService()
        material = self._create_test_material("Update Expiry Material", True, UnitType.COUNT)
        self._ensure_default_location()

        batch = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="UPD-EXP",
                quantity=Decimal("100"),
                unit="units",
                expiry_date=date(2027, 1, 1),
            )
        )

        # Act - update expiry date
        updated_batch = service.update_batch(
            batch_id=batch.id,
            dto=UpdateBatchDTO(expiry_date=date(2028, 12, 31)),
        )

        # Assert
        self.assertEqual(updated_batch.expiry_date, date(2028, 12, 31))

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()
        material.delete_instance()

    def test_update_batch_multiple_fields(self):
        """Test updating multiple batch fields at once"""
        service = MaterialBatchService()
        material = self._create_test_material("Multi Update Material", True, UnitType.COUNT)
        self._ensure_default_location()

        batch = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="MULTI-UPD",
                quantity=Decimal("100"),
                unit="units",
                label="Old Label",
                notes="Old Notes",
                expiry_date=date(2027, 1, 1),
            )
        )

        # Act - update multiple fields (note: batch_number is NOT updatable via update_batch)
        updated_batch = service.update_batch(
            batch_id=batch.id,
            dto=UpdateBatchDTO(
                notes="New Notes",
                expiry_date=date(2030, 6, 15),
            ),
        )

        # Assert - batch_number unchanged, other fields updated
        self.assertEqual(updated_batch.batch_number, "MULTI-UPD")  # Unchanged
        self.assertEqual(updated_batch.notes, "New Notes")
        self.assertEqual(updated_batch.expiry_date, date(2030, 6, 15))

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()
        material.delete_instance()

    # ============== DELETE BATCH TESTS (Story 5.4) ==============

    def test_delete_batch_hard_delete_only_creation_activity(self):
        """Test deleting a batch with only creation activity results in hard delete"""
        service = MaterialBatchService()
        material = self._create_test_material("Hard Delete Material", True, UnitType.COUNT)
        self._ensure_default_location()

        batch = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="HARD-DEL",
                quantity=Decimal("100"),
                unit="units",
            )
        )
        batch_id = batch.id

        # Verify only 1 activity (creation receive)
        activity_count = Activity.count_by_batch_id(batch.id)
        self.assertEqual(activity_count, 1)

        # Act
        result = service.delete_batch(batch_id, notes="Test deletion")

        # Assert - hard deleted
        self.assertEqual(result, DeleteBatchResultDTO.DELETED)
        self.assertFalse(MaterialBatch.select().where(MaterialBatch.id == batch_id).exists())
        # Activities should also be deleted
        self.assertEqual(Activity.count_by_batch_id(batch_id), 0)

        # Cleanup
        material.delete_instance()

    def test_delete_batch_soft_delete_with_usage_history(self):
        """Test deleting a batch with usage history results in soft delete (discard)"""
        service = MaterialBatchService()
        material = self._create_test_material("Soft Delete Material", True, UnitType.COUNT)
        self._ensure_default_location()

        batch = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="SOFT-DEL",
                quantity=Decimal("100"),
                unit="units",
            )
        )
        batch_id = batch.id

        # Add additional activity (receive more stock)
        service.receive_batch(
            batch_id,
            ReceiveBatchDTO(quantity=Decimal("50"), unit="units"),
        )

        # Verify more than 1 activity
        activity_count = Activity.count_by_batch_id(batch.id)
        self.assertGreater(activity_count, 1)

        # Act
        result = service.delete_batch(batch_id, notes="Expired stock")

        # Assert - soft deleted (discarded)
        self.assertEqual(result, DeleteBatchResultDTO.DISCARDED)

        # Batch still exists but is discarded
        db_batch = MaterialBatch.get_by_id(batch_id)
        self.assertIsNotNone(db_batch)
        self.assertTrue(db_batch.is_discarded())

        # Activities are preserved including the discard activity
        activities = Activity.find_by_batch_id(batch_id)
        self.assertGreater(len(activities), activity_count)  # Discard activity added

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        db_batch.delete_instance()
        material.delete_instance()

    def test_delete_batch_discarded_not_in_list(self):
        """Test that discarded batches are not returned by list_batches by default"""
        service = MaterialBatchService()
        material = self._create_test_material("List Filter Material", True, UnitType.COUNT)
        self._ensure_default_location()

        # Create batch and add activity
        batch = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="LIST-FILTER",
                quantity=Decimal("100"),
                unit="units",
            )
        )
        batch_id = batch.id

        # Add activity to ensure soft delete
        service.receive_batch(
            batch_id,
            ReceiveBatchDTO(quantity=Decimal("50"), unit="units"),
        )

        # Verify batch is in list
        batches_before = service.list_batches(material_id=material.id)
        batch_ids_before = [b.id for b in batches_before]
        self.assertIn(batch_id, batch_ids_before)

        # Discard the batch
        service.delete_batch(batch_id, notes="Test")

        # Verify batch is NOT in default list
        batches_after = service.list_batches(material_id=material.id)
        batch_ids_after = [b.id for b in batches_after]
        self.assertNotIn(batch_id, batch_ids_after)

        # Verify batch IS in list when include_discarded=True
        batches_with_discarded = service.list_batches(
            material_id=material.id, include_discarded=True
        )
        batch_ids_with_discarded = [b.id for b in batches_with_discarded]
        self.assertIn(batch_id, batch_ids_with_discarded)

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        MaterialBatch.get_by_id(batch_id).delete_instance()
        material.delete_instance()

    def test_delete_batch_already_discarded_fails(self):
        """Test deleting an already discarded batch fails"""
        service = MaterialBatchService()
        material = self._create_test_material("Already Discarded Material", True, UnitType.COUNT)
        self._ensure_default_location()

        batch = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="ALREADY-DISC",
                quantity=Decimal("100"),
                unit="units",
            )
        )
        batch_id = batch.id

        # Add activity to ensure soft delete
        service.receive_batch(
            batch_id,
            ReceiveBatchDTO(quantity=Decimal("50"), unit="units"),
        )

        # Discard the batch
        service.delete_batch(batch_id, notes="First discard")

        # Act & Assert - try to delete again
        with self.assertRaises(BadRequestException) as context:
            service.delete_batch(batch_id, notes="Second discard")

        self.assertIn("already discarded", str(context.exception).lower())

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        MaterialBatch.get_by_id(batch_id).delete_instance()
        material.delete_instance()

    def test_delete_batch_with_children_fails(self):
        """Test deleting a batch with active child batches fails"""
        service = MaterialBatchService()
        material = self._create_test_material("Parent Batch Material", True, UnitType.COUNT)
        location = self._create_test_location("Parent Batch Location")

        # Create parent batch
        parent_batch = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="PARENT-001",
                quantity=Decimal("100"),
                unit="units",
                location_id=location.id,
            )
        )

        # Create child batch (aliquot) manually
        child_batch = MaterialBatch()
        child_batch.material = material
        child_batch.batch_number = "CHILD-001"
        child_batch.quantity = Decimal("20")
        child_batch.unit_type = UnitType.COUNT
        child_batch.location = location
        child_batch.parent_batch = parent_batch
        child_batch.save()

        # Act & Assert - try to delete parent
        with self.assertRaises(BadRequestException) as context:
            service.delete_batch(parent_batch.id)

        self.assertIn("child batch", str(context.exception).lower())
        self.assertIn("1", str(context.exception))  # Should mention count of children

        # Verify parent batch still exists and is active
        db_parent = MaterialBatch.get_by_id(parent_batch.id)
        self.assertTrue(db_parent.is_active())

        # Cleanup - delete child first, then parent
        child_batch.delete_instance()
        Activity.delete().where(Activity.batch == parent_batch).execute()
        parent_batch.delete_instance()
        material.delete_instance()
        location.delete_instance()

    def test_delete_batch_not_found_fails(self):
        """Test deleting a non-existent batch fails"""
        service = MaterialBatchService()

        # Act & Assert
        with self.assertRaises(Exception):  # NotFoundException
            service.delete_batch("non-existent-batch-id")

    def test_delete_batch_creates_discard_activity(self):
        """Test soft deleting a batch creates a discard activity with note"""
        service = MaterialBatchService()
        material = self._create_test_material("Discard Activity Material", True, UnitType.COUNT)
        self._ensure_default_location()

        batch = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="DISCARD-ACT",
                quantity=Decimal("100"),
                unit="units",
            )
        )
        batch_id = batch.id

        # Add activity to ensure soft delete
        service.receive_batch(
            batch_id,
            ReceiveBatchDTO(quantity=Decimal("50"), unit="units"),
        )

        # Act - delete batch with notes
        service.delete_batch(batch_id, notes="Expired stock")

        # Assert - discard activity was created
        discard_activity = (
            Activity.select(
                Activity.id,
                Activity.activity_type,
                Activity.quantity,
            )
            .where(Activity.batch == batch)
            .where(Activity.activity_type == ActivityType.DISCARD)
            .first()
        )
        self.assertIsNotNone(discard_activity)
        self.assertEqual(discard_activity.quantity, Decimal("150"))  # 100 + 50

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        MaterialBatch.get_by_id(batch_id).delete_instance()
        material.delete_instance()

    # ============== RELABEL BATCH TESTS ==============

    def test_relabel_batch_number(self):
        """Test relabeling a batch (changing batch_number)"""
        service = MaterialBatchService()
        material = self._create_test_material("Relabel Material", True, UnitType.COUNT)
        self._ensure_default_location()

        batch = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="OLD-NUM",
                quantity=Decimal("100"),
                unit="units",
            )
        )
        self.assertEqual(batch.batch_number, "OLD-NUM")

        # Act - relabel batch
        updated_batch = service.relabel_batch(
            batch_id=batch.id,
            dto=RelabelBatchDTO(batch_number="NEW-NUM"),
        )

        # Assert
        self.assertEqual(updated_batch.batch_number, "NEW-NUM")

        # Verify in database
        db_batch = MaterialBatch.get_by_id(batch.id)
        self.assertEqual(db_batch.batch_number, "NEW-NUM")

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()
        material.delete_instance()

    def test_relabel_batch_label(self):
        """Test relabeling a batch (changing label)"""
        service = MaterialBatchService()
        material = self._create_test_material("Relabel Label Material", True, UnitType.COUNT)
        self._ensure_default_location()

        batch = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="RELBL-001",
                quantity=Decimal("100"),
                unit="units",
                label="Original Label",
            )
        )

        # Act - relabel batch (change label only)
        updated_batch = service.relabel_batch(
            batch_id=batch.id,
            dto=RelabelBatchDTO(label="New Label"),
        )

        # Assert
        self.assertEqual(updated_batch.label, "New Label")
        self.assertEqual(updated_batch.batch_number, "RELBL-001")  # Unchanged

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()
        material.delete_instance()

    def test_relabel_batch_both_fields(self):
        """Test relabeling a batch (changing both batch_number and label)"""
        service = MaterialBatchService()
        material = self._create_test_material("Relabel Both Material", True, UnitType.COUNT)
        self._ensure_default_location()

        batch = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="OLD-BOTH",
                quantity=Decimal("100"),
                unit="units",
                label="Old Label",
            )
        )

        # Act - relabel both fields
        updated_batch = service.relabel_batch(
            batch_id=batch.id,
            dto=RelabelBatchDTO(batch_number="NEW-BOTH", label="New Label"),
        )

        # Assert
        self.assertEqual(updated_batch.batch_number, "NEW-BOTH")
        self.assertEqual(updated_batch.label, "New Label")

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()
        material.delete_instance()

    def test_relabel_batch_creates_activity(self):
        """Test that relabeling a batch creates a RELABEL activity"""
        service = MaterialBatchService()
        material = self._create_test_material("Relabel Activity Material", True, UnitType.COUNT)
        self._ensure_default_location()

        batch = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="RELBL-ACT",
                quantity=Decimal("100"),
                unit="units",
            )
        )
        initial_activity_count = Activity.count_by_batch_id(batch.id)

        # Act - relabel batch
        service.relabel_batch(
            batch_id=batch.id,
            dto=RelabelBatchDTO(batch_number="NEW-ACT"),
        )

        # Assert - new activity created
        activity_count = Activity.count_by_batch_id(batch.id)
        self.assertEqual(activity_count, initial_activity_count + 1)

        # Find the relabel activity
        relabel_activity = (
            Activity.select(
                Activity.id,
                Activity.activity_type,
                Activity.notes,
            )
            .where(Activity.batch == batch)
            .where(Activity.activity_type == ActivityType.RELABEL)
            .first()
        )
        self.assertIsNotNone(relabel_activity)
        self.assertIn("RELBL-ACT", relabel_activity.notes)
        self.assertIn("NEW-ACT", relabel_activity.notes)

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()
        material.delete_instance()

    def test_relabel_batch_no_fields_fails(self):
        """Test relabeling without any fields fails"""
        service = MaterialBatchService()
        material = self._create_test_material("Relabel No Fields Material", True, UnitType.COUNT)
        self._ensure_default_location()

        batch = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="NO-FIELDS",
                quantity=Decimal("100"),
                unit="units",
            )
        )

        # Act & Assert
        with self.assertRaises(BadRequestException) as context:
            service.relabel_batch(batch.id, RelabelBatchDTO())

        self.assertIn("At least one", str(context.exception))

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()
        material.delete_instance()

    def test_relabel_batch_empty_batch_number_fails(self):
        """Test relabeling with empty batch_number fails"""
        service = MaterialBatchService()
        material = self._create_test_material("Relabel Empty Material", True, UnitType.COUNT)
        self._ensure_default_location()

        batch = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="VALID-NUM",
                quantity=Decimal("100"),
                unit="units",
            )
        )

        # Act & Assert
        with self.assertRaises(BadRequestException) as context:
            service.relabel_batch(batch.id, RelabelBatchDTO(batch_number=""))

        self.assertIn("Batch number is required", str(context.exception))

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()
        material.delete_instance()

    def test_relabel_batch_no_change_no_activity(self):
        """Test relabeling with same values doesn't create activity"""
        service = MaterialBatchService()
        material = self._create_test_material("Relabel No Change Material", True, UnitType.COUNT)
        self._ensure_default_location()

        batch = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="SAME-NUM",
                quantity=Decimal("100"),
                unit="units",
                label="Same Label",
            )
        )
        initial_activity_count = Activity.count_by_batch_id(batch.id)

        # Act - relabel with same values
        updated_batch = service.relabel_batch(
            batch_id=batch.id,
            dto=RelabelBatchDTO(batch_number="SAME-NUM", label="Same Label"),
        )

        # Assert - no new activity created
        activity_count = Activity.count_by_batch_id(batch.id)
        self.assertEqual(activity_count, initial_activity_count)
        self.assertEqual(updated_batch.batch_number, "SAME-NUM")
        self.assertEqual(updated_batch.label, "Same Label")

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()
        material.delete_instance()

    def test_relabel_batch_not_found_fails(self):
        """Test relabeling a non-existent batch fails"""
        service = MaterialBatchService()

        # Act & Assert
        with self.assertRaises(Exception):  # NotFoundException
            service.relabel_batch(
                "non-existent-batch-id",
                RelabelBatchDTO(batch_number="NEW-NUM"),
            )

    # ============== GET PARENT HIERARCHY TESTS ==============

    def test_get_parent_hierarchy(self):
        """Test getting the parent hierarchy of a batch with aliquots"""
        service = MaterialBatchService()
        material = self._create_test_material("Hierarchy Material", True, UnitType.VOLUME)
        self._ensure_default_location()

        # Create parent batch
        parent_batch = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="PARENT-HIER",
                quantity=Decimal("100"),
                unit="L",
            )
        )

        # Create first aliquot from parent
        aliquot1 = service.create_aliquot(
            CreateAliquotDTO(
                parent_batch_id=parent_batch.id,
                source_quantity=Decimal("20"),
                source_unit="L",
                aliquot_quantity=Decimal("20"),
                aliquot_unit="L",
                aliquot_batch_number="ALIQUOT-1",
            )
        )

        # Create second aliquot from first aliquot (grandchild)
        aliquot2 = service.create_aliquot(
            CreateAliquotDTO(
                parent_batch_id=aliquot1.id,
                source_quantity=Decimal("5"),
                source_unit="L",
                aliquot_quantity=Decimal("5"),
                aliquot_unit="L",
                aliquot_batch_number="ALIQUOT-2",
            )
        )

        # Test hierarchy without include_self and include_material
        hierarchy = service.get_parent_hierarchy(aliquot2.id)
        self.assertEqual(len(hierarchy), 2)
        self.assertEqual(hierarchy[0].id, aliquot1.id)
        self.assertEqual(hierarchy[0].name, "ALIQUOT-1")
        self.assertEqual(hierarchy[1].id, parent_batch.id)
        self.assertEqual(hierarchy[1].name, "PARENT-HIER")

        # Test hierarchy with include_self=True
        hierarchy_with_self = service.get_parent_hierarchy(aliquot2.id, include_self=True)
        self.assertEqual(len(hierarchy_with_self), 3)
        self.assertEqual(hierarchy_with_self[0].id, aliquot2.id)
        self.assertEqual(hierarchy_with_self[0].name, "ALIQUOT-2")
        self.assertEqual(hierarchy_with_self[1].id, aliquot1.id)
        self.assertEqual(hierarchy_with_self[2].id, parent_batch.id)

        # Test hierarchy with include_material=True
        hierarchy_with_material = service.get_parent_hierarchy(aliquot2.id, include_material=True)
        self.assertEqual(len(hierarchy_with_material), 3)
        self.assertEqual(hierarchy_with_material[0].id, aliquot1.id)
        self.assertEqual(hierarchy_with_material[1].id, parent_batch.id)
        self.assertEqual(hierarchy_with_material[2].id, material.id)
        self.assertEqual(hierarchy_with_material[2].name, "Hierarchy Material")

        # Test hierarchy with both flags
        hierarchy_full = service.get_parent_hierarchy(
            aliquot2.id, include_self=True, include_material=True
        )
        self.assertEqual(len(hierarchy_full), 4)
        self.assertEqual(hierarchy_full[0].id, aliquot2.id)
        self.assertEqual(hierarchy_full[1].id, aliquot1.id)
        self.assertEqual(hierarchy_full[2].id, parent_batch.id)
        self.assertEqual(hierarchy_full[3].id, material.id)

        # Test parent batch has empty hierarchy (no parent)
        parent_hierarchy = service.get_parent_hierarchy(parent_batch.id)
        self.assertEqual(len(parent_hierarchy), 0)

        # Cleanup
        Activity.delete().where(Activity.batch == aliquot2).execute()
        Activity.delete().where(Activity.batch == aliquot1).execute()
        Activity.delete().where(Activity.batch == parent_batch).execute()
        aliquot2.delete_instance()
        aliquot1.delete_instance()
        parent_batch.delete_instance()
        material.delete_instance()
