"""Acceso a `borradores_factura` y sus líneas: tablas mutables (research R-9)."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import StaleDataError

from app.core.errors import ConflictoVersion
from app.models.borrador_factura import BorradorFactura

MENSAJE_CONFLICTO = "El borrador ha cambiado desde que lo abriste."


async def get(
    session: AsyncSession, borrador_id: uuid.UUID, *, for_update: bool = False
) -> BorradorFactura | None:
    stmt = select(BorradorFactura).where(BorradorFactura.id == borrador_id)
    if for_update:
        # Solo la fila del borrador: el cliente y los usuarios unidos no se bloquean.
        stmt = stmt.with_for_update(of=BorradorFactura)
    return (await session.execute(stmt)).unique().scalar_one_or_none()


async def save(session: AsyncSession, borrador: BorradorFactura) -> BorradorFactura:
    session.add(borrador)
    try:
        await session.flush()
    except StaleDataError as exc:  # otra sesión guardó entre la lectura y la escritura
        raise ConflictoVersion(MENSAJE_CONFLICTO) from exc
    await session.refresh(borrador)
    return borrador


async def delete(session: AsyncSession, borrador: BorradorFactura) -> None:
    await session.delete(borrador)
    await session.flush()
