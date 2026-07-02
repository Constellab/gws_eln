"""State for the create/update note form dialog."""

from collections.abc import Callable, Coroutine
from typing import Any

import reflex as rx
from gws_core import NoteDTO, NoteSaveDTO, NoteService
from gws_eln.notes.eln_note_service import ElnNoteService
from gws_reflex_base import ReflexAppException
from gws_reflex_main import FormDialogState, ReflexMainState

FormDialogCloseCallback = Callable[[], Coroutine[Any, Any, None]]


class NoteFormDialogState(FormDialogState, rx.State):
    """State management for the create/update note dialog."""

    form_title: str = ""

    _editing_note_id: str | None = None
    _callback_after_close: FormDialogCloseCallback | None = None

    @rx.event
    async def open_create_dialog(self):
        """Open the dialog in create mode."""
        self.form_title = ""
        self._editing_note_id = None
        self.is_update_mode = False
        self.dialog_opened = True

    @rx.event
    async def open_update_dialog(self, note: NoteDTO):
        """Open the dialog in update mode with existing note data.

        :param note: The note to update
        :type note: NoteDTO
        """
        self._editing_note_id = note.id
        self.form_title = note.title
        self.is_update_mode = True
        await self.open_dialog()

    async def _create(self, form_data: dict):
        """Create a new note using the form data.

        :param form_data: Dictionary containing form fields
        :type form_data: dict
        """
        title = form_data.get("title", "").strip()

        if not title:
            raise ReflexAppException("Note title is required")

        main_state: ReflexMainState
        async with self:
            main_state = await self.get_state(ReflexMainState)

        with await main_state.authenticate_user():
            eln_note_service = ElnNoteService()
            dto = NoteSaveDTO(title=title)
            eln_note_service.create_note(dto)

        yield rx.toast.success("Note created successfully")

        if self._callback_after_close:
            await self._callback_after_close()

    async def _update(self, form_data: dict):
        """Update an existing note using the form data.

        :param form_data: Dictionary containing form fields
        :type form_data: dict
        """
        title = form_data.get("title", "").strip()

        if not title:
            raise ReflexAppException("Note title is required")

        main_state: ReflexMainState
        async with self:
            main_state = await self.get_state(ReflexMainState)

        with await main_state.authenticate_user():
            dto = NoteSaveDTO(title=title)
            NoteService.update(self._editing_note_id, dto)

        yield rx.toast.success("Note updated successfully")

        if self._callback_after_close:
            await self._callback_after_close()

    async def _clear_form_state(self):
        """Clear all form state after successful operation."""
        self.form_title = ""
        self._editing_note_id = None
        self.is_update_mode = False

    def set_callback_after_close(self, callback: FormDialogCloseCallback | None):
        """Set the callback to invoke after the dialog closes successfully.

        :param callback: The async callback function to invoke, or None to clear
        :type callback: FormDialogCloseCallback | None
        """
        self._callback_after_close = callback
