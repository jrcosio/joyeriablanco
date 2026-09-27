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


async def list_usuarios(session: AsyncSession) -> list[Usuario]:
    resultado = await session.execute(select(Usuario).order_by(Usuario.nombre, Usuario.id))
    return list(resultado.scalars())


async def lock_active_admins(session: AsyncSession) -> list[uuid.UUID]:
    """Bloquea (FOR UPDATE) los administradores activos y devuelve sus id (research R-9)."""
    stmt = (
        select(Usuario.id)
        .where(Usuario.rol == "administrador", Usuario.activo.is_(True))
        .order_by(Usuario.id)
        .with_for_update()
    )
    return list((await session.execute(stmt)).scalars())
