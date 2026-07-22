"""Note activity launcher (chooser) component.

Asks for an activity type and an item, then launches the matching shared dialog.
The "Continue" button dispatches to the real dialog,
which carries the note context and links the created activity to the block.
"""

import reflex as rx
from gws_reflex_main.gws_components import select_component

from ...items.core.item_select_component import item_select_component
from .note_activity_form_dialog_state import SUPPORTED_ACTIVITY_TYPES, NoteActivityFormDialogState

S = NoteActivityFormDialogState

_ACTIVITY_TYPE_DATA = [{"value": value, "label": label} for value, label in SUPPORTED_ACTIVITY_TYPES]


def _activity_type_select() -> rx.Component:
    """Select limited to the activity types creatable from a note."""
    return select_component(
        data=_ACTIVITY_TYPE_DATA,
        placeholder="Select an activity type...",
        value=S.form_activity_type,
        on_change=S.set_activity_type,
        width="100%",
    )


def _dialog() -> rx.Component:
    """The chooser dialog."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.heading("Add Item Activity", size="4"),
                rx.text(
                    "Choose an activity type and an item. The activity form opens next.",
                    size="2",
                    color="gray",
                    margin_bottom="0.5rem",
                ),
                rx.vstack(
                    rx.text("Activity Type*", size="2", weight="bold"),
                    _activity_type_select(),
                    width="100%",
                    spacing="1",
                ),
                rx.vstack(
                    rx.text("Item*", size="2", weight="bold"),
                    item_select_component(
                        placeholder="Search an item...",
                        selected_item=S.form_item,
                        item_selected=S.set_item,
                    ),
                    width="100%",
                    spacing="1",
                ),
                rx.hstack(
                    rx.button(
                        "Cancel",
                        type="button",
                        variant="soft",
                        color_scheme="gray",
                        on_click=S.close_dialog,
                    ),
                    rx.button("Continue", type="button", on_click=S.continue_to_dialog),
                    margin_top="1em",
                    spacing="2",
                ),
                width="100%",
                spacing="3",
            ),
            max_width="500px",
            on_interact_outside=S.close_dialog,
            on_escape_key_down=S.close_dialog,
        ),
        open=S.dialog_opened,
    )


def note_activity_form_dialog() -> rx.Component:
    """Launcher dialog for creating an activity from a note.

    Controlled by NoteActivityFormDialogState.dialog_opened. Open it with:
        NoteActivityFormDialogState.open_dialog(note_id, note_block_id, rich_text_content)

    :return: The note activity launcher dialog component
    :rtype: rx.Component
    """
    return _dialog()
