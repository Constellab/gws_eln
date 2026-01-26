from gws_core import SearchBuilder

from gws_eln.activities.activity import Activity
from gws_eln.activities.activity_type import ActivityType


class ActivitySearchBuilder(SearchBuilder):
    def __init__(self) -> None:
        super().__init__(Activity, default_orders=[Activity.created_at.desc()])

    def add_activity_type_filter(self, activity_type: ActivityType) -> "ActivitySearchBuilder":
        """Filter the search query by activity type"""
        self.add_expression(Activity.activity_type == activity_type)
        return self

    def add_activity_types_filter(
        self, activity_types: list[ActivityType]
    ) -> "ActivitySearchBuilder":
        """Filter the search query by multiple activity types"""
        self.add_expression(Activity.activity_type.in_(activity_types))
        return self

    def add_entity_filter(self, entity_id: str) -> "ActivitySearchBuilder":
        """Filter the search query by entity (material batch) ID"""
        self.add_expression(Activity.batch == entity_id)
        return self
