from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from .base import Base


class Database:
    def __init__(self, url: URL, echo: bool = False):
        self.url = url

        self._engine = create_async_engine(self.url, echo=echo)
        self._session_maker = sessionmaker(
            self._engine, expire_on_commit=False, class_=AsyncSession # type: ignore
        )

    @asynccontextmanager
    async def begin_session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self._session_maker() as session: # type: ignore
            async with session.begin():
                yield session

    async def close(self):
        await self._engine.dispose()

    def get_session(self) -> AsyncSession:
        return self._session_maker() # type: ignore

    async def init(self):
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
