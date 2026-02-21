from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from anonflow.database.orm import Moderator

from .base import BaseRepository


class ModeratorRepository(BaseRepository):
    model = Moderator

    async def add(
        self,
        session: AsyncSession,
        user_id: int,
        **fields
    ):
        await super()._add(
            session,
            model_args={
                "user_id": user_id,
                **fields
            }
        )

    async def get(self, session: AsyncSession, user_id: int) -> Optional[Moderator]:
        return await super()._get(
            session,
            filters={"user_id": user_id},
            options=[
                joinedload(Moderator.user)
            ]
        )

    async def has(self, session: AsyncSession, user_id: int):
        return await super()._has(
            session,
            filters={"user_id": user_id}
        )

    async def remove(self, session: AsyncSession, user_id: int):
        await super()._remove(
            session,
            filters={"user_id": user_id}
        )

    async def update(self, session: AsyncSession, user_id: int, **fields):
        await super()._update(
            session,
            filters={"user_id": user_id},
            fields=fields
        )
