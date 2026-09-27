"""Acceso a `usuarios`."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.usuario import Usuario


async def get(session: AsyncSession, usuario_id: uuid.UUID) -> Usuario | None:
    return await session.get(Usuario, usuario_id)


async def get_by_nombre_usuario(session: AsyncSession, nombre_usuario: str) -> Usuario | None:
    stmt = select(Usuario).where(func.lower(Usuario.nombre_usuario) == nombre_usuario.lower())
    return (await session.execute(stmt)).scalar_one_or_none()


async def add(session: AsyncSession, usuario: Usuario) -> Usuario:
    session.add(usuario)
    await session.flush()
    await session.refresh(usuario)
    return usuario
