"""/v1/facturas: parámetros del modal (US1), emisión y detalle (US2), listado (US3) y
correcciones (US5). El router valida, delega en los servicios y serializa (constitución V)."""

import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Header, Query, Response, status
from pydantic import Field

from app.api.deps import CurrentSession, DbDep, OrigenDep, get_current_session
from app.domain.tipos import CausaRectificacion, MotivoModificacion, TipoCorreccion, TipoFactura
from app.models.factura import Factura
from app.schemas.comunes import Pagina
from app.schemas.configuracion_facturacion import DatosEmisorSalida, ParametrosFacturacionSalida
from app.schemas.factura import (
    ClienteFacturaSalida,
    CorreccionSalida,
    DesgloseSalida,
    FacturaEntrada,
    FacturaReferencia,
    FacturaResumenSalida,
    FacturaSalida,
    LineaEntrada,
    LineaSalida,
    RectificaA,
    RegistroResumen,
    TotalesSalida,
)
from app.schemas.usuario import UsuarioReferencia
from app.services import configuracion_facturacion, emision
from app.services import facturas as servicio
from app.services.facturas import CorreccionVista, DetalleFactura

router = APIRouter(
    prefix="/facturas", tags=["facturas"], dependencies=[Depends(get_current_session)]
)

ClaveIdempotencia = Annotated[
    uuid.UUID,
    Header(
        alias="Idempotency-Key",
        description="Clave de la operación; se reutiliza en los reintentos (FR-047, R-18)",
    ),
]
REPETICION: dict[int | str, dict[str, Any]] = {
    status.HTTP_200_OK: {
        "model": FacturaSalida,
        "description": "Repetición con una Idempotency-Key ya usada: el mismo resultado",
    }
}


# ------------------------------------------------------------------------ conversiones


def datos_lineas(lineas: list[LineaEntrada]) -> tuple[emision.DatosLinea, ...]:
    return tuple(
        emision.DatosLinea(
            unidades=linea.unidades,
            descripcion=linea.descripcion,
            precio_unitario=linea.precio_unitario,
        )
        for linea in lineas
    )


def _referencia(factura: Factura | None) -> FacturaReferencia | None:
    return FacturaReferencia(id=factura.id, num_serie=factura.num_serie) if factura else None


def _correccion(vista: CorreccionVista) -> CorreccionSalida:
    c = vista.correccion
    return CorreccionSalida(
        tipo=TipoCorreccion(c.tipo),
        motivo=MotivoModificacion(c.motivo),
        motivo_texto=c.motivo_texto,
        creada_en=c.creada_en,
        creada_por=UsuarioReferencia.from_model(c.creada_por),
        factura_nueva=_referencia(vista.factura_nueva),
        en_vigor=vista.en_vigor,
    )


def _rectifica_a(detalle: DetalleFactura) -> RectificaA | None:
    f = detalle.factura
    rectificada = _referencia(detalle.rectifica_a)
    if rectificada is None:
        return None
    if f.base_rectificada is None or f.cuota_rectificada is None or not f.causa_rectificacion:
        msg = f"Rectificativa {f.num_serie} sin importes rectificados"
        raise ValueError(msg)
    return RectificaA(
        factura=rectificada,
        base_rectificada=f.base_rectificada,
        cuota_rectificada=f.cuota_rectificada,
        causa=CausaRectificacion(f.causa_rectificacion),
    )


