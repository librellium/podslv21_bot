import logging
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from anonflow.database import BanRepository, Database, ModeratorRepository

from .exceptions import ForbiddenError


class ModeratorService:
    def __init__(
        self,
        database: Database,
        ban_repository: BanRepository,
        moderator_repository: ModeratorRepository
    ):
        self._logger = logging.getLogger(__name__)

        self._database = database
        self._ban_repository = ban_repository
        self._moderator_repository = moderator_repository

    async def add(self, actor_user_id: int, user_id: int):
        try:
            async with self._database.get_session() as session:
                if await self._can_manage_moderators(session, actor_user_id):
                    await self._moderator_repository.add(session, user_id)
                else:
                    raise ForbiddenError()
        except IntegrityError:
            self._logger.warning("Failed to add moderator user_id=%s", user_id)

    async def ban(self, actor_user_id: int, user_id: int):
        async with self._database.get_session() as session:
            if await self._can_manage_bans(session, actor_user_id):
                await self._ban_repository.ban(session, actor_user_id, user_id)
            else:
                raise ForbiddenError()

    async def _get_permission(self, session: AsyncSession, actor_user_id: int, name: str) -> bool:
        moderator = await self._moderator_repository.get(session, actor_user_id)
        return getattr(getattr(moderator, name, None), "value", False)

    async def _can_approve_posts(self, session: AsyncSession, actor_user_id: int):
        return await self._get_permission(session, actor_user_id, "can_approve_posts")

    async def can_approve_posts(self, actor_user_id: int):
        async with self._database.get_session() as session:
            return await self._can_approve_posts(session, actor_user_id)

    async def _can_manage_bans(self, session: AsyncSession, actor_user_id: int):
        return await self._get_permission(session, actor_user_id, "can_manage_bans")

    async def can_manage_bans(self, actor_user_id: int):
        async with self._database.get_session() as session:
            return await self._can_manage_bans(session, actor_user_id)

    async def _can_manage_moderators(self, session: AsyncSession, actor_user_id: int):
        return await self._get_permission(session, actor_user_id, "can_manage_moderators")

    async def can_manage_moderators(self, actor_user_id: int):
        async with self._database.get_session() as session:
            return await self._can_manage_moderators(session, actor_user_id)

    async def get(self, user_id: int):
        async with self._database.get_session() as session:
            return await self._moderator_repository.get(session, user_id)

    async def get_permissions(self, user_id: int):
        async with self._database.get_session() as session:
            return await self._moderator_repository.get_permissions(session, user_id)

    async def has(self, user_id: int):
        async with self._database.get_session() as session:
            return await self._moderator_repository.has(session, user_id)

    async def is_banned(self, user_id: int):
        async with self._database.get_session() as session:
            return await self._ban_repository.is_banned(session, user_id)

    async def remove(self, actor_user_id: int, user_id: int):
        try:
            async with self._database.get_session() as session:
                if await self._can_manage_moderators(session, actor_user_id):
                    await self._moderator_repository.remove(session, user_id)
                else:
                    raise ForbiddenError()
        except IntegrityError:
            self._logger.warning("Failed to remove moderator user_id=%s", user_id)

    async def unban(self, actor_user_id: int, user_id: int):
        async with self._database.get_session() as session:
            if await self._can_manage_bans(session, actor_user_id):
                await self._ban_repository.unban(session, actor_user_id, user_id)
            else:
                raise ForbiddenError()

    async def update(self, actor_user_id: int, user_id: int, **fields):
        try:
            async with self._database.get_session() as session:
                if await self._can_manage_moderators(session, actor_user_id):
                    await self._moderator_repository.update(session, user_id, **fields)
                else:
                    raise ForbiddenError()
        except IntegrityError:
            self._logger.warning("Failed to update moderator user_id=%s", user_id)

    async def update_permissions(
        self,
        actor_user_id: int,
        user_id: int,
        *,
        can_approve_posts: Optional[bool] = None,
        can_manage_bans: Optional[bool] = None,
        can_manage_moderators: Optional[bool] = None
    ):
        try:
            async with self._database.get_session() as session:
                if await self._can_manage_moderators(session, actor_user_id):
                    await self._moderator_repository.update_permissions(
                        session,
                        user_id,
                        can_approve_posts=can_approve_posts,
                        can_manage_bans=can_manage_bans,
                        can_manage_moderators=can_manage_moderators
                    )
                else:
                    raise ForbiddenError()
        except IntegrityError:
            self._logger.warning("Failed to update moderator user_id=%s", user_id)
