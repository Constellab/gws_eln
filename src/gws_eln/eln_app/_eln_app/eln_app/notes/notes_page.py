"""Notes list page component."""

import reflex as rx
from gws_core import NoteDTO
from gws_reflex_main import main_component, user_with_date_component

from ..common.page_layout import page_layout
from .note_form_dialog.note_form_dialog_component import note_create_dialog, note_update_dialog
from .note_actions_menu import note_actions_menu
from .notes_list_state import NotesListState


def _filter_bar() -> rx.Component:
    """Create the filter bar with search input.

    :return: The filter bar component
    :rtype: rx.Component
    """
    return rx.hstack(
        rx.input(
            placeholder="Search notes...",
            value=NotesListState.search_text,
            on_change=NotesListState.handle_search_change,
            width="200px",
        ),
        width="100%",
        spacing="3",
        wrap="wrap",
        align="center",
    )


def _create_note_button() -> rx.Component:
    """Create the button to open the create note dialog.

    :return: The create note button component
    :rtype: rx.Component
    """
    return rx.fragment(
        rx.button(
            rx.icon("plus", size=18),
            "Create New Note",
            size="3",
            on_click=NotesListState.open_create_dialog,
        ),
        note_create_dialog(),
        note_update_dialog(),
    )


def _row(note: NoteDTO) -> rx.Component:
    """Create a table row for a note.

    :param note: The note DTO to display
    :type note: NoteDTO
    :return: The table row component
    :rtype: rx.Component
    """
    return rx.table.row(
        rx.table.cell(rx.text(note.title)),
        rx.table.cell(user_with_date_component(note.created_by, note.created_at, size="small")),
        rx.table.cell(
            rx.box(
                note_actions_menu(
                    on_update=lambda: NotesListState.open_update_dialog(note),
                    on_delete=lambda: NotesListState.open_delete_dialog(note),
                    stop_propagation=True,
                ),
                display="flex",
                justify_content="flex-end",
                align_items="center",
            )
        ),
        style={":hover": {"background_color": "var(--gray-3)"}, "cursor": "pointer"},
        on_click=lambda: NotesListState.go_to_note(note.id),
    )


def notes_page() -> rx.Component:
    """Create the notes list page component.

    This component displays a table of notes with columns for
    title, created by, and created at.
    Includes a search filter for title.

    :return: The notes list page component
    :rtype: rx.Component
    """
    return main_component(
        page_layout(
            rx.vstack(
                _filter_bar(),
                rx.cond(
                    NotesListState.error_message != "",
                    rx.callout(
                        NotesListState.error_message,
                        icon="triangle_alert",
                        color_scheme="red",
                        role="alert",
                        margin_bottom="1rem",
                    ),
                ),
                rx.cond(
                    NotesListState.is_loading,
                    rx.center(rx.spinner(size="3"), padding="2rem"),
                    rx.cond(
                        NotesListState.notes.length() > 0,
                        rx.table.root(
                            rx.table.header(
                                rx.table.row(
                                    rx.table.column_header_cell("Title"),
                                    rx.table.column_header_cell("Creation"),
                                    rx.table.column_header_cell(
                                        "Actions", width="100px", justify="end"
                                    ),
                                ),
                            ),
                            rx.table.body(rx.foreach(NotesListState.notes, _row)),
                            width="100%",
                            variant="surface",
                        ),
                        rx.center(
                            rx.vstack(
                                rx.icon("notebook-text", size=48, color="gray"),
                                rx.text(
                                    "No notes found", size="4", color="gray", margin_top="1rem"
                                ),
                                spacing="2",
                                align="center",
                            ),
                            padding="3rem",
                            width="100%",
                        ),
                    ),
                ),
                width="100%",
                spacing="4",
            ),
            header_content=rx.hstack(
                rx.heading("Notes", size="6"),
                _create_note_button(),
                justify="between",
                align="center",
                width="100%",
            ),
        )
    )