def factura_salida(detalle: DetalleFactura) -> FacturaSalida:
    f = detalle.factura
    return FacturaSalida(
        id=f.id,
        num_serie=f.num_serie,
        tipo_factura=TipoFactura(f.tipo_factura),
        tipo_rectificativa=f.tipo_rectificativa,
        estado=detalle.estado,
        fecha_expedicion=f.fecha_expedicion,
        fecha_operacion=f.fecha_operacion,
        emisor=DatosEmisorSalida(
            nombre=f.emisor_nombre,
            nif=f.emisor_nif,
            direccion=f.emisor_direccion,
            codigo_postal=f.emisor_codigo_postal,
            localidad=f.emisor_localidad,
            provincia=f.emisor_provincia,
        ),
        cliente=ClienteFacturaSalida(
            id=f.cliente_id,
            nombre=f.dest_nombre,
            identificacion_pais=f.dest_identificacion_pais,
            identificacion_tipo=f.dest_identificacion_tipo,
            identificacion_numero=f.dest_identificacion_numero,
            direccion=f.dest_direccion,
            codigo_postal=f.dest_codigo_postal,
            localidad=f.dest_localidad,
            provincia=f.dest_provincia,
            pais=f.dest_pais,
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
            for linea in f.lineas
        ],
        totales=TotalesSalida(
            desglose=[
                DesgloseSalida(tipo_iva=d.tipo_iva, base=d.base, cuota=d.cuota) for d in f.desgloses
            ],
            base_total=f.base_total,
            cuota_total=f.cuota_total,
            importe_total=f.importe_total,
        ),
        descripcion_operacion=f.descripcion_operacion,
        rectifica_a=_rectifica_a(detalle),
        sustituye_a=_referencia(detalle.sustituye_a),
        vigente_actual=_referencia(detalle.vigente_actual),
        correcciones=[_correccion(v) for v in detalle.correcciones],
        emitida_en=f.emitida_en,
        emitida_por=UsuarioReferencia.from_model(f.emitida_por),
        registros=[
            RegistroResumen(
                tipo=r.tipo,
                secuencia=r.secuencia,
                huella=r.huella,
                fecha_hora_huso_gen=r.fecha_hora_huso_gen,
                estado_remision=r.estado_remision,
            )
            for r in detalle.registros
        ],
    )


# --------------------------------------------------------------------------- rutas

AnioListado = Annotated[int, Field(ge=2024, le=9999)] | Literal["todos"]


@router.get("")
async def listar_facturas(
    db: DbDep,
    q: Annotated[str | None, Query(max_length=100)] = None,
    anio: Annotated[AnioListado | None, Query(description="Por defecto, el año en curso")] = None,
    mes: Annotated[int | None, Query(ge=1, le=12)] = None,
    orden: Literal["recientes", "antiguas", "total_desc", "total_asc"] = "recientes",
    pagina: Annotated[int, Query(ge=1)] = 1,
    tamano: Annotated[int, Query(ge=1, le=100)] = 25,
) -> Pagina[FacturaResumenSalida]:
    filas, total = await servicio.list_facturas(
        db,
        servicio.FiltrosFacturas(
            q=q, anio=anio, mes=mes, orden=orden, pagina=pagina, tamano=tamano
        ),
    )
    return Pagina[FacturaResumenSalida](
        elementos=[
            FacturaResumenSalida(
                tipo_documento="borrador" if f.tipo_documento == "borrador" else "factura",
                id=f.id,
                num_serie=f.num_serie,
                fecha=f.fecha,
                cliente_nombre=f.cliente_nombre,
                identificacion=f.identificacion,
                base=f.base,
                cuota=f.cuota,
                total=f.total,
                estado=f.estado,
            )
            for f in filas
        ],
        total=total,
        pagina=pagina,
        tamano=tamano,
    )


@router.get("/parametros")
async def obtener_parametros(db: DbDep) -> ParametrosFacturacionSalida:
    parametros = await configuracion_facturacion.get_parametros(db)
    return ParametrosFacturacionSalida(
        iva_por_defecto=parametros.iva_por_defecto,
        emision_posible=not parametros.faltan,
        faltan=parametros.faltan,
        proximo_numero=parametros.proximo_numero,
        hoy=parametros.hoy,
        fecha_minima=parametros.fecha_minima,
    )


@router.post("", status_code=status.HTTP_201_CREATED, responses=REPETICION)
async def emitir_factura(
    datos: FacturaEntrada,
    clave: ClaveIdempotencia,
    sesion: CurrentSession,
    db: DbDep,
    origen: OrigenDep,
    response: Response,
) -> FacturaSalida:
    factura, creada = await emision.emit_factura(
        db,
        emision.DatosFactura(
            fecha_expedicion=datos.fecha_expedicion,
            cliente_id=datos.cliente_id,
            lineas=datos_lineas(datos.lineas),
        ),
        actor=sesion.usuario,
        origen=origen,
        clave=clave,
    )
    if not creada:
        response.status_code = status.HTTP_200_OK
    return factura_salida(await servicio.get_factura(db, factura.id))


@router.get("/{factura_id}")
async def obtener_factura(factura_id: uuid.UUID, db: DbDep) -> FacturaSalida:
    return factura_salida(await servicio.get_factura(db, factura_id))
