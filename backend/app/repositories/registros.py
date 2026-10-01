"""Acceso a `registros_facturacion`: cadena lineal de solo inserción (research R-6).

El cerrojo de la cadena es un cerrojo consultivo transaccional: serializa TODAS las operaciones
que generan registros (emitir, anular y modificar), porque la cadena es única por obligado
(F-10, art. 7.c). Se libera al terminar la transacción. Orden de cerrojos: primero la cadena y
después el contador (R-7), para descartar interbloqueos.
"""

import uuid
from typing import Final

from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.registro_facturacion import RegistroFacturacion

CLAVE_CERROJO_CADENA: Final = 0x4A42_4641_4354  # «JBFACT»: fija para toda la aplicación


async def lock_chain(session: AsyncSession) -> None:
    await session.execute(select(func.pg_advisory_xact_lock(CLAVE_CERROJO_CADENA)))


async def get_last(session: AsyncSession) -> RegistroFacturacion | None:
    resultado = await session.execute(
        select(RegistroFacturacion).order_by(RegistroFacturacion.secuencia.desc()).limit(1)
    )
    return resultado.scalar_one_or_none()


async def insert(session: AsyncSession, registro: RegistroFacturacion) -> RegistroFacturacion:
    session.add(registro)
    await session.flush()
    return registro


async def exists_any(session: AsyncSession) -> bool:
    return bool((await session.execute(select(exists().select_from(RegistroFacturacion)))).scalar())


async def list_in_order(session: AsyncSession) -> list[RegistroFacturacion]:
    resultado = await session.execute(
        select(RegistroFacturacion).order_by(RegistroFacturacion.secuencia)
    )
    return list(resultado.scalars())


async def list_by_factura(
    session: AsyncSession, factura_id: uuid.UUID
) -> list[RegistroFacturacion]:
    resultado = await session.execute(
        select(RegistroFacturacion)
        .where(RegistroFacturacion.factura_id == factura_id)
        .order_by(RegistroFacturacion.secuencia)
    )
    return list(resultado.scalars())
