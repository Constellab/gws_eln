"""Note detail page component."""

import reflex as rx
from gws_reflex_main import (
    main_component,
    right_sidebar_close_button,
    right_sidebar_open_button,
    user_inline_component,
)

from ..common.detail_page_layout import detail_content_layout
from ..common.page_layout import page_layout
from ..items.item_event_form_dialog.item_event_form_dialog_component import (
    item_event_form_dialog,
)
from ..items.move_item_form_dialog.move_item_form_dialog_component import move_item_dialog
from ..items.relabel_item_form_dialog.relabel_item_form_dialog_component import (
    relabel_item_dialog,
)
from ..items.transform_item_form_dialog.transform_item_form_dialog_component import (
    transform_item_dialog,
)
from .eln_note_component.eln_note_component import eln_note_component
from .note_actions_menu import note_actions_menu
from .note_activity_form_dialog.note_activity_form_dialog_component import (
    note_activity_form_dialog,
)
from .note_detail_state import NoteDetailState
from .note_form_dialog.note_form_dialog_component import note_update_dialog


def _sidebar_section_label(label: str) -> rx.Component:
    """Create a small uppercase gray label for a sidebar section.

    :param label: The label text
    :type label: str
    :return: The styled label component
    :rtype: rx.Component
    """
    return rx.text(
        label,
        size="1",
        color="gray",
        weight="bold",
        style={
            "text-transform": "uppercase",
            "letter-spacing": "0.06em",
        },
    )


def _sidebar_metadata_row(label: str, value: rx.Component) -> rx.Component:
    """Create a metadata row with a label on the left and value on the right.

    :param label: The label text
    :type label: str
    :param value: The value component
    :type value: rx.Component
    :return: The metadata row component
    :rtype: rx.Component
    """
    return rx.hstack(
        rx.text(label, size="2", color="gray"),
        rx.spacer(),
        value,
        width="100%",
        align="center",
    )


def _details_sidebar() -> rx.Component:
    """Create the details sidebar with note information.

    :return: The details sidebar component
    :rtype: rx.Component
    """
    return rx.vstack(
        # Heading with close button
        rx.hstack(
            _sidebar_section_label("Note details"),
            rx.spacer(),
            right_sidebar_close_button(),
            width="100%",
            align="center",
            margin_bottom="1rem",
        ),
        # Main info grid (label + value per row)
        rx.grid(
            # Title
            rx.text("Title", size="2", color="gray", weight="medium"),
            rx.text(NoteDetailState.note.title, size="2"),
            columns="2",
            spacing="3",
            width="100%",
            row_gap="1rem",
        ),
        # Validation section (only shown if validated)
        rx.cond(
            NoteDetailState.note.is_validated,
            rx.vstack(
                rx.divider(margin_top="1.5rem", margin_bottom="1.5rem"),
                _sidebar_section_label("Validation"),
                _sidebar_metadata_row(
                    "Validated by",
                    rx.cond(
                        NoteDetailState.note.validated_by,
                        user_inline_component(NoteDetailState.note.validated_by, size="small"),
                        rx.text("-", size="2"),
                    ),
                ),
                _sidebar_metadata_row(
                    "Validated at",
                    rx.cond(
                        NoteDetailState.note.validated_at,
                        rx.text(
                            rx.moment(
                                NoteDetailState.note.validated_at, format="MMM D, YYYY HH:mm"
                            ),
                            size="1",
                            weight="medium",
                        ),
                        rx.text("-", size="2"),
                    ),
                ),
                spacing="1",
                align_items="start",
                width="100%",
                gap="0.5rem",
            ),
        ),
        # Last sync section (only shown if synced)
        rx.cond(
            NoteDetailState.note.last_sync_at,
            rx.vstack(
                rx.divider(margin_top="1.5rem", margin_bottom="1.5rem"),
                _sidebar_section_label("Sync"),
                _sidebar_metadata_row(
                    "Last sync by",
                    rx.cond(
                        NoteDetailState.note.last_sync_by,
                        user_inline_component(NoteDetailState.note.last_sync_by, size="small"),
                        rx.text("-", size="2"),
                    ),
                ),
                _sidebar_metadata_row(
                    "Last sync at",
                    rx.text(
                        rx.moment(NoteDetailState.note.last_sync_at, format="MMM D, YYYY HH:mm"),
                        size="1",
                        weight="medium",
                    ),
                ),
                spacing="1",
                align_items="start",
                width="100%",
                gap="0.5rem",
            ),
        ),
        # Divider + metadata section
        rx.vstack(
            rx.divider(margin_top="1.5rem", margin_bottom="1.5rem"),
            _sidebar_metadata_row(
                "Created by",
                user_inline_component(NoteDetailState.note.created_by, size="small"),
            ),
            _sidebar_metadata_row(
                "Created at",
                rx.text(
                    rx.moment(NoteDetailState.note.created_at, format="MMM D, YYYY HH:mm"),
                    size="1",
                    weight="medium",
                ),
            ),
            _sidebar_metadata_row(
                "Last modified by",
                user_inline_component(NoteDetailState.note.last_modified_by, size="small"),
            ),
            _sidebar_metadata_row(
                "Last modified at",
                rx.text(
                    rx.moment(NoteDetailState.note.last_modified_at, format="MMM D, YYYY HH:mm"),
                    size="1",
                    weight="medium",
                ),
            ),
            spacing="1",
            width="100%",
            padding_top="0.5rem",
        ),
        width="100%",
        spacing="0",
        align_items="start",
    )


def _header() -> rx.Component:
    """Create the header component for the note detail page.

    :return: The header component
    :rtype: rx.Component
    """
    return rx.hstack(
        rx.heading(NoteDetailState.note.title, size="6"),
        rx.spacer(),
        note_actions_menu(
            on_update=NoteDetailState.open_update_dialog,
            on_delete=NoteDetailState.open_delete_dialog,
        ),
        right_sidebar_open_button(),
        note_update_dialog(),
        note_activity_form_dialog(),
        # Shared activity dialogs launched from the note chooser
        transform_item_dialog(),
        move_item_dialog(),
        relabel_item_dialog(),
        item_event_form_dialog(),
        width="100%",
        align="center",
        spacing="4",
    )


def note_detail_page() -> rx.Component:
    """Create the note detail page component.

    Displays note information in a sidebar on the right side,
    with a main content area on the left.

    :return: The note detail page component
    :rtype: rx.Component
    """
    return rx.box(
        main_component(
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
                            detail_content_layout(
                                main_content=eln_note_component(),
                                header_content=_header(),
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
                right_sidebar_content=_details_sidebar(),
                max_content_width="1200px",
                height="100vh",
                padding="0 0 1em 0",
            )
        ),
    )
