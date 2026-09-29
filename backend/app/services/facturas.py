"""Consulta de facturas emitidas: detalle con estado derivado, enlaces e historial (FR-026)."""

import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NoEncontrado
from app.domain.tipos import EstadoFactura, TipoCorreccion
from app.models.correccion_factura import CorreccionFactura
from app.models.factura import Factura
from app.models.registro_facturacion import RegistroFacturacion
from app.repositories import correcciones, facturas, registros


@dataclass(frozen=True, slots=True)
class CorreccionVista:
    correccion: CorreccionFactura
    factura_nueva: Factura | None
    en_vigor: bool


@dataclass(frozen=True, slots=True)
class DetalleFactura:
    factura: Factura
    estado: EstadoFactura
    rectifica_a: Factura | None
    sustituye_a: Factura | None
    vigente_actual: Factura | None
    correcciones: list[CorreccionVista]
    registros: list[RegistroFacturacion]


async def _vigente_actual(
    db: AsyncSession, vistas: list[CorreccionVista], estado: EstadoFactura
) -> Factura | None:
    """La factura vigente que sustituye a esta (reemisión o rectificativa), siguiendo la cadena."""
    if estado is EstadoFactura.VIGENTE:
        return None
    en_vigor = [v for v in vistas if v.en_vigor and v.factura_nueva is not None]
    siguiente = en_vigor[-1].factura_nueva if en_vigor else None
    visitadas: set[uuid.UUID] = set()
    while siguiente is not None and siguiente.id not in visitadas:
        visitadas.add(siguiente.id)
        if await facturas.estado(db, siguiente.id) is EstadoFactura.VIGENTE:
            return siguiente
        vistas_siguiente = await _vistas(db, siguiente.id)
        en_vigor = [v for v in vistas_siguiente if v.en_vigor and v.factura_nueva is not None]
        siguiente = en_vigor[-1].factura_nueva if en_vigor else None
    return None


async def _vistas(db: AsyncSession, factura_id: uuid.UUID) -> list[CorreccionVista]:
    vistas: list[CorreccionVista] = []
    for correccion in await correcciones.list_by_factura(db, factura_id):
        nueva = (
            await facturas.get(db, correccion.factura_nueva_id)
            if correccion.factura_nueva_id
            else None
        )
        en_vigor = True
        if correccion.tipo == TipoCorreccion.RECTIFICACION_SUSTITUCION and nueva is not None:
            # Una rectificación deja de estar en vigor si se anula la rectificativa (FR-048).
            en_vigor = await facturas.estado(db, nueva.id) is not EstadoFactura.ANULADA
        vistas.append(
            CorreccionVista(correccion=correccion, factura_nueva=nueva, en_vigor=en_vigor)
        )
    return vistas


async def get_factura(db: AsyncSession, factura_id: uuid.UUID) -> DetalleFactura:
    factura = await facturas.get(db, factura_id)
    if factura is None:
        raise NoEncontrado("La factura no existe.")
    estado = await facturas.estado(db, factura.id)
    vistas = await _vistas(db, factura.id)
    rectifica_a = (
        await facturas.get(db, factura.factura_rectificada_id)
        if factura.factura_rectificada_id
        else None
    )
    origen = await correcciones.get_by_factura_nueva(db, factura.id)
    sustituye_a = (
        await facturas.get(db, origen.factura_id)
        if origen is not None and origen.tipo == TipoCorreccion.ANULACION_Y_REEMISION
        else None
    )
    return DetalleFactura(
        factura=factura,
        estado=estado,
        rectifica_a=rectifica_a,
        sustituye_a=sustituye_a,
        vigente_actual=await _vigente_actual(db, vistas, estado),
        correcciones=vistas,
        registros=await registros.list_by_factura(db, factura.id),
    )
