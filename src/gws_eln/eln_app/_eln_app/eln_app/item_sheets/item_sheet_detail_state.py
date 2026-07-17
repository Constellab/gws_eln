"""State for the item_sheet detail page."""

import reflex as rx
from gws_eln.items.item_sheet import ItemSheet
from gws_eln.items.item_sheet_dto import DeleteItemSheetMode, ItemSheetDTO
from gws_eln.items.item_sheet_service import ItemSheetService
from gws_reflex_main import ReflexMainState

from ..common.eln_app_router import ElnAppRouter
from .delete_item_sheet_form_dialog.delete_item_sheet_form_dialog_state import (
    DeleteItemSheetFormDialogState,
)
from .item_sheet_form_dialog.item_sheet_form_dialog_state import ItemSheetFormDialogState


class ItemSheetDetailState(rx.State):
    """State for managing the item_sheet detail page.

    This state handles fetching and displaying a single item_sheet's details.
    """

    item_sheet: ItemSheetDTO | None = None
    is_loading: bool = True  # Start loading so the page shows a spinner, before on_load
    error_message: str = ""

    async def load_item_sheet(self, item_sheet_id: str):
        """Load a item_sheet by its ID.

        :param item_sheet_id: The ID of the item_sheet to load
        :type item_sheet_id: str
        """
        main_state = await self.get_state(ReflexMainState)
        if not await main_state.check_authentication():
            self.error_message = "You must be authenticated to view this item sheet"
            return

        self.is_loading = True
        self.error_message = ""

        try:
            item_sheet_service = ItemSheetService()
            item_sheet: ItemSheet
            with await main_state.authenticate_user():
                item_sheet = item_sheet_service.get_item_sheet(item_sheet_id)

            if item_sheet:
                self.item_sheet = item_sheet.to_dto()
            else:
                self.error_message = "Item sheet not found"
                self.item_sheet = None

        except Exception as e:
            self.error_message = f"Error loading item sheet: {str(e)}"
            self.item_sheet = None
        finally:
            self.is_loading = False

    @rx.event
    async def on_load(self):
        """Event handler called when the page loads."""
        # Get item_sheet ID from URL params
        item_sheet_id = self.item_sheet_id
        if item_sheet_id:
            await self.load_item_sheet(item_sheet_id)
        else:
            self.error_message = "No item sheet ID provided"

    @rx.event
    async def open_update_dialog(self):
        """Open the update item_sheet dialog."""
        if not self.item_sheet:
            return
        form_state = await self.get_state(ItemSheetFormDialogState)
        form_state.set_callback_after_close(self._on_dialog_close)
        await form_state.open_update_dialog(self.item_sheet)

    async def _on_dialog_close(self, _: ItemSheetDTO):
        """Callback when dialog is closed to refresh the item_sheet."""
        await self.load_item_sheet(self.item_sheet.id)

    @rx.event
    async def open_delete_dialog(self):
        """Open the delete/discard item_sheet dialog."""
        if not self.item_sheet:
            return

        delete_dialog_state = await self.get_state(DeleteItemSheetFormDialogState)
        delete_dialog_state.set_callback_after_close(self._on_delete_close)
        # open_delete_dialog may yield a toast (e.g. a blocked sheet); forward it.
        async for event in delete_dialog_state.open_delete_dialog(self.item_sheet):
            yield event

    async def _on_delete_close(self, mode: DeleteItemSheetMode):
        """After delete: leave for the list if the sheet is gone, else reload it
        (a discarded sheet stays, now showing its red reason banner)."""
        if mode == DeleteItemSheetMode.DELETE:
            yield rx.redirect(ElnAppRouter.get_item_sheet_list_url())
        else:
            await self.load_item_sheet(self.item_sheet.id)
