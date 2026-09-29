"""Contadores de numeración por serie y año (research R-7; constitución, «Numeración»).

Bloqueo explícito sobre la tabla de contadores: `SELECT … FOR UPDATE` de la fila (serie, año) y
avance dentro de la MISMA transacción que la factura y su registro. Si algo falla, el rollback
deshace también el avance: no quedan huecos. `MAX(numero)+1` está prohibido.
"""

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.tipos import Serie
from app.models.contador_factura import ContadorFactura


async def _lock(session: AsyncSession, serie: Serie, anio: int) -> ContadorFactura:
    await session.execute(
        pg_insert(ContadorFactura)
        .values(serie=serie.value, anio=anio, ultimo_numero=0)
        .on_conflict_do_nothing(index_elements=["serie", "anio"])
    )
    resultado = await session.execute(
        select(ContadorFactura)
        .where(ContadorFactura.serie == serie.value, ContadorFactura.anio == anio)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    return resultado.scalar_one()


async def assign_numero(session: AsyncSession, serie: Serie, anio: int) -> int:
    contador = await _lock(session, serie, anio)
    contador.ultimo_numero += 1
    await session.flush()
    return contador.ultimo_numero


async def last_used(session: AsyncSession, serie: Serie, anio: int) -> int:
    resultado = await session.execute(
        select(ContadorFactura.ultimo_numero).where(
            ContadorFactura.serie == serie.value, ContadorFactura.anio == anio
        )
    )
    return resultado.scalar_one_or_none() or 0


async def lock_last_used(session: AsyncSession, serie: Serie, anio: int) -> int:
    return (await _lock(session, serie, anio)).ultimo_numero


async def raise_next(session: AsyncSession, serie: Serie, anio: int, proximo: int) -> None:
    """Deja el contador para que la siguiente asignación sea `proximo` (solo al alza)."""
    contador = await _lock(session, serie, anio)
    contador.ultimo_numero = max(contador.ultimo_numero, proximo - 1)
    await session.flush()
