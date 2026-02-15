from dataclasses import dataclass
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from anonflow.database.orm import Moderator

from .base import BaseRepository


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
        user_id: int,
        *,
        can_approve_posts: bool = True,
        can_manage_bans: bool = False,
        can_manage_moderators: bool = False
    ):
        await super()._add(
            session,
            model_args={
                "user_id": user_id,
                "can_approve_posts": can_approve_posts,
                "can_manage_bans": can_manage_bans,
                "can_manage_moderators": can_manage_moderators
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

    async def get_permissions(self, session: AsyncSession, user_id: int):
        result = await self.get(session, user_id)
        if result:
            return ModeratorPermissions(
                result.can_approve_posts.value,
                result.can_manage_bans.value,
                result.can_manage_moderators.value
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

    async def update_permissions(
        self,
        session: AsyncSession,
        user_id: int,
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
            user_id,
            **to_update
        )
