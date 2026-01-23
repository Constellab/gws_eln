"""State for the batches list component."""

import reflex as rx
from gws_eln.locations.location_dto import LocationDTO
from gws_eln.locations.location_search_builder import LocationSearchBuilder
from gws_eln.materials.batch_status import BatchStatus
from gws_eln.materials.material_batch_dto import MaterialBatchDTO
from gws_eln.materials.material_batch_search_builder import MaterialBatchSearchBuilder
from gws_eln.suppliers.supplier_dto import SupplierDTO
from gws_eln.suppliers.supplier_search_builder import SupplierSearchBuilder
from gws_reflex_main import ReflexMainState

from ..material_batch_form_dialog.material_batch_form_dialog_state import (
    MaterialBatchFormDialogState,
)

# Constants for "all" filter options
ALL_FILTER_VALUE = "__all__"


class BatchesListState(ReflexMainState):
    """State for managing the batches list component.

    This state handles fetching and displaying the list of batches
    for a specific material with filtering capabilities.
    """

    _material_id: str | None = None
    _batches: list[MaterialBatchDTO] = []
    is_loading: bool = False
    error_message: str = ""

    # Available options for dropdown filters
    available_locations: list[LocationDTO] = []
    available_suppliers: list[SupplierDTO] = []

    # Filter state
    search_text: str = ""
    filter_location_id: str = "__all__"
    filter_supplier_id: str = "__all__"
    filter_status: str = "__all__"  # "__all__", "active", "discarded"

    @rx.var
    def batches(self) -> list[MaterialBatchDTO]:
        """Return the list of batches as DTOs.

        :return: List of MaterialBatchDTOs
        :rtype: list[MaterialBatchDTO]
        """
        return self._batches

    @rx.var
    def current_material_id(self) -> str:
        """Return the current material ID.

        :return: The material ID
        :rtype: str
        """
        return self._material_id or ""

    async def _load_filter_options(self):
        """Load available options for the filter dropdowns."""
        with await self.authenticate_user():
            # Load locations
            location_search_builder = LocationSearchBuilder()
            locations = location_search_builder.search_all()
            self.available_locations = [location.to_dto() for location in locations]

            # Load suppliers
            supplier_search_builder = SupplierSearchBuilder()
            suppliers = supplier_search_builder.search_all()
            self.available_suppliers = [supplier.to_dto() for supplier in suppliers]

    async def _load_batches(self):
        """Load the list of batches with applied filters.

        Uses MaterialBatchSearchBuilder to apply filters.
        """
        if not self._material_id:
            return

        self.is_loading = True
        self.error_message = ""

        try:
            search_builder = MaterialBatchSearchBuilder()

            # Always filter by material_id
            search_builder.add_material_filter(self._material_id)

            # Apply text search filter (batch number)
            if self.search_text:
                search_builder.add_batch_number_filter(self.search_text)

            # Apply location filter
            if self.filter_location_id and self.filter_location_id != ALL_FILTER_VALUE:
                search_builder.add_location_filter(self.filter_location_id)

            # Apply supplier filter
            if self.filter_supplier_id and self.filter_supplier_id != ALL_FILTER_VALUE:
                search_builder.add_supplier_filter(self.filter_supplier_id)

            # Apply status filter
            if self.filter_status and self.filter_status != ALL_FILTER_VALUE:
                status = BatchStatus(self.filter_status)
                search_builder.add_status_filter(status)

            batches = search_builder.search_all()

            self._batches = [batch.to_dto() for batch in batches]

        finally:
            self.is_loading = False

    @rx.event(background=True)
    async def fetch_batches_on_mount(self, material_id: str):
        """Event handler to fetch batches when the component is mounted.

        :param material_id: The ID of the material to fetch batches for
        :type material_id: str
        """
        async with self:
            if not material_id:
                return

            # Check if we already have batches for this material
            if self._material_id == material_id:
                return

            self._material_id = material_id
            self._batches = []
            self.is_loading = True

        try:
            with await self.authenticate_user():
                async with self:
                    await self._load_filter_options()
                    await self._load_batches()
        except Exception:
            async with self:
                self._batches = []
                self.is_loading = False
                self.error_message = "Failed to load batches"

    @rx.event
    async def handle_search_change(self, value: str):
        """Handle text search filter change.

        :param value: The search text
        :type value: str
        """
        self.search_text = value
        await self._load_batches()

    @rx.event
    async def handle_location_filter_change(self, value: str):
        """Handle location filter change.

        :param value: The location ID or ALL_FILTER_VALUE
        :type value: str
        """
        self.filter_location_id = value
        await self._load_batches()

    @rx.event
    async def handle_supplier_filter_change(self, value: str):
        """Handle supplier filter change.

        :param value: The supplier ID or ALL_FILTER_VALUE
        :type value: str
        """
        self.filter_supplier_id = value
        await self._load_batches()

    @rx.event
    async def handle_status_filter_change(self, value: str):
        """Handle status filter change.

        :param value: "active", "discarded", or ALL_FILTER_VALUE
        :type value: str
        """
        self.filter_status = value
        await self._load_batches()

    @rx.event
    async def clear_filters(self):
        """Clear all filters and reload batches."""
        self.search_text = ""
        self.filter_location_id = ALL_FILTER_VALUE
        self.filter_supplier_id = ALL_FILTER_VALUE
        self.filter_status = ALL_FILTER_VALUE
        await self._load_batches()

    @rx.event
    async def open_create_dialog(self):
        """Open the create batch dialog (placeholder for future implementation)."""
        if not self._material_id:
            raise ValueError("Material ID is not set")
        batch_form_state = await self.get_state(MaterialBatchFormDialogState)
        await batch_form_state.open_create_dialog(self._material_id)
        batch_form_state.set_callback_after_close(self._reload_batches)

    async def _reload_batches(self, _):
        """Reload the batches list (can be called after batch creation/update)."""
        await self._load_batches()
