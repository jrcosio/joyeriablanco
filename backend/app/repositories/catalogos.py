"""Acceso al catálogo de provincias."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.provincia import Provincia


async def list_provincias(session: AsyncSession) -> list[Provincia]:
    resultado = await session.execute(select(Provincia).order_by(Provincia.nombre_visible))
    return list(resultado.scalars())


async def get_provincia(session: AsyncSession, codigo: str) -> Provincia | None:
    return await session.get(Provincia, codigo)
