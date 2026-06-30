"""Request-scoped DB cache for a single lineage computation.

The lineage graph is built in one pass over display-only data, so nothing can
change between reads. ``LineageRepo`` fetches every activity's ingredient inputs
/ outputs / type from the DB at most once (batched), and every item's adjacency
once; all build phases (walk, expand, edge quantities) then read from memory
instead of re-querying.
"""

from collections.abc import Collection

from gws_eln.activities.activity import Activity
from gws_eln.activities.activity_input import ActivityInput
from gws_eln.activities.activity_input_role import ActivityInputRole
from gws_eln.activities.activity_output import ActivityOutput
from gws_eln.activities.activity_type import ActivityType


class LineageRepo:
    """Loads and caches the activity graph rows for one lineage computation."""

    def __init__(self) -> None:
        self._loaded_activity_ids: set[str] = set()
        self._ingredient_inputs_by_activity: dict[str, list[ActivityInput]] = {}
        self._outputs_by_activity: dict[str, list[ActivityOutput]] = {}
        self._activity_type: dict[str, ActivityType] = {}
        self._activity_ids_by_input_item: dict[str, list[str]] = {}
        self._activity_ids_by_output_item: dict[str, list[str]] = {}

    def load_activities(self, activity_ids: list[str]) -> None:
        """Fetch (once, batched) the inputs, outputs and type of new activities."""
        missing = [
            activity_id
            for activity_id in dict.fromkeys(activity_ids)
            if activity_id not in self._loaded_activity_ids
        ]
        if not missing:
            return
        # Pre-create empty buckets so an activity with no input/output still
        # counts as loaded and its accessors return [].
        for activity_id in missing:
            self._ingredient_inputs_by_activity[activity_id] = []
            self._outputs_by_activity[activity_id] = []
            self._loaded_activity_ids.add(activity_id)

        for inp in ActivityInput.select().where(
            (ActivityInput.activity.in_(missing))
            & (ActivityInput.role == ActivityInputRole.INGREDIENT)
        ):
            self._ingredient_inputs_by_activity[inp.activity_id].append(inp)
        for out in ActivityOutput.select().where(ActivityOutput.activity.in_(missing)):
            self._outputs_by_activity[out.activity_id].append(out)
        for activity in Activity.select(Activity.id, Activity.activity_type).where(
            Activity.id.in_(missing)
        ):
            self._activity_type[activity.id] = activity.activity_type

    def activity_type(self, activity_id: str) -> ActivityType:
        """The activity's type (loading it if needed)."""
        self.load_activities([activity_id])
        return self._activity_type[activity_id]

    def ingredient_inputs(self, activity_id: str) -> list[ActivityInput]:
        """The activity's INGREDIENT inputs (loading it if needed)."""
        self.load_activities([activity_id])
        return self._ingredient_inputs_by_activity[activity_id]

    def outputs(self, activity_id: str) -> list[ActivityOutput]:
        """The activity's outputs (loading it if needed)."""
        self.load_activities([activity_id])
        return self._outputs_by_activity[activity_id]

    def activity_ids_by_input_items(self, item_ids: Collection[str]) -> dict[str, list[str]]:
        """Per item, ids of activities where it is an INGREDIENT input.

        Batched: resolves the whole frontier in a single query (the not-yet-cached
        items), so a BFS level costs one query instead of one per item.

        :return: ``{item_id: [activity_id, ...]}`` for every requested item.
        """
        missing = [
            item_id
            for item_id in dict.fromkeys(item_ids)
            if item_id not in self._activity_ids_by_input_item
        ]
        if missing:
            for item_id in missing:
                self._activity_ids_by_input_item[item_id] = []
            for inp in ActivityInput.select(
                ActivityInput.item, ActivityInput.activity
            ).where(
                (ActivityInput.item.in_(missing))
                & (ActivityInput.role == ActivityInputRole.INGREDIENT)
            ):
                self._activity_ids_by_input_item[inp.item_id].append(inp.activity_id)
        return {item_id: self._activity_ids_by_input_item[item_id] for item_id in item_ids}

    def activity_ids_by_output_items(self, item_ids: Collection[str]) -> dict[str, list[str]]:
        """Per item, ids of activities that output it (batched, one query).

        :return: ``{item_id: [activity_id, ...]}`` for every requested item.
        """
        missing = [
            item_id
            for item_id in dict.fromkeys(item_ids)
            if item_id not in self._activity_ids_by_output_item
        ]
        if missing:
            for item_id in missing:
                self._activity_ids_by_output_item[item_id] = []
            for out in ActivityOutput.select(
                ActivityOutput.item, ActivityOutput.activity
            ).where(ActivityOutput.item.in_(missing)):
                self._activity_ids_by_output_item[out.item_id].append(out.activity_id)
        return {item_id: self._activity_ids_by_output_item[item_id] for item_id in item_ids}

    def activity_ids_with_input_item(self, item_id: str) -> list[str]:
        """Ids of activities where the item is an INGREDIENT input (cached)."""
        return self.activity_ids_by_input_items([item_id])[item_id]

    def activity_ids_with_output_item(self, item_id: str) -> list[str]:
        """Ids of activities that output the item (cached)."""
        return self.activity_ids_by_output_items([item_id])[item_id]
