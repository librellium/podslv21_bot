from aiogram.types import ChatIdUnion
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from .base import BaseRepository
from anonflow.database.orm import User


class UserRepository(BaseRepository):
    model = User

    async def add(self, session: AsyncSession, chat_id: ChatIdUnion):
        await super()._add(
            session,
            model_args={"chat_id": chat_id}
        )

    async def get(self, session: AsyncSession, chat_id: ChatIdUnion):
        return await super()._get(
            session,
            filters={"chat_id": chat_id},
            options=[
                selectinload(User.bans),
                joinedload(User.moderator)
            ]
        )

    async def has(self, session: AsyncSession, chat_id: ChatIdUnion):
        return await super()._has(
            session,
            filters={"chat_id": chat_id}
        )

    async def remove(self, session: AsyncSession, chat_id: ChatIdUnion):
        await super()._remove(
            session,
            filters={"chat_id": chat_id}
        )

    async def update(self, session: AsyncSession, chat_id: ChatIdUnion, **fields):
        await super()._update(
            session,
            filters={"chat_id": chat_id}, fields=fields
        )
