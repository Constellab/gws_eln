"""State for the activities list component."""

import reflex as rx
from gws_eln.activities.activity_dto import ActivityDTO
from gws_eln.activities.activity_search_builder import ActivitySearchBuilder
from gws_eln.activities.activity_type import ActivityType
from gws_reflex_main import ReflexMainState

ALL_FILTER_VALUE = "__all__"


class ActivitiesListState(ReflexMainState):
    """State for managing the activities list component.

    This state handles fetching and displaying the list of activities
    for a specific batch with filtering capabilities.
    """

    _batch_id: str | None = None
    _activities: list[ActivityDTO] = []
    is_loading: bool = False
    error_message: str = ""

    filter_activity_type: str = "__all__"

    @rx.var
    def activities(self) -> list[ActivityDTO]:
        """Return the list of activities as DTOs.

        :return: List of ActivityDTOs
        :rtype: list[ActivityDTO]
        """
        return self._activities

    @rx.var
    def current_batch_id(self) -> str:
        """Return the current batch ID.

        :return: The batch ID
        :rtype: str
        """
        return self._batch_id or ""

    async def _load_activities(self):
        """Load the list of activities with applied filters.

        Uses ActivitySearchBuilder to apply filters.
        """
        if not self._batch_id:
            return

        self.is_loading = True
        self.error_message = ""

        try:
            search_builder = ActivitySearchBuilder()

            search_builder.add_entity_filter(self._batch_id)

            if self.filter_activity_type and self.filter_activity_type != ALL_FILTER_VALUE:
                activity_type = ActivityType(self.filter_activity_type)
                search_builder.add_activity_type_filter(activity_type)

            activities = search_builder.search_all()

            self._activities = [activity.to_dto() for activity in activities]

        finally:
            self.is_loading = False

    @rx.event(background=True)
    async def fetch_activities_on_mount(self, batch_id: str):
        """Event handler to fetch activities when the component is mounted.

        :param batch_id: The ID of the batch to fetch activities for
        :type batch_id: str
        """
        async with self:
            if not batch_id:
                return

            if self._batch_id == batch_id and len(self._activities) > 0:
                return

            self._batch_id = batch_id
            self._activities = []
            self.is_loading = True

        try:
            with await self.authenticate_user():
                async with self:
                    await self._load_activities()
        except Exception:
            async with self:
                self._activities = []
                self.is_loading = False
                self.error_message = "Failed to load activities"

    @rx.event
    async def handle_activity_type_filter_change(self, value: str):
        """Handle activity type filter change.

        :param value: The activity type value or ALL_FILTER_VALUE
        :type value: str
        """
        self.filter_activity_type = value
        await self._load_activities()

    @rx.event
    async def clear_filters(self):
        """Clear all filters and reload activities."""
        self.filter_activity_type = ALL_FILTER_VALUE
        await self._load_activities()

    @rx.event
    async def refresh_activities(self):
        """Refresh the activities list."""
        with await self.authenticate_user():
            await self._load_activities()
