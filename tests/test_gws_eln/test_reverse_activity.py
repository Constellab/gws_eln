"""
Test suite for MaterialBatchService.reverse_activity().

Tests the reversal logic for each activity type:
- RECEIVE, CONSUME, MOVE, USE, DISCARD, ALIQUOT, ALIQUOT_CREATED, RELABEL
"""

from decimal import Decimal

from gws_core import BadRequestException, BaseTestCase
from gws_eln.activities.activity import Activity
from gws_eln.activities.activity_dto import CreateActivityDTO
from gws_eln.activities.activity_service import ActivityService
from gws_eln.activities.activity_type import ActivityType
from gws_eln.core.unit_type import UnitType
from gws_eln.locations.location import Location
from gws_eln.locations.location_dto import CreateLocationDTO
from gws_eln.locations.location_service import LocationService
from gws_eln.materials.batch_status import BatchStatus
from gws_eln.materials.material import Material
from gws_eln.materials.material_batch import MaterialBatch
from gws_eln.materials.material_batch_dto import (
    CreateAliquotDTO,
    CreateBatchDTO,
    DecrementQuantityDTO,
    MoveBatchDTO,
    ReceiveBatchDTO,
    RelabelBatchDTO,
)
from gws_eln.materials.material_batch_service import MaterialBatchService
from gws_eln.materials.material_dto import CreateMaterialDTO
from gws_eln.materials.material_service import MaterialService
from gws_eln.user.eln_user_sync_service import ElnUserSyncService


