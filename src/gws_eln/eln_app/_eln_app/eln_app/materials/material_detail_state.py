"""State for the material detail page."""

import reflex as rx
from gws_eln.materials.material import Material
from gws_eln.materials.material_dto import MaterialDTO
from gws_eln.materials.material_service import MaterialService
from gws_reflex_main import ReflexMainState


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
