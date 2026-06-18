"""State for the items list component."""

from typing import cast

import reflex as rx
from gws_core import Logger
from gws_eln.items.item import Item
from gws_eln.items.item_dto import DeleteItemResultDTO, ItemDTO
from gws_eln.items.item_search_builder import ItemSearchBuilder
from gws_eln.items.item_status import ItemStatus
from gws_reflex_main import ReflexMainState

from .combine_item_form_dialog.combine_item_form_dialog_state import (
    CombineItemFormDialogState,
)
from .concentrate_item_form_dialog.concentrate_item_form_dialog_state import (
    ConcentrateItemFormDialogState,
)
from .delete_item_form_dialog.delete_item_form_dialog_state import (
    DeleteItemFormDialogState,
)
from .dilute_item_form_dialog.dilute_item_form_dialog_state import (
    DiluteItemFormDialogState,
)
from .item_event_form_dialog.item_event_form_dialog_state import (
    ItemEventFormDialogState,
    ItemEventType,
)
from .item_form_dialog.item_form_dialog_state import (
    ItemFormDialogState,
)
from .move_item_form_dialog.move_item_form_dialog_state import (
    MoveItemFormDialogState,
)
from .relabel_item_form_dialog.relabel_item_form_dialog_state import (
    RelabelItemFormDialogState,
)
from .split_item_form_dialog.split_item_form_dialog_state import (
    SplitItemFormDialogState,
)
from .update_item_form_dialog.update_item_form_dialog_state import (
    UpdateItemFormDialogState,
)
from .use_item_form_dialog.use_item_form_dialog_state import (
    UseItemFormDialogState,
)

# Constants for "all" filter options
ALL_FILTER_VALUE = "__all__"


