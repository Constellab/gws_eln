"""State for the activities list component."""

from typing import cast

import reflex as rx
from gws_core import Logger
from gws_eln.activities.activity import Activity
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
            main_state = await self.get_state(ReflexMainState)
            with await main_state.authenticate_user():
                search_builder = ActivitySearchBuilder()

                search_builder.add_entity_filter(self._item_id)

                if self.filter_activity_type and self.filter_activity_type != ALL_FILTER_VALUE:
                    activity_type = ActivityType(self.filter_activity_type)
                    search_builder.add_activity_type_filter(activity_type)

                activities = cast(list[Activity], search_builder.search_all())

            dtos = []
            for activity in activities:
                dto = activity.to_dto()
                # Show the quantity from the current item's perspective (already
                # signed) instead of the activity subject's quantity.
                current_item_pretty_quantity = self._get_current_item_pretty_quantity(dto)
                dto.pretty_quantity = current_item_pretty_quantity
                dto.quantity_color = self._quantity_color(current_item_pretty_quantity)
                dtos.append(dto)
            self._activities = dtos

        finally:
            self.is_loading = False

    def _get_current_item_pretty_quantity(self, dto: ActivityDTO) -> str:
        """Signed pretty quantity of the current item's entry in this activity.

        Returns the matching input's quantity ("-") in priority,
        else the matching output's ("+"), else "" (no quantity to show, e.g.
        move/relabel/use). For activities where the item is not the subject
        (combine ingredient, split child) this differs from the subject's
        quantity. Inputs before outputs is unambiguous: an item is never both an
        input and an output of the same activity.

        :param dto: The activity DTO (its inputs/outputs are already materialized)
        :return: The item's signed pretty quantity, or "" if none
        """
        return (
            next(
                (
                    i.pretty_quantity
                    for i in dto.inputs
                    if i.item.id == self._item_id and i.pretty_quantity
                ),
                None,
            )
            or next(
                (
                    o.pretty_quantity
                    for o in dto.outputs
                    if o.item.id == self._item_id and o.pretty_quantity
                ),
                None,
            )
            or ""
        )

    def _quantity_color(self, signed_quantity: str) -> str:
        """CSS color token for a signed quantity ("-" red, "+" green, "" default)."""
        if signed_quantity.startswith("-"):
            return "var(--red-11)"
        if signed_quantity.startswith("+"):
            return "var(--green-11)"
        return ""

    @rx.event(background=True)
    async def fetch_activities_on_mount(self, item_id: str):
        """Event handler to fetch activities when the component is mounted.

        :param item_id: The ID of the item to fetch activities for
        :type item_id: str
        """
        async with self:
            if not item_id:
                return

            if self._item_id == item_id and self.is_loading:
                return

            item_changed = self._item_id != item_id
            self._item_id = item_id

            if item_changed:
                self._activities = []
            self.is_loading = True

        try:
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

    async def refresh_activities(self):
        """Refresh the activities list from the backend."""
        await self._load_activities()
