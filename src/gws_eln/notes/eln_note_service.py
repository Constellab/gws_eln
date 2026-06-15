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
from gws_eln.core.eln_db_manager import ElnDbManager
from gws_eln.notes.eln_note_dto import LinkNoteActivityDTO
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
    def link_activity(self, dto: LinkNoteActivityDTO) -> Note:
        """Link an existing activity to a note block.

        The activity is created beforehand in the app (any type, including the
        split/combine/dilute/concentrate transforms); here the note block only
        stores its id and renders it (the block is a view onto an activity,
        never its owner). This never mutates inventory.

        :param dto: DTO with note_id, note_block_id, activity_id and the current
            rich text content
        :type dto: LinkNoteActivityDTO
        :return: The updated note
        :rtype: Note
        :raises BadRequestException: If the block is missing or is not an Item
            Activity block
        """
        # Verify the note and the activity exist
        NoteService.get_by_id_and_check(dto.note_id)
        ActivityService().get_by_id_and_check(dto.activity_id)

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

        block.set_data(RichTextBlockItemActivity(activity_id=dto.activity_id))
        rich_text.replace_block_by_id(block.id, block)

        return NoteService.update_content(dto.note_id, rich_text.to_dto())

    @ElnDbManager.transaction()
    def remove_activity_block(self, note_id: str, note_block_id: str, rich_text_content) -> Note:
        """Remove an (unlinked) item-activity block from a note.

        Used when the user aborts creating the activity: the editor already
        inserted the block, so on cancel it is dropped to avoid an empty
        "Activity ID missing" block. Never touches inventory.

        :param note_id: The note holding the block
        :param note_block_id: The block to remove
        :param rich_text_content: The current rich text content of the note
        :return: The updated note
        :rtype: Note
        """
        NoteService.get_by_id_and_check(note_id)

        rich_text = RichText(rich_text_content)
        if rich_text.get_block_by_id(note_block_id) is not None:
            rich_text.remove_block_by_id(note_block_id)

        return NoteService.update_content(note_id, rich_text.to_dto())

    def get_activity(
        self,
        activity_id: str,
    ) -> Activity:
        """Get the activity for the given activity ID.

        :param activity_id: The ID of the activity
        :type activity_id: str
        :return: The activity
        :rtype: Activity
        """
        return ActivityService().get_by_id_and_check(activity_id)
