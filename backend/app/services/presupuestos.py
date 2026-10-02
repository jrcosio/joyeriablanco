"""Presupuestos emitidos: emisión, consulta, listado y cierres (005; research R-3, R-5 a R-7).

Un presupuesto sigue el ciclo de la factura sin ninguna pieza fiscal (constitución 2.3.0): número
`PRE-AAAA-NNNN` con el contador bloqueado de 002, copia del emisor y del destinatario, líneas e
importes con la política única de `domain/importes.py`, y ningún registro ni huella (FR-005).

Todo en UNA transacción, tras el cerrojo de presupuestos (R-6): idempotencia, validaciones,
cálculo, número y escritura. Si algo falla, se deshace entera y no queda número consumido.
"""

import logging
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Final, Literal

from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import (
    RESTRICCIONES_PRESUPUESTO,
    CampoError,
    ClienteNoFacturable,
    DatosNoValidos,
    EmisionNoDisponible,
    FechaExpedicionNoValida,
    IdempotenciaConflicto,
    NoEncontrado,
    PresupuestoNoModificable,
    SinCambios,
    restriccion,
)
from app.core.http import Origen
from app.core.tiempo import hoy
from app.domain.importes import line_amount
from app.domain.numeracion import format_num_serie
from app.domain.presupuestos import estado_visible
from app.domain.registro import FECHA_MINIMA_EXPEDICION
from app.domain.tipos import (
    EstadoPresupuesto,
    OperacionIdempotente,
    Serie,
    TipoCierrePresupuesto,
    TipoEvento,
)
from app.models.borrador_factura import BorradorFactura
from app.models.cierre_presupuesto import CierrePresupuesto
from app.models.cliente import Cliente
from app.models.configuracion_facturacion import ConfiguracionFacturacion
from app.models.factura import Factura
from app.models.presupuesto import DesglosePresupuesto, LineaPresupuesto, Presupuesto
from app.models.usuario import Usuario
from app.repositories import borradores as borradores_factura
from app.repositories import cierres_presupuesto as cierres
from app.repositories import clientes as clientes_repo
from app.repositories import configuracion_facturacion as configuracion_repo
from app.repositories import contadores
from app.repositories import facturas as facturas_repo
from app.repositories import presupuestos as repo
from app.services import facturas as facturas_servicio
from app.services.auditoria import record_event
from app.services.configuracion_facturacion import CAMPOS_EMISION
from app.services.contenido import (
    DatosLinea,
    calcular_totales,
    check_lineas,
    copia_destinatario,
    copia_emisor,
)

logger = logging.getLogger(__name__)

NO_EXISTE: Final = "El presupuesto no existe."
SIN_LINEAS: Final = "El presupuesto debe tener al menos una línea."


@dataclass(frozen=True, slots=True)
class DatosPresupuesto:
    fecha: date
    valido_hasta: date
    cliente_id: uuid.UUID
    lineas: tuple[DatosLinea, ...]
    oro_inversion: bool = False


# ------------------------------------------------------------------------ validaciones


def missing_for_presupuesto(config: ConfiguracionFacturacion) -> list[str]:
    """Datos del emisor que faltan. La modalidad no se exige: no hay registros (FR-011)."""
    return [
        clave
        for clave, atributo in CAMPOS_EMISION
        if clave != "modalidad" and getattr(config, atributo) is None
    ]


def check_fechas(fecha: date, valido_hasta: date) -> None:
    """FR-008 y FR-009: la fecha, entre el 28/10/2024 y hoy; la validez, no anterior a ella."""
    errores: list[CampoError] = []
    if fecha > hoy():
        errores.append(CampoError("fecha", "La fecha no puede ser posterior a hoy."))
    elif fecha < FECHA_MINIMA_EXPEDICION:
        errores.append(CampoError("fecha", "La fecha no puede ser anterior al 28/10/2024."))
    if valido_hasta < fecha:
        errores.append(
            CampoError("valido_hasta", "«Válido hasta» no puede ser anterior a la fecha.")
        )
    if errores:
        raise DatosNoValidos(errores=errores)


