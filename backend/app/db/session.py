"""Async SQLAlchemy engine va sessiya fabrikasi (asyncpg drayveri)."""

from collections.abc import AsyncIterator
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import Settings


def create_engine(settings: Settings) -> AsyncEngine:
    connect_args: dict = {"server_settings": {"application_name": "ombor-ai-api"}}
    if settings.db_use_pgbouncer:
        # Supabase transaction pooler: prepared statement keshini o'chirish shart,
        # aks holda "prepared statement already exists" xatosi chiqadi.
        connect_args |= {
            "statement_cache_size": 0,
            "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__",
        }
        return create_async_engine(
            settings.database_url, echo=settings.db_echo, poolclass=NullPool, connect_args=connect_args
        )

    return create_async_engine(
        settings.database_url,
        echo=settings.db_echo,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_pre_ping=True,
        connect_args=connect_args,
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


async def session_scope(factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
    """Bitta so'rov = bitta tranzaksiya (Unit of Work). Xato bo'lsa — rollback."""
    async with factory() as session, session.begin():
        yield session
