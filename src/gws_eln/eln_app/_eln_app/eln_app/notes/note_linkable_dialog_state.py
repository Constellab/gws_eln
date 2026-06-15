"""Reusable mixin making a form dialog able to link its created activity to a
note block.

The shared transform/event dialogs are launched in BOTH hosts (the
standalone app and from a note). When launched from a note, the dialog passes
``note_id`` into its service DTO (so the created Activity links to the note) and,
after creation, writes the resulting ``activity_id`` into the note block so the
block renders it. The block is a view onto the activity, never its owner.

A dialog opts in by mixing this in and, inside its ``_create``:
- setting ``dto.note_id = self.note_dto_id`` before the service call, and
- calling ``self._link_note_activity(result.activity.id)`` inside the
  authenticated block, then ``await self._after_note_link(linked_note)`` after.
When not launched from a note, all of these are no-ops.
"""

from collections.abc import Callable, Coroutine
from typing import Any

import reflex as rx
from gws_core import Note, RichTextDTO
from gws_eln.notes.eln_note_dto import LinkNoteActivityDTO
from gws_eln.notes.eln_note_service import ElnNoteService
from gws_reflex_main import ReflexMainState

NoteLinkCallback = Callable[[Note], Coroutine[Any, Any, None]]


class NoteLinkableDialogState(rx.State, mixin=True):
    """Mixin adding optional note-block linking to a form dialog."""

    # Note context - empty when the dialog is launched from the app (no linking).
    _note_id: str = ""
    _note_block_id: str = ""
    _note_rich_text: RichTextDTO | None = None
    _note_callback: NoteLinkCallback | None = None
    # True once the created activity has been linked into the block (success).
    _note_linked: bool = False

    def set_note_context(
        self,
        note_id: str,
        note_block_id: str,
        rich_text_content: RichTextDTO | None,
        callback: NoteLinkCallback | None = None,
    ):
        """Arm the dialog to link its created activity to a note block."""
        self._note_id = note_id
        self._note_block_id = note_block_id
        self._note_rich_text = rich_text_content
        self._note_callback = callback
        self._note_linked = False

    def clear_note_context(self):
        """Disarm note linking (call from ``_clear_form_state``)."""
        self._note_id = ""
        self._note_block_id = ""
        self._note_rich_text = None
        self._note_callback = None
        self._note_linked = False

    @property
    def note_dto_id(self) -> str | None:
        """The ``note_id`` to set on the service DTO (None when app-launched)."""
        return self._note_id or None

    def _link_note_activity(self, activity_id: str) -> Note | None:
        """Write the created activity's id into the note block (no-op if app-launched).

        Must be called inside the authenticated block (it hits the note service).
        Returns the updated Note, or None when not launched from a note.
        """
        if not self._note_id or self._note_rich_text is None:
            return None
        dto = LinkNoteActivityDTO(
            note_id=self._note_id,
            note_block_id=self._note_block_id,
            activity_id=activity_id,
            rich_text_content=self._note_rich_text,
        )
        return ElnNoteService().link_activity(dto)

    async def _after_note_link(self, note: Note | None):
        """Mark the block as linked and refresh the note after a successful link.

        ``submit_form`` is a background event, so the dialog's own state may only
        be mutated inside ``async with self`` - hence the flag is set here, not in
        the (sync, DB-only) ``_link_note_activity``.
        """
        if note is None:
            return
        async with self:
            self._note_linked = True
        if self._note_callback is not None:
            await self._note_callback(note)

    @rx.event
    async def close_dialog(self):
        """Close the dialog; if launched from a note but the activity was never
        created (cancel / click-outside / escape), drop the empty block so no
        orphan "Activity ID missing" block is left behind (§15 end state).
        """
        if self._note_id and not self._note_linked and self._note_rich_text is not None:
            main_state = await self.get_state(ReflexMainState)
            with await main_state.authenticate_user():
                note = ElnNoteService().remove_activity_block(
                    self._note_id, self._note_block_id, self._note_rich_text
                )
            if self._note_callback is not None:
                await self._note_callback(note)

        await super().close_dialog()
