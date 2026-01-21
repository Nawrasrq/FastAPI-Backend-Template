"""
Async database session management using SQLAlchemy 2.0.

This module initializes the async SQLAlchemy engine and session factory
for use throughout the application with FastAPI's dependency injection.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# Create async engine
# For SQLite, we need connect_args for thread safety
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides an async database session.
    Yields a session and ensures cleanup after request completes.

    Yields
    ------
    AsyncSession
        Async database session for the request
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """
    Create all database tables.

    Should be called during application startup or migrations.
    """
    from app.models.base import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_db() -> None:
    """
    Drop all database tables.

    Use with caution - this will delete all data.
    """
    from app.models.base import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
