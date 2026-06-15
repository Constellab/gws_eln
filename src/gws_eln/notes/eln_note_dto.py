from gws_core import (
    BaseModelDTO,
    RichTextDTO,
)


class LinkNoteActivityDTO(BaseModelDTO):
    """DTO for linking an existing activity to a note block.

    The activity is created beforehand in the app; the
    note block only references it by id (the block is a view onto an
    activity, never its owner). The block stores the ``activity_id`` and renders
    the activity; deleting the block only unlinks it.
    """

    note_id: str
    note_block_id: str
    activity_id: str
    rich_text_content: RichTextDTO
