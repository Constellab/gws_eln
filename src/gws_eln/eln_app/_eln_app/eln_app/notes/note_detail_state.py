"""State for the note detail page."""

import reflex as rx
from gws_core import Note, NoteDTO, NoteService, RichTextDTO
from gws_reflex_main import ConfirmDialogState, ReflexMainState

from ..common.eln_app_router import ElnAppRouter
from .note_activity_form_dialog.note_activity_form_dialog_state import NoteActivityFormDialogState
from .note_form_dialog.note_form_dialog_state import NoteFormDialogState


class NoteDetailState(rx.State):
    """State for managing the note detail page.

    This state handles fetching and displaying a single note's details.
    """

    note: NoteDTO | None = None
    note_content: RichTextDTO | None = None
    is_loading: bool = False
    error_message: str = ""

    async def load_note(self, note_id: str):
        """Load a note by its ID.

        :param note_id: The ID of the note to load
        :type note_id: str
        """
        main_state = await self.get_state(ReflexMainState)
        if not await main_state.check_authentication():
            self.error_message = "You must be authenticated to view this note"
            return

        self.is_loading = True
        self.error_message = ""

        try:
            with await main_state.authenticate_user():
                note = NoteService.get_by_id_and_check(note_id)

            if note:
                self.note = note.to_dto()
                self.note_content = note.content
            else:
                self.error_message = "Note not found"
                self.note = None
                self.note_content = None

        except Exception as e:
            self.error_message = f"Error loading note: {str(e)}"
            self.note = None
            self.note_content = None
        finally:
            self.is_loading = False

    @rx.event
    async def on_load(self):
        """Event handler called when the page loads."""
        note_id = self.note_id
        if note_id:
            await self.load_note(note_id)
        else:
            self.error_message = "No note ID provided"

    @rx.event
    async def open_update_dialog(self):
        """Open the update note dialog."""
        if not self.note:
            return
        form_state = await self.get_state(NoteFormDialogState)
        form_state.set_callback_after_close(self._on_dialog_close)
        await form_state.open_update_dialog(self.note)

    async def _on_dialog_close(self):
        """Callback when dialog is closed to refresh the note."""
        await self.load_note(self.note.id)

    @rx.event
    async def open_delete_dialog(self):
        """Open the delete note confirmation dialog."""
        if not self.note:
            return

        delete_dialog_state = await self.get_state(ConfirmDialogState)
        delete_dialog_state.open_dialog(
            title="Delete Note",
            content=f"Are you sure you want to delete the note '{self.note.title}'?",
            action=lambda: self._delete_action(self.note.id),
        )

    async def _delete_action(self, note_id: str):
        """Delete the note and navigate back to the notes list.

        :param note_id: The ID of the note to delete
        :type note_id: str
        """
        main_state = await self.get_state(ReflexMainState)
        with await main_state.authenticate_user():
            NoteService.delete(note_id)

        yield rx.toast.success("Note deleted successfully")
        yield rx.redirect(ElnAppRouter.get_notes_list_url())

    @rx.event
    async def save_note_content(self, content: dict):
        """Save the note content.

        :param content: The new content for the note
        :type content: RichTextDTO
        """
        rich_text_dto = RichTextDTO.from_json(content)

        main_state = await self.get_state(ReflexMainState)

        note: Note
        with await main_state.authenticate_user():
            try:
                note = NoteService.update_content(self.note.id, rich_text_dto)
            except Exception as e:
                # rollback on error
                self.note_content = self.note_content
                raise e
        self.note = note.to_dto()
        self.note_content = note.content

    @rx.event
    async def on_custom_tool_event(self, event: dict):
        if not self.note:
            return

        rich_text_json = event.get("richTextContent")
        if not rich_text_json:
            raise ValueError("richTextContent is required in the event data")

        rich_text = RichTextDTO.from_editor_js_json(rich_text_json)
        if event.get("type") == "activity_block_appended":
            block_id = event.get("block_id")
            if not block_id:
                raise ValueError("block_id is required in the event data")

            form_state = await self.get_state(NoteActivityFormDialogState)
            form_state.set_callback_after_close(self._on_note_activity_added)
            form_state.open_dialog(
                note_id=self.note.id,
                note_block_id=block_id,
                rich_text_content=rich_text,
            )

    async def _on_note_activity_added(self, note: Note):
        """Callback when a note activity is added to refresh the note.

        :param note: The updated note
        :type note: Note
        """
        self.note = note.to_dto()
        self.note_content = note.content
