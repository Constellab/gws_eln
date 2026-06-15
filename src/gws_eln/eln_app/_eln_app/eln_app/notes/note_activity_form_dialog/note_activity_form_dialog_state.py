"""State for the note activity launcher (chooser).

When an Item Activity block is appended in a note, this chooser asks for the
activity type and the item, then launches the SAME shared dialog used in the app
(one shared form per transform, both hosts). The launched dialog is armed
with the note context so that, on success, it links the created activity to the
block (and the activity carries ``note_id``). This chooser never calls a service
itself - it only dispatches.
"""

import inspect
from collections.abc import Callable, Coroutine
from typing import Any

import reflex as rx
from gws_core import Note, RichTextDTO
from gws_eln.activities.activity_type import ActivityType
from gws_eln.items.item_dto import ItemDTO
from gws_eln.notes.eln_note_service import ElnNoteService
from gws_reflex_main import ReflexMainState
from gws_reflex_main.gws_components import InputSearchResultDTO

from ...items.combine_item_form_dialog.combine_item_form_dialog_state import (
    CombineItemFormDialogState,
)
from ...items.concentrate_item_form_dialog.concentrate_item_form_dialog_state import (
    ConcentrateItemFormDialogState,
)
from ...items.dilute_item_form_dialog.dilute_item_form_dialog_state import (
    DiluteItemFormDialogState,
)
from ...items.item_event_form_dialog.item_event_form_dialog_state import (
    ItemEventFormDialogState,
    ItemEventType,
)
from ...items.move_item_form_dialog.move_item_form_dialog_state import (
    MoveItemFormDialogState,
)
from ...items.relabel_item_form_dialog.relabel_item_form_dialog_state import (
    RelabelItemFormDialogState,
)
from ...items.split_item_form_dialog.split_item_form_dialog_state import (
    SplitItemFormDialogState,
)

NoteActivityCallback = Callable[[Note], Coroutine[Any, Any, None]]

# Activity types that can be created from a note (those with a shared app dialog).
# (value, label) - ordered for the select.
SUPPORTED_ACTIVITY_TYPES: list[tuple[str, str]] = [
    (ActivityType.RECEIVE.value, "Receive stock"),
    (ActivityType.CONSUME.value, "Consume stock"),
    (ActivityType.MOVE.value, "Move"),
    (ActivityType.RELABEL.value, "Relabel"),
    (ActivityType.SPLIT.value, "Split"),
    (ActivityType.COMBINE.value, "Combine"),
    (ActivityType.CONCENTRATE.value, "Concentrate"),
    (ActivityType.DILUTE.value, "Dilute"),
]

# Dispatch for the chooser: activity type -> (dialog state class, open-method name,
# event_type). event_type is only used by the shared receive/consume dialog
# (open_dialog_for_event); it is None for every other dialog. The open method may be
# sync or async - the caller awaits it only when it returns an awaitable.
_ACTIVITY_DISPATCH: dict[str, tuple[type, str, "ItemEventType | None"]] = {
    ActivityType.SPLIT.value: (SplitItemFormDialogState, "open_split_dialog", None),
    ActivityType.COMBINE.value: (CombineItemFormDialogState, "open_combine_dialog", None),
    ActivityType.CONCENTRATE.value: (
        ConcentrateItemFormDialogState,
        "open_concentrate_dialog",
        None,
    ),
    ActivityType.DILUTE.value: (DiluteItemFormDialogState, "open_dilute_dialog", None),
    ActivityType.MOVE.value: (MoveItemFormDialogState, "open_move_dialog", None),
    ActivityType.RELABEL.value: (RelabelItemFormDialogState, "open_relabel_dialog", None),
    ActivityType.RECEIVE.value: (
        ItemEventFormDialogState,
        "open_dialog_for_event",
        ItemEventType.RECEIVE,
    ),
    ActivityType.CONSUME.value: (
        ItemEventFormDialogState,
        "open_dialog_for_event",
        ItemEventType.CONSUME,
    ),
}


class NoteActivityFormDialogState(rx.State):
    """Chooser state: pick an activity type + item, then launch the shared dialog."""

    # Note context (set when opening the chooser)
    _note_id: str = ""
    _note_block_id: str = ""
    _rich_text_content: RichTextDTO | None = None
    _note_callback: NoteActivityCallback | None = None

    dialog_opened: bool = False

    # Step 1: activity type + item selection
    form_activity_type: str = ""
    form_item: InputSearchResultDTO | None = None
    _item: ItemDTO | None = None

    @rx.var
    def activity_type_options(self) -> list[list[str]]:
        """The (value, label) options for the activity-type select."""
        return [list(pair) for pair in SUPPORTED_ACTIVITY_TYPES]

    @rx.var
    def has_item(self) -> bool:
        """Whether an item has been selected."""
        return self.form_item is not None

    def open_dialog(
        self, note_id: str, note_block_id: str, rich_text_content: RichTextDTO | None = None
    ):
        """Open the chooser for a specific note block."""
        self._note_id = note_id
        self._note_block_id = note_block_id
        self._rich_text_content = rich_text_content
        self.form_activity_type = ""
        self.form_item = None
        self._item = None
        self.dialog_opened = True

    @rx.event
    def set_activity_type(self, value: str):
        """Handle activity type selection change."""
        self.form_activity_type = value

    @rx.event
    def set_item(self, value: dict):
        """Handle item selection change."""
        if not value:
            self.form_item = None
            self._item = None
            return
        self.form_item = InputSearchResultDTO.from_json_object(value, ItemDTO)
        self._item = self.form_item.object

    @rx.event
    async def close_dialog(self):
        """Close the chooser without launching anything.

        The editor already inserted the activity block; since the user aborted
        before choosing, drop that empty block so no orphan is left behind.
        """
        if self._note_id and self._rich_text_content is not None:
            main_state = await self.get_state(ReflexMainState)
            with await main_state.authenticate_user():
                note = ElnNoteService().remove_activity_block(
                    self._note_id, self._note_block_id, self._rich_text_content
                )
            if self._note_callback is not None:
                await self._note_callback(note)

        self.dialog_opened = False
        self._clear()

    @rx.event
    async def continue_to_dialog(self):
        """Validate the selection and launch the matching shared dialog.

        The launched dialog is armed with the note context so it links the
        created activity to the block on success.
        """
        if not self.form_activity_type:
            yield rx.toast.error("Please select an activity type")
            return
        if not self._item:
            yield rx.toast.error("Please select an item")
            return

        spec = _ACTIVITY_DISPATCH.get(self.form_activity_type)
        if spec is None:
            yield rx.toast.error("Unsupported activity type")
            return

        state_class, open_method, event_type = spec
        target = await self.get_state(state_class)
        target.set_callback_after_close(None)
        target.set_note_context(
            self._note_id, self._note_block_id, self._rich_text_content, self._note_callback
        )

        open_args = (self._item,) if event_type is None else (self._item, event_type)
        result = getattr(target, open_method)(*open_args)
        if inspect.isawaitable(result):
            await result

        self.dialog_opened = False
        self._clear()

    def set_callback_after_close(self, callback: NoteActivityCallback | None):
        """Set the callback the launched dialog invokes after linking (note refresh)."""
        self._note_callback = callback

    def _clear(self):
        """Reset the chooser selection (keeps no note context)."""
        self.form_activity_type = ""
        self.form_item = None
        self._item = None
        self._note_id = ""
        self._note_block_id = ""
        self._rich_text_content = None
