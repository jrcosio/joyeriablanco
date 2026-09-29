"""Acceso a las facturas emitidas (solo inserción) y al listado (research R-8, R-12).

El estado de una factura no es una columna: lo calcula la función SQL `estado_factura()`, única
implementación del estado derivado (migración 0005).
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Date,
    Integer,
    Numeric,
    Text,
    UnaryExpression,
    Uuid,
    column,
    exists,
    extract,
    func,
    or_,
    select,
    table,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.domain.identificacion import normalize_identificacion
from app.domain.tipos import EstadoFactura
from app.models.borrador_factura import BorradorFactura
from app.models.factura import DesgloseFactura, Factura, LineaFactura
from app.repositories.clientes import escape_like


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


# --------------------------------------------------------------------------- listado (US3)

# Vista de solo lectura de la migración 0005 (research R-12). Se declara con `table()` para no
# registrarla en los metadatos del ORM.
v_listado = table(
    "v_listado_facturas",
    column("tipo_documento", Text),
    column("id", Uuid),
    column("num_serie", Text),
    column("numero", Integer),
    column("fecha", Date),
    column("cliente_nombre", Text),
    column("identificacion", Text),
    column("base", Numeric(12, 2)),
    column("cuota", Numeric(12, 2)),
    column("total", Numeric(12, 2)),
    column("estado", Text),
    column("texto_busqueda", Text),
)


@dataclass(frozen=True, slots=True)
class FilaListado:
    tipo_documento: str
    id: uuid.UUID
    num_serie: str | None
    fecha: date
    cliente_nombre: str | None
    identificacion: str | None
    base: Decimal
    cuota: Decimal
    total: Decimal
    estado: EstadoFactura


def _filtros(*, q: str | None, anio: int | None, mes: int | None) -> list[ColumnElement[bool]]:
    """FR-034 y FR-035. `anio=None` es «todos los años». La fecha de un borrador es la propuesta."""
    v = v_listado.c
    condiciones: list[ColumnElement[bool]] = []
    if anio is not None:
        if mes is not None:
            inicio = date(anio, mes, 1)
            fin = date(anio + 1, 1, 1) if mes == 12 else date(anio, mes + 1, 1)
        else:
            inicio, fin = date(anio, 1, 1), date(anio + 1, 1, 1)
        condiciones += [v.fecha >= inicio, v.fecha < fin]
    elif mes is not None:
        condiciones.append(extract("month", v.fecha) == mes)
    termino = (q or "").strip()
    if termino:
        patron = func.concat("%", func.inmutable_unaccent(func.lower(escape_like(termino))), "%")
        opciones: list[ColumnElement[bool]] = [v.texto_busqueda.ilike(patron, escape="\\")]
        sin_separadores = normalize_identificacion(termino)
        if sin_separadores:
            opciones.append(v.identificacion.like(f"%{escape_like(sin_separadores)}%", escape="\\"))
        condiciones.append(or_(*opciones))
    return condiciones


_v = v_listado.c
# Desempate estable por `id` en todos (FR-035). En `recientes`, el número nulo de un borrador va
# primero entre los documentos de su fecha; en `antiguas`, al final.
_ORDENES: dict[str, tuple[UnaryExpression[Any], ...]] = {
    "recientes": (_v.fecha.desc(), _v.numero.desc().nulls_first(), _v.id.desc()),
    "antiguas": (_v.fecha.asc(), _v.numero.asc().nulls_last(), _v.id.asc()),
    "total_desc": (_v.total.desc(), _v.id.desc()),
    "total_asc": (_v.total.asc(), _v.id.asc()),
}


async def list_facturas(
    session: AsyncSession,
    *,
    q: str | None,
    anio: int | None,
    mes: int | None,
    orden: str,
    pagina: int,
    tamano: int,
) -> tuple[list[FilaListado], int]:
    condiciones = _filtros(q=q, anio=anio, mes=mes)
    total = await session.scalar(select(func.count()).select_from(v_listado).where(*condiciones))
    stmt = (
        select(
            _v.tipo_documento,
            _v.id,
            _v.num_serie,
            _v.fecha,
            _v.cliente_nombre,
            _v.identificacion,
            _v.base,
            _v.cuota,
            _v.total,
            _v.estado,
        )
        .where(*condiciones)
        .order_by(*_ORDENES[orden])
        .offset((pagina - 1) * tamano)
        .limit(tamano)
    )
    filas = [
        FilaListado(
            tipo_documento=f.tipo_documento,
            id=f.id,
            num_serie=f.num_serie,
            fecha=f.fecha,
            cliente_nombre=f.cliente_nombre,
            identificacion=f.identificacion,
            base=f.base,
            cuota=f.cuota,
            total=f.total,
            estado=EstadoFactura(f.estado),
        )
        for f in await session.execute(stmt)
    ]
    return filas, int(total or 0)
