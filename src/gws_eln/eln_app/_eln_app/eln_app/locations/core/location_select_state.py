from dataclasses import dataclass

import reflex as rx
from gws_eln.locations.location import Location
from gws_reflex_main import ReflexMainState


@dataclass
class LocationSelectDTO:
    value: str
    label: str


class LocationSelectState(rx.State):
    """State for managing location selection and loading locations from database."""

    # Explicit list var (not a computed var) so it can be reliably refreshed
    # after a location is created on the fly from another form.
    locations: list[LocationSelectDTO] = []
    _loaded: bool = False

    async def _load(self) -> None:
        """Load all locations from the database, sorted by name."""
        main_state = await self.get_state(ReflexMainState)
        try:
            with await main_state.authenticate_user():
                location_list = list(Location.select().order_by(Location.name))
        except Exception:
            self.locations = []
            return
        self.locations = [
            LocationSelectDTO(value=str(location.id), label=location.name)
            for location in location_list
        ]
        self._loaded = True

    @rx.event
    async def ensure_loaded(self):
        """Load the locations once, when a select mounts."""
        if not self._loaded:
            await self._load()

    async def reload(self) -> None:
        """Force the location list to be reloaded from the database."""
        await self._load()