async def cliente_activo(db: AsyncSession, cliente_id: uuid.UUID) -> Cliente:
    """El cliente debe existir y estar activo. El domicilio no se exige (FR-011)."""
    cliente = await clientes_repo.get(db, cliente_id)
    if cliente is None:
        raise DatosNoValidos(errores=[CampoError("cliente_id", "El cliente no existe.")])
    if not cliente.activo:
        raise ClienteNoFacturable(
            "El cliente está desactivado.",
            extra={"faltan": ["activo"], "cliente_id": str(cliente.id)},
        )
    if "provincia" in inspect(cliente).unloaded:
        # Cliente dado de alta en esta misma sesión: la provincia se copia (FR-010) y en asíncrono
        # no se puede cargar de forma perezosa.
        await db.refresh(cliente, ["provincia"])
    return cliente


# ------------------------------------------------------------------------ idempotencia


async def find_previous_presupuesto(
    db: AsyncSession,
    clave: uuid.UUID,
    operacion: OperacionIdempotente,
    origen_id: uuid.UUID | None,
) -> Presupuesto | None:
    """Resultado ya creado con esta clave para esta misma operación y origen (R-7), o `None`.

    Para `anular`, el presupuesto anulado. Una clave usada en otra operación o sobre otro documento
    es un conflicto: nunca se devuelve el resultado de otra operación.
    """
    previo = await repo.get_by_idempotency_key(db, clave)
    if previo is not None:
        if (
            previo.operacion_idempotencia != operacion.value
            or previo.origen_idempotencia != origen_id
        ):
            raise IdempotenciaConflicto
        return previo
    cierre = await cierres.get_by_idempotency_key(db, clave)
    if cierre is not None:
        if operacion is not OperacionIdempotente.ANULAR or cierre.presupuesto_id != origen_id:
            raise IdempotenciaConflicto
        return await repo.get(db, cierre.presupuesto_id)
    return None


# --------------------------------------------------------------------------- emisión


async def emit_presupuesto(
    db: AsyncSession,
    datos: DatosPresupuesto,
    *,
    actor: Usuario,
    origen: Origen,
    clave: uuid.UUID,
    operacion: OperacionIdempotente = OperacionIdempotente.EMITIR,
    origen_id: uuid.UUID | None = None,
    bloqueado: bool = False,
) -> tuple[Presupuesto, bool]:
    """Emite un presupuesto. Devuelve el presupuesto y si se ha creado ahora (`False` si es la
    repetición de una clave ya usada).

    `bloqueado`: quien llama ya tomó el cerrojo y comprobó la clave (borrador o modificación).
    """
    if not bloqueado:
        await repo.lock_presupuestos(db)
        if previo := await find_previous_presupuesto(db, clave, operacion, origen_id):
            return previo, False
    config = await configuracion_repo.get(db)
    if faltan := missing_for_presupuesto(config):
        raise EmisionNoDisponible(extra={"faltan": faltan})
    check_fechas(datos.fecha, datos.valido_hasta)
    cliente = await cliente_activo(db, datos.cliente_id)
    check_lineas(datos.lineas, sin_lineas=SIN_LINEAS)
    tipo_iva = None if datos.oro_inversion else config.iva_por_defecto
    totales = calcular_totales(datos.lineas, tipo_iva)
    if totales.importe_total <= 0:
        raise DatosNoValidos(
            errores=[CampoError("lineas", "El total del presupuesto debe ser mayor que cero.")]
        )

    anio = datos.fecha.year
    numero = await contadores.assign_numero(db, Serie.PRESUPUESTO, anio)
    presupuesto = await repo.insert_emitido(
        db,
        Presupuesto(
            serie=Serie.PRESUPUESTO.value,
            anio=anio,
            numero=numero,
            num_serie=format_num_serie(Serie.PRESUPUESTO, anio, numero),
            fecha=datos.fecha,
            valido_hasta=datos.valido_hasta,
            **copia_emisor(config),
            cliente_id=cliente.id,
            **copia_destinatario(cliente),
            oro_inversion=datos.oro_inversion,
            base_total=totales.base_total,
            cuota_total=totales.cuota_total,
            importe_total=totales.importe_total,
            emitido_por_id=actor.id,
            clave_idempotencia=clave,
            operacion_idempotencia=operacion.value,
            origen_idempotencia=origen_id,
        ),
        [
            LineaPresupuesto(
                orden=i,
                unidades=linea.unidades,
                descripcion=linea.descripcion.strip(),
                precio_unitario=linea.precio_unitario,
                tipo_iva=tipo_iva,
                importe=line_amount(linea.unidades, linea.precio_unitario),
            )
            for i, linea in enumerate(datos.lineas, start=1)
        ],
        [
            DesglosePresupuesto(orden=orden, tipo_iva=d.tipo_iva, base=d.base, cuota=d.cuota)
            for orden, d in enumerate(totales.desglose, start=1)
        ],
    )
    await record_event(
        db,
        TipoEvento.PRESUPUESTO_EMITIDO,
        origen=origen,
        actor=actor,
        cliente_id=cliente.id,
        detalle={
            "presupuesto_id": presupuesto.id,
            "num_serie": presupuesto.num_serie,
            "fecha": presupuesto.fecha,
            "valido_hasta": presupuesto.valido_hasta,
            "importe_total": presupuesto.importe_total,
            **(
                {"borrador_id": origen_id}
                if operacion is OperacionIdempotente.EMITIR_BORRADOR
                else {}
            ),
        },
    )
    # Sin datos personales ni importes (FR-035).
    logger.info("Presupuesto %s emitido (%s)", presupuesto.num_serie, operacion.value)
    return presupuesto, True


