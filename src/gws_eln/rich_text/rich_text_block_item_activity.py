from gws_core import RichTextBlockDataSpecial, rich_text_block_decorator

from gws_eln.activities.activity import Activity
from gws_eln.activities.activity_input_role import ActivityInputRole


@rich_text_block_decorator("itemActivity", human_name="Item Activity")
class RichTextBlockItemActivity(RichTextBlockDataSpecial):
    """Block representing an inventory activity in a note.

    Stores only the activity_id - a reference to an Activity entity in the
    database (the block is a view onto an activity, never its owner). The
    activity is created beforehand via the service and selected into the
    block; deleting the block only unlinks it.

    When the note content is served, to_html() loads the activity and renders
    its inputs -> outputs (an activity is a N-to-M event).
    """

    activity_id: str | None = None

    @staticmethod
    def _format_endpoint(item_number: str, pretty_quantity: str | None) -> str:
        """Render one lineage endpoint as ``CODE (±qty)`` (or just ``CODE``)."""
        if pretty_quantity:
            return f"{item_number} ({pretty_quantity})"
        return item_number

    def _lineage_parts(self, activity: Activity) -> tuple[list[str], list[str], list[str]]:
        """Split an activity into ingredient inputs, outputs and instruments.

        :return: (ingredient endpoints, output endpoints, instrument labels)
        """
        ingredient_inputs = [
            self._format_endpoint(i.item.item_number, i.get_pretty_quantity())
            for i in activity.inputs
            if i.role == ActivityInputRole.INGREDIENT
        ]
        outputs = [
            self._format_endpoint(o.item.item_number, o.get_pretty_quantity())
            for o in activity.outputs
        ]
        instruments = [
            i.item.item_number for i in activity.inputs if i.role == ActivityInputRole.INSTRUMENT
        ]
        return ingredient_inputs, outputs, instruments

    def _lineage_core(
        self,
        activity: Activity,
        ingredient_inputs: list[str],
        outputs: list[str],
        instruments: list[str],
        arrow: str,
    ) -> str:
        """Build the ``inputs -> outputs`` core string (degenerate cases included).

        ``arrow`` is the separator inserted between inputs and outputs in the
        caller's format (HTML entity or plain text).
        """
        if ingredient_inputs and outputs:
            return f"{' + '.join(ingredient_inputs)} {arrow} {' + '.join(outputs)}"
        if outputs:  # receive
            return " + ".join(outputs)
        if ingredient_inputs:  # consume / move / relabel / discard
            return " + ".join(ingredient_inputs)
        if instruments:  # use (instruments only)
            return ", ".join(instruments)
        return activity.item.item_number  # fallback

    def to_html(self) -> str:
        """Render the activity as HTML for display in the note.

        Called by RichText.to_dto(convert_special_blocks=True) when serving
        note content via GET /note/{id}/content. Renders the activity's
        inputs -> outputs (N-to-M model).
        """
        if not self.activity_id:
            return '<div class="material-activity error">Activity ID missing</div>'

        try:
            activity = Activity.get_by_id(self.activity_id)
        except Exception:
            activity = None

        if not activity:
            return '<div class="material-activity error">Activity not found</div>'

        type_label = activity.activity_type.value.capitalize()
        ingredient_inputs, outputs, instruments = self._lineage_parts(activity)
        core = self._lineage_core(activity, ingredient_inputs, outputs, instruments, "&rarr;")
        # Instruments already form the core for a bare `use`; don't repeat them.
        show_instruments = instruments and (ingredient_inputs or outputs)

        html = '<div class="material-activity">'
        html += f"<strong>{type_label}</strong>"
        html += f' &mdash; <span class="lineage">{core}</span>'
        if activity.from_location and activity.to_location:
            html += f" &mdash; {activity.from_location.name} &rarr; {activity.to_location.name}"
        elif activity.to_location:
            html += f" &mdash; &rarr; {activity.to_location.name}"
        if show_instruments:
            html += f' &mdash; <span class="instruments">using {", ".join(instruments)}</span>'
        if activity.notes:
            html += f"<br/><em>{activity.notes}</em>"
        html += "</div>"
        return html

    def to_markdown(self) -> str:
        """Convert the block to markdown for export (inputs -> outputs, §12)."""
        if not self.activity_id:
            return "[Activity: missing]"

        try:
            activity = Activity.get_by_id(self.activity_id)
        except Exception:
            activity = None

        if not activity:
            return "[Activity: not found]"

        type_label = activity.activity_type.value.capitalize()
        ingredient_inputs, outputs, instruments = self._lineage_parts(activity)
        core = self._lineage_core(activity, ingredient_inputs, outputs, instruments, "→")

        return f"**{type_label}** — {core}"
