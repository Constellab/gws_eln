from gws_core import (
    CurrentUserService,
    EntityTagList,
    Note,
    NoteSaveDTO,
    NoteService,
    Tag,
    TagEntityType,
    TagOrigin,
    TagOriginType,
)
from gws_eln.core.eln_db_manager import ElnDbManager


class ElnNoteService:
    ELN_NOTE_TAG = Tag("eln", "note")
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
