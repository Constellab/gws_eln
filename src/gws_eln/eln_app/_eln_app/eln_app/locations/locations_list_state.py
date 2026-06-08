"""State for the locations list page."""

import reflex as rx
from gws_eln.locations.location_dto import LocationDTO
from gws_eln.locations.location_search_builder import LocationSearchBuilder
from gws_eln.locations.location_service import LocationService
from gws_reflex_main import ConfirmDialogState, ReflexMainState

from .location_form_dialog.location_form_dialog_state import LocationFormDialogState


class LocationsListState(rx.State):
    """State for managing the locations list page.

    This state handles fetching and displaying the list of locations
    with filtering capabilities.
    """

    locations: list[LocationDTO] = []
    is_loading: bool = False
    error_message: str = ""

    # Filter state
    search_text: str = ""

    async def load_locations(self):
        """Load the list of locations with applied filters.

        Uses LocationSearchBuilder to apply text search filter.
        """
        main_state = await self.get_state(ReflexMainState)
        if not await main_state.check_authentication():
            self.error_message = "You must be authenticated to view locations"
            return

        self.is_loading = True
        self.error_message = ""

        try:
            search_builder = LocationSearchBuilder()

            if self.search_text:
                search_builder.add_name_filter(self.search_text)

            locations = search_builder.search_all()

            self.locations = [location.to_dto() for location in locations]

        finally:
            self.is_loading = False

    @rx.event
    async def on_load(self):
        """Event handler called when the page loads."""
        await self.load_locations()

    @rx.event
    async def handle_search_change(self, value: str):
        """Handle text search filter change.

        :param value: The search text
        :type value: str
        """
        self.search_text = value
        await self.load_locations()

    @rx.event
    async def clear_filters(self):
        """Clear all filters and reload locations."""
        self.search_text = ""
        await self.load_locations()

    @rx.event
    async def open_create_dialog(self):
        """Open the create location dialog."""
        form_state = await self.get_state(LocationFormDialogState)
        form_state.set_callback_after_close(self._on_dialog_close)
        await form_state.open_create_dialog()

    @rx.event
    async def open_update_dialog(self, location: LocationDTO):
        """Open the update location dialog.

        :param location: The location to update
        :type location: LocationDTO
        """
        form_state = await self.get_state(LocationFormDialogState)
        form_state.set_callback_after_close(self._on_dialog_close)
        await form_state.open_update_dialog(location)

    async def _on_dialog_close(self, _: LocationDTO):
        """Callback when any dialog is closed to refresh the locations list."""
        await self.load_locations()

    @rx.event
    async def open_delete_dialog(self, location: LocationDTO):
        """Open the delete location confirmation dialog.

        :param location: The location to delete
        :type location: LocationDTO
        """
        delete_dialog_state = await self.get_state(ConfirmDialogState)

        delete_dialog_state.open_dialog(
            title="Delete Location",
            content=f"Are you sure you want to delete the location '{location.name}'?",
            action=lambda: self._delete_action(location.id),
        )

    async def _delete_action(self, location_id: str):
        """Delete the location.

        :param location_id: The ID of the location to delete
        :type location_id: str
        """
        main_state = await self.get_state(ReflexMainState)
        with await main_state.authenticate_user():
            location_service = LocationService()
            location_service.delete_location(location_id)

        yield rx.toast.success("Location deleted successfully")

        await self.load_locations()