# --------------------------------------------------------------------------- consulta


@dataclass(frozen=True, slots=True)
class DetallePresupuesto:
    presupuesto: Presupuesto
    estado: EstadoPresupuesto
    sustituye_a: Presupuesto | None
    vigente_actual: Presupuesto | None
    cierre: CierrePresupuesto | None
    presupuesto_nuevo: Presupuesto | None
    factura: Factura | None
    factura_vigente: Factura | None
    borrador_factura_id: uuid.UUID | None


async def _vigente_actual(db: AsyncSession, cierre: CierrePresupuesto | None) -> Presupuesto | None:
    """El último presupuesto de la cadena de sustituciones (SUSTITUIDO por…, R-10)."""
    visitados: set[uuid.UUID] = set()
    siguiente: Presupuesto | None = None
    while (
        cierre is not None
        and cierre.presupuesto_nuevo_id is not None
        and cierre.presupuesto_nuevo_id not in visitados
    ):
        visitados.add(cierre.presupuesto_nuevo_id)
        siguiente = await repo.get(db, cierre.presupuesto_nuevo_id)
        cierre = await cierres.get_by_presupuesto(db, cierre.presupuesto_nuevo_id)
    return siguiente


async def _factura_vigente(db: AsyncSession, factura: Factura | None) -> Factura | None:
    """Si la factura de la conversión se corrigió después, la vigente que la sustituye."""
    if factura is None:
        return None
    detalle = await facturas_servicio.get_factura(db, factura.id)
    return detalle.vigente_actual


async def get_presupuesto(db: AsyncSession, presupuesto_id: uuid.UUID) -> DetallePresupuesto:
    presupuesto = await repo.get(db, presupuesto_id)
    if presupuesto is None:
        raise NoEncontrado(NO_EXISTE)
    guardado = await repo.estado(db, presupuesto.id)
    cierre = await cierres.get_by_presupuesto(db, presupuesto.id)
    origen = await cierres.get_by_presupuesto_nuevo(db, presupuesto.id)
    factura = (
        await facturas_repo.get(db, cierre.factura_id)
        if cierre is not None and cierre.factura_id
        else None
    )
    nuevo = (
        await repo.get(db, cierre.presupuesto_nuevo_id)
        if cierre is not None and cierre.presupuesto_nuevo_id
        else None
    )
    borrador = await borradores_factura.get_by_presupuesto(db, presupuesto.id)
    return DetallePresupuesto(
        presupuesto=presupuesto,
        estado=estado_visible(guardado, presupuesto.valido_hasta, hoy()),
        sustituye_a=await repo.get(db, origen.presupuesto_id) if origen is not None else None,
        vigente_actual=await _vigente_actual(db, cierre),
        cierre=cierre,
        presupuesto_nuevo=nuevo,
        factura=factura,
        factura_vigente=await _factura_vigente(db, factura),
        borrador_factura_id=borrador.id if borrador is not None else None,
    )


