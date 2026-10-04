"""Acceso a `registros_evento`: cadena lineal de solo inserción (004, research R-7).

El cerrojo de la cadena de eventos es un cerrojo consultivo transaccional propio («JBEVEN»): no
se comparte con el de los registros de facturación. Una emisión tiene el de facturación en su
transacción y el evento usa otra conexión con este, así que no hay ciclo de espera.
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Final

from sqlalchemy import TIMESTAMP, ColumnElement, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.registro_evento import RegistroEvento

CLAVE_CERROJO_EVENTOS: Final = 0x4A42_4556_454E  # «JBEVEN»


def _generado() -> ColumnElement[datetime]:
    """La fecha y hora de generación con su huso, como instante comparable."""
    return cast(RegistroEvento.fecha_hora_huso_gen, TIMESTAMP(timezone=True))


async def lock_events(session: AsyncSession) -> None:
    await session.execute(select(func.pg_advisory_xact_lock(CLAVE_CERROJO_EVENTOS)))


async def get_last(session: AsyncSession) -> RegistroEvento | None:
    resultado = await session.execute(
        select(RegistroEvento).order_by(RegistroEvento.secuencia.desc()).limit(1)
    )
    return resultado.scalar_one_or_none()


async def get_by_secuencia(session: AsyncSession, secuencia: int) -> RegistroEvento | None:
    resultado = await session.execute(
        select(RegistroEvento).where(RegistroEvento.secuencia == secuencia)
    )
    return resultado.scalar_one_or_none()


async def insert(session: AsyncSession, evento: RegistroEvento) -> RegistroEvento:
    session.add(evento)
    await session.flush()
    return evento


async def list_events(
    session: AsyncSession,
    *,
    tipo: str | None,
    desde: datetime | None,
    hasta: datetime | None,
    pagina: int,
    tamano: int,
) -> tuple[list[RegistroEvento], int]:
    """Del más reciente al más antiguo (FR-016)."""
    condiciones = []
    if tipo is not None:
        condiciones.append(RegistroEvento.tipo_evento == tipo)
    if desde is not None:
        condiciones.append(_generado() >= desde)
    if hasta is not None:
        condiciones.append(_generado() <= hasta)
    total = await session.scalar(
        select(func.count()).select_from(RegistroEvento).where(*condiciones)
    )
    resultado = await session.execute(
        select(RegistroEvento)
        .where(*condiciones)
        .order_by(RegistroEvento.secuencia.desc())
        .offset((pagina - 1) * tamano)
        .limit(tamano)
    )
    return list(resultado.scalars()), int(total or 0)


async def list_in_order(
    session: AsyncSession, *, desde: datetime | None = None, hasta: datetime | None = None
) -> list[RegistroEvento]:
    condiciones = []
    if desde is not None:
        condiciones.append(_generado() >= desde)
    if hasta is not None:
        condiciones.append(_generado() <= hasta)
    resultado = await session.execute(
        select(RegistroEvento).where(*condiciones).order_by(RegistroEvento.secuencia)
    )
    return list(resultado.scalars())


async def last_of_types(session: AsyncSession, tipos: Sequence[str]) -> RegistroEvento | None:
    resultado = await session.execute(
        select(RegistroEvento)
        .where(RegistroEvento.tipo_evento.in_(tipos))
        .order_by(RegistroEvento.secuencia.desc())
        .limit(1)
    )
    return resultado.scalar_one_or_none()


async def list_of_type_desc(session: AsyncSession, tipo: str) -> list[RegistroEvento]:
    resultado = await session.execute(
        select(RegistroEvento)
        .where(RegistroEvento.tipo_evento == tipo)
        .order_by(RegistroEvento.secuencia.desc())
    )
    return list(resultado.scalars())


async def count_by_type_after(session: AsyncSession, secuencia: int) -> dict[str, int]:
    resultado = await session.execute(
        select(RegistroEvento.tipo_evento, func.count())
        .where(RegistroEvento.secuencia > secuencia)
        .group_by(RegistroEvento.tipo_evento)
    )
    return {str(tipo): int(n) for tipo, n in resultado.all()}


async def exists_anomaly(
    session: AsyncSession, *, tipo_evento: str, tipo_anomalia: str, secuencia_afectada: int | None
) -> bool:
    """Si esa anomalía ya se registró: una comprobación no la repite (research R-9)."""
    condiciones = [
        RegistroEvento.tipo_evento == tipo_evento,
        RegistroEvento.tipo_anomalia == tipo_anomalia,
        RegistroEvento.secuencia_afectada.is_(None)
        if secuencia_afectada is None
        else RegistroEvento.secuencia_afectada == secuencia_afectada,
    ]
    return bool(
        await session.scalar(select(func.count()).select_from(RegistroEvento).where(*condiciones))
    )


async def list_anomalies(session: AsyncSession) -> list[RegistroEvento]:
    resultado = await session.execute(
        select(RegistroEvento)
        .where(RegistroEvento.tipo_evento.in_(("04", "06")))
        .order_by(RegistroEvento.secuencia)
    )
    return list(resultado.scalars())
