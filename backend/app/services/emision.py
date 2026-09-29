"""Emisión de facturas: el único punto que expide facturas y genera registros (research R-9).

Todo en UNA transacción (FR-021; F-8, art. 9: registro «simultáneo» a la expedición):

1. Cerrojo de la cadena (R-6) y búsqueda de la clave de idempotencia (R-18).
2. Comprobación previa de la cadena (F-10, art. 7.i).
3. Validaciones: configuración (FR-004), cliente (FR-017), fecha (FR-018), líneas (FR-012) e IVA
   (F-3 §15.1).
4. Cálculo con la política única de `domain/importes.py` (R-10).
5. Número con el contador bajo `SELECT … FOR UPDATE` (R-7).
6. Factura con las copias del emisor y del destinatario (FR-016), líneas, desglose y registro de
   alta con su huella (R-3).
7. Auditoría. En los logs, solo el número y el tipo de operación (FR-051).

Si cualquier paso falla, la transacción se deshace entera: no queda número consumido.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Final

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import (
    CampoError,
    ClienteNoFacturable,
    DatosNoValidos,
    EmisionNoDisponible,
    FacturaNoModificable,
    FechaExpedicionNoValida,
    IdempotenciaConflicto,
    NoEncontrado,
    SinCambios,
    TipoIvaNoAdmitido,
)
from app.core.http import Origen
from app.core.tiempo import hoy
from app.domain.huella import format_date
from app.domain.importes import (
    MAX_LINEAS,
    MAX_PRECIO,
    MAX_UNIDADES,
    ImporteFueraDeRango,
    LineaCalculo,
    compute_totals,
    is_rate_allowed,
    line_amount,
)
from app.domain.numeracion import format_num_serie
from app.domain.registro import CALIFICACION_SUJETA_NO_EXENTA, build_descripcion_operacion
from app.domain.tipos import (
    CausaRectificacion,
    EstadoFactura,
    MotivoModificacion,
    OperacionIdempotente,
    Serie,
    TipoCorreccion,
    TipoEvento,
    TipoFactura,
    TipoRectificativa,
)
from app.models.cliente import Cliente
from app.models.configuracion_facturacion import ConfiguracionFacturacion
from app.models.correccion_factura import CorreccionFactura
from app.models.factura import DesgloseFactura, Factura, LineaFactura
from app.models.usuario import Usuario
from app.repositories import clientes as clientes_repo
from app.repositories import configuracion_facturacion as configuracion_repo
from app.repositories import contadores, correcciones, facturas, registros
from app.services import cadena
from app.services.auditoria import record_event
from app.services.configuracion_facturacion import missing_for_emission

logger = logging.getLogger(__name__)

FECHA_MINIMA: Final = date(2024, 10, 28)  # F-3 §3.1.3.1: entrada en vigor de la Orden


@dataclass(frozen=True, slots=True)
class DatosLinea:
    unidades: Decimal
    descripcion: str
    precio_unitario: Decimal


@dataclass(frozen=True, slots=True)
class DatosFactura:
    fecha_expedicion: date
    cliente_id: uuid.UUID
    lineas: tuple[DatosLinea, ...]


# ------------------------------------------------------------------------ validaciones


def emissible_config(config: ConfiguracionFacturacion) -> ConfiguracionFacturacion:
    if faltan := missing_for_emission(config):
        raise EmisionNoDisponible(extra={"faltan": faltan})
    return config


async def billable_cliente(db: AsyncSession, cliente_id: uuid.UUID) -> Cliente:
    cliente = await clientes_repo.get(db, cliente_id)
    if cliente is None:
        raise DatosNoValidos(errores=[CampoError("cliente_id", "El cliente no existe.")])
    faltan = [] if cliente.activo else ["activo"]
    faltan += [c for c in ("direccion", "codigo_postal", "localidad") if not getattr(cliente, c)]
    if faltan:
        detalle = (
            "El cliente está desactivado."
            if not cliente.activo
            else "Al cliente le falta el domicilio completo (dirección, código postal y localidad)."
        )
        raise ClienteNoFacturable(detalle, extra={"faltan": faltan, "cliente_id": str(cliente.id)})
    if "provincia" in inspect(cliente).unloaded:
        # Cliente dado de alta en esta misma sesión: la provincia se copia a la factura (FR-016)
        # y en asíncrono no se puede cargar de forma perezosa.
        await db.refresh(cliente, ["provincia"])
    return cliente


async def check_fecha_expedicion(db: AsyncSession, fecha: date, serie: Serie) -> None:
    """FR-018: no futura; del año en curso o del anterior; no antes del 28/10/2024 (F-3) ni de la
    última factura emitida de la serie en ese año (numeración correlativa, F-6 art. 6.1.a)."""
    hoy_madrid = hoy()
    if fecha > hoy_madrid:
        raise FechaExpedicionNoValida("La fecha de expedición no puede ser posterior a hoy.")
    if fecha.year < hoy_madrid.year - 1 or fecha < FECHA_MINIMA:
        raise FechaExpedicionNoValida(
            "La fecha de expedición debe ser del año en curso o del anterior."
        )
    ultima = await facturas.last_fecha_in_serie(db, serie, fecha.year)
    if ultima is not None and fecha < ultima:
        raise FechaExpedicionNoValida(
            "La fecha no puede ser anterior a la de la última factura de la serie "
            f"({format_date(ultima)})."
        )


def check_lineas(lineas: tuple[DatosLinea, ...], *, permitir_vacio: bool = False) -> None:
    errores: list[CampoError] = []
    if not lineas and not permitir_vacio:
        errores.append(CampoError("lineas", "La factura debe tener al menos una línea."))
    if len(lineas) > MAX_LINEAS:
        errores.append(CampoError("lineas", f"Como máximo {MAX_LINEAS} líneas."))
    for i, linea in enumerate(lineas):
        if not linea.descripcion.strip():
            errores.append(CampoError(f"lineas.{i}.descripcion", "Campo obligatorio."))
        if linea.unidades > MAX_UNIDADES:
            errores.append(CampoError(f"lineas.{i}.unidades", "Demasiadas unidades."))
        if linea.precio_unitario > MAX_PRECIO:
            errores.append(CampoError(f"lineas.{i}.precio_unitario", "Precio demasiado alto."))
    if errores:
        raise DatosNoValidos(errores=errores)


# ------------------------------------------------------------------------ idempotencia


async def find_previous(
    db: AsyncSession,
    clave: uuid.UUID,
    operacion: OperacionIdempotente,
    origen_id: uuid.UUID | None,
) -> Factura | None:
    """Factura ya creada con esta clave para esta misma operación y origen (R-18), o `None`.

    Una clave usada para otra operación o sobre otro documento es un conflicto: nunca se devuelve
    el resultado de otra operación.
    """
    previa = await facturas.get_by_idempotency_key(db, clave)
    if previa is not None:
        if (
            previa.operacion_idempotencia != operacion.value
            or previa.origen_idempotencia != origen_id
        ):
            raise IdempotenciaConflicto
        return previa
    if await correcciones.get_by_idempotency_key(db, clave) is not None:
        raise IdempotenciaConflicto
    return None


# --------------------------------------------------------------------------- creación


def _destinatario(cliente: Cliente) -> dict[str, str | None]:
    provincia = (
        cliente.provincia.nombre_visible
        if cliente.provincia is not None
        else cliente.provincia_texto
    )
    return {
        "dest_nombre": cliente.nombre,
        "dest_identificacion_pais": cliente.identificacion_pais,
        "dest_identificacion_tipo": cliente.identificacion_tipo,
        "dest_identificacion_numero": cliente.identificacion_numero,
        "dest_direccion": cliente.direccion,
        "dest_codigo_postal": cliente.codigo_postal,
        "dest_localidad": cliente.localidad,
        "dest_provincia": provincia,
        "dest_pais": cliente.pais_residencia,
    }


@dataclass(frozen=True, slots=True)
class Rectificacion:
    """Datos de una rectificativa por sustitución (R-4): factura rectificada y causa."""

    rectificada: Factura
    causa: CausaRectificacion


async def create_factura(
    db: AsyncSession,
    *,
    config: ConfiguracionFacturacion,
    cliente: Cliente,
    fecha_expedicion: date,
    fecha_operacion: date | None,
    lineas: tuple[DatosLinea, ...],
    actor: Usuario,
    clave: uuid.UUID,
    operacion: OperacionIdempotente,
    origen_id: uuid.UUID | None,
    rectificacion: Rectificacion | None = None,
) -> Factura:
    """Expide una factura y su registro de alta. Exige el cerrojo de la cadena ya tomado."""
    serie = Serie.RECTIFICATIVA if rectificacion else Serie.ORDINARIA
    await check_fecha_expedicion(db, fecha_expedicion, serie)
    check_lineas(lineas, permitir_vacio=rectificacion is not None)
    tipo_iva = config.iva_por_defecto
    if not is_rate_allowed(tipo_iva, fecha_operacion or fecha_expedicion):
        raise TipoIvaNoAdmitido
    try:
        totales = compute_totals(
            [LineaCalculo(linea.unidades, linea.precio_unitario, tipo_iva) for linea in lineas],
            tipo_iva_por_defecto=tipo_iva,
        )
    except ImporteFueraDeRango as exc:
        raise DatosNoValidos(errores=[CampoError("lineas", str(exc))]) from exc
    if rectificacion is None and totales.importe_total <= 0:
        raise DatosNoValidos(
            errores=[CampoError("lineas", "El total de la factura debe ser mayor que cero.")]
        )

    anio = fecha_expedicion.year
    numero = await contadores.assign_numero(db, serie, anio)
    rectificada = rectificacion.rectificada if rectificacion else None
    tipo_factura = rectificacion.causa.tipo_factura if rectificacion else TipoFactura.COMPLETA
    factura = Factura(
        serie=serie.value,
        anio=anio,
        numero=numero,
        num_serie=format_num_serie(serie, anio, numero),
        tipo_factura=tipo_factura.value,
        tipo_rectificativa=TipoRectificativa.SUSTITUCION.value if rectificacion else None,
        causa_rectificacion=rectificacion.causa.value if rectificacion else None,
        factura_rectificada_id=rectificada.id if rectificada else None,
        base_rectificada=rectificada.base_total if rectificada else None,
        cuota_rectificada=rectificada.cuota_total if rectificada else None,
        fecha_expedicion=fecha_expedicion,
        fecha_operacion=fecha_operacion,
        descripcion_operacion=build_descripcion_operacion(
            [linea.descripcion for linea in lineas],
            num_rectificada=rectificada.num_serie if rectificada else None,
        ),
        emisor_nif=config.emisor_nif,
        emisor_nombre=config.emisor_nombre,
        emisor_direccion=config.emisor_direccion,
        emisor_codigo_postal=config.emisor_codigo_postal,
        emisor_localidad=config.emisor_localidad,
        emisor_provincia=config.emisor_provincia.nombre_visible
        if config.emisor_provincia
        else None,
        cliente_id=cliente.id,
        **_destinatario(cliente),
        clave_regimen=config.clave_regimen,
        modalidad=config.modalidad,
        base_total=totales.base_total,
        cuota_total=totales.cuota_total,
        importe_total=totales.importe_total,
        emitida_por_id=actor.id,
        clave_idempotencia=clave,
        operacion_idempotencia=operacion.value,
        origen_idempotencia=origen_id,
    )
    factura = await facturas.insert_emitida(
        db,
        factura,
        [
            LineaFactura(
                orden=i,
                unidades=linea.unidades,
                descripcion=linea.descripcion.strip(),
                precio_unitario=linea.precio_unitario,
                tipo_iva=tipo_iva,
                importe=line_amount(linea.unidades, linea.precio_unitario),
            )
            for i, linea in enumerate(lineas, start=1)
        ],
        [
            DesgloseFactura(
                tipo_iva=d.tipo_iva,
                clave_regimen=config.clave_regimen,
                calificacion_operacion=CALIFICACION_SUJETA_NO_EXENTA,
                base=d.base,
                cuota=d.cuota,
            )
            for d in totales.desglose
        ],
    )
    await cadena.create_registro_alta(db, factura, rectificada=rectificada)
    logger.info("Factura %s expedida (%s)", factura.num_serie, operacion.value)
    return factura


async def emit_factura(
    db: AsyncSession,
    datos: DatosFactura,
    *,
    actor: Usuario,
    origen: Origen,
    clave: uuid.UUID,
    operacion: OperacionIdempotente = OperacionIdempotente.EMITIR,
    origen_id: uuid.UUID | None = None,
    cadena_bloqueada: bool = False,
) -> tuple[Factura, bool]:
    """Emite una factura ordinaria. Devuelve la factura y si se ha creado ahora (`False` si es la
    repetición de una clave ya usada, R-18).

    `cadena_bloqueada`: quien llama ya tomó el cerrojo y comprobó la clave (emisión de borrador).
    """
    if not cadena_bloqueada:
        await registros.lock_chain(db)
        if previa := await find_previous(db, clave, operacion, origen_id):
            return previa, False
    await cadena.verify_tail(db, origen=origen, actor=actor)
    config = emissible_config(await configuracion_repo.get(db))
    cliente = await billable_cliente(db, datos.cliente_id)
    factura = await create_factura(
        db,
        config=config,
        cliente=cliente,
        fecha_expedicion=datos.fecha_expedicion,
        fecha_operacion=None,
        lineas=datos.lineas,
        actor=actor,
        clave=clave,
        operacion=operacion,
        origen_id=origen_id,
    )
    await record_event(
        db,
        TipoEvento.FACTURA_EMITIDA,
        origen=origen,
        actor=actor,
        cliente_id=cliente.id,
        detalle={
            "factura_id": factura.id,
            "num_serie": factura.num_serie,
            "fecha_expedicion": factura.fecha_expedicion,
            "importe_total": factura.importe_total,
            **(
                {"borrador_id": origen_id}
                if operacion is OperacionIdempotente.EMITIR_BORRADOR
                else {}
            ),
        },
    )
    return factura, True


# --------------------------------------------------------------------- correcciones (US5)


@dataclass(frozen=True, slots=True)
class DatosModificacion:
    motivo: MotivoModificacion
    causa: CausaRectificacion | None
    motivo_texto: str
    cliente_id: uuid.UUID
    lineas: tuple[DatosLinea, ...]


async def find_previous_correccion(
    db: AsyncSession,
    clave: uuid.UUID,
    operacion: OperacionIdempotente,
    factura_id: uuid.UUID,
) -> CorreccionFactura | None:
    """Corrección ya hecha con esta clave sobre esta factura (R-18), o `None`.

    La clave de una modificación queda también en la factura nueva; la de otra operación o de otra
    factura es un conflicto.
    """
    previa = await correcciones.get_by_idempotency_key(db, clave)
    if previa is not None:
        if previa.operacion_idempotencia != operacion.value or previa.factura_id != factura_id:
            raise IdempotenciaConflicto
        return previa
    if await facturas.get_by_idempotency_key(db, clave) is not None:
        raise IdempotenciaConflicto
    return None


async def _vigente(db: AsyncSession, factura_id: uuid.UUID) -> Factura:
    """La factura a corregir, que debe estar vigente (R-8). El trigger `validar_correccion` lo
    vuelve a comprobar al insertar la corrección."""
    factura = await facturas.get(db, factura_id)
    if factura is None:
        raise NoEncontrado("La factura no existe.")
    if await facturas.estado(db, factura.id) is not EstadoFactura.VIGENTE:
        raise FacturaNoModificable
    return factura


def fecha_operacion_heredada(original: Factura) -> date:
    """La de la factura original: su fecha de operación o, si no la tenía, la de expedición
    (F-9; FR-018)."""
    return original.fecha_operacion or original.fecha_expedicion


def _tipo_iva_de(factura: Factura) -> Decimal:
    tipos = {linea.tipo_iva for linea in factura.lineas} or {d.tipo_iva for d in factura.desgloses}
    if len(tipos) != 1:
        msg = f"La factura {factura.num_serie} no tiene un único tipo de IVA"
        raise ValueError(msg)
    return tipos.pop()


def _sin_cambios(
    original: Factura, cliente: Cliente, lineas: tuple[DatosLinea, ...], tipo_iva: Decimal
) -> bool:
    """¿Sería la rectificativa idéntica a la vigente? Se comparan el destinatario tal como se
    copiaría, las líneas normalizadas y el tipo de IVA que se aplicaría (R-9)."""
    destinatario = _destinatario(cliente)
    mismo_destinatario = original.cliente_id == cliente.id and all(
        getattr(original, campo) == valor for campo, valor in destinatario.items()
    )
    actuales = [
        (linea.unidades, linea.descripcion, linea.precio_unitario) for linea in original.lineas
    ]
    nuevas = [
        (
            linea.unidades.quantize(Decimal("0.01")),
            linea.descripcion.strip(),
            linea.precio_unitario.quantize(Decimal("0.01")),
        )
        for linea in lineas
    ]
    return mismo_destinatario and actuales == nuevas and _tipo_iva_de(original) == tipo_iva


async def _registrar_emision(
    db: AsyncSession,
    factura: Factura,
    *,
    actor: Usuario,
    origen: Origen,
    detalle: dict[str, object],
) -> None:
    await record_event(
        db,
        TipoEvento.FACTURA_EMITIDA,
        origen=origen,
        actor=actor,
        cliente_id=factura.cliente_id,
        detalle={
            "factura_id": factura.id,
            "num_serie": factura.num_serie,
            "fecha_expedicion": factura.fecha_expedicion,
            "importe_total": factura.importe_total,
            **detalle,
        },
    )


async def anular_factura(
    db: AsyncSession,
    factura_id: uuid.UUID,
    *,
    motivo_texto: str,
    actor: Usuario,
    origen: Origen,
    clave: uuid.UUID,
) -> tuple[Factura, bool]:
    """Anulación sin reemisión (FR-025): solo el registro de anulación y la corrección.

    Si es una rectificativa, la factura que rectificaba vuelve a estar vigente por derivación, sin
    registro nuevo (FR-048). Devuelve la factura anulada y si se ha anulado ahora.
    """
    await registros.lock_chain(db)
    if previa := await find_previous_correccion(db, clave, OperacionIdempotente.ANULAR, factura_id):
        anulada = await facturas.get(db, previa.factura_id)
        if anulada is None:  # pragma: no cover — FK
            raise NoEncontrado("La factura no existe.")
        return anulada, False
    await cadena.verify_tail(db, origen=origen, actor=actor)
    factura = await _vigente(db, factura_id)
    config = await configuracion_repo.get(db)
    if config.modalidad is None:  # no ocurre: la modalidad se bloquea con el primer registro
        raise EmisionNoDisponible(extra={"faltan": missing_for_emission(config)})
    registro = await cadena.create_registro_anulacion(db, factura, modalidad=config.modalidad)
    await correcciones.insert(
        db,
        CorreccionFactura(
            factura_id=factura.id,
            tipo=TipoCorreccion.ANULACION.value,
            motivo=MotivoModificacion.NO_DEBIO_EMITIRSE.value,
            motivo_texto=motivo_texto.strip(),
            registro_anulacion_id=registro.id,
            creada_por_id=actor.id,
            clave_idempotencia=clave,
            operacion_idempotencia=OperacionIdempotente.ANULAR.value,
        ),
    )
    rectificada = (
        await facturas.get(db, factura.factura_rectificada_id)
        if factura.factura_rectificada_id
        else None
    )
    await record_event(
        db,
        TipoEvento.FACTURA_ANULADA,
        origen=origen,
        actor=actor,
        cliente_id=factura.cliente_id,
        detalle={
            "factura_id": factura.id,
            "num_serie": factura.num_serie,
            "motivo_texto": motivo_texto.strip(),
            **({"reactivada": rectificada.num_serie} if rectificada else {}),
        },
    )
    logger.info("Factura %s anulada", factura.num_serie)
    return factura, True


async def modify_factura(
    db: AsyncSession,
    factura_id: uuid.UUID,
    datos: DatosModificacion,
    *,
    actor: Usuario,
    origen: Origen,
    clave: uuid.UUID,
) -> tuple[Factura, bool]:
    """«Modificar» una factura emitida mediante la corrección que corresponde (FR-024, R-4, R-9):

    - `no_debio_emitirse`: registro de anulación de la original y factura FAC nueva con el
      siguiente número (sin cambios también: es como se corrige un número erróneo).
    - `factura_entregada`: rectificativa por sustitución REC, R1 o R4 según la causa.

    La corrección se inserta la última, con sus referencias ya conocidas. Devuelve la factura nueva
    y si se ha creado ahora.
    """
    operacion = OperacionIdempotente.MODIFICAR
    await registros.lock_chain(db)
    if previa := await find_previous_correccion(db, clave, operacion, factura_id):
        nueva = await facturas.get(db, previa.factura_nueva_id) if previa.factura_nueva_id else None
        if nueva is None:  # pragma: no cover — una modificación siempre crea factura
            raise NoEncontrado("La factura no existe.")
        return nueva, False
    await cadena.verify_tail(db, origen=origen, actor=actor)
    original = await _vigente(db, factura_id)
    reemision = datos.motivo is MotivoModificacion.NO_DEBIO_EMITIRSE
    if reemision and original.serie == Serie.RECTIFICATIVA.value:
        raise DatosNoValidos(
            errores=[
                CampoError(
                    "motivo",
                    "Una rectificativa no se reemite: anúlala y modifica después la original.",
                )
            ]
        )
    if not reemision and datos.causa is None:
        raise DatosNoValidos(errores=[CampoError("causa", "Indica la causa de la rectificación.")])
    devolucion = datos.causa is CausaRectificacion.DEVOLUCION_O_PRECIO
    if not datos.lineas and (reemision or not devolucion):
        raise DatosNoValidos(
            errores=[
                CampoError(
                    "lineas",
                    "La factura debe tener al menos una línea (sin líneas solo cabe una "
                    "devolución total).",
                )
            ]
        )
    config = emissible_config(await configuracion_repo.get(db))
    cliente = await billable_cliente(db, datos.cliente_id)
    if not reemision and _sin_cambios(original, cliente, datos.lineas, config.iva_por_defecto):
        raise SinCambios

    async def expedir(rectificacion: Rectificacion | None) -> Factura:
        # La factura nueva se expide hoy y conserva la fecha de operación de la original (FR-018).
        return await create_factura(
            db,
            config=config,
            cliente=cliente,
            fecha_expedicion=hoy(),
            fecha_operacion=fecha_operacion_heredada(original),
            lineas=datos.lineas,
            actor=actor,
            clave=clave,
            operacion=operacion,
            origen_id=original.id,
            rectificacion=rectificacion,
        )

    motivo_texto = datos.motivo_texto.strip()
    if reemision:
        registro = await cadena.create_registro_anulacion(
            db, original, modalidad=config.modalidad or ""
        )
        nueva = await expedir(None)
        correccion = CorreccionFactura(
            factura_id=original.id,
            tipo=TipoCorreccion.ANULACION_Y_REEMISION.value,
            motivo=datos.motivo.value,
            motivo_texto=motivo_texto,
            factura_nueva_id=nueva.id,
            registro_anulacion_id=registro.id,
            creada_por_id=actor.id,
            clave_idempotencia=clave,
            operacion_idempotencia=operacion.value,
        )
    else:
        causa = datos.causa or CausaRectificacion.ERROR_DATOS
        nueva = await expedir(Rectificacion(rectificada=original, causa=causa))
        correccion = CorreccionFactura(
            factura_id=original.id,
            tipo=TipoCorreccion.RECTIFICACION_SUSTITUCION.value,
            motivo=datos.motivo.value,
            motivo_texto=motivo_texto,
            factura_nueva_id=nueva.id,
            creada_por_id=actor.id,
            clave_idempotencia=clave,
            operacion_idempotencia=operacion.value,
        )
    await correcciones.insert(db, correccion)

    if reemision:
        await record_event(
            db,
            TipoEvento.FACTURA_ANULADA,
            origen=origen,
            actor=actor,
            cliente_id=original.cliente_id,
            detalle={
                "factura_id": original.id,
                "num_serie": original.num_serie,
                "motivo_texto": motivo_texto,
                "sustituida_por": nueva.num_serie,
            },
        )
        detalle_nueva: dict[str, object] = {"sustituye_a": original.num_serie}
    else:
        await record_event(
            db,
            TipoEvento.FACTURA_RECTIFICADA,
            origen=origen,
            actor=actor,
            cliente_id=original.cliente_id,
            detalle={
                "factura_id": original.id,
                "num_serie": original.num_serie,
                "causa": datos.causa,
                "motivo_texto": motivo_texto,
                "rectificativa": nueva.num_serie,
            },
        )
        detalle_nueva = {"rectifica_a": original.num_serie}
    await _registrar_emision(db, nueva, actor=actor, origen=origen, detalle=detalle_nueva)
    logger.info("Factura %s corregida con %s", original.num_serie, nueva.num_serie)
    return nueva, True
