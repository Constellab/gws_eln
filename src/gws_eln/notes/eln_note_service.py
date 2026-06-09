from typing import Any

from gws_core import (
    BadRequestException,
    CurrentUserService,
    EntityTagList,
    Note,
    NoteSaveDTO,
    NoteService,
    RichText,
    Tag,
    TagEntityType,
    TagOrigin,
    TagOriginType,
)
from gws_eln.activities.activity import Activity
from gws_eln.activities.activity_service import ActivityService
from gws_eln.activities.activity_type import ActivityType
from gws_eln.core.eln_db_manager import ElnDbManager
from gws_eln.items.item_activity_dto import ItemActivityResult
from gws_eln.items.item_dto import (
    CreateItemDTO,
    DecrementQuantityDTO,
    DiscardItemDTO,
    MoveItemDTO,
    ReceiveItemDTO,
    RelabelItemDTO,
    UseItemDTO,
)
from gws_eln.items.item_service import ItemService
from gws_eln.notes.eln_note_dto import AddNoteActivityDTO
from gws_eln.rich_text.rich_text_block_item_activity import RichTextBlockItemActivity


class ElnNoteService:
    ELN_NOTE_TAG_KEY = "eln"
    ELN_NOTE_TAG_VALUE = "note"

    @ElnDbManager.transaction()
    def create_note(self, save_note_dto: NoteSaveDTO) -> Note:
        """Create a new note with the given title.

        :param title: The title of the note.
        :return: The ID of the created note.
        :rtype: str
        """
        note = NoteService.create(save_note_dto)

        current_user = CurrentUserService.get_and_check_current_user()

        note_tags = EntityTagList(TagEntityType.NOTE, note.id)
        tag = Tag(self.ELN_NOTE_TAG_KEY, self.ELN_NOTE_TAG_VALUE)
        tag.origins.add_origin(TagOrigin(TagOriginType.SYSTEM, current_user.id))
        note_tags.add_tag(tag)
        return note

    def note_is_eln_note(self, note_id: str) -> bool:
        """Check if the given note is an ELN note.

        :param note: The note to check.
        :type note: Note
        :return: True if the note is an ELN note, False otherwise.
        :rtype: bool
        """
        note_tags = EntityTagList.find_by_entity(TagEntityType.NOTE, note_id)
        return note_tags.has_tag(Tag(self.ELN_NOTE_TAG_KEY, self.ELN_NOTE_TAG_VALUE))

    @ElnDbManager.transaction()
    def add_activity(self, dto: AddNoteActivityDTO) -> Note:
        """Add an item activity from a note block.

        Verifies the note exists, builds the appropriate item action DTO
        based on the activity type, then delegates to ItemService.

        :param dto: DTO containing note_id, note_block_id, activity_type, and activity_data
        :type dto: AddNoteActivityDTO
        :return: The item and activity result
        :rtype: ItemActivityResult
        :raises BadRequestException: If the activity type is unsupported or data is invalid
        """
        # Verify the note exists
        NoteService.get_by_id_and_check(dto.note_id)

        rich_text = RichText(dto.rich_text_content)

        block = rich_text.get_block_by_id(dto.note_block_id)
        if block is None:
            raise BadRequestException(
                f"Note block with ID {dto.note_block_id} not found in note {dto.note_id}"
            )

        if block.type != RichTextBlockItemActivity.get_typing_name():
            raise BadRequestException(
                f"Note block with ID {dto.note_block_id} is not an Item Activity block"
            )

        item_service = ItemService()
        activity_data = dto.activity_data

        handler = self._get_activity_handler(dto.activity_type)
        item_result = handler(item_service, dto.item_id, activity_data, dto.note_id)

        # if activity was created, set the activity id in the block data
        activity = item_result.activity
        if activity:
            block.set_data(RichTextBlockItemActivity(activity_id=activity.id))
            rich_text.replace_block_by_id(block.id, block)
        else:
            # if no activity was created, remove the block from the note
            rich_text.remove_block_by_id(dto.note_block_id)

        return NoteService.update_content(dto.note_id, rich_text.to_dto())

    def _get_activity_handler(self, activity_type: ActivityType):
        """Return the handler method for the given activity type.

        :param activity_type: The type of activity to handle
        :type activity_type: ActivityType
        :return: The handler method
        :raises BadRequestException: If the activity type is unsupported
        """
        handlers = {
            ActivityType.RECEIVE: self._handle_receive,
            ActivityType.CONSUME: self._handle_consume,
            ActivityType.MOVE: self._handle_move,
            ActivityType.USE: self._handle_use,
            ActivityType.DISCARD: self._handle_discard,
            ActivityType.RELABEL: self._handle_relabel,
        }
        handler = handlers.get(activity_type)
        if handler is None:
            raise BadRequestException(
                f"Unsupported activity type for note activity: {activity_type.value}"
            )
        return handler

    def _handle_receive(
        self,
        item_service: ItemService,
        item_id: str | None,
        activity_data: dict[str, Any],
        note_id: str,
    ) -> ItemActivityResult:
        """Handle a RECEIVE activity.

        RECEIVE is the single way an item enters the inventory:
        - new item (an ``item_sheet_id`` is provided, no existing item) → create the item;
        - existing item (an ``item_id`` is targeted) → increment its quantity.
        Both log a RECEIVE activity.
        """
        if activity_data.get("item_sheet_id"):
            create_dto = CreateItemDTO(
                item_sheet_id=activity_data["item_sheet_id"],
                item_number=activity_data.get("item_number"),
                quantity=activity_data["quantity"],
                unit=activity_data["unit"],
                location_id=activity_data.get("location_id"),
                supplier_id=activity_data.get("supplier_id"),
                expiry_date=activity_data.get("expiry_date"),
                label=activity_data.get("label"),
                notes=activity_data.get("notes"),
                note_id=note_id,
            )
            return item_service.create_item(create_dto)

        receive_dto = ReceiveItemDTO(
            quantity=activity_data["quantity"],
            unit=activity_data["unit"],
            notes=activity_data.get("notes"),
            note_id=note_id,
        )
        return item_service.receive_item(item_id, receive_dto)

    def _handle_consume(
        self,
        item_service: ItemService,
        item_id: str,
        activity_data: dict[str, Any],
        note_id: str,
    ) -> ItemActivityResult:
        item_dto = DecrementQuantityDTO(
            quantity=activity_data["quantity"],
            unit=activity_data["unit"],
            notes=activity_data.get("notes"),
            note_id=note_id,
        )
        return item_service.consume_quantity(item_id, item_dto)

    def _handle_move(
        self,
        item_service: ItemService,
        item_id: str,
        activity_data: dict[str, Any],
        note_id: str,
    ) -> ItemActivityResult:
        item_dto = MoveItemDTO(
            to_location_id=activity_data["to_location_id"],
            note_id=note_id,
        )
        return item_service.move_item(item_id, item_dto)

    def _handle_use(
        self,
        item_service: ItemService,
        item_id: str,
        activity_data: dict[str, Any],
        note_id: str,
    ) -> ItemActivityResult:
        item_dto = UseItemDTO(
            notes=activity_data.get("notes"),
            note_id=note_id,
        )
        return item_service.use_item(item_id, item_dto)

    def _handle_discard(
        self,
        item_service: ItemService,
        item_id: str,
        activity_data: dict[str, Any],
        note_id: str,
    ) -> ItemActivityResult:
        item_dto = DiscardItemDTO(
            notes=activity_data.get("notes"),
            note_id=note_id,
        )
        return item_service.discard_item(item_id, item_dto)

    def _handle_relabel(
        self,
        item_service: ItemService,
        item_id: str,
        activity_data: dict[str, Any],
        note_id: str,
    ) -> ItemActivityResult:
        item_dto = RelabelItemDTO(
            item_number=activity_data.get("item_number"),
            label=activity_data.get("label"),
            note_id=note_id,
        )
        return item_service.relabel_item(item_id, item_dto)

    def get_activity(
        self,
        activity_id: str,
    ) -> Activity:
        """Get the item activity block for the given activity ID.

        :param activity_id: The ID of the activity
        :type activity_id: str
        :return: The item activity block
        :rtype: RichTextBlockItemActivity
        """
        return ActivityService().get_by_id_and_check(activity_id)
