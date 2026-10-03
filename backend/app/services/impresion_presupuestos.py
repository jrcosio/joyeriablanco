"""Presupuesto impreso (005, US2; FR-029 a FR-031) y listado impreso (US5; FR-030; R-9 a R-11).

Como la factura de 003 (`services/impresion.py`), con las piezas de `impresion_comun.py`. El
emisor y el cliente salen de la copia guardada al emitir y el contacto y el pie, de la
configuración vigente. El modelo **no tiene campo `qr`**: un presupuesto nunca lleva QR tributario,
mención VERI*FACTU, registro ni huella (FAQ AEAT de proformas y borradores, F-13). Los registros de
actividad solo llevan el número (FR-035).
"""

import logging
import time
import uuid
from dataclasses import dataclass
from datetime import date
from typing import Final

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ListadoDemasiadoGrande
from app.core.pdf import plantillas, render
from app.core.tiempo import ahora, hoy
from app.domain.exenciones import MENCION_EXENCION_ORO_INVERSION
from app.domain.formato import (
    format_euros,
    format_fecha,
    format_fecha_hora,
    format_iban,
    format_porcentaje,
    nombre_mes,
)
from app.domain.tipos import EstadoPresupuesto, TipoCierrePresupuesto
from app.repositories import configuracion_facturacion
from app.repositories import presupuestos as repo_presupuestos
from app.services import presupuestos
from app.services.impresion_comun import LIMITE_LISTADO_IMPRESO as LIMITE_LISTADO_IMPRESO
from app.services.impresion_comun import (
    TEXTO_ORDEN,
    ContactoImpreso,
    DesgloseImpreso,
    DocumentoPdf,
    FilaImpresa,
    FiltroImpreso,
    LineaImpresa,
    ListadoImpreso,
    ParteImpresa,
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

TITULO: Final = "PRESUPUESTO"
AVISO_NO_FISCAL: Final = "Documento sin validez fiscal. No es una factura."


@dataclass(frozen=True, slots=True)
class PresupuestoImpreso:
    titulo: str
    aviso_no_fiscal: str
    num_serie: str
    fecha: str
    valido_hasta: str
    marcas: tuple[str, ...]
    emisor: ParteImpresa
    contacto: ContactoImpreso
    destinatario: ParteImpresa
    lineas: tuple[LineaImpresa, ...]
    desglose: tuple[DesgloseImpreso, ...]
    base_total: str
    cuota_total: str
    importe_total: str
    mencion_exencion: str | None
    iban: str | None
    pie: str | None


def _marcas(detalle: presupuestos.DetallePresupuesto) -> tuple[str, ...]:
    """R-10. Un pendiente, un caducado o uno en facturación no llevan marca.

    «SUSTITUIDO por» apunta al vigente actual de la cadena; «CONVERTIDO en», a la factura del
    cierre, que es en la que se convirtió aunque después se haya corregido.
    """
    if detalle.estado is EstadoPresupuesto.ANULADO:
        return ("ANULADO",)
    if detalle.estado is EstadoPresupuesto.SUSTITUIDO and detalle.vigente_actual is not None:
        return (f"SUSTITUIDO por {detalle.vigente_actual.num_serie}",)
    cierre = detalle.cierre
    if (
        detalle.estado is EstadoPresupuesto.CONVERTIDO
        and cierre is not None
        and TipoCierrePresupuesto(cierre.tipo) is TipoCierrePresupuesto.CONVERSION
        and detalle.factura is not None
    ):
        return (f"CONVERTIDO en {detalle.factura.num_serie}",)
    return ()


async def build_presupuesto_impreso(
    db: AsyncSession, presupuesto_id: uuid.UUID, *, iban: bool
) -> PresupuestoImpreso:
    detalle = await presupuestos.get_presupuesto(db, presupuesto_id)  # 404 si no existe
    p = detalle.presupuesto
    config = await configuracion_facturacion.get(db)
    return PresupuestoImpreso(
        titulo=TITULO,
        aviso_no_fiscal=AVISO_NO_FISCAL,
        num_serie=p.num_serie,
        fecha=format_fecha(p.fecha),
        valido_hasta=format_fecha(p.valido_hasta),
        marcas=_marcas(detalle),
        emisor=emisor(p),
        contacto=contacto(config),
        destinatario=destinatario(p),
        lineas=lineas_impresas(p.lineas),
        desglose=desglose_impreso(p.desgloses),
        base_total=format_euros(p.base_total),
        cuota_total=format_euros(p.cuota_total),
        importe_total=format_euros(p.importe_total),
        mencion_exencion=MENCION_EXENCION_ORO_INVERSION if p.oro_inversion else None,
        iban=format_iban(p.emisor_iban) if iban and p.emisor_iban else None,
        pie=config.pie_presupuesto or config.pie_factura,  # FR-031
    )


def html_presupuesto(modelo: PresupuestoImpreso) -> str:
    return plantillas.render_html("presupuesto.html", {"p": modelo})


async def presupuesto_pdf(
    db: AsyncSession, presupuesto_id: uuid.UUID, *, iban: bool
) -> DocumentoPdf:
    inicio = time.perf_counter()
    modelo = await build_presupuesto_impreso(db, presupuesto_id, iban=iban)
    html = html_presupuesto(modelo)
    # El limitador de los documentos sueltos de 003 (factura y presupuesto), sin renombrar.
    contenido = await render.en_hilo(lambda: render.html_a_pdf(html), render.LIMITE_FACTURAS)
    logger.info(
        "PDF del presupuesto %s generado en %d ms",
        modelo.num_serie,
        round((time.perf_counter() - inicio) * 1000),
    )
    return DocumentoPdf(nombre=f"{modelo.num_serie}.pdf", contenido=contenido)


# ------------------------------------------------------------------- listado (US5)


TEXTOS_LISTADO: Final = TextosListado(
    titulo="Listado de presupuestos",
    sin_filas="No hay presupuestos con este filtro",
    titulo_totales=(
        "Totales de los presupuestos pendientes, caducados, en facturación y convertidos"
    ),
)

# Las marcas de la pantalla junto al número (contracts/documentos-pdf.md). Un pendiente no lleva.
_MARCAS: Final = {
    EstadoPresupuesto.EN_FACTURACION: "En facturación",
    EstadoPresupuesto.CADUCADO: "Caducado",
    EstadoPresupuesto.CONVERTIDO: "Convertido",
    EstadoPresupuesto.SUSTITUIDO: "Sustituido",
    EstadoPresupuesto.ANULADO: "Anulado",
}


def _fila(fila: repo_presupuestos.FilaListado, fecha_hoy: date) -> FilaImpresa:
    return FilaImpresa(
        numero=fila.num_serie or "Borrador",
        marca=_MARCAS.get(presupuestos.estado_de_fila(fila, fecha_hoy)),
        fecha=format_fecha(fila.fecha),
        cliente=fila.cliente_nombre or "Sin cliente",
        identificacion=fila.identificacion or "",
        base=format_euros(fila.base),
        iva="Exenta" if fila.oro_inversion else format_euros(fila.cuota),
        total=format_euros(fila.total),
    )


async def build_listado_presupuestos(
    db: AsyncSession, filtros: presupuestos.FiltrosPresupuestos
) -> ListadoImpreso:
    """Todas las filas del filtro y los totales de los que se suman (FR-030), como en 003."""
    fecha_hoy = hoy()
    anio_filtro = fecha_hoy.year if filtros.anio is None else filtros.anio  # como la pantalla
    anio = None if anio_filtro == "todos" else anio_filtro
    q, mes = filtros.q, filtros.mes
    total_filas = await repo_presupuestos.count_listado(db, q=q, anio=anio, mes=mes)
    if total_filas > LIMITE_LISTADO_IMPRESO:
        raise ListadoDemasiadoGrande(
            f"El listado tiene {total_filas:,} presupuestos y el máximo para imprimir es "
            f"{LIMITE_LISTADO_IMPRESO:,}. Acota el filtro, por ejemplo por año.".replace(",", "."),
            extra={"limite": LIMITE_LISTADO_IMPRESO, "total": total_filas},
        )
    filas = await repo_presupuestos.list_presupuestos_impresion(
        db, q=q, anio=anio, mes=mes, orden=filtros.orden
    )
    totales = await repo_presupuestos.totales_presupuestos(db, q=q, anio=anio, mes=mes)
    config = await configuracion_facturacion.get(db)
    busqueda = (filtros.q or "").strip()
    excluidos = [
        texto
        for n, texto in (
            (totales.borradores, cuenta(totales.borradores, "borrador", "borradores")),
            (totales.sustituidos, cuenta(totales.sustituidos, "sustituido", "sustituidos")),
            (totales.anulados, cuenta(totales.anulados, "anulado", "anulados")),
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
            f"{cuenta(len(filas), 'presupuesto', 'presupuestos')} · Generado el "
            f"{format_fecha_hora(ahora())}"
        ),
        filas=tuple(_fila(fila, fecha_hoy) for fila in filas),
        desglose=tuple(
            importes(
                "Exenta" if d.tipo_iva is None else f"IVA {format_porcentaje(d.tipo_iva)}",
                d.base,
                d.cuota,
            )
            for d in totales.desglose
        ),
        totales=importes(
            f"Total ({cuenta(totales.sumados, 'presupuesto', 'presupuestos')})",
            totales.base,
            totales.cuota,
        ),
        excluidas=f"No se suman: {enumerar(excluidos)}" if excluidos else None,
        nombre_fichero=nombre_fichero("presupuestos", anio, filtros.mes),
        textos=TEXTOS_LISTADO,
    )


async def listado_presupuestos_pdf(
    db: AsyncSession, filtros: presupuestos.FiltrosPresupuestos
) -> DocumentoPdf:
    inicio = time.perf_counter()
    modelo = await build_listado_presupuestos(db, filtros)
    contenido = await render.en_hilo(lambda: pdf_listado(modelo), render.LIMITE_LISTADOS)
    # Sin el texto de búsqueda (FR-035): solo cuántas filas y cuánto ha tardado.
    logger.info(
        "PDF del listado de presupuestos generado: %d filas en %d ms",
        len(modelo.filas),
        round((time.perf_counter() - inicio) * 1000),
    )
    return DocumentoPdf(nombre=modelo.nombre_fichero, contenido=contenido)
