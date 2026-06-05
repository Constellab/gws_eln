from gws_core import Model, TypedBooleanField, TypedCharField, TypedEnumField, UserDTO, UserGroup
from gws_core import User as GwsCoreUser

from gws_eln.core.eln_db_manager import ElnDbManager


class User(Model):
    email = TypedCharField()
    first_name = TypedCharField()
    last_name = TypedCharField()
    group = TypedEnumField(choices=UserGroup, default=UserGroup.USER)
    is_active = TypedBooleanField(default=True)

    photo = TypedCharField(null=True)

    def to_dto(self) -> UserDTO:
        return UserDTO(
            id=self.id,
            email=self.email,
            first_name=self.first_name,
            last_name=self.last_name,
            photo=self.photo,
        )

    @classmethod
    def get_real_users(cls) -> list["User"]:
        """Get all real users (excluding SYSUSER) that are active.

        :return: Query of real users ordered by first and last name
        :rtype: ModelSelect
        """
        return list(
            User.select()
            .where(User.group != UserGroup.SYSUSER)
            .order_by(User.first_name, User.last_name)
        )

    @classmethod
    def from_gws_core_user(cls, gws_core_user: GwsCoreUser) -> "User":
        """Create or get a User instance from a gws_core User.

        :param gws_core_user: The gws_core User object
        :type gws_core_user: GwsCoreUser
        :return: The corresponding User instance
        :rtype: User
        """
        return User(
            id=gws_core_user.id,
            email=gws_core_user.email,
            first_name=gws_core_user.first_name,
            last_name=gws_core_user.last_name,
            group=gws_core_user.group,
            is_active=gws_core_user.is_active,
            photo=gws_core_user.photo,
            created_at=gws_core_user.created_at,
            last_modified_at=gws_core_user.last_modified_at,
        )

    class Meta:
        table_name = "gws_eln_user"
        database = ElnDbManager.get_instance().db
        is_table = True
        db_manager = ElnDbManager.get_instance()
