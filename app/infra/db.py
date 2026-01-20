from __future__ import annotations

from typing import AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, async_sessionmaker, create_async_engine

from app.core.config import settings


def create_engine() -> AsyncEngine:
    return create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_recycle=settings.db_pool_recycle,
        pool_timeout=settings.db_pool_timeout,
    )


def create_session_maker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    session_maker = request.app.state.db_session_maker
    async with session_maker() as session:
        async with session.begin():
            yield session