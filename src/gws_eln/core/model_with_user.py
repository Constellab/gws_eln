from gws_core import CurrentUserService, Model, TypedForeignKeyField

from gws_eln.user.user import User


class ModelWithUser(Model):
    """
    Model class with created_by and last_modified_by columns.

    Uses ForeignKey relationships to the local User entity in the same database.
    """

    # Use ForeignKey to reference the local User entity
    created_by = TypedForeignKeyField(User, null=False, backref="+")
    last_modified_by = TypedForeignKeyField(User, null=False, backref="+")

    def _before_insert(self) -> None:
        super()._before_insert()
        current_user = CurrentUserService.get_and_check_current_user()
        self.created_by = current_user
        self.last_modified_by = current_user

    def _before_update(self) -> None:
        super()._before_update()
        current_user = CurrentUserService.get_and_check_current_user()
        self.last_modified_by = current_user
