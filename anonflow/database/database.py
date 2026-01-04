from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from anonflow.paths import DATABASE_FILEPATH

from .base import Base
from .repositories import UserRepository


class Database:
    def __init__(self, filepath: Path = DATABASE_FILEPATH, echo: bool = False):
        self.url = f"sqlite+aiosqlite:///{filepath}"
        self._engine = create_async_engine(self.url, echo=echo, future=True) #type: ignore
        self._session_maker = sessionmaker( # type: ignore
            self._engine, expire_on_commit=False, class_=AsyncSession # type: ignore
        )

        self.users = UserRepository(self)

    async def close(self):
        await self._engine.dispose()

    def get_session(self):
        return self._session_maker()

    async def init(self):
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
