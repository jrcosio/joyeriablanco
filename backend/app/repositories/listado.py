"""Filtros, órdenes y consulta comunes de los listados de documentos (005, research R-8).

Se extrajo de `repositories/facturas.py` sin cambiar su comportamiento. Lo usan el listado de
facturas (`v_listado_facturas`) y el de presupuestos (`v_listado_presupuestos`), que comparten las
columnas `fecha`, `numero`, `id`, `total`, `identificacion` y `texto_busqueda`. Así las dos
pantallas buscan, filtran y ordenan exactamente igual (002, FR-034 y FR-035; 005, FR-025).
"""

from datetime import date
from typing import Any

from sqlalchemy import Select, TableClause, UnaryExpression, extract, func, or_, select
from sqlalchemy.sql.elements import ColumnElement

from app.domain.identificacion import normalize_identificacion
from app.repositories.clientes import escape_like


def filtros(
    v: TableClause, *, q: str | None, anio: int | None, mes: int | None
) -> list[ColumnElement[bool]]:
    """`anio=None` es «todos los años». La fecha de un borrador es la propuesta."""
    c = v.c
    condiciones: list[ColumnElement[bool]] = []
    if anio is not None:
        if mes is not None:
            inicio = date(anio, mes, 1)
            fin = date(anio + 1, 1, 1) if mes == 12 else date(anio, mes + 1, 1)
        else:
            inicio, fin = date(anio, 1, 1), date(anio + 1, 1, 1)
        condiciones += [c.fecha >= inicio, c.fecha < fin]
    elif mes is not None:
        condiciones.append(extract("month", c.fecha) == mes)
    termino = (q or "").strip()
    if termino:
        patron = func.concat("%", func.inmutable_unaccent(func.lower(escape_like(termino))), "%")
        opciones: list[ColumnElement[bool]] = [c.texto_busqueda.ilike(patron, escape="\\")]
        sin_separadores = normalize_identificacion(termino)
        if sin_separadores:
            opciones.append(c.identificacion.like(f"%{escape_like(sin_separadores)}%", escape="\\"))
        condiciones.append(or_(*opciones))
    return condiciones


def ordenes(v: TableClause) -> dict[str, tuple[UnaryExpression[Any], ...]]:
    """Desempate estable por `id` en todos. En `recientes`, el número nulo de un borrador va
    primero entre los documentos de su fecha; en `antiguas`, al final."""
    c = v.c
    return {
        "recientes": (c.fecha.desc(), c.numero.desc().nulls_first(), c.id.desc()),
        "antiguas": (c.fecha.asc(), c.numero.asc().nulls_last(), c.id.asc()),
        "total_desc": (c.total.desc(), c.id.desc()),
        "total_asc": (c.total.asc(), c.id.asc()),
    }


def consulta_filas(
    v: TableClause, columnas: tuple[str, ...], condiciones: list[ColumnElement[bool]], orden: str
) -> Select[Any]:
    return select(*(v.c[n] for n in columnas)).where(*condiciones).order_by(*ordenes(v)[orden])


def contar(v: TableClause, condiciones: list[ColumnElement[bool]]) -> Select[Any]:
    return select(func.count()).select_from(v).where(*condiciones)