class ItemsListState(rx.State):
    """State for managing the items list component.

    This state handles fetching and displaying the list of items
    for a specific item_sheet with filtering capabilities.
    """

    _item_sheet_id: str | None = None
    _items: list[ItemDTO] = []
    is_loading: bool = False
    error_message: str = ""

    # Filter state
    search_text: str = ""
    filter_location_id: str = "__all__"
    filter_supplier_id: str = "__all__"
    filter_status: str = "__all__"  # "__all__", "active", "discarded"

    @rx.var
    def items(self) -> list[ItemDTO]:
        """Return the list of items as DTOs.

        :return: List of ItemDTOs
        :rtype: list[ItemDTO]
        """
        return self._items

    @rx.var
    def current_item_sheet_id(self) -> str:
        """Return the current item_sheet ID.

        :return: The item_sheet ID
        :rtype: str
        """
        return self._item_sheet_id or ""

    async def _load_items(self):
        """Load the list of items with applied filters.

        Uses ItemSearchBuilder to apply filters.
        """
        if not self._item_sheet_id:
            return

        self.is_loading = True
        self.error_message = ""

        try:
            search_builder = ItemSearchBuilder()

            # Always filter by item_sheet_id
            search_builder.add_item_sheet_filter(self._item_sheet_id)

            # Apply text search filter (label or code)
            if self.search_text:
                search_builder.add_label_or_code_filter(self.search_text)

            # Apply location filter
            if self.filter_location_id and self.filter_location_id != ALL_FILTER_VALUE:
                search_builder.add_location_filter(self.filter_location_id)

            # Apply supplier filter
            if self.filter_supplier_id and self.filter_supplier_id != ALL_FILTER_VALUE:
                search_builder.add_supplier_filter(self.filter_supplier_id)

            # Apply status filter
            if self.filter_status and self.filter_status != ALL_FILTER_VALUE:
                status = ItemStatus(self.filter_status)
                search_builder.add_status_filter(status)

            items = cast(list[Item], search_builder.search_all())

            self._items = [item.to_dto() for item in items]

        finally:
            self.is_loading = False

    @rx.event(background=True)
    async def fetch_items_on_mount(self, item_sheet_id: str):
        """Event handler to fetch items when the component is mounted.

        :param item_sheet_id: The ID of the item_sheet to fetch items for
        :type item_sheet_id: str
        """
        async with self:
            if not item_sheet_id:
                return

            # Check if we already have items for this item_sheet
            if self._item_sheet_id == item_sheet_id:
                return

            self._item_sheet_id = item_sheet_id
            self._items = []
            self.is_loading = True
            main_state = await self.get_state(ReflexMainState)

        try:
            with await main_state.authenticate_user():
                async with self:
                    await self._load_items()
        except Exception as e:
            Logger.error(f"Error loading items: {str(e)}")
            Logger.log_exception_stack_trace(e)
            async with self:
                self._items = []
                self.is_loading = False
                self.error_message = "Failed to load items"

    @rx.event
    def on_unmount(self):
        """Reset state when the component is unmounted."""
        self._item_sheet_id = None
        self._items = []
        self.is_loading = False
        self.error_message = ""
        self.search_text = ""
        self.filter_location_id = ALL_FILTER_VALUE
        self.filter_supplier_id = ALL_FILTER_VALUE
        self.filter_status = ALL_FILTER_VALUE

    @rx.event
    async def handle_search_change(self, value: str):
        """Handle text search filter change.

        :param value: The search text
        :type value: str
        """
        self.search_text = value
        await self._load_items()

    @rx.event
    async def handle_location_filter_change(self, value: str):
        """Handle location filter change.

        :param value: The location ID or ALL_FILTER_VALUE
        :type value: str
        """
        self.filter_location_id = value
        await self._load_items()

    @rx.event
    async def handle_supplier_filter_change(self, value: str):
        """Handle supplier filter change.

        :param value: The supplier ID or ALL_FILTER_VALUE
        :type value: str
        """
        self.filter_supplier_id = value
        await self._load_items()

    @rx.event
    async def handle_status_filter_change(self, value: str):
        """Handle status filter change.

        :param value: "active", "discarded", or ALL_FILTER_VALUE
        :type value: str
        """
        self.filter_status = value
        await self._load_items()

    @rx.event
    async def clear_filters(self):
        """Clear all filters and reload items."""
        self.search_text = ""
        self.filter_location_id = ALL_FILTER_VALUE
        self.filter_supplier_id = ALL_FILTER_VALUE
        self.filter_status = ALL_FILTER_VALUE
        await self._load_items()

    @rx.event
    async def open_create_dialog(self):
        """Open the create item dialog (placeholder for future implementation)."""
        if not self._item_sheet_id:
            raise ValueError("ItemSheet ID is not set")
        item_form_state = await self.get_state(ItemFormDialogState)
        await item_form_state.open_create_dialog(self._item_sheet_id)
        item_form_state.set_callback_after_close(self._reload_items)

    async def _reload_items(self, _):
        """Reload the items list (can be called after item creation/update)."""
        await self._load_items()

    async def _on_delete_success(self, result: DeleteItemResultDTO):
        """Callback after item delete (discarded or deleted).

        :param result: The result of the delete operation
        :type result: DeleteItemResultDTO
        """
        await self._load_items()
        yield

    @rx.event
    async def open_receive_dialog(self, item: ItemDTO):
        """Open the receive stock dialog for a item.

        :param item: The item to receive stock for
        :type item: ItemDTO
        """
        dialog_state = await self.get_state(ItemEventFormDialogState)
        dialog_state.set_callback_after_close(self._reload_items)
        dialog_state.open_dialog_for_event(item, ItemEventType.RECEIVE)

    @rx.event
    async def open_consume_dialog(self, item: ItemDTO):
        """Open the consume stock dialog for a item.

        :param item: The item to consume stock from
        :type item: ItemDTO
        """
        dialog_state = await self.get_state(ItemEventFormDialogState)
        dialog_state.set_callback_after_close(self._reload_items)
        dialog_state.open_dialog_for_event(item, ItemEventType.CONSUME)

    @rx.event
    async def open_move_dialog(self, item: ItemDTO):
        """Open the move item dialog for a item.

        :param item: The item to move
        :type item: ItemDTO
        """
        dialog_state = await self.get_state(MoveItemFormDialogState)
        dialog_state.set_callback_after_close(self._reload_items)
        await dialog_state.open_move_dialog(item)

    @rx.event
    async def open_update_dialog(self, item: ItemDTO):
        """Open the update item dialog for a item.

        :param item: The item to update
        :type item: ItemDTO
        """
        dialog_state = await self.get_state(UpdateItemFormDialogState)
        dialog_state.set_callback_after_close(self._reload_items)
        await dialog_state.open_update_dialog(item)

    @rx.event
    async def open_relabel_dialog(self, item: ItemDTO):
        """Open the relabel item dialog for a item.

        :param item: The item to relabel
        :type item: ItemDTO
        """
        dialog_state = await self.get_state(RelabelItemFormDialogState)
        dialog_state.set_callback_after_close(self._reload_items)
        await dialog_state.open_relabel_dialog(item)

    @rx.event
    async def open_use_dialog(self, item: ItemDTO):
        """Open the use item dialog for a item.

        :param item: The item to use
        :type item: ItemDTO
        """
        dialog_state = await self.get_state(UseItemFormDialogState)
        dialog_state.set_callback_after_close(self._reload_items)
        await dialog_state.open_use_dialog(item)

    @rx.event
    async def open_split_dialog(self, item: ItemDTO):
        """Open the split item dialog for a item.

        :param item: The item to split
        :type item: ItemDTO
        """
        dialog_state = await self.get_state(SplitItemFormDialogState)
        dialog_state.set_callback_after_close(self._reload_items)
        dialog_state.open_split_dialog(item)

    @rx.event
    async def open_combine_dialog(self, item: ItemDTO):
        """Open the combine items dialog seeded with a item.

        :param item: The item to seed as the first ingredient
        :type item: ItemDTO
        """
        dialog_state = await self.get_state(CombineItemFormDialogState)
        dialog_state.set_callback_after_close(self._reload_items)
        dialog_state.open_combine_dialog(item)

    @rx.event
    async def open_concentrate_dialog(self, item: ItemDTO):
        """Open the concentrate item dialog for a item.

        :param item: The item to concentrate
        :type item: ItemDTO
        """
        dialog_state = await self.get_state(ConcentrateItemFormDialogState)
        dialog_state.set_callback_after_close(self._reload_items)
        dialog_state.open_concentrate_dialog(item)

    @rx.event
    async def open_dilute_dialog(self, item: ItemDTO):
        """Open the dilute item dialog for a item.

        :param item: The item to dilute (the target)
        :type item: ItemDTO
        """
        dialog_state = await self.get_state(DiluteItemFormDialogState)
        dialog_state.set_callback_after_close(self._reload_items)
        dialog_state.open_dilute_dialog(item)

    @rx.event
    async def open_delete_dialog(self, item: ItemDTO):
        """Open the delete item dialog for a item.

        :param item: The item to delete
        :type item: ItemDTO
        """
        dialog_state = await self.get_state(DeleteItemFormDialogState)
        dialog_state.set_callback_after_close(self._on_delete_success)
        await dialog_state.open_delete_dialog(item)
