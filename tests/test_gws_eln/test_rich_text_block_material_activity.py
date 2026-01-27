"""
Test suite for RichTextBlockMaterialActivity.

Tests Step 3 from ELN dev steps: Block RichTextBlockMaterialActivity.

Tests cover:
- Block serialization/deserialization with and without activity_id
- to_html() with existing activity, missing activity, and no activity_id
- to_markdown() with existing and missing activities
"""

from decimal import Decimal

from gws_core import BaseTestCase
from gws_eln.activities.activity import Activity
from gws_eln.activities.activity_dto import CreateActivityDTO
from gws_eln.activities.activity_service import ActivityService
from gws_eln.activities.activity_type import ActivityType
from gws_eln.core.unit_type import UnitType
from gws_eln.locations.location import Location
from gws_eln.locations.location_dto import CreateLocationDTO
from gws_eln.locations.location_service import LocationService
from gws_eln.materials.material import Material
from gws_eln.materials.material_batch_dto import CreateBatchDTO
from gws_eln.materials.material_batch_service import MaterialBatchService
from gws_eln.materials.material_dto import CreateMaterialDTO
from gws_eln.materials.material_service import MaterialService
from gws_eln.rich_text.rich_text_block_material_activity import RichTextBlockMaterialActivity
from gws_eln.user.eln_user_sync_service import ElnUserSyncService


class TestRichTextBlockMaterialActivity(BaseTestCase):
    """Test suite for RichTextBlockMaterialActivity"""

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

    # ============== SERIALIZATION / DESERIALIZATION TESTS ==============

    def test_block_serialization_with_activity_id(self):
        """Test block serialization/deserialization with activity_id"""
        block_data = RichTextBlockMaterialActivity(activity_id="test-123")

        # Serialize to JSON dict
        json_dict = block_data.to_json_dict()
        self.assertEqual(json_dict["activity_id"], "test-123")

        # Deserialize from JSON
        restored = RichTextBlockMaterialActivity.from_json(json_dict)
        self.assertEqual(restored.activity_id, "test-123")

    def test_block_serialization_with_no_activity_id(self):
        """Test block serialization/deserialization with no activity_id"""
        block_data = RichTextBlockMaterialActivity(activity_id=None)

        # Serialize to JSON dict
        json_dict = block_data.to_json_dict()
        self.assertIsNone(json_dict.get("activity_id"))

        # Deserialize from JSON
        restored = RichTextBlockMaterialActivity.from_json(json_dict)
        self.assertIsNone(restored.activity_id)

    # ============== to_html() TESTS ==============

    def test_to_html_with_existing_activity(self):
        """Test to_html() with an existing activity in the database"""
        material = self._create_test_material("HTML Test Material", True, UnitType.VOLUME)
        self._ensure_default_location()
        batch_service = MaterialBatchService()

        # Create batch
        batch = batch_service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="HTML-001",
                quantity=Decimal("100"),
                unit="L",
            )
        )

        # Create a CONSUME activity via ActivityService
        activity_service = ActivityService()
        activity = activity_service.log_activity(
            CreateActivityDTO(
                activity_type=ActivityType.CONSUME,
                batch_id=batch.id,
                quantity=Decimal("25"),
                unit_type=UnitType.VOLUME,
                notes="Used in experiment",
            )
        )

        # Create block with the activity's ID
        block_data = RichTextBlockMaterialActivity(activity_id=activity.id)
        html = block_data.to_html()

        # Verify HTML contains activity type, batch number, material name
        self.assertIn("Consume", html)
        self.assertIn("HTML-001", html)
        self.assertIn("HTML Test Material", html)
        self.assertIn("material-activity", html)
        self.assertIn("Used in experiment", html)

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()
        material.delete_instance()

    def test_to_html_with_missing_activity(self):
        """Test to_html() with a non-existent activity_id"""
        block_data = RichTextBlockMaterialActivity(activity_id="non-existent-id")
        html = block_data.to_html()

        self.assertIn("not found", html)
        self.assertIn("material-activity", html)
        self.assertIn("error", html)

    def test_to_html_with_no_activity_id(self):
        """Test to_html() with no activity_id"""
        block_data = RichTextBlockMaterialActivity(activity_id=None)
        html = block_data.to_html()

        self.assertIn("missing", html)
        self.assertIn("material-activity", html)
        self.assertIn("error", html)

    def test_to_html_with_move_activity(self):
        """Test to_html() renders location info for MOVE activities"""
        material = self._create_test_material("Move HTML Material", True, UnitType.COUNT)
        location_from = self._create_test_location("Lab A")
        location_to = self._create_test_location("Lab B")

        batch_service = MaterialBatchService()
        batch = batch_service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="MOVE-HTML",
                quantity=Decimal("50"),
                unit="units",
                location_id=location_from.id,
            )
        )

        # Create a MOVE activity with locations
        activity_service = ActivityService()
        activity = activity_service.log_activity(
            CreateActivityDTO(
                activity_type=ActivityType.MOVE,
                batch_id=batch.id,
                from_location_id=location_from.id,
                to_location_id=location_to.id,
            )
        )

        block_data = RichTextBlockMaterialActivity(activity_id=activity.id)
        html = block_data.to_html()

        # Verify location rendering
        self.assertIn("Move", html)
        self.assertIn("Lab A", html)
        self.assertIn("Lab B", html)
        self.assertIn("&rarr;", html)

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()
        material.delete_instance()
        location_from.delete_instance()
        location_to.delete_instance()

    # ============== to_markdown() TESTS ==============

    def test_to_markdown_with_existing_activity(self):
        """Test to_markdown() with an existing activity"""
        material = self._create_test_material("MD Test Material", True, UnitType.VOLUME)
        self._ensure_default_location()
        batch_service = MaterialBatchService()

        batch = batch_service.create_batch(
            CreateBatchDTO(
                material_id=material.id,
                batch_number="MD-001",
                quantity=Decimal("100"),
                unit="L",
            )
        )

        activity_service = ActivityService()
        activity = activity_service.log_activity(
            CreateActivityDTO(
                activity_type=ActivityType.CONSUME,
                batch_id=batch.id,
                quantity=Decimal("10"),
                unit_type=UnitType.VOLUME,
            )
        )

        block_data = RichTextBlockMaterialActivity(activity_id=activity.id)
        markdown = block_data.to_markdown()

        self.assertIn("**Consume**", markdown)
        self.assertIn("MD-001", markdown)

        # Cleanup
        Activity.delete().where(Activity.batch == batch).execute()
        batch.delete_instance()
        material.delete_instance()

    def test_to_markdown_with_missing_activity(self):
        """Test to_markdown() with a non-existent activity_id"""
        block_data = RichTextBlockMaterialActivity(activity_id="non-existent-id")
        markdown = block_data.to_markdown()

        self.assertEqual(markdown, "[Activity: not found]")

    def test_to_markdown_with_no_activity_id(self):
        """Test to_markdown() with no activity_id"""
        block_data = RichTextBlockMaterialActivity(activity_id=None)
        markdown = block_data.to_markdown()

        self.assertEqual(markdown, "[Activity: missing]")
