import logging

from aiogram.types import ChatIdUnion
from sqlalchemy import exists
from sqlalchemy.future import select

from anonflow.database.orm import User


class UserRepository:
    def __init__(self, db):
        self._logger = logging.getLogger(__name__)

        self._database = db

    async def add(self, chat_id: ChatIdUnion):
        async with self._database.get_session() as session: # type: ignore
            user = User(chat_id=chat_id)
            session.add(user)
            await session.commit()

    async def block(self, chat_id: ChatIdUnion):
        async with self._database.get_session() as session: # type: ignore
            user = await self.get(chat_id)
            if user:
                user.is_blocked = True
                await session.commit()

    async def get(self, chat_id: ChatIdUnion):
        if await self.has(chat_id):
            self._logger.warning("User chat_id=%s already exists.", chat_id)
            return

        async with self._database.get_session() as session: # type: ignore
            result = await session.execute(select(User).where(User.chat_id == chat_id))
            return result.scalar_one_or_none()

    async def has(self, chat_id: ChatIdUnion):
        async with self._database.get_session() as session:
            result = await session.execute(
                select(exists().where(User.chat_id == chat_id))
            )
            return result.scalar()

    async def unblock(self, chat_id: ChatIdUnion):
        async with self._database.get_session() as session: # type: ignore
            user = await self.get(chat_id)
            if user:
                user.is_blocked = False
                await session.commit()