# ---------------------------------------------------------------------------- cierres


async def no_modificable(db: AsyncSession, presupuesto_id: uuid.UUID) -> PresupuestoNoModificable:
    """El 409 con el estado visible de ahora y, si está en facturación, su borrador (R-6)."""
    presupuesto = await repo.get(db, presupuesto_id)
    if presupuesto is None:
        return PresupuestoNoModificable("pendiente")
    guardado = await repo.estado(db, presupuesto_id)
    borrador = await borradores_factura.get_by_presupuesto(db, presupuesto_id)
    return PresupuestoNoModificable(
        estado_visible(guardado, presupuesto.valido_hasta, hoy()).value,
        borrador.id if borrador is not None else None,
    )


async def guard_presupuesto[T](
    db: AsyncSession, presupuesto_id: uuid.UUID, escribir: Callable[[], Awaitable[T]]
) -> T:
    """Escribe en un punto de guardado y traduce las barreras de la BD (R-6) a un 409.

    Solo salta quien pierde una carrera: la unicidad del cierre o del borrador vinculado, o uno de
    los dos triggers. Se identifica por el nombre de la restricción, nunca por el mensaje, y la
    respuesta no lleva detalles técnicos. Cualquier otra violación sigue su camino.
    """
    try:
        async with db.begin_nested():
            return await escribir()
    except IntegrityError as exc:
        if restriccion(exc) not in RESTRICCIONES_PRESUPUESTO:
            raise
        raise await no_modificable(db, presupuesto_id) from exc


def check_fecha_conversion(borrador: BorradorFactura, fecha_expedicion: date) -> None:
    """La factura de una conversión no puede ser anterior a su presupuesto (FR-019)."""
    presupuesto = borrador.presupuesto
    if presupuesto is not None and fecha_expedicion < presupuesto.fecha:
        raise FechaExpedicionNoValida(
            f"La fecha de expedición no puede ser anterior a la del presupuesto "
            f"{presupuesto.num_serie} ({presupuesto.fecha:%d/%m/%Y})."
        )


async def close_conversion(
    db: AsyncSession,
    borrador: BorradorFactura,
    factura: Factura,
    *,
    actor: Usuario,
    origen: Origen,
) -> CierrePresupuesto:
    """Cierre `conversion` del presupuesto del borrador, en la transacción de la emisión (R-5)."""
    presupuesto = borrador.presupuesto
    if presupuesto is None:
        msg = f"El borrador {borrador.id} no procede de ningún presupuesto"
        raise ValueError(msg)
    cierre = await guard_presupuesto(
        db,
        presupuesto.id,
        lambda: cierres.insert(
            db,
            CierrePresupuesto(
                presupuesto_id=presupuesto.id,
                tipo=TipoCierrePresupuesto.CONVERSION.value,
                factura_id=factura.id,
                creado_por_id=actor.id,
            ),
        ),
    )
    await record_event(
        db,
        TipoEvento.PRESUPUESTO_CONVERTIDO,
        origen=origen,
        actor=actor,
        cliente_id=factura.cliente_id,
        detalle={
            "presupuesto_id": presupuesto.id,
            "num_serie": presupuesto.num_serie,
            "factura_id": factura.id,
            "factura_num_serie": factura.num_serie,
        },
    )
    # Sin datos personales ni importes (FR-035).
    logger.info("Presupuesto %s convertido en %s", presupuesto.num_serie, factura.num_serie)
    return cierre


# ------------------------------------------------------------- modificar y anular (US4)

SIN_CAMBIOS: Final = (
    "El presupuesto nuevo sería idéntico al original: cambia algún dato además de la fecha."
)


