"""Note form dialog component."""

import reflex as rx
from gws_reflex_main import form_dialog_component

from .note_form_dialog_state import NoteFormDialogState


def _form_content() -> rx.Component:
    """Form content for entering note details."""
    return rx.vstack(
        # Note Title field
        rx.vstack(
            rx.text("Note Title*", size="2", weight="bold"),
            rx.input(
                placeholder="Enter note title",
                name="title",
                required=True,
                width="100%",
                default_value=NoteFormDialogState.form_title,
            ),
            width="100%",
            spacing="1",
        ),
        width="100%",
        spacing="3",
    )


def _dialog() -> rx.Component:
    """The base dialog component without a trigger.

    :return: The dialog component
    :rtype: rx.Component
    """
    return form_dialog_component(
        state=NoteFormDialogState,
        title=rx.cond(NoteFormDialogState.is_update_mode, "Update Note", "Create New Note"),
        description=rx.cond(
            NoteFormDialogState.is_update_mode,
            "Update the note details below.",
            "Fill in the details below to create a new note.",
        ),
        form_content=_form_content(),
        max_width="500px",
    )


def note_create_dialog() -> rx.Component:
    """Dialog component for creating a new note.

    :return: The create note dialog component
    :rtype: rx.Component
    """
    return _dialog()


def note_update_dialog() -> rx.Component:
    """Dialog component for updating an existing note.

    This component provides just the dialog (without a trigger button).
    The dialog is controlled by the NoteFormDialogState.dialog_opened state.

    :return: The update note dialog component
    :rtype: rx.Component
    """
    return _dialog()
