"""Comprobación de integridad de la cadena y de los documentos (US6; FR-031, SC-004; R-14).

Recorre los registros en orden de `secuencia` y, para cada uno:

1. Comprueba la secuencia y el enlace con el anterior, y recalcula su huella (F-2).
2. Coteja las columnas de la huella con la factura y reconstruye con `domain/registro.py` el
   `contenido` que debería tener. El bloque `SistemaInformatico` y la hora de generación se toman
   del propio registro, porque dependen de la versión y del momento.
3. Recalcula con `domain/importes.py` los totales y el desglose de la factura desde sus líneas.

Así se detectan también las alteraciones de campos que no forman parte de la huella. Informa de la
primera discrepancia: es el «detecte y avise» de F-8, art. 8.2.a, para lo que un dueño de la BD
pudiera hacer saltándose los triggers (R-8, límite conocido).
"""

import logging
import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.http import Origen
from app.domain.huella import format_date
from app.domain.importes import LineaCalculo, compute_totals, line_amount
from app.domain.registro import (
    SistemaInformatico,
    build_contenido_alta,
    build_contenido_anulacion,
)
from app.domain.tipos import TipoEvento, TipoRegistro
from app.models.factura import Factura
from app.models.registro_facturacion import RegistroFacturacion
from app.models.usuario import Usuario
from app.repositories import facturas
from app.repositories import registros as registros_repo
from app.services import cadena
from app.services.auditoria import ACTOR_CONSOLA, record_event

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Discrepancia:
    secuencia: int
    num_serie: str
    motivo: str


@dataclass(frozen=True, slots=True)
class ResultadoIntegridad:
    registros: int
    discrepancia: Discrepancia | None

    @property
    def integra(self) -> bool:
        return self.discrepancia is None


def _problema_de_totales(factura: Factura) -> str | None:
    """Totales y desglose de la factura frente a los que resultan de sus líneas (FR-015)."""
    for linea in factura.lineas:
        if linea.importe != line_amount(linea.unidades, linea.precio_unitario):
            return f"el importe de la línea {linea.orden} no resulta de sus unidades y su precio"
    tipos = {d.tipo_iva for d in factura.desgloses}
    if not tipos:
        return "la factura no tiene desglose"
    totales = compute_totals(
        [LineaCalculo(li.unidades, li.precio_unitario, li.tipo_iva) for li in factura.lineas],
        tipo_iva_por_defecto=min(tipos),
    )
    esperado = [(d.tipo_iva, d.base, d.cuota) for d in totales.desglose]
    guardado = sorted((d.tipo_iva, d.base, d.cuota) for d in factura.desgloses)
    if guardado != esperado:
        return "el desglose no resulta de las líneas"
    if (factura.base_total, factura.cuota_total, factura.importe_total) != (
        totales.base_total,
        totales.cuota_total,
        totales.importe_total,
    ):
        return "los totales no resultan de las líneas"
    return None


def _problema_de_columnas(registro: RegistroFacturacion, factura: Factura) -> str | None:
    """Las columnas de la huella deben ser las de la factura (F-2)."""
    esperadas: dict[str, object] = {
        "id_emisor": factura.emisor_nif,
        "num_serie": factura.num_serie,
        "fecha_expedicion": format_date(factura.fecha_expedicion),
    }
    if registro.tipo == TipoRegistro.ALTA:
        esperadas |= {
            "tipo_factura": factura.tipo_factura,
            "cuota_total": factura.cuota_total,
            "importe_total": factura.importe_total,
        }
    for campo, valor in esperadas.items():
        if getattr(registro, campo) != valor:
            return f"el campo {campo} del registro no coincide con la factura"
    return None


