"""State for the item_sheets list page."""

import reflex as rx
from gws_eln.core.unit_type import UnitType
from gws_eln.items.item_sheet_dto import ItemSheetDTO
from gws_eln.items.item_sheet_search_builder import ItemSheetSearchBuilder
from gws_eln.items.item_sheet_service import ItemSheetService
from gws_eln.suppliers.supplier_dto import SupplierDTO
from gws_eln.suppliers.supplier_search_builder import SupplierSearchBuilder
from gws_reflex_main import ConfirmDialogState, ReflexMainState

from ..items.item_form_dialog.item_form_dialog_state import ItemFormDialogState
from ..items.items_list_state import ItemsListState
from .item_sheet_detail_state import ItemSheetDetailState
from .item_sheet_form_dialog.item_sheet_form_dialog_state import ItemSheetFormDialogState

# Constants for "all" filter options
ALL_FILTER_VALUE = "__all__"


class ItemSheetsListState(rx.State):
    """State for managing the item_sheets list page.

    This state handles fetching and displaying the list of item_sheets
    with filtering capabilities.
    """

    item_sheets: list[ItemSheetDTO] = []
    is_loading: bool = False
    error_message: str = ""

    # Available suppliers for dropdown filter
    available_suppliers: list[SupplierDTO] = []

    # Filter state
    search_text: str = ""
    filter_supplier_id: str = "__all__"
    filter_is_consumable: str = "__all__"  # "__all__", "true", "false"
    filter_unit_type: str = "__all__"

    async def _load_suppliers(self):
        """Load available suppliers for the filter dropdown."""
        main_state = await self.get_state(ReflexMainState)
        with await main_state.authenticate_user():
            search_builder = SupplierSearchBuilder()
            suppliers = search_builder.search_all()
            self.available_suppliers = [supplier.to_dto() for supplier in suppliers]

    async def load_item_sheets(self):
        """Load the list of item_sheets with applied filters.

        Uses ItemSheetSearchBuilder to apply filters.
        """
        main_state = await self.get_state(ReflexMainState)
        if not await main_state.check_authentication():
            self.error_message = "You must be authenticated to view item sheets"
            return

        self.is_loading = True
        self.error_message = ""

        try:
            with await main_state.authenticate_user():
                search_builder = ItemSheetSearchBuilder()

                # Apply text search filter
                if self.search_text:
                    search_builder.add_name_filter(self.search_text)

                # Apply supplier filter
                if self.filter_supplier_id and self.filter_supplier_id != ALL_FILTER_VALUE:
                    search_builder.add_supplier_filter(self.filter_supplier_id)

                # Apply consumable filter
                if self.filter_is_consumable and self.filter_is_consumable != ALL_FILTER_VALUE:
                    is_consumable = self.filter_is_consumable == "true"
                    search_builder.add_is_consumable_filter(is_consumable)

                # Apply unit type filter
                if self.filter_unit_type and self.filter_unit_type != ALL_FILTER_VALUE:
                    unit_type = UnitType(self.filter_unit_type)
                    search_builder.add_unit_type_filter(unit_type)

                item_sheets = search_builder.search_all()

                self.item_sheets = [item_sheet.to_dto() for item_sheet in item_sheets]

        finally:
            self.is_loading = False

    @rx.event
    async def on_load(self):
        """Event handler called when the page loads."""
        await self._load_suppliers()
        await self.load_item_sheets()

    @rx.event
    async def handle_search_change(self, value: str):
        """Handle text search filter change.

        :param value: The search text
        :type value: str
        """
        self.search_text = value
        await self.load_item_sheets()

    @rx.event
    async def handle_supplier_filter_change(self, value: str):
        """Handle supplier filter change.

        :param value: The supplier ID or ALL_FILTER_VALUE
        :type value: str
        """
        self.filter_supplier_id = value
        await self.load_item_sheets()

    @rx.event
    async def handle_consumable_filter_change(self, value: str):
        """Handle consumable filter change.

        :param value: "true", "false", or ALL_FILTER_VALUE
        :type value: str
        """
        self.filter_is_consumable = value
        await self.load_item_sheets()

    @rx.event
    async def handle_unit_type_filter_change(self, value: str):
        """Handle unit type filter change.

        :param value: The unit type value or ALL_FILTER_VALUE
        :type value: str
        """
        self.filter_unit_type = value
        await self.load_item_sheets()

    @rx.event
    async def clear_filters(self):
        """Clear all filters and reload item_sheets."""
        self.search_text = ""
        self.filter_supplier_id = ALL_FILTER_VALUE
        self.filter_is_consumable = ALL_FILTER_VALUE
        self.filter_unit_type = ALL_FILTER_VALUE
        await self.load_item_sheets()

    @rx.event
    async def open_create_dialog(self):
        """Open the create item_sheet dialog."""
        form_state = await self.get_state(ItemSheetFormDialogState)
        form_state.set_callback_after_close(self.on_dialog_close)
        await form_state.open_create_dialog()

    @rx.event
    async def open_create_item_dialog(self, item_sheet: ItemSheetDTO):
        """Open the dialog to create a new item for the given item_sheet.

        :param item_sheet: The item_sheet to create an item for
        :type item_sheet: ItemSheetDTO
        """
        item_form_state = await self.get_state(ItemFormDialogState)
        await item_form_state.open_create_dialog(item_sheet.id)
        # No list refresh needed: the item_sheets list does not display items.
        item_form_state.set_callback_after_close(None)

    @rx.event
    async def open_update_dialog(self, item_sheet: ItemSheetDTO):
        """Open the update item_sheet dialog.

        :param item_sheet: The item_sheet to update
        :type item_sheet: ItemSheetDTO
        """
        form_state = await self.get_state(ItemSheetFormDialogState)
        form_state.set_callback_after_close(self.on_dialog_close)
        await form_state.open_update_dialog(item_sheet)

    async def on_dialog_close(self, _: ItemSheetDTO):
        """Callback when any dialog is closed to refresh the item_sheets list."""
        await self._load_suppliers()
        await self.load_item_sheets()

    @rx.event
    async def open_delete_dialog(self, item_sheet: ItemSheetDTO):
        """Open the delete item_sheet confirmation dialog.

        :param item_sheet: The item_sheet to delete
        :type item_sheet: ItemSheetDTO
        """
        delete_dialog_state = await self.get_state(ConfirmDialogState)

        delete_dialog_state.open_dialog(
            title="Delete item sheet",
            content=f"Are you sure you want to delete the item sheet '{item_sheet.name}'?",
            action=lambda: self._delete_action(item_sheet.id),
        )

    async def _delete_action(self, item_sheet_id: str):
        """Delete the item_sheet.

        :param item_sheet_id: The ID of the item_sheet to delete
        :type item_sheet_id: str
        """
        main_state = await self.get_state(ReflexMainState)
        with await main_state.authenticate_user():
            item_sheet_service = ItemSheetService()
            item_sheet_service.delete_item_sheet(item_sheet_id)

        yield rx.toast.success("Item sheet deleted successfully")

        await self.load_item_sheets()

    @rx.event
    async def prepare_item_sheet_navigation(self, item_sheet_id: str):
        """Prime the destination states to "loading" for an item_sheet detail view.

        The navigation itself is a client-side ``rx.redirect`` fired from the
        row's ``on_click`` (instant, no backend round-trip). This event runs in
        parallel to reset the detail/items states so the destination page shows
        a spinner instead of the previous sheet's data while it reloads.

        :param item_sheet_id: The ID of the item_sheet being opened
        :type item_sheet_id: str
        """
        detail_state = await self.get_state(ItemSheetDetailState)
        detail_state.is_loading = True
        detail_state.item_sheet = None
        detail_state.error_message = ""

        items_state = await self.get_state(ItemsListState)
        items_state.is_loading = True
        items_state._items = []
        items_state._item_sheet_id = None  # Force a reload for the new sheet
        items_state.error_message = ""
