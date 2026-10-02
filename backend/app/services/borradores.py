"""Borradores de factura (US4; FR-011, FR-019, FR-020; research R-9).

Un borrador no es una factura expedida (constitución III): se guarda incompleto, se edita con
concurrencia optimista y se borra sin consumir número ni generar registro. Al guardarlo se
calculan con `domain/importes.py` el IVA y los totales PREVISTOS, que solo sirven para el listado
y para avisar si el IVA cambia; al emitir, `emision` lo recalcula todo con el IVA vigente.

Un borrador de oro de inversión (`oro_inversion`, research R-21) prevé los totales sin cuota. El
IVA previsto sigue siendo el vigente al guardarlo, por si se desmarca la casilla.
"""

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Final

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import CampoError, ConflictoVersion, DatosNoValidos, NoEncontrado
from app.core.http import Origen
from app.domain.tipos import OperacionIdempotente, TipoEvento
from app.models.borrador_factura import BorradorFactura, LineaBorrador
from app.models.factura import Factura
from app.models.usuario import Usuario
from app.repositories import borradores as repo
from app.repositories import clientes as clientes_repo
from app.repositories import configuracion_facturacion as configuracion_repo
from app.repositories import registros
from app.services import emision
from app.services.auditoria import diff, record_event
from app.services.contenido import DatosLinea, lineas_json, normalize_lineas, previstos

NO_EXISTE: Final = "Este borrador ya no existe: puede que se haya emitido o eliminado."


@dataclass(frozen=True, slots=True)
class DatosBorrador:
    fecha_expedicion: date
    cliente_id: uuid.UUID | None
    lineas: tuple[DatosLinea, ...]
    oro_inversion: bool = False


# --------------------------------------------------------------------------- validaciones


async def _check_cliente(
    db: AsyncSession, cliente_id: uuid.UUID | None, *, actual: uuid.UUID | None
) -> None:
    """El cliente debe existir. Uno desactivado no se puede elegir (001), pero si ya estaba en el
    borrador se conserva: el borrador se puede seguir guardando y no se emitirá hasta cambiarlo."""
    if cliente_id is None:
        return
    cliente = await clientes_repo.get(db, cliente_id)
    if cliente is None:
        raise DatosNoValidos(errores=[CampoError("cliente_id", "El cliente no existe.")])
    if not cliente.activo and cliente_id != actual:
        raise DatosNoValidos(
            errores=[CampoError("cliente_id", "El cliente está desactivado: elige otro.")]
        )


def _contenido(borrador: BorradorFactura) -> dict[str, object]:
    """Lo que el usuario edita, más el IVA previsto, para el *diff* de auditoría."""
    return {
        "fecha_expedicion": borrador.fecha_expedicion,
        "cliente_id": borrador.cliente_id,
        "lineas": lineas_json(borrador.lineas),
        "oro_inversion": borrador.oro_inversion,
        "tipo_iva_previsto": borrador.tipo_iva_previsto,
    }


def _contenido_nuevo(
    datos: DatosBorrador, lineas: tuple[DatosLinea, ...], tipo_iva: Decimal
) -> dict[str, object]:
    return {
        "fecha_expedicion": datos.fecha_expedicion,
        "cliente_id": datos.cliente_id,
        "lineas": lineas_json(lineas),
        "oro_inversion": datos.oro_inversion,
        "tipo_iva_previsto": tipo_iva,
    }


def _aplicar(
    borrador: BorradorFactura,
    datos: DatosBorrador,
    lineas: tuple[DatosLinea, ...],
    tipo_iva: Decimal,
) -> None:
    totales = previstos(lineas, None if datos.oro_inversion else tipo_iva)
    borrador.fecha_expedicion = datos.fecha_expedicion
    borrador.oro_inversion = datos.oro_inversion
    borrador.cliente_id = datos.cliente_id
    borrador.lineas = [
        LineaBorrador(
            orden=orden,
            unidades=linea.unidades,
            descripcion=linea.descripcion,
            precio_unitario=linea.precio_unitario,
        )
        for orden, linea in enumerate(lineas, start=1)
    ]
    borrador.tipo_iva_previsto = tipo_iva
    borrador.base_prevista = totales.base_total
    borrador.cuota_prevista = totales.cuota_total
    borrador.total_previsto = totales.importe_total


# ------------------------------------------------------------------------------ operaciones


async def get_borrador(db: AsyncSession, borrador_id: uuid.UUID) -> BorradorFactura:
    borrador = await repo.get(db, borrador_id)
    if borrador is None:
        raise NoEncontrado(NO_EXISTE)
    return borrador


