from gws_core import RichTextBlockDataSpecial, rich_text_block_decorator

from gws_eln.activities.activity import Activity


@rich_text_block_decorator("materialActivity", human_name="Material Activity")
class RichTextBlockMaterialActivity(RichTextBlockDataSpecial):
    """Block representing an inventory activity in a note.

    Stores only the activity_id — a reference to an Activity entity
    in the database. The activity is created via a dedicated API
    endpoint (Step 6) before the block is added to the note.

    When the note content is served, to_html() loads the activity
    from the database and renders it as HTML.
    """

    activity_id: str | None = None

    def to_html(self) -> str:
        """Render the activity as HTML for display in the note.

        Called by RichText.to_dto(convert_special_blocks=True) when serving
        note content via GET /note/{id}/content.

        Loads the Activity from the database and renders its details.
        """
        if not self.activity_id:
            return '<div class="material-activity error">Activity ID missing</div>'

        try:
            activity = Activity.get_by_id(self.activity_id)
        except Exception:
            activity = None

        if not activity:
            return '<div class="material-activity error">Activity not found</div>'

        pretty_qty = activity.get_pretty_quantity() or ""
        activity_label = activity.activity_type.value.capitalize()
        batch_label = activity.batch.batch_number
        material_name = activity.batch.material.name

        html = '<div class="material-activity">'
        html += f"<strong>{activity_label}</strong>"
        html += f' &mdash; <span class="batch">{material_name} ({batch_label})</span>'
        if pretty_qty:
            html += f" &mdash; {pretty_qty}"
        if activity.from_location and activity.to_location:
            html += f" &mdash; {activity.from_location.name} &rarr; {activity.to_location.name}"
        elif activity.to_location:
            html += f" &mdash; &rarr; {activity.to_location.name}"
        if activity.notes:
            html += f"<br/><em>{activity.notes}</em>"
        html += "</div>"
        return html

    def to_markdown(self) -> str:
        """Convert the block to markdown for export."""
        if not self.activity_id:
            return "[Activity: missing]"

        from gws_eln.activities.activity import Activity

        try:
            activity = Activity.get_by_id(self.activity_id)
        except Exception:
            activity = None

        if not activity:
            return "[Activity: not found]"

        pretty_qty = activity.get_pretty_quantity() or ""
        activity_label = activity.activity_type.value.capitalize()
        batch_label = activity.batch.batch_number

        parts = [f"**{activity_label}**", batch_label]
        if pretty_qty:
            parts.append(pretty_qty)
        return " — ".join(parts)
