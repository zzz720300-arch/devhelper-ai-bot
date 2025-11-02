"""Database session management for AIU-FREELANCE-HUB."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator, Callable, Optional

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


_ENGINE: Optional[AsyncEngine] = None
_SESSION_FACTORY: Optional[Callable[[], AsyncSession]] = None


def _make_async_dsn(dsn: str) -> str:
    if dsn.startswith("postgresql://"):
        return dsn.replace("postgresql://", "postgresql+asyncpg://", 1)
    if dsn.startswith("postgres://"):
        return dsn.replace("postgres://", "postgresql+asyncpg://", 1)
    return dsn


def init_engine(dsn: str) -> AsyncEngine:
    """Initialise global engine and session factory."""
    global _ENGINE, _SESSION_FACTORY
    if _ENGINE is None:
        _ENGINE = create_async_engine(_make_async_dsn(dsn), future=True, echo=False)
        _SESSION_FACTORY = sessionmaker(_ENGINE, expire_on_commit=False, class_=AsyncSession)
    return _ENGINE


def get_engine() -> AsyncEngine:
    if _ENGINE is None:
        raise RuntimeError("Database engine is not initialised. Call init_engine first.")
    return _ENGINE


def get_session_factory() -> Callable[[], AsyncSession]:
    if _SESSION_FACTORY is None:
        raise RuntimeError("Session factory is not initialised. Call init_engine first.")
    return _SESSION_FACTORY


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    session_factory = get_session_factory()
    session = session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def create_all(metadata) -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)


async def drop_all(metadata) -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(metadata.drop_all)


def run_sync(coro):
    return asyncio.get_event_loop().run_until_complete(coro)