async def _check_abierto(db: AsyncSession, presupuesto: Presupuesto) -> None:
    """Pendiente o caducado y sin borrador vinculado (FR-017, FR-021).

    Orden de lectura de R-6: primero el borrador y después el cierre. Si la emisión del borrador
    termina entre las dos lecturas, la segunda ve su cierre.
    """
    borrador = await borradores_factura.get_by_presupuesto(db, presupuesto.id)
    if borrador is not None:
        raise PresupuestoNoModificable(EstadoPresupuesto.EN_FACTURACION.value, borrador.id)
    if await cierres.get_by_presupuesto(db, presupuesto.id) is not None:
        raise await no_modificable(db, presupuesto.id)


def _sin_cambios(
    original: Presupuesto, cliente: Cliente, datos: DatosPresupuesto, tipo_iva: Decimal | None
) -> bool:
    """¿Sería el nuevo idéntico al original? La regla de `emision._sin_cambios` de 002 con la
    validez añadida. La fecha no cuenta: el modal propone la de hoy (R-7, Clarifications)."""
    destinatario = copia_destinatario(cliente)
    mismo_cliente = original.cliente_id == cliente.id and all(
        getattr(original, campo) == valor for campo, valor in destinatario.items()
    )
    actuales = [
        (linea.unidades, linea.descripcion, linea.precio_unitario)
        for linea in sorted(original.lineas, key=lambda linea: linea.orden)
    ]
    nuevas = [
        (
            linea.unidades.quantize(Decimal("0.01")),
            linea.descripcion.strip(),
            linea.precio_unitario.quantize(Decimal("0.01")),
        )
        for linea in datos.lineas
    ]
    tipo_original = None if original.oro_inversion else original.lineas[0].tipo_iva
    return (
        mismo_cliente
        and actuales == nuevas
        and original.oro_inversion == datos.oro_inversion
        and tipo_original == tipo_iva
        and original.valido_hasta == datos.valido_hasta
    )


async def modify_presupuesto(
    db: AsyncSession,
    presupuesto_id: uuid.UUID,
    datos: DatosPresupuesto,
    *,
    motivo_texto: str,
    actor: Usuario,
    origen: Origen,
    clave: uuid.UUID,
) -> tuple[Presupuesto, bool]:
    """Sustituye el presupuesto por uno nuevo con el siguiente número PRE (FR-015; R-7).

    Devuelve el nuevo y si se ha creado ahora. La clave se busca antes de mirar el estado: tras
    la primera petición el original ya está sustituido, y una repetición debe devolver lo mismo.
    """
    await repo.lock_presupuestos(db)
    operacion = OperacionIdempotente.MODIFICAR
    if previo := await find_previous_presupuesto(db, clave, operacion, presupuesto_id):
        return previo, False
    original = await repo.get(db, presupuesto_id)
    if original is None:
        raise NoEncontrado(NO_EXISTE)
    await _check_abierto(db, original)
    check_fechas(datos.fecha, datos.valido_hasta)
    check_lineas(datos.lineas, sin_lineas=SIN_LINEAS)
    cliente = await cliente_activo(db, datos.cliente_id)
    config = await configuracion_repo.get(db)
    if _sin_cambios(
        original, cliente, datos, None if datos.oro_inversion else config.iva_por_defecto
    ):
        raise SinCambios(SIN_CAMBIOS)
    nuevo, _ = await emit_presupuesto(
        db,
        datos,
        actor=actor,
        origen=origen,
        clave=clave,
        operacion=operacion,
        origen_id=original.id,
        bloqueado=True,
    )
    motivo = motivo_texto.strip()
    await guard_presupuesto(
        db,
        original.id,
        lambda: cierres.insert(
            db,
            CierrePresupuesto(
                presupuesto_id=original.id,
                tipo=TipoCierrePresupuesto.SUSTITUCION.value,
                motivo_texto=motivo,
                presupuesto_nuevo_id=nuevo.id,
                creado_por_id=actor.id,
            ),
        ),
    )
    await record_event(
        db,
        TipoEvento.PRESUPUESTO_MODIFICADO,
        origen=origen,
        actor=actor,
        cliente_id=nuevo.cliente_id,
        detalle={
            "presupuesto_id": original.id,
            "num_serie": original.num_serie,
            "presupuesto_nuevo_id": nuevo.id,
            "num_serie_nuevo": nuevo.num_serie,
            "motivo_texto": motivo,
        },
    )
    logger.info("Presupuesto %s sustituido por %s", original.num_serie, nuevo.num_serie)
    return nuevo, True


