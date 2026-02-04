from dataclasses import dataclass
from typing import Optional

from aiogram.types import ChatIdUnion
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from .base import BaseRepository
from anonflow.database.orm import Moderator


@dataclass
class ModeratorPermissions:
    can_approve: bool
    can_ban: bool
    can_manage_moderators: bool

class ModeratorRepository(BaseRepository):
    model = Moderator

    async def add(
        self,
        session: AsyncSession,
        chat_id: ChatIdUnion,
        *,
        can_approve_posts: bool = True,
        can_manage_bans: bool = False,
        can_manage_moderators: bool = False
    ):
        await super()._add(
            session,
            model_args={
                "chat_id": chat_id,
                "can_approve_posts": can_approve_posts,
                "can_manage_bans": can_manage_bans,
                "can_manage_moderators": can_manage_moderators
            }
        )

    async def get(self, session: AsyncSession, chat_id: ChatIdUnion) -> Optional[Moderator]:
        return await super()._get(
            session,
            filters={"chat_id": chat_id},
            options=[
                joinedload(Moderator.user)
            ]
        )

    async def get_permissions(self, session: AsyncSession, chat_id: ChatIdUnion):
        result = await self.get(session, chat_id)
        if result:
            return ModeratorPermissions(
                result.can_approve_posts.value,
                result.can_manage_bans.value,
                result.can_manage_moderators.value
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

    async def update_permissions(
        self,
        session: AsyncSession,
        chat_id: ChatIdUnion,
        *,
        can_approve_posts: Optional[bool] = None,
        can_manage_bans: Optional[bool] = None,
        can_manage_moderators: Optional[bool] = None
    ):
        to_update = {}
        for key, value in (
            ("can_approve_posts", can_approve_posts),
            ("can_manage_bans", can_manage_bans),
            ("can_manage_moderators", can_manage_moderators),
        ):
            if value is not None:
                to_update[key] = value

        await self.update(
            session,
            chat_id,
            **to_update
        )
