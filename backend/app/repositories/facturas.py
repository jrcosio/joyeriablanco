"""Acceso a las facturas emitidas (solo inserción) y al listado (research R-8, R-12).

El estado de una factura no es una columna: lo calcula la función SQL `estado_factura()`, única
implementación del estado derivado (migración 0005).
"""

import uuid
from collections.abc import Sequence
from datetime import date

from sqlalchemy import exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.tipos import EstadoFactura, Serie
from app.models.borrador_factura import BorradorFactura
from app.models.factura import DesgloseFactura, Factura, LineaFactura


async def last_fecha_in_serie(session: AsyncSession, serie: Serie, anio: int) -> date | None:
    resultado = await session.execute(
        select(func.max(Factura.fecha_expedicion)).where(
            Factura.serie == serie.value, Factura.anio == anio
        )
    )
    return resultado.scalar_one_or_none()


async def insert_emitida(
    session: AsyncSession,
    factura: Factura,
    lineas: Sequence[LineaFactura],
    desgloses: Sequence[DesgloseFactura],
) -> Factura:
    session.add(factura)
    await session.flush()
    for linea in lineas:
        linea.factura_id = factura.id
    for desglose in desgloses:
        desglose.factura_id = factura.id
    session.add_all([*lineas, *desgloses])
    await session.flush()
    await session.refresh(factura, ["lineas", "desgloses"])
    return factura


async def get(session: AsyncSession, factura_id: uuid.UUID) -> Factura | None:
    return await session.get(Factura, factura_id)


async def get_by_idempotency_key(session: AsyncSession, clave: uuid.UUID) -> Factura | None:
    resultado = await session.execute(select(Factura).where(Factura.clave_idempotencia == clave))
    return resultado.scalar_one_or_none()


async def estado(session: AsyncSession, factura_id: uuid.UUID) -> EstadoFactura:
    valor: str = (await session.execute(select(func.estado_factura(factura_id)))).scalar_one()
    return EstadoFactura(valor)


async def has_documentos(session: AsyncSession, cliente_id: uuid.UUID) -> bool:
    """¿Tiene el cliente alguna factura o borrador? (FR-042)."""
    consulta = select(
        or_(
            exists().where(Factura.cliente_id == cliente_id),
            exists().where(BorradorFactura.cliente_id == cliente_id),
        )
    )
    return bool((await session.execute(consulta)).scalar())
