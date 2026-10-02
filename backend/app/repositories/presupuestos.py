"""Acceso a los presupuestos emitidos (solo inserción) y a su listado (005; R-3, R-6, R-11).

El estado guardado no es una columna: lo calcula la función SQL `estado_presupuesto()` (migración
0008). La caducidad la añade el servicio con la fecha de hoy (`domain/presupuestos`).
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Final

from sqlalchemy import (
    Boolean,
    Date,
    Integer,
    Numeric,
    Select,
    Text,
    Uuid,
    and_,
    column,
    exists,
    func,
    or_,
    select,
    table,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.models.borrador_presupuesto import BorradorPresupuesto
from app.models.presupuesto import DesglosePresupuesto, LineaPresupuesto, Presupuesto
from app.repositories import listado

# «JBPRES»: serializa las operaciones que emiten o cierran presupuestos (research R-6). `jb_app` no
# tiene UPDATE sobre `presupuestos`, así que no puede usar `SELECT … FOR UPDATE`.
CLAVE_CERROJO_PRESUPUESTOS: Final = 0x4A42_5052_4553


async def lock_presupuestos(session: AsyncSession) -> None:
    await session.execute(select(func.pg_advisory_xact_lock(CLAVE_CERROJO_PRESUPUESTOS)))


async def insert_emitido(
    session: AsyncSession,
    presupuesto: Presupuesto,
    lineas: Sequence[LineaPresupuesto],
    desgloses: Sequence[DesglosePresupuesto],
) -> Presupuesto:
    session.add(presupuesto)
    await session.flush()
    for linea in lineas:
        linea.presupuesto_id = presupuesto.id
    for desglose in desgloses:
        desglose.presupuesto_id = presupuesto.id
    session.add_all([*lineas, *desgloses])
    await session.flush()
    await session.refresh(presupuesto, ["lineas", "desgloses"])
    return presupuesto


async def get(session: AsyncSession, presupuesto_id: uuid.UUID) -> Presupuesto | None:
    return await session.get(Presupuesto, presupuesto_id)


async def get_by_idempotency_key(session: AsyncSession, clave: uuid.UUID) -> Presupuesto | None:
    resultado = await session.execute(
        select(Presupuesto).where(Presupuesto.clave_idempotencia == clave)
    )
    return resultado.scalar_one_or_none()


async def estado(session: AsyncSession, presupuesto_id: uuid.UUID) -> str:
    """Estado guardado: `pendiente`, `en_facturacion`, `convertido`, `sustituido` o `anulado`."""
    valor: str = (
        await session.execute(select(func.estado_presupuesto(presupuesto_id)))
    ).scalar_one()
    return valor


async def exists_any(session: AsyncSession) -> bool:
    """¿Hay algún presupuesto emitido? (idempotencia de los datos de ejemplo)."""
    return bool(
        (await session.execute(select(exists().where(Presupuesto.id.isnot(None))))).scalar()
    )


async def has_documentos(session: AsyncSession, cliente_id: uuid.UUID) -> bool:
    """¿Tiene el cliente algún presupuesto o borrador de presupuesto? (005, FR-033)."""
    consulta = select(
        or_(
            exists().where(Presupuesto.cliente_id == cliente_id),
            exists().where(BorradorPresupuesto.cliente_id == cliente_id),
        )
    )
    return bool((await session.execute(consulta)).scalar())


# --------------------------------------------------------------------------- listado (US1)

# Vista de la migración 0008, con las columnas de `v_listado_facturas` más `valido_hasta`.
v_listado = table(
    "v_listado_presupuestos",
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
    column("valido_hasta", Date),
)
_COLUMNAS = (
    "tipo_documento",
    "id",
    "num_serie",
    "fecha",
    "valido_hasta",
    "cliente_nombre",
    "identificacion",
    "base",
    "cuota",
    "total",
    "estado",
    "oro_inversion",
)


@dataclass(frozen=True, slots=True)
class FilaListado:
    tipo_documento: str
    id: uuid.UUID
    num_serie: str | None
    fecha: date
    valido_hasta: date
    cliente_nombre: str | None
    identificacion: str | None
    base: Decimal
    cuota: Decimal
    total: Decimal
    estado: str  # el guardado; la caducidad la añade el servicio
    oro_inversion: bool


def _filtros(*, q: str | None, anio: int | None, mes: int | None) -> list[ColumnElement[bool]]:
    return listado.filtros(v_listado, q=q, anio=anio, mes=mes)


def _consulta(condiciones: list[ColumnElement[bool]], orden: str) -> Select[Any]:
    return listado.consulta_filas(v_listado, _COLUMNAS, condiciones, orden)


async def _filas(session: AsyncSession, stmt: Select[Any]) -> list[FilaListado]:
    return [
        FilaListado(
            tipo_documento=f.tipo_documento,
            id=f.id,
            num_serie=f.num_serie,
            fecha=f.fecha,
            valido_hasta=f.valido_hasta,
            cliente_nombre=f.cliente_nombre,
            identificacion=f.identificacion,
            base=f.base,
            cuota=f.cuota,
            total=f.total,
            estado=f.estado,
            oro_inversion=f.oro_inversion,
        )
        for f in await session.execute(stmt)
    ]


async def count_listado(
    session: AsyncSession, *, q: str | None, anio: int | None, mes: int | None
) -> int:
    total = await session.scalar(listado.contar(v_listado, _filtros(q=q, anio=anio, mes=mes)))
    return int(total or 0)


async def list_presupuestos(
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
        _consulta(_filtros(q=q, anio=anio, mes=mes), orden)
        .offset((pagina - 1) * tamano)
        .limit(tamano)
    )
    return await _filas(session, stmt), total


async def list_presupuestos_impresion(
    session: AsyncSession, *, q: str | None, anio: int | None, mes: int | None, orden: str
) -> list[FilaListado]:
    """Todas las filas del filtro, sin paginar, en el orden y con el desempate de la pantalla."""
    return await _filas(session, _consulta(_filtros(q=q, anio=anio, mes=mes), orden))


# ------------------------------------------------------------------- listado impreso (US5)

_v = v_listado.c
# Los que se suman en los totales del listado impreso (FR-030, Clarifications): pendientes (también
# los caducados, que en la BD son pendientes), en facturación y convertidos.
ESTADOS_SUMADOS: Final = ("pendiente", "en_facturacion", "convertido")


@dataclass(frozen=True, slots=True)
class DesgloseSumado:
    tipo_iva: Decimal | None  # None: base exenta de oro de inversión
    base: Decimal
    cuota: Decimal


@dataclass(frozen=True, slots=True)
class TotalesPresupuestos:
    desglose: list[DesgloseSumado]
    sumados: int
    base: Decimal
    cuota: Decimal
    total: Decimal
    borradores: int
    sustituidos: int
    anulados: int


async def totales_presupuestos(
    session: AsyncSession, *, q: str | None, anio: int | None, mes: int | None
) -> TotalesPresupuestos:
    """Totales del filtro por tipo de IVA, como `facturas.totales_vigentes` de 003 (FR-030)."""
    condiciones = _filtros(q=q, anio=anio, mes=mes)
    sumado = and_(_v.tipo_documento == "presupuesto", _v.estado.in_(ESTADOS_SUMADOS))
    desglose = await session.execute(
        select(
            DesglosePresupuesto.tipo_iva,
            func.sum(DesglosePresupuesto.base),
            func.sum(DesglosePresupuesto.cuota),
        )
        .select_from(v_listado)
        .join(DesglosePresupuesto, DesglosePresupuesto.presupuesto_id == _v.id)
        .where(sumado, *condiciones)
        .group_by(DesglosePresupuesto.tipo_iva)
        .order_by(DesglosePresupuesto.tipo_iva.desc().nulls_last())
    )
    cero = Decimal("0.00")
    resumen = (
        await session.execute(
            select(
                func.count().filter(sumado),
                func.coalesce(func.sum(_v.base).filter(sumado), cero),
                func.coalesce(func.sum(_v.cuota).filter(sumado), cero),
                func.coalesce(func.sum(_v.total).filter(sumado), cero),
                func.count().filter(_v.tipo_documento == "borrador"),
                func.count().filter(_v.estado == "sustituido"),
                func.count().filter(_v.estado == "anulado"),
            ).where(*condiciones)
        )
    ).one()
    return TotalesPresupuestos(
        desglose=[DesgloseSumado(tipo, base, cuota) for tipo, base, cuota in desglose],
        sumados=int(resumen[0]),
        base=Decimal(resumen[1]),
        cuota=Decimal(resumen[2]),
        total=Decimal(resumen[3]),
        borradores=int(resumen[4]),
        sustituidos=int(resumen[5]),
        anulados=int(resumen[6]),
    )