class TestReverseActivity(BaseTestCase):
    @classmethod
    def init_before_test(cls):
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

    # ============== RECEIVE REVERSAL ==============

    def test_reverse_receive(self):
        """Test reversing a RECEIVE activity restores batch quantity."""
        service = MaterialBatchService()
        material = self._create_test_material("Rev Receive Material", True, UnitType.VOLUME)
        self._ensure_default_location()

        # Create batch with 100 mL (stored as 0.1 L)
        batch = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="REV-RCV-001",
                quantity=Decimal("100"),
                unit="mL",
            )
        )
        original_quantity = batch.quantity  # 0.1 L in base units

        # Receive 50 mL more
        updated_batch = service.receive_batch(
            batch.id,
            ReceiveBatchDTO(quantity=Decimal("50"), unit="mL"),
        )
        self.assertEqual(updated_batch.quantity, original_quantity + Decimal("0.05"))

        # Find the second RECEIVE activity (not the creation one)
        activities = Activity.find_by_batch_id(batch.id)
        receive_activities = [a for a in activities if a.activity_type == ActivityType.RECEIVE]
        # Most recent first (ordered by created_at DESC)
        receive_activity = receive_activities[0]

        # Reverse the receive
        service.reverse_activity(receive_activity.id)

        # Verify batch quantity is back to original
        db_batch = MaterialBatch.get_by_id(batch.id)
        self.assertEqual(db_batch.quantity, original_quantity)

        # Verify the RECEIVE activity is deleted
        remaining = Activity.select().where(Activity.id == receive_activity.id).count()
        self.assertEqual(remaining, 0)

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()
        material.delete_instance()

    # ============== CONSUME REVERSAL ==============

    def test_reverse_consume(self):
        """Test reversing a CONSUME activity restores batch quantity."""
        service = MaterialBatchService()
        material = self._create_test_material("Rev Consume Material", True, UnitType.VOLUME)
        self._ensure_default_location()

        # Create batch with 100 mL
        batch = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="REV-CON-001",
                quantity=Decimal("100"),
                unit="mL",
            )
        )
        original_quantity = batch.quantity

        # Consume 30 mL
        service.consume_quantity(
            batch.id,
            DecrementQuantityDTO(quantity=Decimal("30"), unit="mL"),
        )

        # Find the CONSUME activity
        activities = Activity.find_by_batch_id(batch.id)
        consume_activity = next(a for a in activities if a.activity_type == ActivityType.CONSUME)

        # Reverse the consume
        service.reverse_activity(consume_activity.id)

        # Verify batch quantity is back to original
        db_batch = MaterialBatch.get_by_id(batch.id)
        self.assertEqual(db_batch.quantity, original_quantity)

        # Verify the CONSUME activity is deleted
        remaining = Activity.select().where(Activity.id == consume_activity.id).count()
        self.assertEqual(remaining, 0)

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()
        material.delete_instance()

    # ============== MOVE REVERSAL ==============

    def test_reverse_move(self):
        """Test reversing a MOVE activity restores batch location."""
        service = MaterialBatchService()
        material = self._create_test_material("Rev Move Material", True, UnitType.COUNT)
        location_a = self._create_test_location("Location A Rev")
        location_b = self._create_test_location("Location B Rev")

        # Create batch at location A
        batch = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="REV-MOV-001",
                quantity=Decimal("10"),
                unit="units",
                location_id=location_a.id,
            )
        )
        self.assertEqual(batch.location.id, location_a.id)

        # Move to location B
        service.move_batch(batch.id, MoveBatchDTO(to_location_id=location_b.id))

        db_batch = MaterialBatch.get_by_id(batch.id)
        self.assertEqual(db_batch.location.id, location_b.id)

        # Find the MOVE activity
        activities = Activity.find_by_batch_id(batch.id)
        move_activity = next(a for a in activities if a.activity_type == ActivityType.MOVE)

        # Reverse the move
        service.reverse_activity(move_activity.id)

        # Verify batch location is back to A
        db_batch = MaterialBatch.get_by_id(batch.id)
        self.assertEqual(db_batch.location.id, location_a.id)

        # Verify the MOVE activity is deleted
        remaining = Activity.select().where(Activity.id == move_activity.id).count()
        self.assertEqual(remaining, 0)

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()
        material.delete_instance()
        location_a.delete_instance()
        location_b.delete_instance()

    # ============== USE REVERSAL ==============

    def test_reverse_use(self):
        """Test reversing a USE activity deletes it without changing batch state."""
        service = MaterialBatchService()
        activity_service = ActivityService()
        material = self._create_test_material("Rev Use Material", False, UnitType.COUNT)
        self._ensure_default_location()

        # Create batch
        batch = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="REV-USE-001",
                quantity=Decimal("5"),
                unit="units",
            )
        )
        original_quantity = batch.quantity

        # Log a USE activity manually via activity service
        use_activity = activity_service.log_activity(
            CreateActivityDTO(
                activity_type=ActivityType.USE,
                batch_id=batch.id,
                notes="Used in experiment",
            )
        )

        # Reverse the use activity
        service.reverse_activity(use_activity.id)

        # Verify batch is unchanged
        db_batch = MaterialBatch.get_by_id(batch.id)
        self.assertEqual(db_batch.quantity, original_quantity)

        # Verify the USE activity is deleted
        remaining = Activity.select().where(Activity.id == use_activity.id).count()
        self.assertEqual(remaining, 0)

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()
        material.delete_instance()

    # ============== DISCARD REVERSAL ==============

    def test_reverse_discard(self):
        """Test reversing a DISCARD activity reactivates the batch."""
        service = MaterialBatchService()
        material = self._create_test_material("Rev Discard Material", True, UnitType.COUNT)
        self._ensure_default_location()

        # Create batch and add extra activity so delete_batch soft-deletes
        batch = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="REV-DISC-001",
                quantity=Decimal("100"),
                unit="units",
            )
        )
        service.receive_batch(
            batch.id,
            ReceiveBatchDTO(quantity=Decimal("50"), unit="units"),
        )

        # Discard the batch
        service.delete_batch(batch.id, notes="Discarding for test")

        db_batch = MaterialBatch.get_by_id(batch.id)
        self.assertTrue(db_batch.is_discarded())

        # Find the DISCARD activity
        activities = Activity.find_by_batch_id(batch.id)
        discard_activity = next(a for a in activities if a.activity_type == ActivityType.DISCARD)

        # Reverse the discard
        service.reverse_activity(discard_activity.id)

        # Verify batch is ACTIVE again
        db_batch = MaterialBatch.get_by_id(batch.id)
        self.assertEqual(db_batch.status, BatchStatus.ACTIVE)
        self.assertTrue(db_batch.is_active())

        # Verify the DISCARD activity is deleted
        remaining = Activity.select().where(Activity.id == discard_activity.id).count()
        self.assertEqual(remaining, 0)

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        db_batch.delete_instance()
        material.delete_instance()

    # ============== ALIQUOT REVERSAL ==============

    def test_reverse_aliquot(self):
        """Test reversing an ALIQUOT activity restores parent quantity and deletes child."""
        service = MaterialBatchService()
        material = self._create_test_material("Rev Aliquot Material", True, UnitType.VOLUME)
        self._ensure_default_location()

        # Create parent batch with 100 mL
        parent = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="REV-ALQ-PARENT",
                quantity=Decimal("100"),
                unit="mL",
            )
        )
        original_parent_quantity = parent.quantity

        # Create aliquot (take 50 mL from parent)
        aliquot = service.create_aliquot(
            CreateAliquotDTO(
                parent_batch_id=parent.id,
                source_quantity=Decimal("50"),
                source_unit="mL",
                aliquot_quantity=Decimal("50"),
                aliquot_unit="mL",
                aliquot_batch_number="REV-ALQ-CHILD",
            )
        )
        aliquot_id = aliquot.id

        # Verify parent quantity decreased
        db_parent = MaterialBatch.get_by_id(parent.id)
        self.assertEqual(db_parent.quantity, original_parent_quantity - Decimal("0.05"))

        # Find the ALIQUOT activity on the parent
        activities = Activity.find_by_batch_id(parent.id)
        aliquot_activity = next(a for a in activities if a.activity_type == ActivityType.ALIQUOT)

        # Reverse the aliquot
        service.reverse_activity(aliquot_activity.id)

        # Verify parent quantity is restored
        db_parent = MaterialBatch.get_by_id(parent.id)
        self.assertEqual(db_parent.quantity, original_parent_quantity)

        # Verify child batch is deleted
        self.assertFalse(MaterialBatch.select().where(MaterialBatch.id == aliquot_id).exists())

        # Verify ALIQUOT and ALIQUOT_CREATED activities are deleted
        remaining_aliquot = Activity.select().where(Activity.id == aliquot_activity.id).count()
        self.assertEqual(remaining_aliquot, 0)

        remaining_created = (
            Activity.select()
            .where(
                (Activity.batch == aliquot_id)
                & (Activity.activity_type == ActivityType.ALIQUOT_CREATED)
            )
            .count()
        )
        self.assertEqual(remaining_created, 0)

        # Cleanup
        Activity.delete().where(Activity.batch == parent).execute()
        parent.delete_instance()
        material.delete_instance()

    # ============== RELABEL REVERSAL ==============

    def test_reverse_relabel(self):
        """Test reversing a RELABEL activity restores original batch_number and label."""
        service = MaterialBatchService()
        material = self._create_test_material("Rev Relabel Material", True, UnitType.COUNT)
        self._ensure_default_location()

        # Create batch with original values
        batch = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="BATCH-001",
                quantity=Decimal("100"),
                unit="units",
                label="Original",
            )
        )

        # Relabel to new values
        service.relabel_batch(
            batch.id,
            RelabelBatchDTO(batch_number="BATCH-002", label="New Label"),
        )

        db_batch = MaterialBatch.get_by_id(batch.id)
        self.assertEqual(db_batch.batch_number, "BATCH-002")
        self.assertEqual(db_batch.label, "New Label")

        # Find the RELABEL activity
        activities = Activity.find_by_batch_id(batch.id)
        relabel_activity = next(a for a in activities if a.activity_type == ActivityType.RELABEL)

        # Reverse the relabel
        service.reverse_activity(relabel_activity.id)

        # Verify batch_number and label are restored
        db_batch = MaterialBatch.get_by_id(batch.id)
        self.assertEqual(db_batch.batch_number, "BATCH-001")
        self.assertEqual(db_batch.label, "Original")

        # Verify the RELABEL activity is deleted
        remaining = Activity.select().where(Activity.id == relabel_activity.id).count()
        self.assertEqual(remaining, 0)

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()
        material.delete_instance()

    # ============== ERROR CASES ==============

    def test_reverse_aliquot_created_fails(self):
        """Test that reversing ALIQUOT_CREATED directly raises an error."""
        service = MaterialBatchService()
        material = self._create_test_material("Rev ACreated Material", True, UnitType.VOLUME)
        self._ensure_default_location()

        # Create parent and aliquot
        parent = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="REV-AC-PARENT",
                quantity=Decimal("100"),
                unit="mL",
            )
        )
        aliquot = service.create_aliquot(
            CreateAliquotDTO(
                parent_batch_id=parent.id,
                source_quantity=Decimal("20"),
                source_unit="mL",
                aliquot_quantity=Decimal("20"),
                aliquot_unit="mL",
                aliquot_batch_number="REV-AC-CHILD",
            )
        )

        # Find the ALIQUOT_CREATED activity on the child
        activities = Activity.find_by_batch_id(aliquot.id)
        aliquot_created_activity = next(
            a for a in activities if a.activity_type == ActivityType.ALIQUOT_CREATED
        )

        # Try to reverse it
        with self.assertRaises(BadRequestException) as context:
            service.reverse_activity(aliquot_created_activity.id)

        self.assertIn("Cannot reverse ALIQUOT_CREATED", str(context.exception))

        # Cleanup
        Activity.delete().where(Activity.batch == aliquot).execute()
        Activity.delete().where(Activity.batch == parent).execute()
        aliquot.delete_instance()
        parent.delete_instance()
        material.delete_instance()

    def test_reverse_receive_insufficient_quantity_fails(self):
        """Test that reversing RECEIVE fails when batch quantity is insufficient."""
        service = MaterialBatchService()
        material = self._create_test_material("Rev Insuff Material", True, UnitType.VOLUME)
        self._ensure_default_location()

        # Create batch with 100 mL
        batch = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="REV-INSUFF-001",
                quantity=Decimal("100"),
                unit="mL",
            )
        )

        # Receive 50 mL more (total 150 mL in base: 0.15 L)
        service.receive_batch(
            batch.id,
            ReceiveBatchDTO(quantity=Decimal("50"), unit="mL"),
        )

        # Consume 120 mL (remaining 30 mL in base: 0.03 L)
        service.consume_quantity(
            batch.id,
            DecrementQuantityDTO(quantity=Decimal("120"), unit="mL"),
        )

        # Find the second RECEIVE activity (the 50 mL one)
        activities = Activity.find_by_batch_id(batch.id)
        receive_activities = [a for a in activities if a.activity_type == ActivityType.RECEIVE]
        # Most recent receive first
        receive_activity = receive_activities[0]

        # Try to reverse the 50 mL receive — batch only has 30 mL
        with self.assertRaises(BadRequestException) as context:
            service.reverse_activity(receive_activity.id)

        self.assertIn("Cannot reverse RECEIVE", str(context.exception))

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()
        material.delete_instance()

    def test_reverse_aliquot_with_sub_aliquots_fails(self):
        """Test that reversing ALIQUOT fails when child has active sub-aliquots."""
        service = MaterialBatchService()
        material = self._create_test_material("Rev SubAlq Material", True, UnitType.VOLUME)
        self._ensure_default_location()

        # Create parent
        parent = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="REV-SUBALQ-PARENT",
                quantity=Decimal("100"),
                unit="mL",
            )
        )

        # Create child aliquot
        child = service.create_aliquot(
            CreateAliquotDTO(
                parent_batch_id=parent.id,
                source_quantity=Decimal("50"),
                source_unit="mL",
                aliquot_quantity=Decimal("50"),
                aliquot_unit="mL",
                aliquot_batch_number="REV-SUBALQ-CHILD",
            )
        )

        # Create sub-aliquot from child
        grandchild = service.create_aliquot(
            CreateAliquotDTO(
                parent_batch_id=child.id,
                source_quantity=Decimal("10"),
                source_unit="mL",
                aliquot_quantity=Decimal("10"),
                aliquot_unit="mL",
                aliquot_batch_number="REV-SUBALQ-GRANDCHILD",
            )
        )

        # Find the ALIQUOT activity on the parent (for creating the child)
        activities = Activity.find_by_batch_id(parent.id)
        aliquot_activity = next(a for a in activities if a.activity_type == ActivityType.ALIQUOT)

        # Try to reverse — child has active sub-aliquots
        with self.assertRaises(BadRequestException) as context:
            service.reverse_activity(aliquot_activity.id)

        self.assertIn("active sub-aliquot", str(context.exception))

        # Cleanup
        Activity.delete().where(Activity.batch == grandchild).execute()
        Activity.delete().where(Activity.batch == child).execute()
        Activity.delete().where(Activity.batch == parent).execute()
        grandchild.delete_instance()
        child.delete_instance()
        parent.delete_instance()
        material.delete_instance()

    def test_reverse_nonexistent_activity_fails(self):
        """Test that reversing a non-existent activity raises an error."""
        service = MaterialBatchService()

        with self.assertRaises(Exception):
            service.reverse_activity("non-existent-id")
