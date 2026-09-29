"""Acceso a `correcciones_factura`: solo inserción (research R-8)."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.correccion_factura import CorreccionFactura


async def get_by_idempotency_key(
    session: AsyncSession, clave: uuid.UUID
) -> CorreccionFactura | None:
    resultado = await session.execute(
        select(CorreccionFactura).where(CorreccionFactura.clave_idempotencia == clave)
    )
    return resultado.scalar_one_or_none()


async def insert(session: AsyncSession, correccion: CorreccionFactura) -> CorreccionFactura:
    session.add(correccion)
    await session.flush()
    return correccion


async def list_by_factura(session: AsyncSession, factura_id: uuid.UUID) -> list[CorreccionFactura]:
    resultado = await session.execute(
        select(CorreccionFactura)
        .where(CorreccionFactura.factura_id == factura_id)
        .order_by(CorreccionFactura.creada_en, CorreccionFactura.id)
    )
    return list(resultado.scalars())


async def get_by_factura_nueva(
    session: AsyncSession, factura_nueva_id: uuid.UUID
) -> CorreccionFactura | None:
    resultado = await session.execute(
        select(CorreccionFactura).where(CorreccionFactura.factura_nueva_id == factura_nueva_id)
    )
    return resultado.scalar_one_or_none()
