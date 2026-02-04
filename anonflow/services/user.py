import logging

from aiogram.types import ChatIdUnion
from sqlalchemy.exc import IntegrityError

from anonflow.database import Database, UserRepository


class UserService:
    def __init__(self, database: Database, user_repository: UserRepository):
        self._logger = logging.getLogger(__name__)

        self._database = database
        self._user_repository = user_repository

    async def add(self, chat_id: ChatIdUnion):
        try:
            async with self._database.get_session() as session:
                await self._user_repository.add(session, chat_id)
        except IntegrityError:
            self._logger.warning("Failed to add user chat_id=%s", chat_id)

    async def get(self, chat_id: ChatIdUnion):
        async with self._database.get_session() as session:
            return await self._user_repository.get(session, chat_id)

    async def has(self, chat_id: ChatIdUnion):
        async with self._database.get_session() as session:
            return await self._user_repository.has(session, chat_id)

    async def remove(self, chat_id: ChatIdUnion):
        try:
            async with self._database.get_session() as session:
                await self._user_repository.remove(session, chat_id)
        except IntegrityError:
            self._logger.warning("Failed to remove user chat_id=%s", chat_id)

    async def update(self, chat_id: ChatIdUnion, **fields):
        try:
            async with self._database.get_session() as session:
                await self._user_repository.update(session, chat_id, **fields)
        except IntegrityError:
            self._logger.warning("Failed to update user chat_id=%s", chat_id)
