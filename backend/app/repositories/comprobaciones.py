"""Acceso a `comprobaciones_integridad`: solo inserción (004, data-model; research R-9, R-11)."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comprobacion_integridad import ComprobacionIntegridad
from app.models.registro_evento import RegistroEvento


async def insert(
    session: AsyncSession, comprobacion: ComprobacionIntegridad
) -> ComprobacionIntegridad:
    session.add(comprobacion)
    await session.flush()
    return comprobacion


async def list_with_launch(session: AsyncSession) -> list[tuple[ComprobacionIntegridad, int]]:
    """Cada comprobación con la secuencia de su evento de lanzamiento (el 03), en orden."""
    resultado = await session.execute(
        select(ComprobacionIntegridad, RegistroEvento.secuencia)
        .join(RegistroEvento, RegistroEvento.id == ComprobacionIntegridad.evento_lanzamiento_id)
        .order_by(RegistroEvento.secuencia)
    )
    return [(c, int(s)) for c, s in resultado.all()]
