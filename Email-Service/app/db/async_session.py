from typing import AsyncGenerator, Annotated

from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.db.base import Base
from app.core.config import settings


async_engine = create_async_engine(
    settings.SQLITE_DATABASE_URL, echo=False, future=True
)

async_session_maker = async_sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_models() -> None:
    async with async_engine.begin() as conn:
        # uncomment below line to drop all tables before creating them
        # await conn.run_sync(Base.metadata.drop_all)

        # enable WAL mode for SQLite to allow concurrent reads/writes
        await conn.execute(text("PRAGMA journal_mode=WAL;"))
        await conn.run_sync(Base.metadata.create_all)


AsyncSessionDep = Annotated[AsyncSession, Depends(get_async_session)]
