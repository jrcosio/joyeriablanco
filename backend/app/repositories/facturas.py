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
    Boolean,
    Date,
    Integer,
    Numeric,
    Select,
    Text,
    UnaryExpression,
    Uuid,
    and_,
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

# Vista de solo lectura de la migración 0005, con `oro_inversion` desde la 0006 (research R-12 y
# R-21). Se declara con `table()` para no registrarla en los metadatos del ORM.
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
    column("oro_inversion", Boolean),
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
    oro_inversion: bool


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


def _consulta_filas(condiciones: list[ColumnElement[bool]], orden: str) -> Select[Any]:
    return (
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
            _v.oro_inversion,
        )
        .where(*condiciones)
        .order_by(*_ORDENES[orden])
    )


async def _filas(session: AsyncSession, stmt: Select[Any]) -> list[FilaListado]:
    return [
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
            oro_inversion=f.oro_inversion,
        )
        for f in await session.execute(stmt)
    ]


async def count_listado(
    session: AsyncSession, *, q: str | None, anio: int | None, mes: int | None
) -> int:
    condiciones = _filtros(q=q, anio=anio, mes=mes)
    total = await session.scalar(select(func.count()).select_from(v_listado).where(*condiciones))
    return int(total or 0)


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
    total = await count_listado(session, q=q, anio=anio, mes=mes)
    stmt = (
        _consulta_filas(_filtros(q=q, anio=anio, mes=mes), orden)
        .offset((pagina - 1) * tamano)
        .limit(tamano)
    )
    return await _filas(session, stmt), total


# ------------------------------------------------------------ listado impreso (003, US2)


async def list_facturas_impresion(
    session: AsyncSession, *, q: str | None, anio: int | None, mes: int | None, orden: str
) -> list[FilaListado]:
    """Todas las filas del filtro, sin paginar, en el orden y con el desempate de la pantalla."""
    return await _filas(session, _consulta_filas(_filtros(q=q, anio=anio, mes=mes), orden))


@dataclass(frozen=True, slots=True)
class DesgloseVigentes:
    tipo_iva: Decimal | None  # None: base exenta de oro de inversión
    base: Decimal
    cuota: Decimal


@dataclass(frozen=True, slots=True)
class TotalesVigentes:
    desglose: list[DesgloseVigentes]
    vigentes: int
    base: Decimal
    cuota: Decimal
    total: Decimal
    borradores: int
    anuladas: int
    rectificadas: int


async def totales_vigentes(
    session: AsyncSession, *, q: str | None, anio: int | None, mes: int | None
) -> TotalesVigentes:
    """Totales de las facturas vigentes del filtro (FR-021, data-model «Totales del listado»)."""
    condiciones = _filtros(q=q, anio=anio, mes=mes)
    es_vigente = and_(_v.tipo_documento == "factura", _v.estado == EstadoFactura.VIGENTE.value)
    desglose = await session.execute(
        select(
            DesgloseFactura.tipo_iva,
            func.sum(DesgloseFactura.base),
            func.sum(DesgloseFactura.cuota),
        )
        .select_from(v_listado)
        .join(DesgloseFactura, DesgloseFactura.factura_id == _v.id)
        .where(es_vigente, *condiciones)
        .group_by(DesgloseFactura.tipo_iva)
        .order_by(DesgloseFactura.tipo_iva.desc().nulls_last())
    )
    cero = Decimal("0.00")
    resumen = (
        await session.execute(
            select(
                func.count().filter(es_vigente),
                func.coalesce(func.sum(_v.base).filter(es_vigente), cero),
                func.coalesce(func.sum(_v.cuota).filter(es_vigente), cero),
                func.coalesce(func.sum(_v.total).filter(es_vigente), cero),
                func.count().filter(_v.tipo_documento == "borrador"),
                func.count().filter(_v.estado == EstadoFactura.ANULADA.value),
                func.count().filter(_v.estado == EstadoFactura.RECTIFICADA.value),
            ).where(*condiciones)
        )
    ).one()
    return TotalesVigentes(
        desglose=[DesgloseVigentes(tipo, base, cuota) for tipo, base, cuota in desglose],
        vigentes=int(resumen[0]),
        base=Decimal(resumen[1]),
        cuota=Decimal(resumen[2]),
        total=Decimal(resumen[3]),
        borradores=int(resumen[4]),
        anuladas=int(resumen[5]),
        rectificadas=int(resumen[6]),
    )
