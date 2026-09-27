"""Acceso a PostgreSQL con SQLAlchemy 2 asíncrono (psycopg 3) como rol `jb_app`."""

from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Any

from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings


def build_engine(url: URL, **opciones: Any) -> AsyncEngine:
    """Motor asíncrono con las opciones comunes (las IP de tipo inet se leen como texto)."""
    return create_async_engine(url, native_inet_types=False, **opciones)


@lru_cache
def get_engine() -> AsyncEngine:
    return build_engine(get_settings().url_app, pool_pre_ping=True, pool_size=5)


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    """Una transacción por petición: se confirma al terminar o se revierte ante un error.

    Los servicios que deben persistir algo aunque luego respondan con error (p. ej. un acceso
    fallido que incrementa el contador y se audita) confirman explícitamente antes de lanzar.
    """
    async with get_sessionmaker()() as session:
        try:
            yield session
            await session.commit()
        except BaseException:
            await session.rollback()
            raise
