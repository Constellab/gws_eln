from dataclasses import dataclass

import reflex as rx
from gws_eln.locations.location import Location


@dataclass
class LocationSelectDTO:
    value: str
    label: str


class LocationSelectState(rx.State):
    """State for managing location selection and loading locations from database."""

    @rx.var
    def locations(self) -> list[LocationSelectDTO]:
        """Load all locations from the database, sorted by name."""
        try:
            location_list = list(Location.select().order_by(Location.name))
        except Exception:
            return []
        return [
            LocationSelectDTO(
                value=str(location.id),
                label=location.name,
            )
            for location in location_list
        ]
