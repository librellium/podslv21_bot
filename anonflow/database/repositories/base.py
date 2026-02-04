from typing import Any, Dict, List, Type

from sqlalchemy import delete, inspect, select, update
from sqlalchemy.ext.asyncio import AsyncSession


class BaseRepository:
    model: Type[Any]

    def __init__(self):
        self._column_names = frozenset(
            c.name for c in inspect(self.model).columns
        )

    async def _add(self, session: AsyncSession, model_args: Dict[str, Any]):
        async with session.begin():
            obj = self.model(**model_args)
            session.add(obj)

    async def _get(self, session: AsyncSession, filters: Dict[str, Any], options: List[Any] = []):
        result = await session.execute(
            select(self.model)
            .options(*options)
            .filter_by(**filters)
        )
        return result.scalar_one_or_none()

    async def _has(self, session: AsyncSession, filters: Dict[str, Any]):
        result = await session.execute(
            select(1)
            .select_from(self.model)
            .filter_by(**filters)
            .limit(1)
        )
        return bool(result.scalar_one_or_none())

    async def _remove(self, session: AsyncSession, filters: Dict[str, Any]):
        async with session.begin():
            await session.execute(
                delete(self.model)
                .filter_by(**filters)
            )

    async def _update(self, session: AsyncSession, filters: Dict[str, Any], fields: Dict[str, Any]):
        if not fields:
            return

        async with session.begin():
            await session.execute(
                update(self.model)
                .filter_by(**filters)
                .values(**fields)
            )
