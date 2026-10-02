"""Presupuesto impreso (005, US2; FR-029 a FR-031; research R-9, R-10).

Como la factura de 003 (`services/impresion.py`), con las piezas de `impresion_comun.py`. El
emisor y el cliente salen de la copia guardada al emitir y el contacto y el pie, de la
configuración vigente. El modelo **no tiene campo `qr`**: un presupuesto nunca lleva QR tributario,
mención VERI*FACTU, registro ni huella (FAQ AEAT de proformas y borradores, F-13). Los registros de
actividad solo llevan el número (FR-034).
"""

import logging
import time
import uuid
from dataclasses import dataclass
from typing import Final

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pdf import plantillas, render
from app.domain.exenciones import MENCION_EXENCION_ORO_INVERSION
from app.domain.formato import format_euros, format_fecha, format_iban
from app.domain.tipos import EstadoPresupuesto, TipoCierrePresupuesto
from app.repositories import configuracion_facturacion
from app.services import presupuestos
from app.services.impresion_comun import (
    ContactoImpreso,
    DesgloseImpreso,
    DocumentoPdf,
    LineaImpresa,
    ParteImpresa,
    contacto,
    desglose_impreso,
    destinatario,
    emisor,
    lineas_impresas,
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
