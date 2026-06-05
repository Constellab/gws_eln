from gws_core import (
    Event,
    EventListener,
    Logger,
    NoteContentUpdatedEvent,
    NoteDeletedEvent,
    RichText,
    RichTextBlock,
    RichTextDTO,
    event_listener,
)

from gws_eln.items.item_service import ItemService
from gws_eln.notes.eln_note_service import ElnNoteService
from gws_eln.rich_text.rich_text_block_material_activity import RichTextBlockItemActivity


@event_listener
class ElnNoteContentListener(EventListener):
    """Synchronous listener for note content changes.

    Handles item activity block DELETIONS only:
    - On block REMOVED from note content: reverses the activity (undoes item state changes)
    - On note DELETED: reverses all itemActivity blocks in the note

    Activity creation is handled by a dedicated endpoint (Step 6),
    NOT by this listener.
    """

    def is_synchronous(self) -> bool:
        return True

    def handle(self, event: Event) -> None:
        if event.type != "note":
            return

        # Only process ELN notes
        if not ElnNoteService().note_is_eln_note(event.note_id):
            return

        if event.action == "content_updated":
            self._on_content_updated(event)
        elif event.action == "deleted":
            self._on_note_deleted(event)

    def _on_content_updated(self, event: NoteContentUpdatedEvent) -> None:
        """Handle note content update.

        Computes the diff between old and new content, then reverses
        activities for any itemActivity blocks that were removed.
        """
        old_content: RichTextDTO | None = event.old_content
        new_content: RichTextDTO | None = event.new_content
        note_id: str = event.note_id

        if old_content is None:
            # First save — no previous content, no blocks to remove
            return

        if new_content is None:
            return

        # Build RichText objects for diffing
        old_rich_text = RichText(old_content)
        new_rich_text = RichText(new_content)

        diff = old_rich_text.diff(new_rich_text)

        # Process DELETED blocks — reverse their activities
        for deleted_block_info in diff.deleted:
            block = deleted_block_info.block
            if block.type == RichTextBlockItemActivity.get_typing_name():
                self._handle_block_deleted(block, note_id)

    def _on_note_deleted(self, event: NoteDeletedEvent) -> None:
        """Handle note deletion.

        Reverse all itemActivity blocks in the note content.
        """
        content: RichTextDTO | None = event.content
        note_id: str = event.note_id

        if content is None:
            return

        rich_text = RichText(content)

        for block in rich_text.get_blocks():
            if block.type == RichTextBlockItemActivity.get_typing_name():
                self._handle_block_deleted(block, note_id)

    def _handle_block_deleted(self, block: RichTextBlock, note_id: str) -> None:
        """Handle a deleted itemActivity block.

        If the block has an activity_id: reverse the activity
        (undo item state changes and delete the activity record).
        """

        block_data = block.get_data(RichTextBlockItemActivity)

        if not block_data.activity_id:
            return  # No activity to reverse

        Logger.debug(
            f"Reversing activity {block_data.activity_id} "
            f"(block {block.id} removed from note {note_id})"
        )
        ItemService().reverse_activity(block_data.activity_id)
