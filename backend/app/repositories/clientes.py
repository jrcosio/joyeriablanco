"""Acceso a `clientes`."""

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import StaleDataError

from app.core.errors import ConflictoVersion
from app.models.cliente import Cliente

RESTRICCION_IDENTIFICACION = "uq_clientes_identificacion"


class IdentificacionDuplicada(Exception):
    """Carrera en el alta o la edición: otro cliente guardó la misma identificación."""


async def get(session: AsyncSession, cliente_id: uuid.UUID) -> Cliente | None:
    return await session.get(Cliente, cliente_id)


async def get_by_identificacion(
    session: AsyncSession, *, pais: str, tipo: str, numero: str
) -> Cliente | None:
    stmt = select(Cliente).where(
        Cliente.identificacion_pais == pais,
        Cliente.identificacion_tipo == tipo,
        Cliente.identificacion_numero == numero,
    )
    return (await session.execute(stmt)).unique().scalar_one_or_none()


async def _flush(session: AsyncSession) -> None:
    try:
        async with session.begin_nested():
            await session.flush()
    except StaleDataError as exc:
        raise ConflictoVersion from exc
    except IntegrityError as exc:
        if RESTRICCION_IDENTIFICACION in str(exc.orig):
            raise IdentificacionDuplicada from exc
        raise


async def add(session: AsyncSession, cliente: Cliente) -> Cliente:
    session.add(cliente)
    await _flush(session)
    await session.refresh(cliente)
    return cliente


async def save(session: AsyncSession, cliente: Cliente) -> Cliente:
    await _flush(session)
    await session.refresh(cliente)
    return cliente
