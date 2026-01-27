"""State for the note detail page."""

import reflex as rx
from gws_core import NoteDTO, NoteService
from gws_reflex_main import ConfirmDialogState, ReflexMainState

from ..common.eln_app_router import ElnAppRouter
from ..note_form_dialog.note_form_dialog_state import NoteFormDialogState


class NoteDetailState(rx.State):
    """State for managing the note detail page.

    This state handles fetching and displaying a single note's details.
    """

    note: NoteDTO | None = None
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
            else:
                self.error_message = "Note not found"
                self.note = None

        except Exception as e:
            self.error_message = f"Error loading note: {str(e)}"
            self.note = None
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
