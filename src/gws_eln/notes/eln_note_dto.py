from typing import Any

from gws_core import (
    BaseModelDTO,
    RichTextDTO,
)
from gws_eln.activities.activity_type import ActivityType


class AddNoteActivityDTO(BaseModelDTO):
    """DTO for adding an activity from a note block."""

    note_id: str
    note_block_id: str
    batch_id: str
    activity_type: ActivityType
    activity_data: dict[str, Any]
    rich_text_content: RichTextDTO