async def annul_presupuesto(
    db: AsyncSession,
    presupuesto_id: uuid.UUID,
    *,
    motivo_texto: str,
    actor: Usuario,
    origen: Origen,
    clave: uuid.UUID,
) -> tuple[Presupuesto, bool]:
    """Anula el presupuesto con un motivo (FR-016; R-7). No emite nada ni consume números."""
    await repo.lock_presupuestos(db)
    operacion = OperacionIdempotente.ANULAR
    if previo := await find_previous_presupuesto(db, clave, operacion, presupuesto_id):
        return previo, False
    presupuesto = await repo.get(db, presupuesto_id)
    if presupuesto is None:
        raise NoEncontrado(NO_EXISTE)
    await _check_abierto(db, presupuesto)
    motivo = motivo_texto.strip()
    await guard_presupuesto(
        db,
        presupuesto.id,
        lambda: cierres.insert(
            db,
            CierrePresupuesto(
                presupuesto_id=presupuesto.id,
                tipo=TipoCierrePresupuesto.ANULACION.value,
                motivo_texto=motivo,
                creado_por_id=actor.id,
                clave_idempotencia=clave,
                operacion_idempotencia=operacion.value,
            ),
        ),
    )
    await record_event(
        db,
        TipoEvento.PRESUPUESTO_ANULADO,
        origen=origen,
        actor=actor,
        cliente_id=presupuesto.cliente_id,
        detalle={
            "presupuesto_id": presupuesto.id,
            "num_serie": presupuesto.num_serie,
            "motivo_texto": motivo,
        },
    )
    logger.info("Presupuesto %s anulado", presupuesto.num_serie)
    return presupuesto, True


# ---------------------------------------------------------------------------- listado


@dataclass(frozen=True, slots=True)
class FiltrosPresupuestos:
    q: str | None = None
    # Por defecto, el año en curso en hora de Madrid (FR-025); «todos» quita el filtro.
    anio: int | Literal["todos"] | None = None
    mes: int | None = None
    orden: str = "recientes"
    pagina: int = 1
    tamano: int = 25


@dataclass(frozen=True, slots=True)
class FilaPresupuesto:
    fila: repo.FilaListado
    estado: EstadoPresupuesto


def estado_de_fila(fila: repo.FilaListado, fecha_hoy: date) -> EstadoPresupuesto:
    if fila.tipo_documento == "borrador":
        return EstadoPresupuesto.BORRADOR
    return estado_visible(fila.estado, fila.valido_hasta, fecha_hoy)


async def list_presupuestos(
    db: AsyncSession, filtros: FiltrosPresupuestos
) -> tuple[list[FilaPresupuesto], int]:
    fecha_hoy = hoy()
    anio = fecha_hoy.year if filtros.anio is None else filtros.anio
    filas, total = await repo.list_presupuestos(
        db,
        q=filtros.q,
        anio=None if anio == "todos" else anio,
        mes=filtros.mes,
        orden=filtros.orden,
        pagina=filtros.pagina,
        tamano=filtros.tamano,
    )
    return [FilaPresupuesto(f, estado_de_fila(f, fecha_hoy)) for f in filas], total


@dataclass(frozen=True, slots=True)
class ParametrosPresupuesto:
    iva_por_defecto: Decimal
    faltan: list[str]
    proximo_numero: str
    hoy: date
    fecha_minima: date
    validez_dias: int


async def get_parametros(db: AsyncSession) -> ParametrosPresupuesto:
    config = await configuracion_repo.get(db)
    fecha = hoy()
    ultimo = await contadores.last_used(db, Serie.PRESUPUESTO, fecha.year)
    return ParametrosPresupuesto(
        iva_por_defecto=config.iva_por_defecto,
        faltan=missing_for_presupuesto(config),
        proximo_numero=format_num_serie(Serie.PRESUPUESTO, fecha.year, ultimo + 1),
        hoy=fecha,
        fecha_minima=FECHA_MINIMA_EXPEDICION,
        validez_dias=config.validez_presupuesto_dias,
    )
