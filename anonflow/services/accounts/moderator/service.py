import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from anonflow.constants import SYSTEM_USER_ID
from anonflow.database import BanRepository, Database, ModeratorRepository

from .exceptions import ModeratorPermissionError, SelfActionError
from .permissions import ModeratorPermission, ModeratorPermissions


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

    @staticmethod
    def _assert_not_self(actor_user_id: int, user_id: int):
        if actor_user_id == user_id:
            raise SelfActionError(
                f"Moderator user_id={actor_user_id} cannot perform this action on themselves (target user_id={user_id})."
            )

    async def add(self, actor_user_id: int, user_id: int):
        try:
            async with self._database.begin_session() as session:
                if await self._can(session, actor_user_id, ModeratorPermission.MANAGE_MODERATORS):
                    self._assert_not_self(actor_user_id, user_id)
                    await self._moderator_repository.add(session, user_id)
                else:
                    raise ModeratorPermissionError(
                        f"Moderator user_id={actor_user_id} does not have permission to perform 'add'."
                    )
        except IntegrityError:
            self._logger.warning("Failed to add moderator user_id=%s", user_id)

    async def ban(self, actor_user_id: int, user_id: int):
        async with self._database.begin_session() as session:
            if await self._can(session, actor_user_id, ModeratorPermission.MANAGE_BANS):
                self._assert_not_self(actor_user_id, user_id)
                await self._ban_repository.ban(session, actor_user_id, user_id)
            else:
                raise ModeratorPermissionError(
                    f"Moderator user_id={actor_user_id} does not have permission to perform 'ban'."
                )

    async def _can(self, session: AsyncSession, actor_user_id: int, permission: ModeratorPermission) -> bool:
        moderator = await self._moderator_repository.get(session, actor_user_id)
        if moderator:
            if moderator.is_root.value:
                return True
            return getattr(getattr(moderator, permission, None), "value", False)

        return False

    async def can(self, actor_user_id: int, permission: ModeratorPermission):
        async with self._database.get_session() as session:
            return self._can(session, actor_user_id, permission)

    async def get(self, user_id: int):
        async with self._database.get_session() as session:
            return await self._moderator_repository.get(session, user_id)

    async def get_permissions(self, user_id: int):
        async with self._database.get_session() as session:
            result = await self._moderator_repository.get(session, user_id)
            if not result:
                return ModeratorPermissions()

            return ModeratorPermissions(
                **{
                    key: value
                    for key, value in result.__dict__.items()
                    if key.startswith("can_")
                }
            )

    async def has(self, user_id: int):
        async with self._database.get_session() as session:
            return await self._moderator_repository.has(session, user_id)

    async def init(self):
        async with self._database.begin_session() as session:
            if not await self._moderator_repository.has(session, SYSTEM_USER_ID):
                await self._moderator_repository.add(session, SYSTEM_USER_ID, is_root=True)

    async def is_banned(self, user_id: int):
        async with self._database.get_session() as session:
            return await self._ban_repository.is_banned(session, user_id)

    async def remove(self, actor_user_id: int, user_id: int):
        try:
            async with self._database.begin_session() as session:
                if await self._can(session, actor_user_id, ModeratorPermission.MANAGE_MODERATORS):
                    self._assert_not_self(actor_user_id, user_id)
                    await self._moderator_repository.remove(session, user_id)
                else:
                    raise ModeratorPermissionError(
                        f"Moderator user_id={actor_user_id} does not have permission to perform 'remove'."
                    )
        except IntegrityError:
            self._logger.warning("Failed to remove moderator user_id=%s", user_id)

    async def unban(self, actor_user_id: int, user_id: int):
        async with self._database.begin_session() as session:
            if await self._can(session, actor_user_id, ModeratorPermission.MANAGE_BANS):
                self._assert_not_self(actor_user_id, user_id)
                await self._ban_repository.unban(session, actor_user_id, user_id)
            else:
                raise ModeratorPermissionError(
                    f"Moderator user_id={actor_user_id} does not have permission to perform 'unban'."
                )

    async def update(self, actor_user_id: int, user_id: int, **fields):
        try:
            async with self._database.begin_session() as session:
                if await self._can(session, actor_user_id, ModeratorPermission.MANAGE_MODERATORS):
                    self._assert_not_self(actor_user_id, user_id)
                    await self._moderator_repository.update(session, user_id, **fields)
                else:
                    raise ModeratorPermissionError(
                        f"Moderator user_id={actor_user_id} does not have permission to perform 'update'."
                    )
        except IntegrityError:
            self._logger.warning("Failed to update moderator user_id=%s", user_id)

    async def update_permissions(
        self,
        actor_user_id: int,
        user_id: int,
        permissions: ModeratorPermissions
    ):
        try:
            async with self._database.begin_session() as session:
                if await self._can(session, actor_user_id, ModeratorPermission.MANAGE_MODERATORS):
                    self._assert_not_self(actor_user_id, user_id)
                    await self._moderator_repository.update(
                        session,
                        user_id,
                        **permissions.to_dict()
                    )
                else:
                    raise ModeratorPermissionError(
                        f"Moderator user_id={actor_user_id} does not have permission to perform 'update_permissions'."
                    )
        except IntegrityError:
            self._logger.warning("Failed to update moderator user_id=%s", user_id)
