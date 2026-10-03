"""Documentos impresos: factura con su QR tributario (US1) y listado filtrado (US2) (003; R-6, R-7).

Compone modelos de vista inmutables con todo el texto ya formateado y los entrega a las
plantillas, que solo pintan. Los datos fiscales salen de la copia guardada en la factura al
emitirla (FR-004). El contacto y el pie, de la configuración vigente (FR-005, FR-025). El QR, del
registro de alta (R-1). Los registros de actividad nunca llevan datos personales ni importes
(FR-029).
"""

import logging
import time
import uuid
from dataclasses import dataclass
from typing import Final

from markupsafe import Markup
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import DuplicadoNoDisponible, ListadoDemasiadoGrande
from app.core.pdf import plantillas, render, tokens
from app.core.tiempo import ahora, hoy
from app.domain.exenciones import mencion_exencion
from app.domain.formato import (
    format_euros,
    format_fecha,
    format_fecha_hora,
    format_iban,
    format_porcentaje,
    nombre_mes,
)
from app.domain.qr import FRASE_VERIFACTU, build_cotejo_url, qr_svg
from app.domain.tipos import (
    TEXTO_CAUSA_RECTIFICACION,
    CausaRectificacion,
    EstadoFactura,
    Modalidad,
    TipoFactura,
    TipoRegistro,
)
from app.repositories import configuracion_facturacion
from app.repositories import facturas as repo_facturas
from app.services import facturas
from app.services.impresion_comun import LIMITE_LISTADO_IMPRESO as LIMITE_LISTADO_IMPRESO
from app.services.impresion_comun import TEXTO_ORDEN as TEXTO_ORDEN
from app.services.impresion_comun import ContactoImpreso as ContactoImpreso
from app.services.impresion_comun import DesgloseImpreso as DesgloseImpreso
from app.services.impresion_comun import DocumentoPdf as DocumentoPdf
from app.services.impresion_comun import FilaImpresa as FilaImpresa
from app.services.impresion_comun import FiltroImpreso as FiltroImpreso
from app.services.impresion_comun import ImportesImpresos as ImportesImpresos
from app.services.impresion_comun import LineaImpresa as LineaImpresa
from app.services.impresion_comun import ListadoImpreso as ListadoImpreso
from app.services.impresion_comun import ParteImpresa as ParteImpresa
from app.services.impresion_comun import (
    TextosListado,
    contacto,
    cuenta,
    desglose_impreso,
    destinatario,
    emisor,
    enumerar,
    importes,
    lineas_impresas,
    nombre_fichero,
    pdf_listado,
)

logger = logging.getLogger("app.impresion")


# ------------------------------------------------------------------ modelos de vista


@dataclass(frozen=True, slots=True)
class QrImpreso:
    url: str
    svg: Markup
    frase: str | None


@dataclass(frozen=True, slots=True)
class RectificacionImpresa:
    num_serie: str
    fecha: str
    causa: str
    base_rectificada: str
    cuota_rectificada: str


@dataclass(frozen=True, slots=True)
class FacturaImpresa:
    titulo: str
    num_serie: str
    fecha_expedicion: str
    fecha_operacion: str | None
    marcas: tuple[str, ...]
    qr: QrImpreso
    emisor: ParteImpresa
    contacto: ContactoImpreso
    destinatario: ParteImpresa
    lineas: tuple[LineaImpresa, ...]
    devolucion_total: str | None
    desglose: tuple[DesgloseImpreso, ...]
    base_total: str
    cuota_total: str
    importe_total: str
    mencion_exencion: str | None
    rectificacion: RectificacionImpresa | None
    iban: str | None
    pie: str | None


# ------------------------------------------------------------------------ composición


def _marcas(detalle: facturas.DetalleFactura, *, duplicado: bool) -> tuple[str, ...]:
    """FR-009: el número es el de la vigente que la sustituye ahora (002, FR-026)."""
    marcas: list[str] = []
    sustituta = detalle.vigente_actual.num_serie if detalle.vigente_actual else None
    if detalle.estado is EstadoFactura.ANULADA:
        marcas.append("ANULADA")
        if sustituta:
            marcas.append(f"Sustituida por {sustituta}")
    elif detalle.estado is EstadoFactura.RECTIFICADA and sustituta:
        marcas.append(f"RECTIFICADA por {sustituta}")
    if duplicado:
        marcas.append("DUPLICADO")
    return tuple(marcas)


