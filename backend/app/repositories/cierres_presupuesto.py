"""Acceso a `cierres_presupuesto`: solo inserción, como mucho uno por presupuesto (005, R-6)."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cierre_presupuesto import CierrePresupuesto


async def insert(session: AsyncSession, cierre: CierrePresupuesto) -> CierrePresupuesto:
    session.add(cierre)
    await session.flush()
    return cierre


async def get_by_presupuesto(
    session: AsyncSession, presupuesto_id: uuid.UUID
) -> CierrePresupuesto | None:
    resultado = await session.execute(
        select(CierrePresupuesto).where(CierrePresupuesto.presupuesto_id == presupuesto_id)
    )
    return resultado.scalar_one_or_none()


async def get_by_presupuesto_nuevo(
    session: AsyncSession, presupuesto_id: uuid.UUID
) -> CierrePresupuesto | None:
    """Cierre de sustitución que creó este presupuesto («Sustituye a…»)."""
    resultado = await session.execute(
        select(CierrePresupuesto).where(CierrePresupuesto.presupuesto_nuevo_id == presupuesto_id)
    )
    return resultado.scalar_one_or_none()


async def get_by_factura(session: AsyncSession, factura_id: uuid.UUID) -> CierrePresupuesto | None:
    """Cierre de conversión de la factura («Procede del presupuesto…», FR-022)."""
    resultado = await session.execute(
        select(CierrePresupuesto).where(CierrePresupuesto.factura_id == factura_id)
    )
    return resultado.scalar_one_or_none()


async def get_by_idempotency_key(
    session: AsyncSession, clave: uuid.UUID
) -> CierrePresupuesto | None:
    resultado = await session.execute(
        select(CierrePresupuesto).where(CierrePresupuesto.clave_idempotencia == clave)
    )
    return resultado.scalar_one_or_none()
