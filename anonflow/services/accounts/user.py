import logging

from sqlalchemy.exc import IntegrityError

from anonflow.database import Database, UserRepository


class UserService:
    def __init__(self, database: Database, user_repository: UserRepository):
        self._logger = logging.getLogger(__name__)

        self._database = database
        self._user_repository = user_repository

    async def add(self, user_id: int):
        try:
            async with self._database.begin_session() as session:
                await self._user_repository.add(session, user_id)
        except IntegrityError:
            self._logger.warning("Failed to add user user_id=%s", user_id)

    async def get(self, user_id: int):
        async with self._database.get_session() as session:
            return await self._user_repository.get(session, user_id)

    async def has(self, user_id: int):
        async with self._database.get_session() as session:
            return await self._user_repository.has(session, user_id)

    async def remove(self, user_id: int):
        try:
            async with self._database.begin_session() as session:
                await self._user_repository.remove(session, user_id)
        except IntegrityError:
            self._logger.warning("Failed to remove user user_id=%s", user_id)

    async def update(self, user_id: int, **fields):
        try:
            async with self._database.begin_session() as session:
                await self._user_repository.update(session, user_id, **fields)
        except IntegrityError:
            self._logger.warning("Failed to update user user_id=%s", user_id)
