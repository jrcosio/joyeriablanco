"""Borradores de presupuesto (005; FR-012 a FR-014; research R-7).

Como los borradores de factura (002, R-9): un borrador se guarda incompleto, se edita con
concurrencia optimista y se borra sin consumir número. Al guardarlo se calculan los totales
PREVISTOS con `domain/importes.py`; al emitir, `presupuestos.emit_presupuesto` lo recalcula todo
con el IVA vigente. A diferencia de la factura, la fecha y la validez se validan ya al guardar
(FR-008, FR-009).
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
from app.models.borrador_presupuesto import BorradorPresupuesto, LineaBorradorPresupuesto
from app.models.presupuesto import Presupuesto
from app.models.usuario import Usuario
from app.repositories import borradores_presupuesto as repo
from app.repositories import clientes as clientes_repo
from app.repositories import configuracion_facturacion as configuracion_repo
from app.repositories import presupuestos as presupuestos_repo
from app.services import presupuestos
from app.services.auditoria import diff, record_event
from app.services.contenido import DatosLinea, lineas_json, normalize_lineas, previstos

NO_EXISTE: Final = "Este borrador ya no existe: puede que se haya emitido o eliminado."


@dataclass(frozen=True, slots=True)
class DatosBorradorPresupuesto:
    fecha: date
    valido_hasta: date
    cliente_id: uuid.UUID | None
    lineas: tuple[DatosLinea, ...]
    oro_inversion: bool = False


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


def _contenido(borrador: BorradorPresupuesto) -> dict[str, object]:
    """Lo que el usuario edita, más el IVA previsto, para el *diff* de auditoría."""
    return {
        "fecha": borrador.fecha,
        "valido_hasta": borrador.valido_hasta,
        "cliente_id": borrador.cliente_id,
        "lineas": lineas_json(borrador.lineas),
        "oro_inversion": borrador.oro_inversion,
        "tipo_iva_previsto": borrador.tipo_iva_previsto,
    }


def _contenido_nuevo(
    datos: DatosBorradorPresupuesto, lineas: tuple[DatosLinea, ...], tipo_iva: Decimal
) -> dict[str, object]:
    return {
        "fecha": datos.fecha,
        "valido_hasta": datos.valido_hasta,
        "cliente_id": datos.cliente_id,
        "lineas": lineas_json(lineas),
        "oro_inversion": datos.oro_inversion,
        "tipo_iva_previsto": tipo_iva,
    }


def _aplicar(
    borrador: BorradorPresupuesto,
    datos: DatosBorradorPresupuesto,
    lineas: tuple[DatosLinea, ...],
    tipo_iva: Decimal,
) -> None:
    totales = previstos(lineas, None if datos.oro_inversion else tipo_iva)
    borrador.fecha = datos.fecha
    borrador.valido_hasta = datos.valido_hasta
    borrador.oro_inversion = datos.oro_inversion
    borrador.cliente_id = datos.cliente_id
    borrador.lineas = [
        LineaBorradorPresupuesto(
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


async def get_borrador(db: AsyncSession, borrador_id: uuid.UUID) -> BorradorPresupuesto:
    borrador = await repo.get(db, borrador_id)
    if borrador is None:
        raise NoEncontrado(NO_EXISTE)
    return borrador


async def create_borrador(
    db: AsyncSession, datos: DatosBorradorPresupuesto, *, actor: Usuario, origen: Origen
) -> BorradorPresupuesto:
    presupuestos.check_fechas(datos.fecha, datos.valido_hasta)
    await _check_cliente(db, datos.cliente_id, actual=None)
    config = await configuracion_repo.get(db)
    borrador = BorradorPresupuesto(creado_por_id=actor.id, actualizado_por_id=actor.id)
    _aplicar(borrador, datos, normalize_lineas(datos.lineas), config.iva_por_defecto)
    await repo.save(db, borrador)
    await record_event(
        db,
        TipoEvento.BORRADOR_PRESUPUESTO_CREADO,
        origen=origen,
        actor=actor,
        cliente_id=borrador.cliente_id,
        detalle={"borrador_id": borrador.id, "lineas": len(borrador.lineas)},
    )
    return borrador


async def update_borrador(
    db: AsyncSession,
    borrador_id: uuid.UUID,
    datos: DatosBorradorPresupuesto,
    *,
    version: int,
    actor: Usuario,
    origen: Origen,
) -> BorradorPresupuesto:
    borrador = await get_borrador(db, borrador_id)
    if borrador.version != version:
        raise ConflictoVersion(repo.MENSAJE_CONFLICTO)
    presupuestos.check_fechas(datos.fecha, datos.valido_hasta)
    await _check_cliente(db, datos.cliente_id, actual=borrador.cliente_id)
    lineas = normalize_lineas(datos.lineas)
    tipo_iva = (await configuracion_repo.get(db)).iva_por_defecto
    previstos(lineas, None if datos.oro_inversion else tipo_iva)  # valida antes de comparar
    cambios = diff(_contenido(borrador), _contenido_nuevo(datos, lineas, tipo_iva))
    if not cambios:
        return borrador
    # Las líneas anteriores se borran antes de insertar las nuevas: el ORM inserta primero y
    # chocaría con la unicidad de (borrador_id, orden).
    borrador.lineas.clear()
    await db.flush()
    _aplicar(borrador, datos, lineas, tipo_iva)
    borrador.actualizado_por_id = actor.id
    # Cambiar solo las líneas no toca la fila: se fuerza su UPDATE para que suba la versión.
    borrador.actualizado_en = func.now()
    await repo.save(db, borrador)
    await record_event(
        db,
        TipoEvento.BORRADOR_PRESUPUESTO_EDITADO,
        origen=origen,
        actor=actor,
        cliente_id=borrador.cliente_id,
        detalle={"borrador_id": borrador.id, "cambios": cambios},
    )
    return borrador


async def delete_borrador(
    db: AsyncSession, borrador_id: uuid.UUID, *, actor: Usuario, origen: Origen
) -> None:
    """Borrado definitivo (FR-012): no consume número; queda en la auditoría."""
    borrador = await get_borrador(db, borrador_id)
    detalle = {"borrador_id": borrador.id, **_contenido(borrador)}
    detalle.pop("tipo_iva_previsto")
    cliente_id = borrador.cliente_id
    await repo.delete(db, borrador)
    await record_event(
        db,
        TipoEvento.BORRADOR_PRESUPUESTO_ELIMINADO,
        origen=origen,
        actor=actor,
        cliente_id=cliente_id,
        detalle=detalle,
    )


async def emit_borrador(
    db: AsyncSession,
    borrador_id: uuid.UUID,
    datos: DatosBorradorPresupuesto,
    *,
    version: int,
    actor: Usuario,
    origen: Origen,
    clave: uuid.UUID,
) -> tuple[Presupuesto, bool]:
    """Emite el borrador con el contenido actual del modal y lo sustituye por el presupuesto.

    Orden de R-6 y R-7: el cerrojo de presupuestos y la clave (una repetición devuelve el mismo
    presupuesto aunque el borrador ya no exista) y después el borrador con `FOR UPDATE`.
    """
    await presupuestos_repo.lock_presupuestos(db)
    operacion = OperacionIdempotente.EMITIR_BORRADOR
    if previo := await presupuestos.find_previous_presupuesto(db, clave, operacion, borrador_id):
        return previo, False
    borrador = await repo.get(db, borrador_id, for_update=True)
    if borrador is None:
        raise NoEncontrado(NO_EXISTE)
    if borrador.version != version:
        raise ConflictoVersion(repo.MENSAJE_CONFLICTO)
    if datos.cliente_id is None:
        raise DatosNoValidos(errores=[CampoError("cliente_id", "Elige el cliente.")])
    presupuesto, _ = await presupuestos.emit_presupuesto(
        db,
        presupuestos.DatosPresupuesto(
            fecha=datos.fecha,
            valido_hasta=datos.valido_hasta,
            cliente_id=datos.cliente_id,
            lineas=normalize_lineas(datos.lineas),
            oro_inversion=datos.oro_inversion,
        ),
        actor=actor,
        origen=origen,
        clave=clave,
        operacion=operacion,
        origen_id=borrador_id,
        bloqueado=True,
    )
    await repo.delete(db, borrador)
    return presupuesto, True
