"""Capa de infraestructura de persistencia: SQLAlchemy 2.x asíncrono.

- Local: SQLite + aiosqlite.
- Render: PostgreSQL + asyncpg (la URL se normaliza en `Settings.async_database_url`).
"""
from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# JSON portable: JSONB en PostgreSQL, JSON (TEXT) en SQLite.
JSONType = JSON().with_variant(JSONB(), "postgresql")


class Base(DeclarativeBase):
    pass


engine = create_async_engine(
    settings.async_database_url,
    connect_args=settings.database_connect_args,
    pool_pre_ping=True,
    echo=False,
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


async def create_all_tables() -> None:
    from app.models import models  # noqa: F401  (registra los modelos en el metadata)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
