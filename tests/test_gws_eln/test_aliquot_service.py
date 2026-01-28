"""
Test suite for Aliquot operations in MaterialBatchService.

Tests Story 6.4 from Epic 6: Service Layer - Aliquots & Lineage.

Tests cover:
- Create aliquot from parent batch
- Create multi-level aliquot (aliquot from aliquot)
- Parent quantity decrements by source_quantity
- Aliquot quantity set to aliquot_quantity
- Material inheritance from parent
- Location defaults to parent location
- Custom batch number support
- Activity logging for both parent and child
- Validation errors (non-consumable, insufficient quantity, etc.)
"""

from datetime import date
from decimal import Decimal

from gws_core import BadRequestException, BaseTestCase
from gws_eln.activities.activity import Activity
from gws_eln.activities.activity_type import ActivityType
from gws_eln.core.unit_type import UnitType
from gws_eln.locations.location import Location
from gws_eln.locations.location_dto import CreateLocationDTO
from gws_eln.locations.location_service import LocationService
from gws_eln.materials.material import Material
from gws_eln.materials.material_batch import MaterialBatch
from gws_eln.materials.material_batch_dto import CreateAliquotDTO, CreateBatchDTO, ReceiveBatchDTO
from gws_eln.materials.material_batch_service import MaterialBatchService
from gws_eln.materials.material_dto import CreateMaterialDTO
from gws_eln.materials.material_service import MaterialService
from gws_eln.user.eln_user_sync_service import ElnUserSyncService


