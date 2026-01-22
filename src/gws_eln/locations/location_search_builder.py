from gws_core import SearchBuilder

from gws_eln.locations.location import Location


class LocationSearchBuilder(SearchBuilder):
    def __init__(self) -> None:
        super().__init__(Location, default_orders=[Location.name])

    def add_name_filter(self, name: str) -> "LocationSearchBuilder":
        """Filter the search query by location name (case-insensitive contains)"""
        like_pattern = f"%{name}%"
        self.add_expression(Location.name.ilike(like_pattern))
        return self
