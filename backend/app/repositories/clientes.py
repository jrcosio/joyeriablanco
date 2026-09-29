"""Acceso a `clientes`."""

import uuid
from typing import Any

from sqlalchemy import ColumnElement, UnaryExpression, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import StaleDataError

from app.core.errors import ConflictoVersion
from app.domain.identificacion import normalize_identificacion
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


async def delete(session: AsyncSession, cliente: Cliente) -> None:
    await session.delete(cliente)
    await session.flush()


async def save(session: AsyncSession, cliente: Cliente) -> Cliente:
    await _flush(session)
    await session.refresh(cliente)
    return cliente


# --------------------------------------------------------------------------- listado (US3)


def escape_like(texto: str) -> str:
    """Escapa los comodines de LIKE (se usa con `escape="\\"`). También lo usa el de facturas."""
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _filtros(
    *, q: str | None, provincia: str | None, tipo: str | None, estado: str
) -> list[ColumnElement[bool]]:
    condiciones: list[ColumnElement[bool]] = []
    if estado == "activos":
        condiciones.append(Cliente.activo.is_(True))
    elif estado == "inactivos":
        condiciones.append(Cliente.activo.is_(False))
    if provincia:
        condiciones.append(Cliente.provincia_codigo == provincia)
    if tipo:
        condiciones.append(Cliente.tipo == tipo)
    termino = (q or "").strip()
    if termino:
        patron = func.concat("%", func.inmutable_unaccent(func.lower(escape_like(termino))), "%")
        opciones: list[ColumnElement[bool]] = [Cliente.texto_busqueda.ilike(patron, escape="\\")]
        sin_separadores = normalize_identificacion(termino)
        if sin_separadores:
            opciones.append(
                Cliente.identificacion_numero.like(f"%{escape_like(sin_separadores)}%", escape="\\")
            )
        condiciones.append(or_(*opciones))
    return condiciones


_ORDENES: dict[str, tuple[UnaryExpression[Any], ...]] = {
    "nombre_asc": (Cliente.nombre.asc(), Cliente.id.asc()),
    "nombre_desc": (Cliente.nombre.desc(), Cliente.id.desc()),
    "recientes": (Cliente.creado_en.desc(), Cliente.id.desc()),
    "antiguos": (Cliente.creado_en.asc(), Cliente.id.asc()),
}


async def list_clientes(
    session: AsyncSession,
    *,
    q: str | None,
    provincia: str | None,
    tipo: str | None,
    estado: str,
    orden: str,
    pagina: int,
    tamano: int,
) -> tuple[list[Cliente], int]:
    condiciones = _filtros(q=q, provincia=provincia, tipo=tipo, estado=estado)
    total = await session.scalar(select(func.count()).select_from(Cliente).where(*condiciones))
    stmt = (
        select(Cliente)
        .where(*condiciones)
        .order_by(*_ORDENES[orden])
        .offset((pagina - 1) * tamano)
        .limit(tamano)
    )
    elementos = list((await session.execute(stmt)).unique().scalars())
    return elementos, int(total or 0)


async def count_indicadores(session: AsyncSession, zona_horaria: str) -> tuple[int, int]:
    """(activos, creados en el año natural en curso según la hora de `zona_horaria`)."""
    inicio_ano = func.timezone(
        zona_horaria, func.date_trunc("year", func.timezone(zona_horaria, func.now()))
    )
    stmt = select(
        func.count().filter(Cliente.activo.is_(True)),
        func.count().filter(Cliente.creado_en >= inicio_ano),
    ).select_from(Cliente)
    activos, nuevos = (await session.execute(stmt)).one()
    return int(activos), int(nuevos)
