"""State management for the delete/discard item sheet form dialog."""

from collections.abc import AsyncGenerator, Callable
from typing import Any

import reflex as rx
from gws_eln.items.item_sheet_dto import DeleteItemSheetMode, ItemSheetDTO
from gws_eln.items.item_sheet_service import ItemSheetService
from gws_reflex_base import ReflexAppException
from gws_reflex_main import FormDialogState, ReflexMainState

FormDialogCloseCallback = Callable[[DeleteItemSheetMode], AsyncGenerator[Any, None]]


class DeleteItemSheetFormDialogState(FormDialogState, rx.State):
    """State for the delete/discard item sheet dialog.

    An item sheet with no items is hard-deleted (no reason). A sheet that still
    holds items, all discarded, is soft-discarded and requires a reason. A sheet
    with any non-discarded item cannot be deleted (blocked).
    """

    _item_sheet: ItemSheetDTO | None = None

    # Reason field (controlled so it can be validated on submit).
    form_reason: str = ""

    # Resolved delete mode ("delete" / "discard" / "blocked"), computed on open.
    mode: str = DeleteItemSheetMode.DELETE.value

    _callback_after_close: FormDialogCloseCallback | None = None

    @rx.var
    def name(self) -> str:
        """The item sheet name for display."""
        return self._item_sheet.name if self._item_sheet else ""

    @rx.var
    def is_discard(self) -> bool:
        """Whether the sheet will be discarded (soft delete, reason required)."""
        return self.mode == DeleteItemSheetMode.DISCARD.value

    @rx.event
    def set_reason(self, value: str):
        """Update the controlled reason field."""
        self.form_reason = value

    @rx.event
    async def open_delete_dialog(self, item_sheet: ItemSheetDTO):
        """Resolve how the delete will play out, then open the dialog.

        A blocked sheet (still has active items) can't be deleted, so there is
        nothing to confirm: the reason is surfaced as an error toast and the
        dialog is not opened. Yields the toast, so callers must forward its events.

        :param item_sheet: The sheet to delete.
        :type item_sheet: ItemSheetDTO
        """
        self._item_sheet = item_sheet
        self.form_reason = ""

        main_state = await self.get_state(ReflexMainState)
        with await main_state.authenticate_user():
            mode = ItemSheetService().get_delete_mode(item_sheet.id)
        self.mode = mode.value

        if mode == DeleteItemSheetMode.BLOCKED:
            yield rx.toast.error(
                f"Cannot delete '{item_sheet.name}': it still has active "
                "(non-discarded) items. Discard or delete them first."
            )
            return

        self.is_update_mode = False
        self.dialog_opened = True

    async def _create(self, form_data: dict):
        """Delete or discard the sheet, then invoke the close callback."""
        if not self._item_sheet:
            raise ReflexAppException("Item sheet is required")

        if self.mode == DeleteItemSheetMode.BLOCKED.value:
            raise ReflexAppException(
                "This item sheet still has active items. Discard or delete them first."
            )

        reason = self.form_reason.strip() or None
        if self.mode == DeleteItemSheetMode.DISCARD.value and not reason:
            raise ReflexAppException("A reason is required to discard this item sheet")

        main_state: ReflexMainState
        async with self:
            main_state = await self.get_state(ReflexMainState)

        with await main_state.authenticate_user():
            result = ItemSheetService().delete_item_sheet(self._item_sheet.id, reason=reason)

        if result == DeleteItemSheetMode.DELETE:
            yield rx.toast.success("Item sheet deleted successfully")
        else:
            yield rx.toast.success("Item sheet discarded successfully")

        if self._callback_after_close:
            # The callback may be an async generator (yields events) or a plain
            # coroutine (just reloads) - support both.
            callback_result = self._callback_after_close(result)
            if hasattr(callback_result, "__aiter__"):
                async for event in callback_result:
                    yield event
            else:
                await callback_result

    async def _update(self, form_data: dict):
        """Not implemented - this dialog only supports delete."""
        raise NotImplementedError("Update is not supported by this dialog")

    async def _clear_form_state(self):
        """Clear all form state after a successful operation."""
        self._item_sheet = None
        self.form_reason = ""
        self.mode = DeleteItemSheetMode.DELETE.value
        self.is_update_mode = False

    def set_callback_after_close(self, callback: FormDialogCloseCallback | None):
        """Set the callback invoked with the delete mode after a successful close."""
        self._callback_after_close = callback
