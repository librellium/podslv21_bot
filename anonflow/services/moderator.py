import logging
from typing import Optional

from aiogram.types import ChatIdUnion
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from anonflow.database import (
    Database,
    BanRepository,
    ModeratorRepository
)


class ForbiddenError(PermissionError): ...

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

    async def add(self, actor_chat_id: ChatIdUnion, chat_id: ChatIdUnion):
        try:
            async with self._database.get_session() as session:
                if await self._can_manage_moderators(session, actor_chat_id):
                    await self._moderator_repository.add(session, chat_id)
                else:
                    raise ForbiddenError()
        except IntegrityError:
            self._logger.warning("Failed to add moderator chat_id=%s", chat_id)

    async def ban(self, actor_chat_id: ChatIdUnion, chat_id: ChatIdUnion):
        async with self._database.get_session() as session:
            if await self._can_manage_bans(session, actor_chat_id):
                await self._ban_repository.ban(session, actor_chat_id, chat_id)
            else:
                raise ForbiddenError()

    async def _get_permission(self, session: AsyncSession, actor_chat_id: ChatIdUnion, name: str) -> bool:
        moderator = await self._moderator_repository.get(session, actor_chat_id)
        return getattr(getattr(moderator, name, None), "value", False)

    async def _can_approve_posts(self, session: AsyncSession, actor_chat_id: ChatIdUnion):
        return await self._get_permission(session, actor_chat_id, "can_approve_posts")

    async def can_approve_posts(self, actor_chat_id: ChatIdUnion):
        async with self._database.get_session() as session:
            return await self._can_approve_posts(session, actor_chat_id)

    async def _can_manage_bans(self, session: AsyncSession, actor_chat_id: ChatIdUnion):
        return await self._get_permission(session, actor_chat_id, "can_manage_bans")

    async def can_manage_bans(self, actor_chat_id: ChatIdUnion):
        async with self._database.get_session() as session:
            return await self._can_manage_bans(session, actor_chat_id)

    async def _can_manage_moderators(self, session: AsyncSession, actor_chat_id: ChatIdUnion):
        return await self._get_permission(session, actor_chat_id, "can_manage_moderators")

    async def can_manage_moderators(self, actor_chat_id: ChatIdUnion):
        async with self._database.get_session() as session:
            return await self._can_manage_moderators(session, actor_chat_id)

    async def get(self, chat_id: ChatIdUnion):
        async with self._database.get_session() as session:
            return await self._moderator_repository.get(session, chat_id)

    async def get_permissions(self, chat_id: ChatIdUnion):
        async with self._database.get_session() as session:
            return await self._moderator_repository.get_permissions(session, chat_id)

    async def has(self, chat_id: ChatIdUnion):
        async with self._database.get_session() as session:
            return await self._moderator_repository.has(session, chat_id)

    async def is_banned(self, chat_id: ChatIdUnion):
        async with self._database.get_session() as session:
            return await self._ban_repository.is_banned(session, chat_id)

    async def remove(self, actor_chat_id: ChatIdUnion, chat_id: ChatIdUnion):
        try:
            async with self._database.get_session() as session:
                if await self._can_manage_moderators(session, actor_chat_id):
                    await self._moderator_repository.remove(session, chat_id)
                else:
                    raise ForbiddenError()
        except IntegrityError:
            self._logger.warning("Failed to remove moderator chat_id=%s", chat_id)

    async def unban(self, actor_chat_id: ChatIdUnion, chat_id: ChatIdUnion):
        async with self._database.get_session() as session:
            if await self._can_manage_bans(session, actor_chat_id):
                await self._ban_repository.unban(session, actor_chat_id, chat_id)
            else:
                raise ForbiddenError()

    async def update(self, actor_chat_id: ChatIdUnion, chat_id: ChatIdUnion, **fields):
        try:
            async with self._database.get_session() as session:
                if await self._can_manage_moderators(session, actor_chat_id):
                    await self._moderator_repository.update(session, chat_id, **fields)
                else:
                    raise ForbiddenError()
        except IntegrityError:
            self._logger.warning("Failed to update moderator chat_id=%s", chat_id)

    async def update_permissions(
        self,
        actor_chat_id: ChatIdUnion,
        chat_id: ChatIdUnion,
        *,
        can_approve_posts: Optional[bool] = None,
        can_manage_bans: Optional[bool] = None,
        can_manage_moderators: Optional[bool] = None
    ):
        try:
            async with self._database.get_session() as session:
                if await self._can_manage_moderators(session, actor_chat_id):
                    await self._moderator_repository.update_permissions(
                        session,
                        chat_id,
                        can_approve_posts=can_approve_posts,
                        can_manage_bans=can_manage_bans,
                        can_manage_moderators=can_manage_moderators
                    )
                else:
                    raise ForbiddenError()
        except IntegrityError:
            self._logger.warning("Failed to update moderator chat_id=%s", chat_id)
