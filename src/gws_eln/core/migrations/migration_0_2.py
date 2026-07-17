"""Database migrations for the gws_eln brick.

gws_eln had no migrations, so any column added to a model never reached an
already-existing app database: on brick load ``create_tables`` creates missing
tables but never alters existing ones. These migrations bring such databases up
to date. They run against the gws_eln database (``ElnDbManager``) and are
discovered automatically (gws_core imports every module of a brick on load).
"""

from gws_core import BrickMigration, NullableTextField, SqlMigrator, Version, brick_migration

from gws_eln.activities.activity_output import ActivityOutput
from gws_eln.core.eln_db_manager import ElnDbManager
from gws_eln.items.item import Item
from gws_eln.items.item_sheet import ItemSheet


@brick_migration(
    "0.2.6",
    short_description="Add discard_reason to items and item sheets, and override_reason to activity outputs",
    db_manager=ElnDbManager.get_instance(),
)
class Migration026(BrickMigration):
    """Add the discard/override reason columns introduced by the discard feature.

    All three are nullable free-text columns, so the change is additive and needs
    no backfill; ``add_column_if_not_exists`` also makes it safe to re-run.
    """

    @classmethod
    def migrate(cls, sql_migrator: SqlMigrator, from_version: Version, to_version: Version) -> None:
        sql_migrator.add_column_if_not_exists(Item, NullableTextField(), "discard_reason")
        sql_migrator.add_column_if_not_exists(ItemSheet, NullableTextField(), "discard_reason")
        sql_migrator.add_column_if_not_exists(
            ActivityOutput, NullableTextField(), "override_reason"
        )
        sql_migrator.migrate()
