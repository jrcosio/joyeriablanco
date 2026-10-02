"""/v1/presupuestos (005): parámetros del modal, listado, emisión y detalle (US1). El router
valida, delega en los servicios y serializa (constitución V)."""

import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.deps import CurrentSession, DbDep, OrigenDep, get_current_session
from app.api.v1.facturas import AnioListado, ClaveIdempotencia, datos_lineas
from app.domain.exenciones import MENCION_EXENCION_ORO_INVERSION
from app.domain.tipos import TipoCierrePresupuesto
from app.models.factura import Factura
from app.models.presupuesto import Presupuesto
from app.schemas.comunes import Pagina
from app.schemas.configuracion_facturacion import DatosEmisorSalida
from app.schemas.factura import (
    ClienteFacturaSalida,
    DesgloseSalida,
    FacturaReferencia,
    LineaSalida,
    TotalesSalida,
)
from app.schemas.presupuesto import (
    BorradorReferencia,
    CierrePresupuestoSalida,
    ParametrosPresupuestoSalida,
    PresupuestoEntrada,
    PresupuestoReferencia,
    PresupuestoResumenSalida,
    PresupuestoSalida,
)
from app.schemas.usuario import UsuarioReferencia
from app.services import presupuestos as servicio
from app.services.presupuestos import DetallePresupuesto

router = APIRouter(
    prefix="/presupuestos", tags=["presupuestos"], dependencies=[Depends(get_current_session)]
)

REPETICION: dict[int | str, dict[str, Any]] = {
    status.HTTP_200_OK: {
        "model": PresupuestoSalida,
        "description": "Repetición con una Idempotency-Key ya usada: el mismo resultado",
    }
}


# ------------------------------------------------------------------------ conversiones


def referencia(presupuesto: Presupuesto | None) -> PresupuestoReferencia | None:
    if presupuesto is None:
        return None
    return PresupuestoReferencia(
        id=presupuesto.id, num_serie=presupuesto.num_serie, fecha=presupuesto.fecha
    )


def _factura(factura: Factura | None) -> FacturaReferencia | None:
    return FacturaReferencia(id=factura.id, num_serie=factura.num_serie) if factura else None


def _cierre(detalle: DetallePresupuesto) -> CierrePresupuestoSalida | None:
    cierre = detalle.cierre
    if cierre is None:
        return None
    return CierrePresupuestoSalida(
        tipo=TipoCierrePresupuesto(cierre.tipo),
        motivo_texto=cierre.motivo_texto,
        creado_en=cierre.creado_en,
        creado_por=UsuarioReferencia.from_model(cierre.creado_por),
        presupuesto_nuevo=referencia(detalle.presupuesto_nuevo),
        factura=_factura(detalle.factura),
        factura_vigente=_factura(detalle.factura_vigente),
    )


def presupuesto_salida(detalle: DetallePresupuesto) -> PresupuestoSalida:
    p = detalle.presupuesto
    return PresupuestoSalida(
        id=p.id,
        num_serie=p.num_serie,
        estado=detalle.estado,
        fecha=p.fecha,
        valido_hasta=p.valido_hasta,
        emisor=DatosEmisorSalida(
            nombre=p.emisor_nombre,
            nif=p.emisor_nif,
            direccion=p.emisor_direccion,
            codigo_postal=p.emisor_codigo_postal,
            localidad=p.emisor_localidad,
            iban=p.emisor_iban,
            provincia=p.emisor_provincia,
        ),
        cliente=ClienteFacturaSalida(
            id=p.cliente_id,
            nombre=p.dest_nombre,
            identificacion_pais=p.dest_identificacion_pais,
            identificacion_tipo=p.dest_identificacion_tipo,
            identificacion_numero=p.dest_identificacion_numero,
            direccion=p.dest_direccion,
            codigo_postal=p.dest_codigo_postal,
            localidad=p.dest_localidad,
            provincia=p.dest_provincia,
            pais=p.dest_pais,
        ),
        lineas=[
            LineaSalida(
                orden=linea.orden,
                unidades=linea.unidades,
                descripcion=linea.descripcion,
                precio_unitario=linea.precio_unitario,
                tipo_iva=linea.tipo_iva,
                importe=linea.importe,
            )
            for linea in p.lineas
        ],
        totales=TotalesSalida(
            desglose=[
                DesgloseSalida(tipo_iva=d.tipo_iva, base=d.base, cuota=d.cuota) for d in p.desgloses
            ],
            base_total=p.base_total,
            cuota_total=p.cuota_total,
            importe_total=p.importe_total,
        ),
        oro_inversion=p.oro_inversion,
        mencion_exencion=MENCION_EXENCION_ORO_INVERSION if p.oro_inversion else None,
        sustituye_a=referencia(detalle.sustituye_a),
        vigente_actual=referencia(detalle.vigente_actual),
        cierre=_cierre(detalle),
        borrador_factura=BorradorReferencia(id=detalle.borrador_factura_id)
        if detalle.borrador_factura_id
        else None,
        emitido_en=p.emitido_en,
        emitido_por=UsuarioReferencia.from_model(p.emitido_por),
    )


