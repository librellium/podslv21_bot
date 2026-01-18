import asyncio
import logging

from aiogram.types import ChatIdUnion
from cachetools import TTLCache
from sqlalchemy import exists, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select

from anonflow.database.database import Database
from anonflow.database.orm import User


class UserRepository:
    def __init__(self, db: Database, cache_size: int, cache_ttl: int):
        self._logger = logging.getLogger(__name__)

        self._database = db
        self._cache = TTLCache(maxsize=cache_size, ttl=cache_ttl)
        self._cache_lock = asyncio.Lock()

    async def add(self, chat_id: ChatIdUnion):
        async with self._database.get_session() as session:
            try:
                user = User(chat_id=chat_id)
                session.add(user)
                await session.commit()

                async with self._cache_lock:
                    self._cache[chat_id] = user
            except IntegrityError:
                await session.rollback()
                self._logger.warning("User chat_id=%s already exists.", chat_id)

    async def block(self, chat_id: ChatIdUnion):
        await self.update(chat_id, is_blocked=True)

    async def get(self, chat_id: ChatIdUnion):
        async with self._cache_lock:
            user = self._cache.get(chat_id)
            if user: return user

        async with self._database.get_session() as session:
            result = await session.execute(
                select(User).where(User.chat_id == chat_id)
            )
            return result.scalar_one_or_none()

    async def has(self, chat_id: ChatIdUnion):
        async with self._cache_lock:
            if self._cache.get(chat_id):
                return True

        async with self._database.get_session() as session:
            result = await session.execute(
                select(exists().where(User.chat_id == chat_id))
            )
            return result.scalar()

    async def unblock(self, chat_id: ChatIdUnion):
        await self.update(chat_id, is_blocked=False)

    async def update(self, chat_id: ChatIdUnion, **fields):
        async with self._database.get_session() as session:
            try:
                await session.execute(
                    update(User)
                    .where(User.chat_id == chat_id)
                    .values(**fields)
                    .execution_options(synchronize_session="fetch")
                )
                await session.commit()

                user = await session.get(User, chat_id)
                async with self._cache_lock:
                    if user:
                        self._cache[chat_id] = user
            except IntegrityError:
                await session.rollback()
                self._logger.warning("Failed to update user chat_id=%s", chat_id)
