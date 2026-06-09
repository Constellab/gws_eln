"""State for the activities list component."""

import reflex as rx
from gws_core import Logger
from gws_eln.activities.activity_dto import ActivityDTO
from gws_eln.activities.activity_search_builder import ActivitySearchBuilder
from gws_eln.activities.activity_type import ActivityType
from gws_reflex_main import ReflexMainState

ALL_FILTER_VALUE = "__all__"


class ActivitiesListState(rx.State):
    """State for managing the activities list component.

    This state handles fetching and displaying the list of activities
    for a specific item with filtering capabilities.
    """

    _item_id: str | None = None
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
    def current_item_id(self) -> str:
        """Return the current item ID.

        :return: The item ID
        :rtype: str
        """
        return self._item_id or ""

    async def _load_activities(self):
        """Load the list of activities with applied filters.

        Uses ActivitySearchBuilder to apply filters.
        """
        if not self._item_id:
            return

        self.is_loading = True
        self.error_message = ""

        try:
            search_builder = ActivitySearchBuilder()

            search_builder.add_entity_filter(self._item_id)

            if self.filter_activity_type and self.filter_activity_type != ALL_FILTER_VALUE:
                activity_type = ActivityType(self.filter_activity_type)
                search_builder.add_activity_type_filter(activity_type)

            activities = search_builder.search_all()

            self._activities = [activity.to_dto() for activity in activities]

        finally:
            self.is_loading = False

    @rx.event(background=True)
    async def fetch_activities_on_mount(self, item_id: str):
        """Event handler to fetch activities when the component is mounted.

        :param item_id: The ID of the item to fetch activities for
        :type item_id: str
        """
        async with self:
            if not item_id:
                return

            if self._item_id == item_id and len(self._activities) > 0:
                return

            self._item_id = item_id
            self._activities = []
            self.is_loading = True
            main_state = await self.get_state(ReflexMainState)

        try:
            with await main_state.authenticate_user():
                async with self:
                    await self._load_activities()
        except Exception as e:
            Logger.error(f"Error loading activities for item {item_id}: {e}")
            Logger.log_exception_stack_trace(e)
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
        main_state = await self.get_state(ReflexMainState)
        with await main_state.authenticate_user():
            await self._load_activities()
