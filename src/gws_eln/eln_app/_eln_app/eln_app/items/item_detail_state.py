"""State for the item detail page."""

import reflex as rx
from gws_eln.items.item import Item
from gws_eln.items.item_dto import DeleteItemResultDTO, ItemDTO
from gws_eln.items.item_service import ItemService
from gws_reflex_main import ReflexMainState

from ..activities.activities_list_state import ActivitiesListState
from ..common.eln_app_router import ElnAppRouter
from .delete_item_form_dialog.delete_item_form_dialog_state import (
    DeleteItemFormDialogState,
)
from .item_event_form_dialog.item_event_form_dialog_state import (
    ItemEventFormDialogState,
    ItemEventType,
)
from .move_item_form_dialog.move_item_form_dialog_state import (
    MoveItemFormDialogState,
)
from .relabel_item_form_dialog.relabel_item_form_dialog_state import (
    RelabelItemFormDialogState,
)
from .transform_item_form_dialog.transform_item_form_dialog_state import (
    TransformItemFormDialogState,
)
from .update_item_form_dialog.update_item_form_dialog_state import (
    UpdateItemFormDialogState,
)
from .use_item_form_dialog.use_item_form_dialog_state import (
    UseItemFormDialogState,
)


class ItemDetailState(rx.State):
    """State for managing the item detail page.

    This state handles fetching and displaying a single item's details.
    """

    item: ItemDTO | None = None
    is_loading: bool = False
    error_message: str = ""

    async def load_item(self, item_id: str):
        """Load a item by its ID.

        :param item_id: The ID of the item to load
        :type item_id: str
        """
        main_state = await self.get_state(ReflexMainState)
        if not await main_state.check_authentication():
            self.error_message = "You must be authenticated to view this item"
            return

        self.is_loading = True
        self.error_message = ""

        try:
            item_service = ItemService()
            item: Item
            with await main_state.authenticate_user():
                item = item_service.get_item(item_id)

            if item:
                self.item = item.to_dto()
            else:
                self.error_message = "Item not found"
                self.item = None

        except Exception as e:
            self.error_message = f"Error loading item: {str(e)}"
            self.item = None
        finally:
            self.is_loading = False

    @rx.event
    async def on_load(self):
        """Event handler called when the page loads."""
        item_id = self.item_id
        if item_id:
            await self.load_item(item_id)
        else:
            self.error_message = "No item ID provided"

    async def _on_item_event_success(self, updated_item: ItemDTO):
        """Callback invoked when a item event completes successfully.

        Updates the item data and refreshes the activities list.

        :param updated_item: The updated item DTO
        :type updated_item: ItemDTO
        """
        # Update the item with the new data
        self.item = updated_item

        # Refresh the activities list
        activities_state = await self.get_state(ActivitiesListState)
        await activities_state.refresh_activities()

    @rx.event
    async def open_receive_dialog(self):
        """Open the receive stock dialog for the current item."""
        if not self.item:
            return
        dialog_state = await self.get_state(ItemEventFormDialogState)
        dialog_state.set_callback_after_close(self._on_item_event_success)
        dialog_state.open_dialog_for_event(self.item, ItemEventType.RECEIVE)

    @rx.event
    async def open_consume_dialog(self):
        """Open the consume stock dialog for the current item."""
        if not self.item:
            return
        dialog_state = await self.get_state(ItemEventFormDialogState)
        dialog_state.set_callback_after_close(self._on_item_event_success)
        dialog_state.open_dialog_for_event(self.item, ItemEventType.CONSUME)

    @rx.event
    async def open_move_dialog(self):
        """Open the move item dialog for the current item."""
        if not self.item:
            return
        dialog_state = await self.get_state(MoveItemFormDialogState)
        dialog_state.set_callback_after_close(self._on_item_event_success)
        await dialog_state.open_move_dialog(self.item)

    async def _on_item_update_success(self, updated_item: ItemDTO):
        """Callback invoked when update_item completes successfully.

        Only refreshes the item data (no activity is created for update).

        :param updated_item: The updated item DTO
        :type updated_item: ItemDTO
        """
        # Update the item with the new data
        self.item = updated_item

    @rx.event
    async def open_update_dialog(self):
        """Open the update item dialog for the current item."""
        if not self.item:
            return
        dialog_state = await self.get_state(UpdateItemFormDialogState)
        dialog_state.set_callback_after_close(self._on_item_update_success)
        await dialog_state.open_update_dialog(self.item)

    @rx.event
    async def open_relabel_dialog(self):
        """Open the relabel item dialog for the current item."""
        if not self.item:
            return
        dialog_state = await self.get_state(RelabelItemFormDialogState)
        dialog_state.set_callback_after_close(self._on_item_event_success)
        await dialog_state.open_relabel_dialog(self.item)

    @rx.event
    async def open_use_dialog(self):
        """Open the use item dialog for the current item."""
        if not self.item:
            return
        dialog_state = await self.get_state(UseItemFormDialogState)
        dialog_state.set_callback_after_close(self._on_item_event_success)
        await dialog_state.open_use_dialog(self.item)

    @rx.event
    async def open_transform_dialog(self):
        """Open the transform dialog seeded with the current item as first input."""
        if not self.item:
            return
        dialog_state = await self.get_state(TransformItemFormDialogState)
        dialog_state.set_callback_after_close(self._on_item_event_success)
        await dialog_state.open_transform_dialog(self.item)

    async def _on_item_delete_success(self, result: DeleteItemResultDTO):
        """Callback invoked when delete_item completes successfully.

        Refreshes the item data and activities list.
        """
        # Reload the item (it may be discarded now or deleted)
        if result == DeleteItemResultDTO.DISCARDED:
            await self.load_item(self.item.id)

            # Refresh the activities list
            activities_state = await self.get_state(ActivitiesListState)
            await activities_state.refresh_activities()
        else:
            yield rx.redirect(ElnAppRouter.get_item_sheet_detail_url(self.item.item_sheet.id))

    @rx.event
    async def open_delete_dialog(self):
        """Open the delete item dialog for the current item."""
        if not self.item:
            return
        dialog_state = await self.get_state(DeleteItemFormDialogState)
        dialog_state.set_callback_after_close(self._on_item_delete_success)
        await dialog_state.open_delete_dialog(self.item)