class TestAliquotService(BaseTestCase):
    """Test suite for Aliquot operations"""

    @classmethod
    def init_before_test(cls):
        """Setup: sync users from gws_core to gws_eln before tests"""
        super().init_before_test()
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

    def _create_test_batch(
        self,
        material: Material,
        batch_number: str = "BATCH-001",
        quantity: Decimal = Decimal("100"),
        unit: str = "L",
        location: Location | None = None,
    ) -> MaterialBatch:
        """Helper to create a test batch."""
        service = MaterialBatchService()
        result = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number=batch_number,
                quantity=quantity,
                unit=unit,
                location_id=location.id if location else None,
            )
        )
        return result.batch

    def _cleanup_batch(self, batch: MaterialBatch):
        """Helper to cleanup a batch and its activities."""
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()

    # ============== CREATE ALIQUOT TESTS ==============

    def test_create_aliquot_basic(self):
        """Test creating a basic aliquot from a parent batch"""
        service = MaterialBatchService()
        material = self._create_test_material("Ethanol", True, UnitType.VOLUME)
        location = self._create_test_location("Lab Storage")

        # Create parent batch with 100L
        parent = self._create_test_batch(
            material=material,
            batch_number="PARENT-001",
            quantity=Decimal("100"),
            unit="L",
            location=location,
        )

        # Act - create aliquot: take 20L to create 15L aliquot (5L lost in process)
        result = service.create_aliquot(
            CreateAliquotDTO(
                parent_batch_id=parent.id,
                source_quantity=Decimal("20"),
                source_unit="L",
                aliquot_quantity=Decimal("15"),
                aliquot_unit="L",
                label="Diluted sample",
            )
        )
        aliquot = result.batch

        # Assert - aliquot properties
        self.assertIsNotNone(aliquot)
        self.assertIsNotNone(aliquot.id)
        self.assertEqual(aliquot.quantity, Decimal("15"))
        self.assertEqual(aliquot.unit_type, UnitType.VOLUME)
        self.assertEqual(aliquot.material.id, material.id)
        self.assertEqual(aliquot.parent_batch.id, parent.id)
        self.assertEqual(aliquot.label, "Diluted sample")
        self.assertEqual(aliquot.location.id, location.id)  # Inherited from parent
        self.assertTrue(aliquot.is_aliquot())
        self.assertFalse(aliquot.is_original_batch())

        # Assert - parent quantity decremented by source_quantity
        updated_parent = service.get_batch(parent.id)
        self.assertEqual(updated_parent.quantity, Decimal("80"))  # 100 - 20

        # Assert - batch number auto-generated
        self.assertEqual(aliquot.batch_number, "PARENT-001-A1")

        # Cleanup
        self._cleanup_batch(aliquot)
        self._cleanup_batch(parent)
        material.delete_instance()
        location.delete_instance()

    def test_create_aliquot_with_custom_batch_number(self):
        """Test creating aliquot with custom batch number"""
        service = MaterialBatchService()
        material = self._create_test_material("Sample Material", True, UnitType.MASS)
        self._ensure_default_location()

        parent = self._create_test_batch(
            material=material,
            batch_number="PARENT-002",
            quantity=Decimal("500"),
            unit="g",
        )

        # Act - create aliquot with custom batch number
        result = service.create_aliquot(
            CreateAliquotDTO(
                parent_batch_id=parent.id,
                source_quantity=Decimal("100"),
                source_unit="g",
                aliquot_quantity=Decimal("100"),
                aliquot_unit="g",
                aliquot_batch_number="CUSTOM-ALQ-001",
            )
        )
        aliquot = result.batch

        # Assert
        self.assertEqual(aliquot.batch_number, "CUSTOM-ALQ-001")

        # Cleanup
        self._cleanup_batch(aliquot)
        self._cleanup_batch(parent)
        material.delete_instance()

    def test_create_aliquot_different_location(self):
        """Test creating aliquot at a different location than parent"""
        service = MaterialBatchService()
        material = self._create_test_material("Chemical", True, UnitType.VOLUME)
        location1 = self._create_test_location("Location A")
        location2 = self._create_test_location("Location B")

        parent = self._create_test_batch(
            material=material,
            batch_number="LOC-PARENT",
            quantity=Decimal("100"),
            unit="L",
            location=location1,
        )

        # Act - create aliquot at different location
        result = service.create_aliquot(
            CreateAliquotDTO(
                parent_batch_id=parent.id,
                source_quantity=Decimal("25"),
                source_unit="L",
                aliquot_quantity=Decimal("25"),
                aliquot_unit="L",
                location_id=location2.id,
            )
        )
        aliquot = result.batch

        # Assert
        self.assertEqual(aliquot.location.id, location2.id)
        self.assertNotEqual(aliquot.location.id, parent.location.id)

        # Cleanup
        self._cleanup_batch(aliquot)
        self._cleanup_batch(parent)
        material.delete_instance()
        location1.delete_instance()
        location2.delete_instance()

    def test_create_aliquot_inherits_material(self):
        """Test that aliquot inherits material from parent"""
        service = MaterialBatchService()
        material = self._create_test_material("Inherited Material", True, UnitType.COUNT)
        self._ensure_default_location()

        parent = self._create_test_batch(
            material=material,
            batch_number="INHERIT-PARENT",
            quantity=Decimal("50"),
            unit="units",
        )

        # Act
        result = service.create_aliquot(
            CreateAliquotDTO(
                parent_batch_id=parent.id,
                source_quantity=Decimal("10"),
                source_unit="units",
                aliquot_quantity=Decimal("10"),
                aliquot_unit="units",
            )
        )
        aliquot = result.batch

        # Assert - material is inherited
        self.assertEqual(aliquot.material.id, material.id)
        self.assertEqual(aliquot.material.name, "Inherited Material")
        self.assertTrue(aliquot.is_consumable())

        # Cleanup
        self._cleanup_batch(aliquot)
        self._cleanup_batch(parent)
        material.delete_instance()

    def test_create_aliquot_inherits_expiry_date(self):
        """Test that aliquot inherits expiry date from parent"""
        service = MaterialBatchService()
        material = self._create_test_material("Expiry Material", True, UnitType.VOLUME)
        self._ensure_default_location()

        # Create parent with expiry date
        parent = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="EXPIRY-PARENT",
                quantity=Decimal("100"),
                unit="L",
                expiry_date=date(2027, 12, 31),
            )
        ).batch

        # Act
        result = service.create_aliquot(
            CreateAliquotDTO(
                parent_batch_id=parent.id,
                source_quantity=Decimal("20"),
                source_unit="L",
                aliquot_quantity=Decimal("20"),
                aliquot_unit="L",
            )
        )
        aliquot = result.batch

        # Assert - expiry date is inherited
        self.assertEqual(aliquot.expiry_date, date(2027, 12, 31))

        # Cleanup
        self._cleanup_batch(aliquot)
        self._cleanup_batch(parent)
        material.delete_instance()

    def test_create_aliquot_creates_both_activities(self):
        """Test that creating aliquot logs activities on both parent and child"""
        service = MaterialBatchService()
        material = self._create_test_material("Activity Material", True, UnitType.VOLUME)
        location = self._create_test_location("Activity Location")

        parent = self._create_test_batch(
            material=material,
            batch_number="ACT-PARENT",
            quantity=Decimal("100"),
            unit="L",
            location=location,
        )

        # Get initial activity count on parent (should have 1 RECEIVE)
        initial_parent_activities = Activity.count_by_batch_id(parent.id)
        self.assertEqual(initial_parent_activities, 1)

        # Act
        result = service.create_aliquot(
            CreateAliquotDTO(
                parent_batch_id=parent.id,
                source_quantity=Decimal("30"),
                source_unit="L",
                aliquot_quantity=Decimal("25"),
                aliquot_unit="L",
            )
        )
        aliquot = result.batch

        # Assert - parent has ALIQUOT activity
        parent_activities = list(
            Activity.select()
            .where(Activity.batch == parent)
            .where(Activity.activity_type == ActivityType.ALIQUOT)
        )
        self.assertEqual(len(parent_activities), 1)
        parent_activity = parent_activities[0]
        self.assertEqual(parent_activity.quantity, Decimal("30"))  # source_quantity
        self.assertEqual(parent_activity.related_batch.id, aliquot.id)

        # Assert - aliquot has ALIQUOT_CREATED activity
        aliquot_activities = list(
            Activity.select()
            .where(Activity.batch == aliquot)
            .where(Activity.activity_type == ActivityType.ALIQUOT_CREATED)
        )
        self.assertEqual(len(aliquot_activities), 1)
        aliquot_activity = aliquot_activities[0]
        self.assertEqual(aliquot_activity.quantity, Decimal("25"))  # aliquot_quantity
        self.assertEqual(aliquot_activity.related_batch.id, parent.id)

        # Cleanup
        self._cleanup_batch(aliquot)
        self._cleanup_batch(parent)
        material.delete_instance()
        location.delete_instance()

    # ============== MULTI-LEVEL ALIQUOT TESTS ==============

    def test_create_multi_level_aliquot(self):
        """Test creating aliquot from aliquot (multi-level)"""
        service = MaterialBatchService()
        material = self._create_test_material("Multi-Level Material", True, UnitType.VOLUME)
        self._ensure_default_location()

        # Create original parent batch
        parent = self._create_test_batch(
            material=material,
            batch_number="MULTI-PARENT",
            quantity=Decimal("100"),
            unit="L",
        )

        # Create first-level aliquot
        aliquot1 = service.create_aliquot(
            CreateAliquotDTO(
                parent_batch_id=parent.id,
                source_quantity=Decimal("40"),
                source_unit="L",
                aliquot_quantity=Decimal("40"),
                aliquot_unit="L",
            )
        ).batch

        # Act - create second-level aliquot (aliquot from aliquot)
        aliquot2 = service.create_aliquot(
            CreateAliquotDTO(
                parent_batch_id=aliquot1.id,
                source_quantity=Decimal("15"),
                source_unit="L",
                aliquot_quantity=Decimal("15"),
                aliquot_unit="L",
            )
        ).batch

        # Assert
        self.assertIsNotNone(aliquot2)
        self.assertEqual(aliquot2.parent_batch.id, aliquot1.id)
        self.assertEqual(aliquot2.material.id, material.id)
        self.assertEqual(aliquot2.quantity, Decimal("15"))

        # Assert - aliquot1 quantity decremented
        updated_aliquot1 = service.get_batch(aliquot1.id)
        self.assertEqual(updated_aliquot1.quantity, Decimal("25"))  # 40 - 15

        # Assert - batch number includes parent chain
        self.assertEqual(aliquot2.batch_number, "MULTI-PARENT-A1-A1")

        # Cleanup
        self._cleanup_batch(aliquot2)
        self._cleanup_batch(aliquot1)
        self._cleanup_batch(parent)
        material.delete_instance()

    def test_create_multiple_aliquots_from_same_parent(self):
        """Test creating multiple aliquots from same parent"""
        service = MaterialBatchService()
        material = self._create_test_material("Multi-Aliquot Material", True, UnitType.VOLUME)
        self._ensure_default_location()

        parent = self._create_test_batch(
            material=material,
            batch_number="MULTI-ALQ-PARENT",
            quantity=Decimal("100"),
            unit="L",
        )

        # Act - create multiple aliquots
        aliquot1 = service.create_aliquot(
            CreateAliquotDTO(
                parent_batch_id=parent.id,
                source_quantity=Decimal("20"),
                source_unit="L",
                aliquot_quantity=Decimal("20"),
                aliquot_unit="L",
            )
        ).batch
        aliquot2 = service.create_aliquot(
            CreateAliquotDTO(
                parent_batch_id=parent.id,
                source_quantity=Decimal("30"),
                source_unit="L",
                aliquot_quantity=Decimal("30"),
                aliquot_unit="L",
            )
        ).batch
        aliquot3 = service.create_aliquot(
            CreateAliquotDTO(
                parent_batch_id=parent.id,
                source_quantity=Decimal("10"),
                source_unit="L",
                aliquot_quantity=Decimal("10"),
                aliquot_unit="L",
            )
        ).batch

        # Assert - batch numbers are incremented
        self.assertEqual(aliquot1.batch_number, "MULTI-ALQ-PARENT-A1")
        self.assertEqual(aliquot2.batch_number, "MULTI-ALQ-PARENT-A2")
        self.assertEqual(aliquot3.batch_number, "MULTI-ALQ-PARENT-A3")

        # Assert - parent quantity decremented correctly
        updated_parent = service.get_batch(parent.id)
        self.assertEqual(updated_parent.quantity, Decimal("40"))  # 100 - 20 - 30 - 10

        # Cleanup
        self._cleanup_batch(aliquot3)
        self._cleanup_batch(aliquot2)
        self._cleanup_batch(aliquot1)
        self._cleanup_batch(parent)
        material.delete_instance()

    # ============== VALIDATION ERROR TESTS ==============

    def test_create_aliquot_non_consumable_fails(self):
        """Test creating aliquot from non-consumable material fails"""
        service = MaterialBatchService()
        material = self._create_test_material("Instrument", False, UnitType.COUNT)
        self._ensure_default_location()

        parent = self._create_test_batch(
            material=material,
            batch_number="INSTRUMENT-001",
            quantity=Decimal("5"),
            unit="units",
        )

        # Act & Assert
        with self.assertRaises(BadRequestException) as context:
            service.create_aliquot(
                CreateAliquotDTO(
                    parent_batch_id=parent.id,
                    source_quantity=Decimal("1"),
                    source_unit="units",
                    aliquot_quantity=Decimal("1"),
                    aliquot_unit="units",
                )
            )

        self.assertIn("non-consumable", str(context.exception).lower())

        # Cleanup
        self._cleanup_batch(parent)
        material.delete_instance()

    def test_create_aliquot_insufficient_quantity_fails(self):
        """Test creating aliquot with more than available quantity fails"""
        service = MaterialBatchService()
        material = self._create_test_material("Limited Material", True, UnitType.VOLUME)
        self._ensure_default_location()

        parent = self._create_test_batch(
            material=material,
            batch_number="LIMITED-001",
            quantity=Decimal("50"),
            unit="L",
        )

        # Act & Assert - try to take more than available
        with self.assertRaises(BadRequestException) as context:
            service.create_aliquot(
                CreateAliquotDTO(
                    parent_batch_id=parent.id,
                    source_quantity=Decimal("100"),  # More than 50 available
                    source_unit="L",
                    aliquot_quantity=Decimal("100"),
                    aliquot_unit="L",
                )
            )

        self.assertIn("Insufficient quantity", str(context.exception))

        # Verify parent quantity unchanged
        updated_parent = service.get_batch(parent.id)
        self.assertEqual(updated_parent.quantity, Decimal("50"))

        # Cleanup
        self._cleanup_batch(parent)
        material.delete_instance()

    def test_create_aliquot_source_unit_mismatch_fails(self):
        """Test creating aliquot with mismatched source unit fails"""
        service = MaterialBatchService()
        material = self._create_test_material("Volume Material", True, UnitType.VOLUME)
        self._ensure_default_location()

        parent = self._create_test_batch(
            material=material,
            batch_number="UNIT-MIS-001",
            quantity=Decimal("100"),
            unit="L",
        )

        # Act & Assert - source unit mismatch (mass unit for volume batch)
        with self.assertRaises(BadRequestException) as context:
            service.create_aliquot(
                CreateAliquotDTO(
                    parent_batch_id=parent.id,
                    source_quantity=Decimal("20"),
                    source_unit="g",  # Mismatch! (mass unit for volume batch)
                    aliquot_quantity=Decimal("20"),
                    aliquot_unit="L",
                )
            )

        self.assertIn("Invalid unit", str(context.exception))

        # Cleanup
        self._cleanup_batch(parent)
        material.delete_instance()

    def test_create_aliquot_aliquot_unit_mismatch_fails(self):
        """Test creating aliquot with mismatched aliquot unit fails"""
        service = MaterialBatchService()
        material = self._create_test_material("Volume Material 2", True, UnitType.VOLUME)
        self._ensure_default_location()

        parent = self._create_test_batch(
            material=material,
            batch_number="UNIT-MIS-002",
            quantity=Decimal("100"),
            unit="L",
        )

        # Act & Assert - aliquot unit mismatch (mass unit for volume batch)
        with self.assertRaises(BadRequestException) as context:
            service.create_aliquot(
                CreateAliquotDTO(
                    parent_batch_id=parent.id,
                    source_quantity=Decimal("20"),
                    source_unit="L",
                    aliquot_quantity=Decimal("20"),
                    aliquot_unit="g",  # Mismatch! (mass unit for volume batch)
                )
            )

        self.assertIn("Invalid aliquot unit", str(context.exception))

        # Cleanup
        self._cleanup_batch(parent)
        material.delete_instance()

    def test_create_aliquot_negative_source_quantity_fails(self):
        """Test creating aliquot with negative source quantity fails"""
        service = MaterialBatchService()
        material = self._create_test_material("Negative Source Material", True, UnitType.VOLUME)
        self._ensure_default_location()

        parent = self._create_test_batch(
            material=material,
            batch_number="NEG-SRC-001",
            quantity=Decimal("100"),
            unit="L",
        )

        # Act & Assert
        with self.assertRaises(BadRequestException) as context:
            service.create_aliquot(
                CreateAliquotDTO(
                    parent_batch_id=parent.id,
                    source_quantity=Decimal("-10"),
                    source_unit="L",
                    aliquot_quantity=Decimal("10"),
                    aliquot_unit="L",
                )
            )

        self.assertIn("positive", str(context.exception).lower())

        # Cleanup
        self._cleanup_batch(parent)
        material.delete_instance()

    def test_create_aliquot_negative_aliquot_quantity_fails(self):
        """Test creating aliquot with negative aliquot quantity fails"""
        service = MaterialBatchService()
        material = self._create_test_material("Negative Aliquot Material", True, UnitType.VOLUME)
        self._ensure_default_location()

        parent = self._create_test_batch(
            material=material,
            batch_number="NEG-ALQ-001",
            quantity=Decimal("100"),
            unit="L",
        )

        # Act & Assert
        with self.assertRaises(BadRequestException) as context:
            service.create_aliquot(
                CreateAliquotDTO(
                    parent_batch_id=parent.id,
                    source_quantity=Decimal("10"),
                    source_unit="L",
                    aliquot_quantity=Decimal("-5"),
                    aliquot_unit="L",
                )
            )

        self.assertIn("positive", str(context.exception).lower())

        # Cleanup
        self._cleanup_batch(parent)
        material.delete_instance()

    def test_create_aliquot_zero_source_quantity_fails(self):
        """Test creating aliquot with zero source quantity fails"""
        service = MaterialBatchService()
        material = self._create_test_material("Zero Source Material", True, UnitType.VOLUME)
        self._ensure_default_location()

        parent = self._create_test_batch(
            material=material,
            batch_number="ZERO-SRC-001",
            quantity=Decimal("100"),
            unit="L",
        )

        # Act & Assert
        with self.assertRaises(BadRequestException) as context:
            service.create_aliquot(
                CreateAliquotDTO(
                    parent_batch_id=parent.id,
                    source_quantity=Decimal("0"),
                    source_unit="L",
                    aliquot_quantity=Decimal("10"),
                    aliquot_unit="L",
                )
            )

        self.assertIn("positive", str(context.exception).lower())

        # Cleanup
        self._cleanup_batch(parent)
        material.delete_instance()

    def test_create_aliquot_from_discarded_batch_fails(self):
        """Test creating aliquot from discarded batch fails"""
        service = MaterialBatchService()
        material = self._create_test_material("Discarded Material", True, UnitType.VOLUME)
        self._ensure_default_location()

        parent = self._create_test_batch(
            material=material,
            batch_number="DISCARD-001",
            quantity=Decimal("100"),
            unit="L",
        )

        # Add activity to force soft delete, then delete
        service.receive_batch(
            parent.id,
            ReceiveBatchDTO(quantity=Decimal("10"), unit="L"),
        )
        service.delete_batch(parent.id, notes="Testing discarded")

        # Act & Assert
        with self.assertRaises(BadRequestException) as context:
            service.create_aliquot(
                CreateAliquotDTO(
                    parent_batch_id=parent.id,
                    source_quantity=Decimal("10"),
                    source_unit="L",
                    aliquot_quantity=Decimal("10"),
                    aliquot_unit="L",
                )
            )

        self.assertIn("discarded", str(context.exception).lower())

        # Cleanup
        Activity.delete().where(Activity.batch == parent).execute()
        MaterialBatch.get_by_id(parent.id).delete_instance()
        material.delete_instance()

    def test_create_aliquot_invalid_parent_fails(self):
        """Test creating aliquot with non-existent parent fails"""
        service = MaterialBatchService()

        # Act & Assert
        with self.assertRaises(Exception):  # NotFoundException
            service.create_aliquot(
                CreateAliquotDTO(
                    parent_batch_id="non-existent-id",
                    source_quantity=Decimal("10"),
                    source_unit="L",
                    aliquot_quantity=Decimal("10"),
                    aliquot_unit="L",
                )
            )

    def test_create_aliquot_empty_batch_number_fails(self):
        """Test creating aliquot with empty custom batch number fails"""
        service = MaterialBatchService()
        material = self._create_test_material("Empty Batch Material", True, UnitType.VOLUME)
        self._ensure_default_location()

        parent = self._create_test_batch(
            material=material,
            batch_number="EMPTY-BN-001",
            quantity=Decimal("100"),
            unit="L",
        )

        # Act & Assert
        with self.assertRaises(BadRequestException) as context:
            service.create_aliquot(
                CreateAliquotDTO(
                    parent_batch_id=parent.id,
                    source_quantity=Decimal("10"),
                    source_unit="L",
                    aliquot_quantity=Decimal("10"),
                    aliquot_unit="L",
                    aliquot_batch_number="   ",  # Whitespace only
                )
            )

        self.assertIn("Batch number is required", str(context.exception))

        # Cleanup
        self._cleanup_batch(parent)
        material.delete_instance()

    def test_create_aliquot_invalid_location_fails(self):
        """Test creating aliquot with non-existent location fails"""
        service = MaterialBatchService()
        material = self._create_test_material("Invalid Loc Material", True, UnitType.VOLUME)
        self._ensure_default_location()

        parent = self._create_test_batch(
            material=material,
            batch_number="INV-LOC-001",
            quantity=Decimal("100"),
            unit="L",
        )

        # Act & Assert
        with self.assertRaises(BadRequestException) as context:
            service.create_aliquot(
                CreateAliquotDTO(
                    parent_batch_id=parent.id,
                    source_quantity=Decimal("10"),
                    source_unit="L",
                    aliquot_quantity=Decimal("10"),
                    aliquot_unit="L",
                    location_id="non-existent-location-id",
                )
            )

        self.assertIn("does not exist", str(context.exception))

        # Cleanup
        self._cleanup_batch(parent)
        material.delete_instance()

    # ============== EDGE CASES ==============

    def test_create_aliquot_exact_quantity(self):
        """Test creating aliquot with exact remaining quantity"""
        service = MaterialBatchService()
        material = self._create_test_material("Exact Qty Material", True, UnitType.VOLUME)
        self._ensure_default_location()

        parent = self._create_test_batch(
            material=material,
            batch_number="EXACT-001",
            quantity=Decimal("50"),
            unit="L",
        )

        # Act - take exactly all available
        aliquot = service.create_aliquot(
            CreateAliquotDTO(
                parent_batch_id=parent.id,
                source_quantity=Decimal("50"),
                source_unit="L",
                aliquot_quantity=Decimal("50"),
                aliquot_unit="L",
            )
        ).batch

        # Assert - parent now has 0
        updated_parent = service.get_batch(parent.id)
        self.assertEqual(updated_parent.quantity, Decimal("0"))
        self.assertEqual(aliquot.quantity, Decimal("50"))

        # Cleanup
        self._cleanup_batch(aliquot)
        self._cleanup_batch(parent)
        material.delete_instance()

    def test_create_aliquot_source_greater_than_aliquot(self):
        """Test creating aliquot where source_quantity > aliquot_quantity (loss in process)"""
        service = MaterialBatchService()
        material = self._create_test_material("Process Loss Material", True, UnitType.MASS)
        self._ensure_default_location()

        parent = self._create_test_batch(
            material=material,
            batch_number="LOSS-001",
            quantity=Decimal("1000"),
            unit="g",
        )

        # Act - take 500g, produce only 300g (200g lost in process)
        aliquot = service.create_aliquot(
            CreateAliquotDTO(
                parent_batch_id=parent.id,
                source_quantity=Decimal("500"),
                source_unit="g",
                aliquot_quantity=Decimal("300"),
                aliquot_unit="g",
            )
        ).batch

        # Assert
        updated_parent = service.get_batch(parent.id)
        self.assertEqual(updated_parent.quantity, Decimal("500"))  # 1000g - 500g = 500g base
        self.assertEqual(aliquot.quantity, Decimal("300"))  # 300g base

        # Cleanup
        self._cleanup_batch(aliquot)
        self._cleanup_batch(parent)
        material.delete_instance()

    def test_create_aliquot_source_less_than_aliquot(self):
        """Test creating aliquot where source_quantity < aliquot_quantity (dilution)"""
        service = MaterialBatchService()
        material = self._create_test_material("Dilution Material", True, UnitType.VOLUME)
        self._ensure_default_location()

        parent = self._create_test_batch(
            material=material,
            batch_number="DILUTE-001",
            quantity=Decimal("100"),
            unit="L",
        )

        # Act - take 10L concentrate, dilute to 100L
        aliquot = service.create_aliquot(
            CreateAliquotDTO(
                parent_batch_id=parent.id,
                source_quantity=Decimal("10"),
                source_unit="L",
                aliquot_quantity=Decimal("100"),
                aliquot_unit="L",
            )
        ).batch

        # Assert
        updated_parent = service.get_batch(parent.id)
        self.assertEqual(updated_parent.quantity, Decimal("90"))  # 100 - 10
        self.assertEqual(aliquot.quantity, Decimal("100"))

        # Cleanup
        self._cleanup_batch(aliquot)
        self._cleanup_batch(parent)
        material.delete_instance()

    # ============== DIFFERENT MATERIAL ALIQUOT TESTS ==============

    def test_create_aliquot_with_different_material(self):
        """Test creating aliquot with a different target material"""
        service = MaterialBatchService()
        # Parent material: a solution (volume-based)
        parent_material = self._create_test_material("Solution A", True, UnitType.VOLUME)
        # Target material: extracted compound (mass-based)
        target_material = self._create_test_material("Compound X", True, UnitType.MASS)
        self._ensure_default_location()

        parent = self._create_test_batch(
            material=parent_material,
            batch_number="SOLUTION-001",
            quantity=Decimal("100"),
            unit="L",
        )

        # Act - extract compound from solution (different material, different unit type)
        aliquot = service.create_aliquot(
            CreateAliquotDTO(
                parent_batch_id=parent.id,
                target_material_id=target_material.id,
                source_quantity=Decimal("50"),
                source_unit="L",  # Taking from volume-based parent
                aliquot_quantity=Decimal("250"),
                aliquot_unit="g",  # Creating mass-based aliquot
                label="Extracted compound",
            )
        ).batch

        # Assert - aliquot has different material
        self.assertEqual(aliquot.material.id, target_material.id)
        self.assertNotEqual(aliquot.material.id, parent_material.id)
        self.assertEqual(aliquot.material.name, "Compound X")

        # Assert - aliquot has correct unit_type from target material
        self.assertEqual(aliquot.unit_type, UnitType.MASS)
        self.assertNotEqual(aliquot.unit_type, parent.unit_type)

        # Assert - quantities are correct
        self.assertEqual(aliquot.quantity, Decimal("250"))  # 250g in base units (g)
        updated_parent = service.get_batch(parent.id)
        self.assertEqual(updated_parent.quantity, Decimal("50"))  # 100L - 50L

        # Assert - parent reference maintained
        self.assertEqual(aliquot.parent_batch.id, parent.id)
        self.assertTrue(aliquot.is_aliquot())

        # Cleanup
        self._cleanup_batch(aliquot)
        self._cleanup_batch(parent)
        parent_material.delete_instance()
        target_material.delete_instance()

    def test_create_aliquot_with_different_material_same_unit_type(self):
        """Test creating aliquot with different material but same unit type"""
        service = MaterialBatchService()
        # Both materials are volume-based
        parent_material = self._create_test_material("Chemical A", True, UnitType.VOLUME)
        target_material = self._create_test_material("Chemical B", True, UnitType.VOLUME)
        self._ensure_default_location()

        parent = self._create_test_batch(
            material=parent_material,
            batch_number="CHEM-A-001",
            quantity=Decimal("100"),
            unit="L",
        )

        # Act - transform Chemical A to Chemical B
        aliquot = service.create_aliquot(
            CreateAliquotDTO(
                parent_batch_id=parent.id,
                target_material_id=target_material.id,
                source_quantity=Decimal("30"),
                source_unit="L",
                aliquot_quantity=Decimal("25"),
                aliquot_unit="L",
            )
        ).batch

        # Assert
        self.assertEqual(aliquot.material.id, target_material.id)
        self.assertEqual(aliquot.unit_type, UnitType.VOLUME)
        self.assertEqual(aliquot.quantity, Decimal("25"))

        # Cleanup
        self._cleanup_batch(aliquot)
        self._cleanup_batch(parent)
        parent_material.delete_instance()
        target_material.delete_instance()

    def test_create_aliquot_without_target_material_inherits_parent(self):
        """Test that omitting target_material_id inherits from parent (backward compatibility)"""
        service = MaterialBatchService()
        material = self._create_test_material("Inherited Material BC", True, UnitType.VOLUME)
        self._ensure_default_location()

        parent = self._create_test_batch(
            material=material,
            batch_number="BC-PARENT",
            quantity=Decimal("100"),
            unit="L",
        )

        # Act - create aliquot without target_material_id
        aliquot = service.create_aliquot(
            CreateAliquotDTO(
                parent_batch_id=parent.id,
                # target_material_id not provided - should inherit from parent
                source_quantity=Decimal("20"),
                source_unit="L",
                aliquot_quantity=Decimal("20"),
                aliquot_unit="L",
            )
        ).batch

        # Assert - material is inherited from parent
        self.assertEqual(aliquot.material.id, material.id)
        self.assertEqual(aliquot.unit_type, UnitType.VOLUME)

        # Cleanup
        self._cleanup_batch(aliquot)
        self._cleanup_batch(parent)
        material.delete_instance()

    def test_create_aliquot_with_non_existent_target_material_fails(self):
        """Test creating aliquot with non-existent target material fails"""
        service = MaterialBatchService()
        material = self._create_test_material("Valid Parent Material", True, UnitType.VOLUME)
        self._ensure_default_location()

        parent = self._create_test_batch(
            material=material,
            batch_number="VALID-PARENT",
            quantity=Decimal("100"),
            unit="L",
        )

        # Act & Assert
        with self.assertRaises(BadRequestException) as context:
            service.create_aliquot(
                CreateAliquotDTO(
                    parent_batch_id=parent.id,
                    target_material_id="non-existent-material-id",
                    source_quantity=Decimal("20"),
                    source_unit="L",
                    aliquot_quantity=Decimal("20"),
                    aliquot_unit="L",
                )
            )

        self.assertIn("does not exist", str(context.exception))

        # Cleanup
        self._cleanup_batch(parent)
        material.delete_instance()

    def test_create_aliquot_with_non_consumable_target_material_fails(self):
        """Test creating aliquot with non-consumable target material fails"""
        service = MaterialBatchService()
        parent_material = self._create_test_material("Consumable Parent", True, UnitType.VOLUME)
        target_material = self._create_test_material("Instrument", False, UnitType.COUNT)
        self._ensure_default_location()

        parent = self._create_test_batch(
            material=parent_material,
            batch_number="CONS-PARENT",
            quantity=Decimal("100"),
            unit="L",
        )

        # Act & Assert - target material is non-consumable
        with self.assertRaises(BadRequestException) as context:
            service.create_aliquot(
                CreateAliquotDTO(
                    parent_batch_id=parent.id,
                    target_material_id=target_material.id,
                    source_quantity=Decimal("20"),
                    source_unit="L",
                    aliquot_quantity=Decimal("5"),
                    aliquot_unit="units",
                )
            )

        self.assertIn("non-consumable", str(context.exception).lower())

        # Cleanup
        self._cleanup_batch(parent)
        parent_material.delete_instance()
        target_material.delete_instance()

    def test_create_aliquot_with_different_material_validates_aliquot_unit(self):
        """Test that aliquot unit is validated against target material's unit type"""
        service = MaterialBatchService()
        parent_material = self._create_test_material("Volume Parent", True, UnitType.VOLUME)
        target_material = self._create_test_material("Mass Target", True, UnitType.MASS)
        self._ensure_default_location()

        parent = self._create_test_batch(
            material=parent_material,
            batch_number="VOL-PARENT",
            quantity=Decimal("100"),
            unit="L",
        )

        # Act & Assert - aliquot unit doesn't match target material's unit type
        with self.assertRaises(BadRequestException) as context:
            service.create_aliquot(
                CreateAliquotDTO(
                    parent_batch_id=parent.id,
                    target_material_id=target_material.id,
                    source_quantity=Decimal("20"),
                    source_unit="L",
                    aliquot_quantity=Decimal("20"),
                    aliquot_unit="L",  # Wrong! Target is MASS, should use g/kg/etc.
                )
            )

        self.assertIn("Invalid aliquot unit", str(context.exception))

        # Cleanup
        self._cleanup_batch(parent)
        parent_material.delete_instance()
        target_material.delete_instance()

    def test_create_aliquot_different_material_activities_have_correct_unit_types(self):
        """Test that activities log correct unit types for different material aliquots"""
        service = MaterialBatchService()
        parent_material = self._create_test_material("Activity Parent Mat", True, UnitType.VOLUME)
        target_material = self._create_test_material("Activity Target Mat", True, UnitType.MASS)
        self._ensure_default_location()

        parent = self._create_test_batch(
            material=parent_material,
            batch_number="ACT-DIFF-PARENT",
            quantity=Decimal("100"),
            unit="L",
        )

        # Act
        aliquot = service.create_aliquot(
            CreateAliquotDTO(
                parent_batch_id=parent.id,
                target_material_id=target_material.id,
                source_quantity=Decimal("30"),
                source_unit="L",
                aliquot_quantity=Decimal("500"),
                aliquot_unit="g",
            )
        ).batch

        # Assert - ALIQUOT activity on parent has parent's unit_type
        parent_activities = list(
            Activity.select()
            .where(Activity.batch == parent)
            .where(Activity.activity_type == ActivityType.ALIQUOT)
        )
        self.assertEqual(len(parent_activities), 1)
        self.assertEqual(parent_activities[0].unit_type, UnitType.VOLUME)
        self.assertEqual(parent_activities[0].quantity, Decimal("30"))

        # Assert - ALIQUOT_CREATED activity on aliquot has target material's unit_type
        aliquot_activities = list(
            Activity.select()
            .where(Activity.batch == aliquot)
            .where(Activity.activity_type == ActivityType.ALIQUOT_CREATED)
        )
        self.assertEqual(len(aliquot_activities), 1)
        self.assertEqual(aliquot_activities[0].unit_type, UnitType.MASS)
        self.assertEqual(aliquot_activities[0].quantity, Decimal("500"))  # 500g base

        # Cleanup
        self._cleanup_batch(aliquot)
        self._cleanup_batch(parent)
        parent_material.delete_instance()
        target_material.delete_instance()

    def test_create_multi_level_aliquot_with_different_materials(self):
        """Test multi-level aliquots where each level can have different materials"""
        service = MaterialBatchService()
        material_a = self._create_test_material("Material A", True, UnitType.VOLUME)
        material_b = self._create_test_material("Material B", True, UnitType.MASS)
        material_c = self._create_test_material("Material C", True, UnitType.COUNT)
        self._ensure_default_location()

        # Create original batch of Material A
        parent = self._create_test_batch(
            material=material_a,
            batch_number="MULTI-MAT-PARENT",
            quantity=Decimal("100"),
            unit="L",
        )

        # Create first-level aliquot with Material B
        aliquot1 = service.create_aliquot(
            CreateAliquotDTO(
                parent_batch_id=parent.id,
                target_material_id=material_b.id,
                source_quantity=Decimal("50"),
                source_unit="L",
                aliquot_quantity=Decimal("200"),
                aliquot_unit="g",
            )
        ).batch

        # Create second-level aliquot with Material C
        aliquot2 = service.create_aliquot(
            CreateAliquotDTO(
                parent_batch_id=aliquot1.id,
                target_material_id=material_c.id,
                source_quantity=Decimal("100"),
                source_unit="g",
                aliquot_quantity=Decimal("50"),
                aliquot_unit="units",
            )
        ).batch

        # Assert - each aliquot has correct material
        self.assertEqual(aliquot1.material.id, material_b.id)
        self.assertEqual(aliquot2.material.id, material_c.id)

        # Assert - each aliquot has correct unit_type
        self.assertEqual(aliquot1.unit_type, UnitType.MASS)
        self.assertEqual(aliquot2.unit_type, UnitType.COUNT)

        # Assert - parent references are correct
        self.assertEqual(aliquot1.parent_batch.id, parent.id)
        self.assertEqual(aliquot2.parent_batch.id, aliquot1.id)

        # Cleanup
        self._cleanup_batch(aliquot2)
        self._cleanup_batch(aliquot1)
        self._cleanup_batch(parent)
        material_a.delete_instance()
        material_b.delete_instance()
        material_c.delete_instance()
