"""Acceso a las facturas emitidas (solo inserción) y al listado (research R-8, R-12)."""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.tipos import Serie
from app.models.factura import Factura


async def last_fecha_in_serie(session: AsyncSession, serie: Serie, anio: int) -> date | None:
    resultado = await session.execute(
        select(func.max(Factura.fecha_expedicion)).where(
            Factura.serie == serie.value, Factura.anio == anio
        )
    )
    return resultado.scalar_one_or_none()
