"""State for the material detail page."""

import reflex as rx
from gws_eln.materials.material import Material
from gws_eln.materials.material_dto import MaterialDTO
from gws_eln.materials.material_service import MaterialService
from gws_reflex_main import ConfirmDialogState, ReflexMainState

from ..common.eln_app_router import ElnAppRouter
from ..material_form_dialog.material_form_dialog_state import MaterialFormDialogState


class MaterialDetailState(rx.State):
    """State for managing the material detail page.

    This state handles fetching and displaying a single material's details.
    """

    material: MaterialDTO | None = None
    is_loading: bool = False
    error_message: str = ""

    async def load_material(self, material_id: str):
        """Load a material by its ID.

        :param material_id: The ID of the material to load
        :type material_id: str
        """
        main_state = await self.get_state(ReflexMainState)
        if not await main_state.check_authentication():
            self.error_message = "You must be authenticated to view this material"
            return

        self.is_loading = True
        self.error_message = ""

        try:
            material_service = MaterialService()
            material: Material
            with await main_state.authenticate_user():
                material = material_service.get_material(material_id)

            if material:
                self.material = material.to_dto()
            else:
                self.error_message = "Material not found"
                self.material = None

        except Exception as e:
            self.error_message = f"Error loading material: {str(e)}"
            self.material = None
        finally:
            self.is_loading = False

    @rx.event
    async def on_load(self):
        """Event handler called when the page loads."""
        # Get material ID from URL params
        material_id = self.material_id
        if material_id:
            await self.load_material(material_id)
        else:
            self.error_message = "No material ID provided"

    @rx.event
    async def open_update_dialog(self):
        """Open the update material dialog."""
        if not self.material:
            return
        form_state = await self.get_state(MaterialFormDialogState)
        form_state.set_callback_after_close(self._on_dialog_close)
        await form_state.open_update_dialog(self.material)

    async def _on_dialog_close(self, _: MaterialDTO):
        """Callback when dialog is closed to refresh the material."""
        await self.load_material(self.material.id)

    @rx.event
    async def open_delete_dialog(self):
        """Open the delete material confirmation dialog."""
        if not self.material:
            return

        delete_dialog_state = await self.get_state(ConfirmDialogState)
        delete_dialog_state.open_dialog(
            title="Delete Material",
            content=f"Are you sure you want to delete the material '{self.material.name}'?",
            action=lambda: self._delete_action(self.material.id),
        )

    async def _delete_action(self, material_id: str):
        """Delete the material and navigate back to the list.

        :param material_id: The ID of the material to delete
        :type material_id: str
        """
        main_state = await self.get_state(ReflexMainState)
        with await main_state.authenticate_user():
            material_service = MaterialService()
            material_service.delete_material(material_id)

        yield rx.toast.success("Material deleted successfully")
        yield rx.redirect(ElnAppRouter.get_material_list_url())