# --------------------------------------------------------------------------- rutas


# Declarada antes de `/{presupuesto_id}`: si no, «parametros» se tomaría por un identificador.
@router.get("/parametros")
async def obtener_parametros(db: DbDep) -> ParametrosPresupuestoSalida:
    parametros = await servicio.get_parametros(db)
    return ParametrosPresupuestoSalida(
        iva_por_defecto=parametros.iva_por_defecto,
        emision_posible=not parametros.faltan,
        faltan=parametros.faltan,
        proximo_numero=parametros.proximo_numero,
        hoy=parametros.hoy,
        fecha_minima=parametros.fecha_minima,
        validez_dias=parametros.validez_dias,
        mencion_exencion_oro_inversion=MENCION_EXENCION_ORO_INVERSION,
    )


@router.get("")
async def listar_presupuestos(
    db: DbDep,
    q: Annotated[str | None, Query(max_length=100)] = None,
    anio: Annotated[AnioListado | None, Query(description="Por defecto, el año en curso")] = None,
    mes: Annotated[int | None, Query(ge=1, le=12)] = None,
    orden: Literal["recientes", "antiguas", "total_desc", "total_asc"] = "recientes",
    pagina: Annotated[int, Query(ge=1)] = 1,
    tamano: Annotated[int, Query(ge=1, le=100)] = 25,
) -> Pagina[PresupuestoResumenSalida]:
    filas, total = await servicio.list_presupuestos(
        db,
        servicio.FiltrosPresupuestos(
            q=q, anio=anio, mes=mes, orden=orden, pagina=pagina, tamano=tamano
        ),
    )
    return Pagina[PresupuestoResumenSalida](
        elementos=[
            PresupuestoResumenSalida(
                tipo_documento="borrador" if f.fila.tipo_documento == "borrador" else "presupuesto",
                id=f.fila.id,
                num_serie=f.fila.num_serie,
                fecha=f.fila.fecha,
                valido_hasta=f.fila.valido_hasta,
                cliente_nombre=f.fila.cliente_nombre,
                identificacion=f.fila.identificacion,
                base=f.fila.base,
                cuota=f.fila.cuota,
                total=f.fila.total,
                estado=f.estado,
                oro_inversion=f.fila.oro_inversion,
            )
            for f in filas
        ],
        total=total,
        pagina=pagina,
        tamano=tamano,
    )


@router.post("", status_code=status.HTTP_201_CREATED, responses=REPETICION)
async def emitir_presupuesto(
    datos: PresupuestoEntrada,
    clave: ClaveIdempotencia,
    sesion: CurrentSession,
    db: DbDep,
    origen: OrigenDep,
    response: Response,
) -> PresupuestoSalida:
    presupuesto, creado = await servicio.emit_presupuesto(
        db,
        servicio.DatosPresupuesto(
            fecha=datos.fecha,
            valido_hasta=datos.valido_hasta,
            cliente_id=datos.cliente_id,
            lineas=datos_lineas(datos.lineas),
            oro_inversion=datos.oro_inversion,
        ),
        actor=sesion.usuario,
        origen=origen,
        clave=clave,
    )
    if not creado:
        response.status_code = status.HTTP_200_OK
    return presupuesto_salida(await servicio.get_presupuesto(db, presupuesto.id))


@router.get("/{presupuesto_id}")
async def obtener_presupuesto(presupuesto_id: uuid.UUID, db: DbDep) -> PresupuestoSalida:
    return presupuesto_salida(await servicio.get_presupuesto(db, presupuesto_id))
