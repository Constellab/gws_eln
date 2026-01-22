

from typing import Optional

from gws_core import LazyAbstractDbManager
from peewee import DatabaseProxy


class ElnDbManager(LazyAbstractDbManager):
    """
    DbManager class for gws_eln.

    Provides backend features for managing databases.
    """

    db = DatabaseProxy()

    _instance: Optional['ElnDbManager'] = None

    @classmethod
    def get_instance(cls) -> 'ElnDbManager':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_name(self) -> str:
        return 'db'

    def get_brick_name(self) -> str:
        return 'gws_eln'