async def _contenido_esperado(
    db: AsyncSession,
    registro: RegistroFacturacion,
    factura: Factura,
    anterior: RegistroFacturacion | None,
) -> dict[str, object]:
    sistema = SistemaInformatico.from_bloque(registro.contenido["SistemaInformatico"])
    enlace = cadena.registro_anterior(anterior)
    if registro.tipo == TipoRegistro.ANULACION:
        return build_contenido_anulacion(
            emisor_nif=factura.emisor_nif,
            num_serie=factura.num_serie,
            fecha_expedicion=factura.fecha_expedicion,
            anterior=enlace,
            sistema=sistema,
            fecha_hora_huso_gen=registro.fecha_hora_huso_gen,
            huella=registro.huella,
        )
    rectificada = (
        await facturas.get(db, factura.factura_rectificada_id)
        if factura.factura_rectificada_id
        else None
    )
    return build_contenido_alta(
        cadena.datos_alta(factura, rectificada),
        anterior=enlace,
        sistema=sistema,
        fecha_hora_huso_gen=registro.fecha_hora_huso_gen,
        huella=registro.huella,
    )


async def _discrepancia(
    db: AsyncSession,
    registro: RegistroFacturacion,
    anterior: RegistroFacturacion | None,
    esperada: int,
    revisadas: set[uuid.UUID],
) -> str | None:
    if registro.secuencia != esperada:
        return f"se esperaba el registro nº {esperada}"
    if registro.primer_registro != (anterior is None):
        return "la marca de primer registro no es correcta"
    if registro.huella_anterior != (anterior.huella if anterior else None):
        return "no encadena con la huella del registro anterior"
    if cadena.recompute_huella(registro) != registro.huella:
        return "la huella no coincide con los datos del registro"
    factura = await facturas.get(db, registro.factura_id)
    if factura is None:  # pragma: no cover — FK
        return "no existe su factura"
    if problema := _problema_de_columnas(registro, factura):
        return problema
    try:
        esperado = await _contenido_esperado(db, registro, factura, anterior)
    except (KeyError, ValueError) as exc:
        return f"el contenido guardado no se puede reconstruir ({exc})"
    if esperado != registro.contenido:
        return "el contenido guardado no coincide con el de su factura"
    if registro.tipo == TipoRegistro.ALTA and factura.id not in revisadas:
        revisadas.add(factura.id)
        if problema := _problema_de_totales(factura):
            return f"factura {factura.num_serie}: {problema}"
    return None


async def verify_chain(
    db: AsyncSession, *, origen: Origen | None = None, actor: Usuario | None = None
) -> ResultadoIntegridad:
    """Comprueba la cadena entera y deja el resultado en la auditoría (R-15)."""
    cola = await registros_repo.list_in_order(db)
    anterior: RegistroFacturacion | None = None
    revisadas: set[uuid.UUID] = set()
    discrepancia: Discrepancia | None = None
    for esperada, registro in enumerate(cola, start=1):
        if motivo := await _discrepancia(db, registro, anterior, esperada, revisadas):
            discrepancia = Discrepancia(registro.secuencia, registro.num_serie, motivo)
            break
        anterior = registro

    actor_nombre = None if actor else ACTOR_CONSOLA
    if discrepancia is None:
        await record_event(
            db,
            TipoEvento.CADENA_VERIFICADA,
            origen=origen,
            actor=actor,
            actor_nombre_usuario=actor_nombre,
            detalle={"registros": len(cola)},
        )
        logger.info("Cadena de registros íntegra (%s registros)", len(cola))
    else:
        await record_event(
            db,
            TipoEvento.CADENA_INCONSISTENTE,
            origen=origen,
            actor=actor,
            actor_nombre_usuario=actor_nombre,
            detalle={
                "secuencia": discrepancia.secuencia,
                "num_serie": discrepancia.num_serie,
                "motivo": discrepancia.motivo,
                "momento": "verificacion",
            },
        )
        logger.error(
            "Cadena de registros inconsistente en la secuencia %s: %s",
            discrepancia.secuencia,
            discrepancia.motivo,
        )
    return ResultadoIntegridad(registros=len(cola), discrepancia=discrepancia)