def _rectificacion(detalle: facturas.DetalleFactura) -> RectificacionImpresa | None:
    f, rectificada = detalle.factura, detalle.rectifica_a
    if rectificada is None:
        return None
    if f.base_rectificada is None or f.cuota_rectificada is None or not f.causa_rectificacion:
        msg = f"Rectificativa {f.num_serie} sin importes rectificados"
        raise ValueError(msg)
    return RectificacionImpresa(
        num_serie=rectificada.num_serie,
        fecha=format_fecha(rectificada.fecha_expedicion),
        causa=TEXTO_CAUSA_RECTIFICACION[CausaRectificacion(f.causa_rectificacion)],
        base_rectificada=format_euros(f.base_rectificada),
        cuota_rectificada=format_euros(f.cuota_rectificada),
    )


def _qr(detalle: facturas.DetalleFactura) -> QrImpreso:
    f = detalle.factura
    alta = next(r for r in detalle.registros if r.tipo == TipoRegistro.ALTA)
    if alta.importe_total is None:
        msg = f"El registro de alta de {f.num_serie} no tiene importe total"
        raise ValueError(msg)
    modalidad = Modalidad(f.modalidad)
    url = build_cotejo_url(
        modalidad,
        get_settings().entorno_aeat,
        nif=alta.id_emisor,
        num_serie=alta.num_serie,
        fecha_expedicion=alta.fecha_expedicion,
        importe_total=alta.importe_total,
    )
    return QrImpreso(
        url=url,
        # SVG generado aquí a partir de la URL ya codificada: no contiene datos sin escapar.
        svg=Markup(qr_svg(url, color=tokens.COLORES["paper-qr"])),  # noqa: S704
        frase=FRASE_VERIFACTU if modalidad is Modalidad.VERIFACTU else None,
    )


async def build_factura_impresa(
    db: AsyncSession, factura_id: uuid.UUID, *, iban: bool, duplicado: bool
) -> FacturaImpresa:
    detalle = await facturas.get_factura(db, factura_id)  # 404 si no existe o es un borrador
    if duplicado and detalle.estado is EstadoFactura.ANULADA:
        raise DuplicadoNoDisponible
    f = detalle.factura
    config = await configuracion_facturacion.get(db)
    rectificativa = TipoFactura(f.tipo_factura) is not TipoFactura.COMPLETA
    lineas = lineas_impresas(f.lineas)
    rectificacion = _rectificacion(detalle)
    return FacturaImpresa(
        titulo="Factura rectificativa" if rectificativa else "Factura",
        num_serie=f.num_serie,
        fecha_expedicion=format_fecha(f.fecha_expedicion),
        fecha_operacion=(
            format_fecha(f.fecha_operacion)
            if f.fecha_operacion and f.fecha_operacion != f.fecha_expedicion
            else None
        ),
        marcas=_marcas(detalle, duplicado=duplicado),
        qr=_qr(detalle),
        emisor=emisor(f),
        contacto=contacto(config),
        destinatario=destinatario(f),
        lineas=lineas,
        devolucion_total=(
            f"Devolución total de la factura {rectificacion.num_serie}"
            if rectificacion and not lineas
            else None
        ),
        desglose=desglose_impreso(f.desgloses),
        base_total=format_euros(f.base_total),
        cuota_total=format_euros(f.cuota_total),
        importe_total=format_euros(f.importe_total),
        mencion_exencion=mencion_exencion(f.clave_regimen),
        rectificacion=rectificacion,
        iban=format_iban(f.emisor_iban) if iban and f.emisor_iban else None,
        pie=config.pie_factura,
    )


def html_factura(modelo: FacturaImpresa) -> str:
    return plantillas.render_html("factura.html", {"f": modelo})


async def factura_pdf(
    db: AsyncSession, factura_id: uuid.UUID, *, iban: bool, duplicado: bool
) -> DocumentoPdf:
    inicio = time.perf_counter()
    modelo = await build_factura_impresa(db, factura_id, iban=iban, duplicado=duplicado)
    html = html_factura(modelo)
    contenido = await render.en_hilo(lambda: render.html_a_pdf(html), render.LIMITE_FACTURAS)
    logger.info(
        "PDF de la factura %s generado en %d ms",
        modelo.num_serie,
        round((time.perf_counter() - inicio) * 1000),
    )
    return DocumentoPdf(nombre=f"{modelo.num_serie}.pdf", contenido=contenido)


# ------------------------------------------------------------------- listado (US2)


