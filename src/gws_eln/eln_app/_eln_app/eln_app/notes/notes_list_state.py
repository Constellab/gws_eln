"""State for the notes list page."""

import reflex as rx
from gws_core import NoteDTO, NoteSearchBuilder, NoteService, Tag
from gws_eln.notes.eln_note_service import ElnNoteService
from gws_reflex_main import ConfirmDialogState, ReflexMainState

from ..common.eln_app_router import ElnAppRouter
from .note_form_dialog.note_form_dialog_state import NoteFormDialogState


class NotesListState(rx.State):
    """State for managing the notes list page."""

    notes: list[NoteDTO] = []
    is_loading: bool = False
    error_message: str = ""

    # Filter state
    search_text: str = ""

    async def load_notes(self):
        """Load the list of ELN notes with applied filters."""
        main_state = await self.get_state(ReflexMainState)

        if not await main_state.check_authentication():
            self.error_message = "You must be authenticated to view notes"
            return

        self.is_loading = True
        self.error_message = ""

        try:
            note_search_builder = NoteSearchBuilder()

            # Apply the ELN note tag filter (same as ElnNoteService.get_eln_notes)
            note_search_builder.add_tag_filter(
                Tag(ElnNoteService.ELN_NOTE_TAG_KEY, ElnNoteService.ELN_NOTE_TAG_VALUE)
            )

            # Apply title search filter
            if self.search_text:
                note_search_builder.add_title_filter(self.search_text)

            notes = note_search_builder.search_all()

            self.notes = [note.to_dto() for note in notes]

        finally:
            self.is_loading = False

    async def on_load(self):
        """Event handler called when the page loads."""
        await self.load_notes()

    @rx.event
    async def handle_search_change(self, value: str):
        """Handle text search filter change.

        :param value: The search text
        :type value: str
        """
        self.search_text = value
        await self.load_notes()

    @rx.event
    async def open_create_dialog(self):
        """Open the create note dialog."""
        form_state = await self.get_state(NoteFormDialogState)
        form_state.set_callback_after_close(self.on_dialog_close)
        await form_state.open_create_dialog()

    async def on_dialog_close(self):
        """Callback when the dialog is closed to refresh the notes list."""
        await self.load_notes()

    @rx.event
    async def open_update_dialog(self, note: NoteDTO):
        """Open the update note dialog.

        :param note: The note to update
        :type note: NoteDTO
        """
        form_state = await self.get_state(NoteFormDialogState)
        form_state.set_callback_after_close(self.on_dialog_close)
        await form_state.open_update_dialog(note)

    @rx.event
    async def open_delete_dialog(self, note: NoteDTO):
        """Open the delete note confirmation dialog.

        :param note: The note to delete
        :type note: NoteDTO
        """
        delete_dialog_state = await self.get_state(ConfirmDialogState)
        delete_dialog_state.open_dialog(
            title="Delete Note",
            content=f"Are you sure you want to delete the note '{note.title}'?",
            action=lambda: self._delete_action(note.id),
        )

    async def _delete_action(self, note_id: str):
        """Delete the note and refresh the list.

        :param note_id: The ID of the note to delete
        :type note_id: str
        """
        main_state = await self.get_state(ReflexMainState)
        with await main_state.authenticate_user():
            NoteService.delete(note_id)

        yield rx.toast.success("Note deleted successfully")
        await self.load_notes()

    @rx.event
    def go_to_note(self, note_id: str):
        """Navigate to the note detail page.

        :param note_id: The ID of the note to view
        :type note_id: str
        """
        return rx.redirect(ElnAppRouter.get_note_detail_url(note_id))
