"""«Convertir en factura»: el borrador de factura vinculado al presupuesto (005, US3; R-5, R-6).

La conversión NO emite nada: crea un borrador de factura de 002 precargado con el cliente, las
líneas y el oro de inversión del presupuesto, con la fecha de hoy y el IVA vigente. No consume
números ni genera registros. La factura se emite después con la emisión de borradores de 002, que
cierra el presupuesto como convertido en la misma transacción (`presupuestos.close_conversion`).

Es idempotente por sí misma: mientras el borrador vinculado exista, convertir otra vez lo devuelve.
"""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NoEncontrado, PresupuestoNoModificable
from app.core.http import Origen
from app.core.tiempo import hoy
from app.domain.tipos import EstadoPresupuesto, TipoEvento
from app.models.borrador_factura import BorradorFactura
from app.models.usuario import Usuario
from app.repositories import borradores as borradores_repo
from app.repositories import configuracion_facturacion as configuracion_repo
from app.repositories import presupuestos as presupuestos_repo
from app.services import borradores, presupuestos
from app.services.auditoria import record_event
from app.services.contenido import DatosLinea

logger = logging.getLogger(__name__)


async def create_borrador_conversion(
    db: AsyncSession, presupuesto_id: uuid.UUID, *, actor: Usuario, origen: Origen
) -> tuple[BorradorFactura, bool]:
    """El borrador vinculado y si se ha creado ahora (`False`: ya estaba en facturación).

    Cerrojo de presupuestos y estado (R-6): un presupuesto cerrado responde 409. El borrador se
    crea directamente con el cliente del presupuesto, aunque se haya desactivado después: un
    borrador se guarda incompleto, y la emisión lo rechazará hasta que se cambie (US3-8).
    """
    await presupuestos_repo.lock_presupuestos(db)
    presupuesto = await presupuestos_repo.get(db, presupuesto_id)
    if presupuesto is None:
        raise NoEncontrado(presupuestos.NO_EXISTE)
    guardado = EstadoPresupuesto(await presupuestos_repo.estado(db, presupuesto.id))
    if guardado is EstadoPresupuesto.EN_FACTURACION:
        existente = await borradores_repo.get_by_presupuesto(db, presupuesto.id)
        if existente is not None:
            return existente, False
    if guardado not in (EstadoPresupuesto.PENDIENTE, EstadoPresupuesto.EN_FACTURACION):
        raise PresupuestoNoModificable(guardado.value)

    config = await configuracion_repo.get(db)
    borrador = borradores.build_borrador(
        borradores.DatosBorrador(
            fecha_expedicion=hoy(),
            cliente_id=presupuesto.cliente_id,
            lineas=tuple(
                DatosLinea(
                    unidades=linea.unidades,
                    descripcion=linea.descripcion,
                    precio_unitario=linea.precio_unitario,
                )
                for linea in sorted(presupuesto.lineas, key=lambda linea: linea.orden)
            ),
            oro_inversion=presupuesto.oro_inversion,
        ),
        actor=actor,
        tipo_iva=config.iva_por_defecto,
        presupuesto_id=presupuesto.id,
    )
    await presupuestos.guard_presupuesto(
        db, presupuesto.id, lambda: borradores_repo.save(db, borrador)
    )
    await record_event(
        db,
        TipoEvento.BORRADOR_FACTURA_CREADO,
        origen=origen,
        actor=actor,
        cliente_id=borrador.cliente_id,
        detalle={
            "borrador_id": borrador.id,
            "lineas": len(borrador.lineas),
            "presupuesto_id": presupuesto.id,
            "num_serie_presupuesto": presupuesto.num_serie,
        },
    )
    logger.info("Presupuesto %s en facturación", presupuesto.num_serie)
    return borrador, True