TEXTOS_LISTADO: Final = TextosListado(
    titulo="Listado de facturas",
    sin_filas="No hay facturas con este filtro",
    titulo_totales="Totales de las facturas vigentes",
)


def _fila(fila: repo_facturas.FilaListado) -> FilaImpresa:
    marcas = {EstadoFactura.ANULADA: "Anulada", EstadoFactura.RECTIFICADA: "Rectificada"}
    return FilaImpresa(
        numero=fila.num_serie or "Borrador",
        marca=marcas.get(fila.estado),
        fecha=format_fecha(fila.fecha),
        cliente=fila.cliente_nombre or "Sin cliente",
        identificacion=fila.identificacion or "",
        base=format_euros(fila.base),
        iva="Exenta" if fila.oro_inversion else format_euros(fila.cuota),
        total=format_euros(fila.total),
    )


async def build_listado_impreso(
    db: AsyncSession, filtros: facturas.FiltrosFacturas
) -> ListadoImpreso:
    """Todas las filas del filtro y los totales de sus vigentes (FR-018 a FR-021)."""
    anio_filtro = hoy().year if filtros.anio is None else filtros.anio  # como la pantalla
    anio = None if anio_filtro == "todos" else anio_filtro
    q, mes = filtros.q, filtros.mes
    total_filas = await repo_facturas.count_listado(db, q=q, anio=anio, mes=mes)
    if total_filas > LIMITE_LISTADO_IMPRESO:
        raise ListadoDemasiadoGrande(
            f"El listado tiene {total_filas:,} facturas y el máximo para imprimir es "
            f"{LIMITE_LISTADO_IMPRESO:,}. Acota el filtro, por ejemplo por año.".replace(",", "."),
            extra={"limite": LIMITE_LISTADO_IMPRESO, "total": total_filas},
        )
    filas = await repo_facturas.list_facturas_impresion(
        db, q=q, anio=anio, mes=mes, orden=filtros.orden
    )
    totales = await repo_facturas.totales_vigentes(db, q=q, anio=anio, mes=mes)
    config = await configuracion_facturacion.get(db)
    busqueda = (filtros.q or "").strip()
    excluidas = [
        texto
        for n, texto in (
            (totales.borradores, cuenta(totales.borradores, "borrador", "borradores")),
            (totales.anuladas, cuenta(totales.anuladas, "anulada", "anuladas")),
            (totales.rectificadas, cuenta(totales.rectificadas, "rectificada", "rectificadas")),
        )
        if n
    ]
    return ListadoImpreso(
        emisor_nombre=config.emisor_nombre,
        filtro=FiltroImpreso(
            busqueda=f"Búsqueda: “{busqueda}”" if busqueda else "Sin búsqueda",
            anio="Todos los años" if anio is None else str(anio),
            mes=nombre_mes(filtros.mes) if filtros.mes else "Todos los meses",
            orden=TEXTO_ORDEN[filtros.orden],
        ),
        resumen=(
            f"{cuenta(len(filas), 'factura', 'facturas')} · Generado el "
            f"{format_fecha_hora(ahora())}"
        ),
        filas=tuple(_fila(fila) for fila in filas),
        desglose=tuple(
            importes(
                "Exenta" if d.tipo_iva is None else f"IVA {format_porcentaje(d.tipo_iva)}",
                d.base,
                d.cuota,
            )
            for d in totales.desglose
        ),
        totales=importes(
            f"Total ({cuenta(totales.vigentes, 'factura', 'facturas')})",
            totales.base,
            totales.cuota,
        ),
        excluidas=f"No se suman: {enumerar(excluidas)}" if excluidas else None,
        nombre_fichero=nombre_fichero("facturas", anio, filtros.mes),
        textos=TEXTOS_LISTADO,
    )


async def listado_pdf(db: AsyncSession, filtros: facturas.FiltrosFacturas) -> DocumentoPdf:
    inicio = time.perf_counter()
    modelo = await build_listado_impreso(db, filtros)
    contenido = await render.en_hilo(lambda: pdf_listado(modelo), render.LIMITE_LISTADOS)
    # Sin el texto de búsqueda (FR-029): solo cuántas filas y cuánto ha tardado.
    logger.info(
        "PDF del listado de facturas generado: %d filas en %d ms",
        len(modelo.filas),
        round((time.perf_counter() - inicio) * 1000),
    )
    return DocumentoPdf(nombre=modelo.nombre_fichero, contenido=contenido)