async def create_borrador(
    db: AsyncSession, datos: DatosBorrador, *, actor: Usuario, origen: Origen
) -> BorradorFactura:
    await _check_cliente(db, datos.cliente_id, actual=None)
    config = await configuracion_repo.get(db)
    borrador = BorradorFactura(creado_por_id=actor.id, actualizado_por_id=actor.id)
    _aplicar(borrador, datos, normalize_lineas(datos.lineas), config.iva_por_defecto)
    await repo.save(db, borrador)
    await record_event(
        db,
        TipoEvento.BORRADOR_FACTURA_CREADO,
        origen=origen,
        actor=actor,
        cliente_id=borrador.cliente_id,
        detalle={"borrador_id": borrador.id, "lineas": len(borrador.lineas)},
    )
    return borrador


async def update_borrador(
    db: AsyncSession,
    borrador_id: uuid.UUID,
    datos: DatosBorrador,
    *,
    version: int,
    actor: Usuario,
    origen: Origen,
) -> BorradorFactura:
    borrador = await get_borrador(db, borrador_id)
    if borrador.version != version:
        raise ConflictoVersion(repo.MENSAJE_CONFLICTO)
    await _check_cliente(db, datos.cliente_id, actual=borrador.cliente_id)
    lineas = normalize_lineas(datos.lineas)
    tipo_iva = (await configuracion_repo.get(db)).iva_por_defecto
    previstos(lineas, None if datos.oro_inversion else tipo_iva)  # valida antes de comparar
    # Si el IVA vigente ha cambiado, volver a guardar actualiza el previsto (y su aviso).
    cambios = diff(_contenido(borrador), _contenido_nuevo(datos, lineas, tipo_iva))
    if not cambios:
        return borrador
    # Las líneas anteriores se borran antes de insertar las nuevas: el ORM inserta primero y
    # chocaría con la unicidad de (borrador_id, orden).
    borrador.lineas.clear()
    await db.flush()
    _aplicar(borrador, datos, lineas, tipo_iva)
    borrador.actualizado_por_id = actor.id
    # Cambiar solo las líneas no toca la fila del borrador: se fuerza su UPDATE para que suba la
    # versión y otra sesión con la versión anterior reciba el conflicto (FR-020).
    borrador.actualizado_en = func.now()
    await repo.save(db, borrador)
    await record_event(
        db,
        TipoEvento.BORRADOR_FACTURA_EDITADO,
        origen=origen,
        actor=actor,
        cliente_id=borrador.cliente_id,
        detalle={"borrador_id": borrador.id, "cambios": cambios},
    )
    return borrador


async def delete_borrador(
    db: AsyncSession, borrador_id: uuid.UUID, *, actor: Usuario, origen: Origen
) -> None:
    """Borrado definitivo (FR-019): no consume número ni genera registro; queda en la auditoría."""
    borrador = await get_borrador(db, borrador_id)
    detalle = {"borrador_id": borrador.id, **_contenido(borrador)}
    detalle.pop("tipo_iva_previsto")
    cliente_id = borrador.cliente_id
    await repo.delete(db, borrador)
    await record_event(
        db,
        TipoEvento.BORRADOR_FACTURA_ELIMINADO,
        origen=origen,
        actor=actor,
        cliente_id=cliente_id,
        detalle=detalle,
    )


async def emit_borrador(
    db: AsyncSession,
    borrador_id: uuid.UUID,
    datos: DatosBorrador,
    *,
    version: int,
    actor: Usuario,
    origen: Origen,
    clave: uuid.UUID,
) -> tuple[Factura, bool]:
    """Emite el borrador con el contenido actual del modal y lo sustituye por la factura (R-9).

    Mismo orden de cerrojos que cualquier emisión: primero la cadena y la clave de idempotencia
    (una repetición devuelve la misma factura aunque el borrador ya no exista) y después el
    borrador con `FOR UPDATE`, que es mutable.
    """
    await registros.lock_chain(db)
    operacion = OperacionIdempotente.EMITIR_BORRADOR
    if previa := await emision.find_previous(db, clave, operacion, borrador_id):
        return previa, False
    borrador = await repo.get(db, borrador_id, for_update=True)
    if borrador is None:
        raise NoEncontrado(NO_EXISTE)
    if borrador.version != version:
        raise ConflictoVersion(repo.MENSAJE_CONFLICTO)
    if datos.cliente_id is None:
        raise DatosNoValidos(errores=[CampoError("cliente_id", "Elige el cliente.")])
    factura, _ = await emision.emit_factura(
        db,
        emision.DatosFactura(
            fecha_expedicion=datos.fecha_expedicion,
            cliente_id=datos.cliente_id,
            lineas=normalize_lineas(datos.lineas),
            oro_inversion=datos.oro_inversion,
        ),
        actor=actor,
        origen=origen,
        clave=clave,
        operacion=operacion,
        origen_id=borrador_id,
        cadena_bloqueada=True,
    )
    await repo.delete(db, borrador)
    return factura, True
