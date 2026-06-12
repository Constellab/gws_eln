from gws_core import SearchBuilder

from gws_eln.activities.activity import Activity
from gws_eln.activities.activity_input import ActivityInput
from gws_eln.activities.activity_output import ActivityOutput
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
        """Filter the search query to every activity that references the item.

        An item appears in an activity in three ways, all of which belong to its
        history: as the activity's subject (``Activity.item``), as an input it was
        taken from (an ``ActivityInput`` row), or as an output it was created by
        (an ``ActivityOutput`` row). For transforms like combine, the ingredients
        are only recorded as inputs, so a subject-only filter would hide the
        combine from each ingredient's timeline.
        """
        activity_ids_as_input = ActivityInput.select(ActivityInput.activity).where(
            ActivityInput.item == entity_id
        )
        activity_ids_as_output = ActivityOutput.select(ActivityOutput.activity).where(
            ActivityOutput.item == entity_id
        )

        self.add_expression(
            (Activity.item == entity_id)
            | (Activity.id.in_(activity_ids_as_input))
            | (Activity.id.in_(activity_ids_as_output))
        )
        return self
