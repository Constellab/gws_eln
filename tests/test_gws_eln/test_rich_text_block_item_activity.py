"""Test suite for RichTextBlockItemActivity.

The block stores only an activity_id and renders the activity's inputs -> outputs
(N-to-M lineage) as HTML / markdown when the note content is served.
Covers serialization and the to_html() / to_markdown() rendering paths.
"""

from decimal import Decimal

from gws_core import BaseTestCase
from gws_eln.core.unit_type import UnitType
from gws_eln.items.item_dto import CreateItemDTO, DecrementQuantityDTO, MoveItemDTO
from gws_eln.items.item_service import ItemService
from gws_eln.items.item_sheet_dto import CreateItemSheetDTO
from gws_eln.items.item_sheet_service import ItemSheetService
from gws_eln.locations.location_dto import CreateLocationDTO
from gws_eln.locations.location_service import LocationService
from gws_eln.rich_text.rich_text_block_item_activity import RichTextBlockItemActivity
from gws_eln.user.eln_user_sync_service import ElnUserSyncService


class TestRichTextBlockItemActivity(BaseTestCase):
    """Test suite for RichTextBlockItemActivity."""

    @classmethod
    def init_before_test(cls):
        super().init_before_test()
        ElnUserSyncService().sync_all_users()

    # ------------------------------------------------------------------ helpers

    def _consumable_item(self, code: str, *, unit_type=UnitType.VOLUME, quantity="100", unit="L"):
        sheet = ItemSheetService().create_item_sheet(
            CreateItemSheetDTO(name=f"Sheet {code}", code=code, unit_type=unit_type)
        )
        return ItemService().create_item(
            CreateItemDTO(item_sheet_id=sheet.id, quantity=Decimal(quantity), unit=unit, label="Test item")
        ).item

    # ------------------------------------------------------ serialization

    def test_block_serialization_with_activity_id(self):
        block = RichTextBlockItemActivity(activity_id="test-123")
        json_dict = block.to_json_dict()
        self.assertEqual(json_dict["activity_id"], "test-123")
        self.assertEqual(RichTextBlockItemActivity.from_json(json_dict).activity_id, "test-123")

    def test_block_serialization_with_no_activity_id(self):
        block = RichTextBlockItemActivity(activity_id=None)
        json_dict = block.to_json_dict()
        self.assertIsNone(json_dict.get("activity_id"))
        self.assertIsNone(RichTextBlockItemActivity.from_json(json_dict).activity_id)

    # ------------------------------------------------------------- to_html

    def test_to_html_with_existing_activity(self):
        item = self._consumable_item("RTC1")
        activity = ItemService().consume_quantity(
            item.id, DecrementQuantityDTO(quantity=Decimal(25), unit="L", notes="Used in experiment")
        ).activity

        html = RichTextBlockItemActivity(activity_id=activity.id).to_html()
        self.assertIn("Consume", html)
        self.assertIn(item.code, html)
        self.assertIn("material-activity", html)
        self.assertIn("Used in experiment", html)

    def test_to_html_with_missing_activity(self):
        html = RichTextBlockItemActivity(activity_id="non-existent-id").to_html()
        self.assertIn("not found", html)
        self.assertIn("error", html)

    def test_to_html_with_no_activity_id(self):
        html = RichTextBlockItemActivity(activity_id=None).to_html()
        self.assertIn("missing", html)
        self.assertIn("error", html)

    def test_to_html_with_move_activity(self):
        loc_a = LocationService().create_location(CreateLocationDTO(name="Lab A RTM"))
        loc_b = LocationService().create_location(CreateLocationDTO(name="Lab B RTM"))
        sheet = ItemSheetService().create_item_sheet(
            CreateItemSheetDTO(name="Sheet RTM1", code="RTM1", unit_type=UnitType.COUNT)
        )
        item = ItemService().create_item(
            CreateItemDTO(
                item_sheet_id=sheet.id, quantity=Decimal(5), unit="units", location_id=loc_a.id,
                label="Test item"
            )
        ).item
        activity = ItemService().move_item(item.id, MoveItemDTO(to_location_id=loc_b.id)).activity

        html = RichTextBlockItemActivity(activity_id=activity.id).to_html()
        self.assertIn("Move", html)
        self.assertIn("Lab A RTM", html)
        self.assertIn("Lab B RTM", html)
        self.assertIn("&rarr;", html)

    # --------------------------------------------------------- to_markdown

    def test_to_markdown_with_existing_activity(self):
        item = self._consumable_item("RTM2")
        activity = ItemService().consume_quantity(
            item.id, DecrementQuantityDTO(quantity=Decimal(10), unit="L")
        ).activity

        markdown = RichTextBlockItemActivity(activity_id=activity.id).to_markdown()
        self.assertIn("**Consume**", markdown)
        self.assertIn(item.code, markdown)

    def test_to_markdown_with_missing_activity(self):
        self.assertEqual(
            RichTextBlockItemActivity(activity_id="non-existent-id").to_markdown(),
            "[Activity: not found]",
        )

    def test_to_markdown_with_no_activity_id(self):
        self.assertEqual(
            RichTextBlockItemActivity(activity_id=None).to_markdown(), "[Activity: missing]"
        )
