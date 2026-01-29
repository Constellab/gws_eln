from collections.abc import Callable, Coroutine
from typing import Any

import reflex as rx
from gws_eln.locations.location import Location
from gws_eln.locations.location_dto import CreateLocationDTO, LocationDTO, UpdateLocationDTO
from gws_eln.locations.location_service import LocationService
from gws_reflex_main import FormDialogState, ReflexMainState

FormDialogCloseCallback = Callable[[LocationDTO], Coroutine[Any, Any, None]]


class LocationFormDialogState(FormDialogState, rx.State):
    """State management for the create/update location dialog functionality."""

    # Location being edited (None for create mode)
    _editing_location: LocationDTO | None = None

    # Form field default values
    form_name: str = ""
    form_description: str = ""

    _callback_after_close: FormDialogCloseCallback | None = None

    @rx.event
    async def open_create_dialog(self):
        """Open the dialog in create mode."""
        # Reset to create mode
        self.is_update_mode = False

        # Open the dialog
        self.dialog_opened = True

    @rx.event
    async def open_update_dialog(self, location: LocationDTO):
        """Open the dialog in update mode with existing location data.

        Args:
            location: The location to update
        """
        # Store the location being edited
        self._editing_location = location

        # Initialize form fields with location data
        self.form_name = location.name
        self.form_description = location.description or ""

        # Mark as editing
        self.is_update_mode = True

        # Open the dialog
        await self.open_dialog()

    def _validate_form_data(self, form_data: dict) -> tuple[str, str]:
        """Validate and parse form data.

        Args:
            form_data: Dictionary containing form fields (name, description)

        Returns:
            Tuple of (name, description) if validation succeeds

        Raises:
            Exception: If validation fails
        """
        # Get values from form data
        name = form_data.get("name", "").strip()
        description = form_data.get("description", "").strip() or None

        # Validate required fields
        if not name:
            raise Exception("Location name is required")

        return name, description

    async def _create(self, form_data: dict):
        """Create a new location using the form data.

        Args:
            form_data: Dictionary containing form fields (name, description)

        Yields:
            Reflex events (rx.toast)
        """
        # Validate and parse form data
        name, description = self._validate_form_data(form_data)

        main_state: ReflexMainState
        async with self:
            main_state = await self.get_state(ReflexMainState)

        # Create the location
        location: Location
        with await main_state.authenticate_user():
            location_service = LocationService()
            dto = CreateLocationDTO(name=name, description=description)
            location = location_service.create_location(dto)

        # Show success toast
        yield rx.toast.success("Location created successfully")

        if self._callback_after_close:
            await self._callback_after_close(location.to_dto())

    async def _update(self, form_data: dict):
        """Update an existing location using the form data.

        Args:
            form_data: Dictionary containing form fields (name, description)

        Yields:
            Reflex events (rx.toast)
        """
        # Validate and parse form data
        name, description = self._validate_form_data(form_data)

        main_state: ReflexMainState
        async with self:
            main_state = await self.get_state(ReflexMainState)

        # Update the location
        location: Location
        with await main_state.authenticate_user():
            location_service = LocationService()
            dto = UpdateLocationDTO(name=name, description=description)
            location = location_service.update_location(self._editing_location.id, dto)

        # Show success toast
        yield rx.toast.success("Location updated successfully")

        if self._callback_after_close:
            await self._callback_after_close(location.to_dto())

    async def _clear_form_state(self):
        """Clear all form state after successful operation."""
        self._editing_location = None
        self.form_name = ""
        self.form_description = ""
        self.is_update_mode = False

    def set_callback_after_close(self, callback: FormDialogCloseCallback | None):
        """Set the callback to invoke after the dialog closes successfully.

        This callback is called after a successful create or update operation,
        typically used to refresh a list or navigate to the created/updated item.

        Args:
            callback: The async callback function to invoke, or None to clear
        """
        self._callback_after_close = callback
