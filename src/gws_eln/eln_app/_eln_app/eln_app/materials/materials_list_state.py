"""State for the materials list page."""

import reflex as rx
from gws_eln.core.unit_type import UnitType
from gws_eln.materials.material_dto import MaterialDTO
from gws_eln.materials.material_search_builder import MaterialSearchBuilder
from gws_eln.materials.material_service import MaterialService
from gws_eln.suppliers.supplier_dto import SupplierDTO
from gws_eln.suppliers.supplier_search_builder import SupplierSearchBuilder
from gws_reflex_main import ConfirmDialogState, ReflexMainState

from ..common.eln_app_router import ElnAppRouter
from .material_form_dialog.material_form_dialog_state import MaterialFormDialogState

# Constants for "all" filter options
ALL_FILTER_VALUE = "__all__"


class MaterialsListState(rx.State):
    """State for managing the materials list page.

    This state handles fetching and displaying the list of materials
    with filtering capabilities.
    """

    materials: list[MaterialDTO] = []
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

    async def load_materials(self):
        """Load the list of materials with applied filters.

        Uses MaterialSearchBuilder to apply filters.
        """
        main_state = await self.get_state(ReflexMainState)
        if not await main_state.check_authentication():
            self.error_message = "You must be authenticated to view materials"
            return

        self.is_loading = True
        self.error_message = ""

        try:
            search_builder = MaterialSearchBuilder()

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

            materials = search_builder.search_all()

            self.materials = [material.to_dto() for material in materials]

        finally:
            self.is_loading = False

    async def on_load(self):
        """Event handler called when the page loads."""
        await self._load_suppliers()
        await self.load_materials()

    @rx.event
    async def handle_search_change(self, value: str):
        """Handle text search filter change.

        :param value: The search text
        :type value: str
        """
        self.search_text = value
        await self.load_materials()

    @rx.event
    async def handle_supplier_filter_change(self, value: str):
        """Handle supplier filter change.

        :param value: The supplier ID or ALL_FILTER_VALUE
        :type value: str
        """
        self.filter_supplier_id = value
        await self.load_materials()

    @rx.event
    async def handle_consumable_filter_change(self, value: str):
        """Handle consumable filter change.

        :param value: "true", "false", or ALL_FILTER_VALUE
        :type value: str
        """
        self.filter_is_consumable = value
        await self.load_materials()

    @rx.event
    async def handle_unit_type_filter_change(self, value: str):
        """Handle unit type filter change.

        :param value: The unit type value or ALL_FILTER_VALUE
        :type value: str
        """
        self.filter_unit_type = value
        await self.load_materials()

    @rx.event
    async def clear_filters(self):
        """Clear all filters and reload materials."""
        self.search_text = ""
        self.filter_supplier_id = ALL_FILTER_VALUE
        self.filter_is_consumable = ALL_FILTER_VALUE
        self.filter_unit_type = ALL_FILTER_VALUE
        await self.load_materials()

    @rx.event
    async def open_create_dialog(self):
        """Open the create material dialog."""
        form_state = await self.get_state(MaterialFormDialogState)
        form_state.set_callback_after_close(self.on_dialog_close)
        await form_state.open_create_dialog()

    @rx.event
    async def open_update_dialog(self, material: MaterialDTO):
        """Open the update material dialog.

        :param material: The material to update
        :type material: MaterialDTO
        """
        form_state = await self.get_state(MaterialFormDialogState)
        form_state.set_callback_after_close(self.on_dialog_close)
        await form_state.open_update_dialog(material)

    async def on_dialog_close(self, _: MaterialDTO):
        """Callback when any dialog is closed to refresh the materials list."""
        await self._load_suppliers()
        await self.load_materials()

    @rx.event
    async def open_delete_dialog(self, material: MaterialDTO):
        """Open the delete material confirmation dialog.

        :param material: The material to delete
        :type material: MaterialDTO
        """
        delete_dialog_state = await self.get_state(ConfirmDialogState)

        delete_dialog_state.open_dialog(
            title="Delete Material",
            content=f"Are you sure you want to delete the material '{material.name}'?",
            action=lambda: self._delete_action(material.id),
        )

    async def _delete_action(self, material_id: str):
        """Delete the material.

        :param material_id: The ID of the material to delete
        :type material_id: str
        """
        main_state = await self.get_state(ReflexMainState)
        with await main_state.authenticate_user():
            material_service = MaterialService()
            material_service.delete_material(material_id)

        yield rx.toast.success("Material deleted successfully")

        await self.load_materials()

    @rx.event
    def go_to_material(self, material_id: str):
        """Navigate to the material detail page.

        :param material_id: The ID of the material to view
        :type material_id: str
        """
        return rx.redirect(ElnAppRouter.get_material_detail_url(material_id))
