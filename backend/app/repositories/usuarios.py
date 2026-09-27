"""Acceso a `usuarios`."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.usuario import Usuario


async def get(
    session: AsyncSession, usuario_id: uuid.UUID, *, for_update: bool = False
) -> Usuario | None:
    """Usuario no eliminado por id; con `for_update`, bloquea la fila y relee su estado (R-21)."""
    if for_update:
        usuario = await session.get(
            Usuario, usuario_id, with_for_update=True, populate_existing=True
        )
    else:
        usuario = await session.get(Usuario, usuario_id)
    return None if usuario is None or usuario.eliminado else usuario


async def get_by_nombre_usuario(session: AsyncSession, nombre_usuario: str) -> Usuario | None:
    """Usuario no eliminado por nombre de usuario: el de un eliminado queda libre (FR-061)."""
    stmt = select(Usuario).where(
        func.lower(Usuario.nombre_usuario) == nombre_usuario.lower(),
        Usuario.eliminado_en.is_(None),
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def add(session: AsyncSession, usuario: Usuario) -> Usuario:
    session.add(usuario)
    await session.flush()
    await session.refresh(usuario)
    return usuario


async def list_usuarios(
    session: AsyncSession, *, incluir_eliminados: bool = False
) -> list[Usuario]:
    stmt = select(Usuario).order_by(Usuario.nombre, Usuario.id)
    if not incluir_eliminados:
        stmt = stmt.where(Usuario.eliminado_en.is_(None))
    return list((await session.execute(stmt)).scalars())


async def lock_active_admins(session: AsyncSession) -> list[uuid.UUID]:
    """Bloquea (FOR UPDATE) los administradores activos y devuelve sus id (research R-9)."""
    stmt = (
        select(Usuario.id)
        .where(Usuario.rol == "administrador", Usuario.activo.is_(True))
        .order_by(Usuario.id)
        .with_for_update()
    )
    return list((await session.execute(stmt)).scalars())
