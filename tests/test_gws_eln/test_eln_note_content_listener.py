from decimal import Decimal

from gws_core import (
    BadRequestException,
    BaseTestCase,
    NoteSaveDTO,
    NoteService,
    RichText,
    RichTextBlock,
)
from gws_eln.activities.activity import Activity
from gws_eln.activities.activity_type import ActivityType
from gws_eln.core.unit_type import UnitType
from gws_eln.materials.material import Material
from gws_eln.materials.material_batch import MaterialBatch
from gws_eln.materials.material_batch_dto import (
    CreateBatchDTO,
    DecrementQuantityDTO,
    ReceiveBatchDTO,
)
from gws_eln.materials.material_batch_service import MaterialBatchService
from gws_eln.materials.material_dto import CreateMaterialDTO
from gws_eln.materials.material_service import MaterialService
from gws_eln.notes.eln_note_service import ElnNoteService
from gws_eln.rich_text.rich_text_block_material_activity import RichTextBlockMaterialActivity
from gws_eln.user.eln_user_sync_service import ElnUserSyncService


# test_eln_note_content_listener.py
class TestElnNoteContentListener(BaseTestCase):
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

    def _create_batch(self, material: Material, quantity_ml: Decimal) -> MaterialBatch:
        """Helper to create a batch with given quantity in mL."""
        service = MaterialBatchService()
        result = service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number=f"BATCH-{quantity_ml}",
                quantity=quantity_ml,
                unit="mL",
            )
        )
        return result.batch

    def _build_activity_block(
        self, activity_id: str | None, block_id: str = "block-1"
    ) -> RichTextBlock:
        """Helper to build a materialActivity RichTextBlock."""
        block_data = RichTextBlockMaterialActivity(activity_id=activity_id)
        return RichTextBlock.from_data(block_data, id_=block_id)

    # ============== Test 1: Removing a materialActivity block reverses the activity ==============

    def test_removing_block_reverses_activity(self):
        """Removing a materialActivity block from note content reverses the activity."""
        material = self._create_test_material("Listener Test Material")
        service = MaterialBatchService()

        # Create batch with 100 mL
        batch = self._create_batch(material, Decimal("100"))

        # Consume 30 mL (batch now at 70 mL)
        service.consume_quantity(
            batch_id=batch.id,
            dto=DecrementQuantityDTO(
                quantity=Decimal("30"),
                unit="mL",
                notes="Consumed for test",
            ),
        )

        # Get the CONSUME activity
        activities = Activity.find_by_batch_id(batch.id)
        consume_activity = [a for a in activities if a.activity_type == ActivityType.CONSUME][0]

        # Create a note
        note = ElnNoteService().create_note(NoteSaveDTO(title="Test Listener Note"))

        # Build content WITH the materialActivity block
        activity_block = self._build_activity_block(consume_activity.id)
        content_with_block = RichText.create_rich_text_dto(
            [
                RichText.create_paragraph("p1", "Some text"),
                activity_block,
            ]
        )

        # Save note content (initial save with block)
        NoteService.update_content(note.id, content_with_block)

        # Now build new content WITHOUT the materialActivity block
        content_without_block = RichText.create_rich_text_dto(
            [
                RichText.create_paragraph("p1", "Some text"),
            ]
        )

        # Save — this should trigger the listener and reverse the CONSUME activity
        NoteService.update_content(note.id, content_without_block)

        # Verify: batch quantity is back to 100 mL (0.1 L in base units)
        refreshed_batch = MaterialBatch.get_by_id(batch.id)
        self.assertEqual(refreshed_batch.quantity, Decimal("0.100000000000"))

        # Verify: the CONSUME activity is deleted
        remaining_activities = [
            a
            for a in Activity.find_by_batch_id(batch.id)
            if a.activity_type == ActivityType.CONSUME
        ]
        self.assertEqual(len(remaining_activities), 0)

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()
        material.delete_instance()

    # ============== Test 2: Deleting a note reverses all materialActivity blocks ==============

    def test_deleting_note_reverses_all_blocks(self):
        """Deleting a note reverses all materialActivity blocks in the note."""
        material = self._create_test_material("Delete Note Material")
        service = MaterialBatchService()

        # Create batch with 100 mL, consume 30 mL (batch at 70 mL)
        batch = self._create_batch(material, Decimal("100"))
        service.consume_quantity(
            batch_id=batch.id,
            dto=DecrementQuantityDTO(
                quantity=Decimal("30"),
                unit="mL",
                notes="Consumed for delete test",
            ),
        )

        # Get the CONSUME activity
        activities = Activity.find_by_batch_id(batch.id)
        consume_activity = [a for a in activities if a.activity_type == ActivityType.CONSUME][0]

        # Create note with materialActivity block
        note = ElnNoteService().create_note(NoteSaveDTO(title="Delete Test Note"))
        activity_block = self._build_activity_block(consume_activity.id)
        content = RichText.create_rich_text_dto(
            [
                RichText.create_paragraph("p1", "Some text"),
                activity_block,
            ]
        )
        NoteService.update_content(note.id, content)

        # Delete the note — should reverse the CONSUME activity
        NoteService.delete(note.id)

        # Verify: batch quantity back to 100 mL (0.1 L in base units)
        refreshed_batch = MaterialBatch.get_by_id(batch.id)
        self.assertEqual(refreshed_batch.quantity, Decimal("0.100000000000"))

        # Verify: CONSUME activity deleted
        remaining_activities = [
            a
            for a in Activity.find_by_batch_id(batch.id)
            if a.activity_type == ActivityType.CONSUME
        ]
        self.assertEqual(len(remaining_activities), 0)

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()
        material.delete_instance()

    # ============== Test 3: Block with no activity_id is ignored ==============

    def test_block_without_activity_id_is_ignored(self):
        """Removing a materialActivity block with no activity_id does not cause errors."""
        # Create a note
        note = ElnNoteService().create_note(NoteSaveDTO(title="No Activity ID Note"))

        # Build content with a materialActivity block that has activity_id=None
        activity_block = self._build_activity_block(None)
        content_with_block = RichText.create_rich_text_dto(
            [
                RichText.create_paragraph("p1", "Some text"),
                activity_block,
            ]
        )
        NoteService.update_content(note.id, content_with_block)

        # Remove the block
        content_without_block = RichText.create_rich_text_dto(
            [
                RichText.create_paragraph("p1", "Some text"),
            ]
        )

        # Should not raise any error
        NoteService.update_content(note.id, content_without_block)

    # ============== Test 4: Activity reversal failure rolls back note save ==============

    def test_reversal_failure_rolls_back_note_save(self):
        """If reversing an activity fails, the note save is rolled back."""
        material = self._create_test_material("Rollback Test Material")
        service = MaterialBatchService()

        # Create batch (100 mL), receive 50 mL (total 150 mL = 0.15 L)
        batch = self._create_batch(material, Decimal("100"))
        service.receive_batch(
            batch_id=batch.id,
            dto=ReceiveBatchDTO(
                quantity=Decimal("50"),
                unit="mL",
                notes="Additional stock",
            ),
        )

        # Then consume 120 mL (remaining 30 mL = 0.03 L)
        service.consume_quantity(
            batch_id=batch.id,
            dto=DecrementQuantityDTO(
                quantity=Decimal("120"),
                unit="mL",
                notes="Big consumption",
            ),
        )

        # Get the RECEIVE activity (50 mL)
        activities = Activity.find_by_batch_id(batch.id)
        receive_activities = [a for a in activities if a.activity_type == ActivityType.RECEIVE]
        # There are 2 RECEIVE activities (initial 100mL + 50mL). Get the 50mL one.
        receive_50_activity = [
            a for a in receive_activities if a.quantity == Decimal("0.050000000000")
        ][0]

        # Create note with a materialActivity block referencing the RECEIVE (50 mL) activity
        note = ElnNoteService().create_note(NoteSaveDTO(title="Rollback Test Note"))
        activity_block = self._build_activity_block(receive_50_activity.id)
        content_with_block = RichText.create_rich_text_dto(
            [
                RichText.create_paragraph("p1", "Some text"),
                activity_block,
            ]
        )
        NoteService.update_content(note.id, content_with_block)

        # Now remove the block — this should try to reverse RECEIVE (50 mL),
        # but batch only has 30 mL → should fail
        content_without_block = RichText.create_rich_text_dto(
            [
                RichText.create_paragraph("p1", "Some text"),
            ]
        )

        with self.assertRaises(BadRequestException):
            NoteService.update_content(note.id, content_without_block)

        # Verify: note content is unchanged (still has the block)
        reloaded_note = NoteService.get_by_id_and_check(note.id)
        block_types = [b.type for b in reloaded_note.content.blocks]
        self.assertIn("RICH_TEXT_BLOCK.gws_eln.materialActivity", block_types)

        # Verify: batch quantity unchanged (30 mL = 0.03 L)
        refreshed_batch = MaterialBatch.get_by_id(batch.id)
        self.assertEqual(refreshed_batch.quantity, Decimal("0.030000000000"))

        # Verify: RECEIVE activity still exists
        receive_still_exists = Activity.get_by_id(receive_50_activity.id)
        self.assertIsNotNone(receive_still_exists)

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()
        material.delete_instance()

    # ============== Test 5: Multiple blocks removed in one save ==============

    def test_multiple_blocks_removed_in_one_save(self):
        """Removing multiple materialActivity blocks reverses all their activities."""
        material = self._create_test_material("Multi Block Material")
        service = MaterialBatchService()

        # Create batch (100 mL), consume 20 mL, then consume 10 mL (remaining 70 mL)
        batch = self._create_batch(material, Decimal("100"))
        service.consume_quantity(
            batch_id=batch.id,
            dto=DecrementQuantityDTO(
                quantity=Decimal("20"),
                unit="mL",
                notes="First consumption",
            ),
        )
        service.consume_quantity(
            batch_id=batch.id,
            dto=DecrementQuantityDTO(
                quantity=Decimal("10"),
                unit="mL",
                notes="Second consumption",
            ),
        )

        # Get both CONSUME activities
        activities = Activity.find_by_batch_id(batch.id)
        consume_activities = [a for a in activities if a.activity_type == ActivityType.CONSUME]
        self.assertEqual(len(consume_activities), 2)

        # Create note with two materialActivity blocks
        note = ElnNoteService().create_note(NoteSaveDTO(title="Multi Block Note"))
        block1 = self._build_activity_block(consume_activities[0].id, "block-1")
        block2 = self._build_activity_block(consume_activities[1].id, "block-2")
        content_with_blocks = RichText.create_rich_text_dto(
            [
                RichText.create_paragraph("p1", "Some text"),
                block1,
                block2,
            ]
        )
        NoteService.update_content(note.id, content_with_blocks)

        # Remove both blocks
        content_without_blocks = RichText.create_rich_text_dto(
            [
                RichText.create_paragraph("p1", "Some text"),
            ]
        )
        NoteService.update_content(note.id, content_without_blocks)

        # Verify: batch quantity back to 100 mL (0.1 L in base units)
        refreshed_batch = MaterialBatch.get_by_id(batch.id)
        self.assertEqual(refreshed_batch.quantity, Decimal("0.100000000000"))

        # Verify: both CONSUME activities deleted
        remaining_consume = [
            a
            for a in Activity.find_by_batch_id(batch.id)
            if a.activity_type == ActivityType.CONSUME
        ]
        self.assertEqual(len(remaining_consume), 0)

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()
        material.delete_instance()

    # ============== Test 6: Content update with no materialActivity changes ==============

    def test_content_update_without_activity_changes(self):
        """Updating only paragraph text does not reverse any activities."""
        material = self._create_test_material("No Change Material")
        service = MaterialBatchService()

        # Create batch (100 mL), consume 30 mL (batch at 70 mL)
        batch = self._create_batch(material, Decimal("100"))
        service.consume_quantity(
            batch_id=batch.id,
            dto=DecrementQuantityDTO(
                quantity=Decimal("30"),
                unit="mL",
                notes="Consumed for no-change test",
            ),
        )

        # Get the CONSUME activity
        activities = Activity.find_by_batch_id(batch.id)
        consume_activity = [a for a in activities if a.activity_type == ActivityType.CONSUME][0]

        # Create note with a paragraph + materialActivity block
        note = ElnNoteService().create_note(NoteSaveDTO(title="No Change Note"))
        activity_block = self._build_activity_block(consume_activity.id)
        content = RichText.create_rich_text_dto(
            [
                RichText.create_paragraph("p1", "Original text"),
                activity_block,
            ]
        )
        NoteService.update_content(note.id, content)

        # Update only the paragraph text (block stays the same)
        updated_content = RichText.create_rich_text_dto(
            [
                RichText.create_paragraph("p1", "Updated text"),
                activity_block,
            ]
        )
        NoteService.update_content(note.id, updated_content)

        # Verify: no reversal — batch quantity unchanged (70 mL = 0.07 L)
        refreshed_batch = MaterialBatch.get_by_id(batch.id)
        self.assertEqual(refreshed_batch.quantity, Decimal("0.070000000000"))

        # Verify: activity still exists
        activity_still_exists = Activity.get_by_id(consume_activity.id)
        self.assertIsNotNone(activity_still_exists)

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()
        material.delete_instance()
