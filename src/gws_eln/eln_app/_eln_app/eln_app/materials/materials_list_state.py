"""State for the materials list page."""

import reflex as rx
from gws_eln.materials.material_dto import MaterialDTO
from gws_eln.materials.material_search_builder import MaterialSearchBuilder
from gws_eln.materials.material_service import MaterialService
from gws_reflex_main import ConfirmDialogState, ReflexMainState

from ..material_form_dialog.material_form_dialog_state import MaterialFormDialogState


class MaterialsListState(rx.State):
    """State for managing the materials list page.

    This state handles fetching and displaying the list of materials
    with filtering capabilities.
    """

    materials: list[MaterialDTO] = []
    is_loading: bool = False
    error_message: str = ""

    # Filter state
    search_text: str = ""

    async def load_materials(self):
        """Load the list of materials with applied filters.

        Uses MaterialSearchBuilder to apply text search filter.
        """
        main_state = await self.get_state(ReflexMainState)
        if not await main_state.check_authentication():
            self.error_message = "You must be authenticated to view materials"
            return

        self.is_loading = True
        self.error_message = ""

        try:
            search_builder = MaterialSearchBuilder()

            if self.search_text:
                search_builder.add_name_filter(self.search_text)

            materials = search_builder.search_all()

            self.materials = [material.to_dto() for material in materials]

        finally:
            self.is_loading = False

    async def on_load(self):
        """Event handler called when the page loads."""
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
    async def clear_filters(self):
        """Clear all filters and reload materials."""
        self.search_text = ""
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
