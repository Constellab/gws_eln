"""State for the suppliers list page."""

import reflex as rx
from gws_eln.suppliers.supplier_dto import SupplierDTO
from gws_eln.suppliers.supplier_search_builder import SupplierSearchBuilder
from gws_eln.suppliers.supplier_service import SupplierService
from gws_reflex_main import ConfirmDialogState, ReflexMainState

from .supplier_form_dialog.supplier_form_dialog_state import SupplierFormDialogState


class SuppliersListState(rx.State):
    """State for managing the suppliers list page.

    This state handles fetching and displaying the list of suppliers
    with filtering capabilities.
    """

    suppliers: list[SupplierDTO] = []
    is_loading: bool = False
    error_message: str = ""

    # Filter state
    search_text: str = ""

    async def load_suppliers(self):
        """Load the list of suppliers with applied filters.

        Uses SupplierSearchBuilder to apply text search filter.
        """
        main_state = await self.get_state(ReflexMainState)
        if not await main_state.check_authentication():
            self.error_message = "You must be authenticated to view suppliers"
            return

        self.is_loading = True
        self.error_message = ""

        try:
            search_builder = SupplierSearchBuilder()

            if self.search_text:
                search_builder.add_name_filter(self.search_text)

            suppliers = search_builder.search_all()

            self.suppliers = [supplier.to_dto() for supplier in suppliers]

        finally:
            self.is_loading = False

    async def on_load(self):
        """Event handler called when the page loads."""
        await self.load_suppliers()

    @rx.event
    async def handle_search_change(self, value: str):
        """Handle text search filter change.

        :param value: The search text
        :type value: str
        """
        self.search_text = value
        await self.load_suppliers()

    @rx.event
    async def clear_filters(self):
        """Clear all filters and reload suppliers."""
        self.search_text = ""
        await self.load_suppliers()

    @rx.event
    async def open_create_dialog(self):
        """Open the create supplier dialog."""
        form_state = await self.get_state(SupplierFormDialogState)
        form_state.set_callback_after_close(self._on_dialog_close)
        await form_state.open_create_dialog()

    @rx.event
    async def open_update_dialog(self, supplier: SupplierDTO):
        """Open the update supplier dialog.

        :param supplier: The supplier to update
        :type supplier: SupplierDTO
        """
        form_state = await self.get_state(SupplierFormDialogState)
        form_state.set_callback_after_close(self._on_dialog_close)
        await form_state.open_update_dialog(supplier)

    async def _on_dialog_close(self, _: SupplierDTO):
        """Callback when any dialog is closed to refresh the suppliers list."""
        await self.load_suppliers()

    @rx.event
    async def open_delete_dialog(self, supplier: SupplierDTO):
        """Open the delete supplier confirmation dialog.

        :param supplier: The supplier to delete
        :type supplier: SupplierDTO
        """
        delete_dialog_state = await self.get_state(ConfirmDialogState)

        delete_dialog_state.open_dialog(
            title="Delete Supplier",
            content=f"Are you sure you want to delete the supplier '{supplier.name}'?",
            action=lambda: self._delete_action(supplier.id),
        )

    async def _delete_action(self, supplier_id: str):
        """Delete the supplier.

        :param supplier_id: The ID of the supplier to delete
        :type supplier_id: str
        """
        main_state = await self.get_state(ReflexMainState)
        with await main_state.authenticate_user():
            supplier_service = SupplierService()
            supplier_service.delete_supplier(supplier_id)

        yield rx.toast.success("Supplier deleted successfully")

        await self.load_suppliers()
