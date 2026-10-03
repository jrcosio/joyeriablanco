"""/v1/facturas: parámetros del modal (US1), emisión y detalle (US2), listado (US3) y
correcciones (US5). El router valida, delega en los servicios y serializa (constitución V)."""

import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Header, Query, Response, status
from pydantic import Field

from app.api.deps import AdminSession, CurrentSession, DbDep, OrigenDep, get_current_session
from app.core.pdf.respuestas import respuesta_pdf
from app.domain.exenciones import is_oro_inversion, mencion_exencion
from app.domain.tipos import CausaRectificacion, MotivoModificacion, TipoCorreccion, TipoFactura
from app.models.factura import Factura
from app.models.presupuesto import Presupuesto
from app.schemas.comunes import Pagina
from app.schemas.configuracion_facturacion import DatosEmisorSalida, ParametrosFacturacionSalida
from app.schemas.factura import (
    AnulacionEntrada,
    ClienteFacturaSalida,
    CorreccionSalida,
    DesgloseSalida,
    FacturaEntrada,
    FacturaReferencia,
    FacturaResumenSalida,
    FacturaSalida,
    LineaEntrada,
    LineaSalida,
    ModificacionEntrada,
    PresupuestoReferencia,
    RectificaA,
    RegistroResumen,
    TotalesSalida,
)
from app.schemas.usuario import UsuarioReferencia
from app.services import configuracion_facturacion, emision, impresion
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


def presupuesto_referencia(presupuesto: Presupuesto | None) -> PresupuestoReferencia | None:
    """Ampliado en 005: el presupuesto de origen de una factura o de un borrador (FR-022)."""
    if presupuesto is None:
        return None
    return PresupuestoReferencia(
        id=presupuesto.id, num_serie=presupuesto.num_serie, fecha=presupuesto.fecha
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
            iban=f.emisor_iban,
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
        oro_inversion=is_oro_inversion(f.clave_regimen),
        mencion_exencion=mencion_exencion(f.clave_regimen),
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
        presupuesto_origen=presupuesto_referencia(detalle.presupuesto_origen),
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
                oro_inversion=f.oro_inversion,
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
        mencion_exencion_oro_inversion=parametros.mencion_exencion_oro_inversion,
    )


RESPUESTA_PDF: dict[int | str, dict[str, Any]] = {
    status.HTTP_200_OK: {
        "content": {"application/pdf": {"schema": {"type": "string", "format": "binary"}}},
        "description": "PDF listo para imprimir o guardar (003, research R-8)",
    }
}


# Declarada antes de `/{factura_id}`: si no, «listado» se tomaría por un identificador.
@router.get("/listado/pdf", response_class=Response, responses=RESPUESTA_PDF)
async def imprimir_listado(
    db: DbDep,
    q: Annotated[str | None, Query(max_length=100)] = None,
    anio: Annotated[AnioListado | None, Query(description="Por defecto, el año en curso")] = None,
    mes: Annotated[int | None, Query(ge=1, le=12)] = None,
    orden: Literal["recientes", "antiguas", "total_desc", "total_asc"] = "recientes",
) -> Response:
    """Listado completo del filtro en PDF, con los totales de las vigentes (003, US2)."""
    documento = await impresion.listado_pdf(
        db, servicio.FiltrosFacturas(q=q, anio=anio, mes=mes, orden=orden)
    )
    return respuesta_pdf(documento.nombre, documento.contenido)


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
            oro_inversion=datos.oro_inversion,
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


@router.get("/{factura_id}/pdf", response_class=Response, responses=RESPUESTA_PDF)
async def imprimir_factura(
    factura_id: uuid.UUID,
    db: DbDep,
    iban: Annotated[bool, Query(description="Incluir el IBAN copiado en la factura")] = False,
    duplicado: Annotated[
        bool, Query(description="Expedir como duplicado (ROF art. 14); 409 si está anulada")
    ] = False,
) -> Response:
    """Factura en PDF con su QR tributario (003, US1). Cualquier sesión, como la consulta."""
    documento = await impresion.factura_pdf(db, factura_id, iban=iban, duplicado=duplicado)
    return respuesta_pdf(documento.nombre, documento.contenido)


@router.post("/{factura_id}/anulacion")
async def anular_factura(
    factura_id: uuid.UUID,
    datos: AnulacionEntrada,
    clave: ClaveIdempotencia,
    sesion: AdminSession,
    db: DbDep,
    origen: OrigenDep,
) -> FacturaSalida:
    """Anulación sin reemisión (FR-025). Una repetición devuelve lo mismo (200 en ambos casos)."""
    factura, _ = await emision.anular_factura(
        db,
        factura_id,
        motivo_texto=datos.motivo_texto,
        actor=sesion.usuario,
        origen=origen,
        clave=clave,
    )
    return factura_salida(await servicio.get_factura(db, factura.id))


@router.post(
    "/{factura_id}/modificacion", status_code=status.HTTP_201_CREATED, responses=REPETICION
)
async def modificar_factura(
    factura_id: uuid.UUID,
    datos: ModificacionEntrada,
    clave: ClaveIdempotencia,
    sesion: AdminSession,
    db: DbDep,
    origen: OrigenDep,
    response: Response,
) -> FacturaSalida:
    """Corrección trazable (FR-023, FR-024): devuelve la factura nueva (FAC o REC)."""
    nueva, creada = await emision.modify_factura(
        db,
        factura_id,
        emision.DatosModificacion(
            motivo=datos.motivo,
            causa=datos.causa,
            motivo_texto=datos.motivo_texto,
            cliente_id=datos.cliente_id,
            lineas=datos_lineas(datos.lineas),
            oro_inversion=datos.oro_inversion,
            fecha_expedicion=datos.fecha_expedicion,
        ),
        actor=sesion.usuario,
        origen=origen,
        clave=clave,
    )
    if not creada:
        response.status_code = status.HTTP_200_OK
    return factura_salida(await servicio.get_factura(db, nueva.id))
