"""Note detail page component."""

import reflex as rx
from gws_eln.core.eln_settings import ELNSettings
from gws_eln.rich_text.rich_text_block_item_activity import RichTextBlockItemActivity
from gws_reflex_main.gws_components import (
    RichTextCustomBlocksConfig,
    rich_text_component,
)

from ..note_detail_state import NoteDetailState

js_asset_path = rx.asset("eln_note_component.js", shared=True)
css_asset_path = rx.asset("eln_note_component.css", shared=True)


def eln_note_component() -> rx.Component:
    """Create the note content component with rich text editor.

    :return: The note content component
    :rtype: rx.Component
    """
    return rx.fragment(
        # Load CSS for custom block styling
        rx.el.link(rel="stylesheet", href=css_asset_path),
        rich_text_component(
            value=NoteDetailState.note_content,
            disabled=NoteDetailState.is_loading,
            output_event=NoteDetailState.save_note_content,
            custom_style={"height": "100%", "minHeight": "400px", "paddingBottom": "0"},
            custom_tools_config=RichTextCustomBlocksConfig(
                jsx_file_path=js_asset_path,  # normalizeAssetPath in JSX handles dev/prod
                custom_blocks={"ActivityBlock": RichTextBlockItemActivity},
                config={"apiUrl": ELNSettings.get_eln_api_url()},
            ),
            custom_tools_event=NoteDetailState.on_custom_tool_event,
        ),
    )
