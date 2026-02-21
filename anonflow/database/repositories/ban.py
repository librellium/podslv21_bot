from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from anonflow.database.orm import Ban


class BanRepository:
    async def ban(self, session: AsyncSession, actor_user_id: int, user_id: int):
        ban = Ban(
            user_id=user_id,
            banned_by=actor_user_id
        )
        session.add(ban)

    async def is_banned(self, session: AsyncSession, user_id: int):
        result = await session.execute(
            select(Ban)
            .where(
                Ban.user_id == user_id,
                Ban.is_active.is_(True)
            )
            .limit(1)
        )
        return bool(result.scalar_one_or_none())

    async def unban(self, session: AsyncSession, actor_user_id: int, user_id: int):
        await session.execute(
            update(Ban)
            .where(
                Ban.user_id == user_id,
                Ban.is_active.is_(True)
            )
            .values(
                is_active=False,
                unbanned_at=func.now(),
                unbanned_by=actor_user_id
            )
        )
