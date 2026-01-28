"""Note detail page component."""

import reflex as rx
from gws_reflex_main import main_component, user_inline_component

from ..common.detail_page_layout import detail_page_layout, detail_toggle_sidebar_button
from ..common.notes.note_actions_menu import note_actions_menu
from ..common.page_layout import page_layout
from ..note_activity_form_dialog.note_activity_form_dialog_component import (
    note_activity_form_dialog,
)
from ..note_form_dialog.note_form_dialog_component import note_update_dialog
from .eln_note_component.eln_note_component import eln_note_component
from .note_detail_state import NoteDetailState


def _details_sidebar() -> rx.Component:
    """Create the details sidebar with note information.

    :return: The details sidebar component
    :rtype: rx.Component
    """
    return rx.vstack(
        rx.heading("Details", size="5", margin_bottom="1rem"),
        rx.grid(
            # Title
            rx.text("Title", size="2", color="gray", weight="medium"),
            rx.text(NoteDetailState.note.title, size="2"),
            # Divider before creation info
            rx.divider(margin_top="0.5rem", margin_bottom="0.5rem", grid_column="span 2"),
            # Created by
            rx.text("Created by", size="2", color="gray", weight="medium"),
            user_inline_component(NoteDetailState.note.created_by, size="small"),
            # Created at
            rx.text("Created at", size="2", color="gray", weight="medium"),
            rx.text(
                rx.moment(NoteDetailState.note.created_at, format="MMM D, YYYY HH:mm"),
                size="2",
            ),
            # Last modified by
            rx.text("Last modified by", size="2", color="gray", weight="medium"),
            user_inline_component(NoteDetailState.note.last_modified_by, size="small"),
            # Last modified at
            rx.text("Last modified at", size="2", color="gray", weight="medium"),
            rx.text(
                rx.moment(NoteDetailState.note.last_modified_at, format="MMM D, YYYY HH:mm"),
                size="2",
            ),
            # Validation section (only shown if validated)
            rx.cond(
                NoteDetailState.note.is_validated,
                rx.fragment(
                    rx.divider(margin_top="0.5rem", margin_bottom="0.5rem", grid_column="span 2"),
                    rx.text("Validated by", size="2", color="gray", weight="medium"),
                    rx.cond(
                        NoteDetailState.note.validated_by,
                        user_inline_component(NoteDetailState.note.validated_by, size="small"),
                        rx.text("-", size="2"),
                    ),
                    rx.text("Validated at", size="2", color="gray", weight="medium"),
                    rx.cond(
                        NoteDetailState.note.validated_at,
                        rx.text(
                            rx.moment(
                                NoteDetailState.note.validated_at, format="MMM D, YYYY HH:mm"
                            ),
                            size="2",
                        ),
                        rx.text("-", size="2"),
                    ),
                ),
            ),
            # Last sync section (only shown if synced)
            rx.cond(
                NoteDetailState.note.last_sync_at,
                rx.fragment(
                    rx.divider(margin_top="0.5rem", margin_bottom="0.5rem", grid_column="span 2"),
                    rx.text("Last sync by", size="2", color="gray", weight="medium"),
                    rx.cond(
                        NoteDetailState.note.last_sync_by,
                        user_inline_component(NoteDetailState.note.last_sync_by, size="small"),
                        rx.text("-", size="2"),
                    ),
                    rx.text("Last sync at", size="2", color="gray", weight="medium"),
                    rx.text(
                        rx.moment(NoteDetailState.note.last_sync_at, format="MMM D, YYYY HH:mm"),
                        size="2",
                    ),
                ),
            ),
            columns="2",
            spacing="3",
            width="100%",
            row_gap="1rem",
        ),
        width="100%",
        spacing="3",
        align_items="start",
    )


def note_detail_page() -> rx.Component:
    """Create the note detail page component.

    Displays note information in a sidebar on the right side,
    with a main content area on the left (empty for now).

    :return: The note detail page component
    :rtype: rx.Component
    """
    return main_component(
        page_layout(
            rx.cond(
                NoteDetailState.error_message != "",
                rx.callout(
                    NoteDetailState.error_message,
                    icon="triangle_alert",
                    color_scheme="red",
                    role="alert",
                ),
                rx.cond(
                    NoteDetailState.is_loading,
                    rx.center(rx.spinner(size="3"), padding="2rem"),
                    rx.cond(
                        NoteDetailState.note,
                        detail_page_layout(
                            main_content=eln_note_component(),
                            sidebar_content=_details_sidebar(),
                            show_header=False,
                        ),
                        rx.center(
                            rx.vstack(
                                rx.icon("notebook-text", size=48, color="gray"),
                                rx.text(
                                    "Note not found",
                                    size="4",
                                    color="gray",
                                    margin_top="1rem",
                                ),
                                spacing="2",
                                align="center",
                            ),
                            padding="3rem",
                            width="100%",
                        ),
                    ),
                ),
            ),
            header_content=rx.hstack(
                rx.heading(NoteDetailState.note.title, size="6"),
                rx.hstack(
                    note_actions_menu(
                        on_update=NoteDetailState.open_update_dialog,
                        on_delete=NoteDetailState.open_delete_dialog,
                    ),
                    detail_toggle_sidebar_button(),
                    note_update_dialog(),
                    note_activity_form_dialog(),
                ),
                justify="between",
                align="center",
                width="100%",
            ),
        )
    )
