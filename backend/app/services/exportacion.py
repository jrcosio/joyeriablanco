"""Exportación de los registros de un periodo (004, US4; FR-022 a FR-026; research R-12).

Orden HAC/1177/2024, art. 8: conservación y exportación de un periodo como «copia fidedigna», en
el formato de los arts. 10 y 11. Ante un requerimiento se entregan los registros «tal cual fueron
generados» (F-4, p. 38). El formato del ZIP está en `contracts/exportacion.md`:

- un XML por registro, **byte a byte** el `xml_firmado`, nombrado por su secuencia;
- `indice.csv` (UTF-8 con BOM y `;`), `resumen.txt` y `manifiesto.sha256` (`sha256sum -c`).

El periodo son días completos de hora de Madrid, con los dos extremos incluidos. Se recorre en
flujo, de 500 en 500, y el ZIP se escribe en un fichero temporal. Al terminarlo se genera el evento
08 o 09, con «dejan de conservarse» siempre en «N»: exportar nunca borra ni altera nada (FR-025). Un
periodo vacío responde `sin-registros` sin fichero ni evento (FR-026).
"""

import csv
import io
import logging
import tempfile
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Final, Literal

from lxml import etree
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import CampoError, DatosNoValidos, SinRegistros
from app.core.http import Origen
from app.domain import eventos as eventos_dominio
from app.domain.huella import format_amount, format_timestamp
from app.domain.tipos import TipoEvento, TipoEventoSif, TipoRegistro
from app.domain.xml_registro import build_registro_alta, build_registro_anulacion
from app.models.registro_evento import RegistroEvento
from app.models.registro_facturacion import RegistroFacturacion
from app.models.usuario import Usuario
from app.repositories import eventos as eventos_repo
from app.repositories import registros as registros_repo
from app.services import eventos_sif, integridad
from app.services.auditoria import ACTOR_CONSOLA, record_event
from app.services.eventos_sif import NuevoEvento
from app.services.registro_fiscal import day_bounds

logger = logging.getLogger(__name__)

type TipoExportacion = Literal["facturacion", "eventos"]

CONSERVACION: Final = "Los registros exportados siguen conservándose en el sistema."
CABECERA_FACTURACION: Final = (
    "secuencia",
    "tipo",
    "num_serie",
    "fecha_expedicion",
    "fecha_hora_generacion",
    "huella",
    "certificado_titular",
)
CABECERA_EVENTOS: Final = (
    "secuencia",
    "tipo_evento",
    "fecha_hora_generacion",
    "huella",
    "certificado_titular",
)


@dataclass(frozen=True, slots=True)
class Exportacion:
    ruta: Path  # fichero temporal: quien lo sirve lo borra
    nombre: str
    registros: int
    sha256: str


@dataclass(slots=True)
class _Zip:
    """El ZIP que se va escribiendo, con su manifiesto y su índice."""

    archivo: zipfile.ZipFile
    indice: io.StringIO = field(default_factory=io.StringIO)
    manifiesto: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.indice.write("﻿")  # BOM: Excel lo abre en UTF-8

    def escribir(self, ruta: str, contenido: bytes) -> None:
        self.archivo.writestr(ruta, contenido)
        self.manifiesto.append(f"{sha256(contenido).hexdigest()}  {ruta}")

    def fila(self, valores: Sequence[object]) -> None:
        csv.writer(self.indice, delimiter=";", lineterminator="\n").writerow(valores)

    def cerrar(self, resumen: str) -> None:
        self.escribir("indice.csv", self.indice.getvalue().encode("utf-8"))
        self.escribir("resumen.txt", resumen.encode("utf-8"))
        self.archivo.writestr("manifiesto.sha256", ("\n".join(self.manifiesto) + "\n").encode())
        self.archivo.close()


def _xml(registro: RegistroFacturacion) -> bytes:
    """El registro tal cual se firmó. Uno de VERI*FACTU, sin firma, se genera de su contenido."""
    if registro.xml_firmado is not None:
        return registro.xml_firmado
    construir = (
        build_registro_alta if registro.tipo == TipoRegistro.ALTA else build_registro_anulacion
    )
    return bytes(
        etree.tostring(construir(registro.contenido), encoding="UTF-8", xml_declaration=True)
    )


def _nombre_fichero(tipo: TipoExportacion, desde: date, hasta: date) -> str:
    return f"registros-{tipo}-{desde:%Y%m%d}-{hasta:%Y%m%d}.zip"


def _temporal() -> Path:
    with tempfile.NamedTemporaryFile(prefix="exportacion-", suffix=".zip", delete=False) as f:
        return Path(f.name)


def _limites(desde: date, hasta: date) -> tuple[datetime, datetime]:
    inicio, fin = day_bounds(desde, hasta)
    if inicio is None or fin is None:  # pragma: no cover — con dos fechas, nunca
        msg = "Periodo sin límites"
        raise ValueError(msg)
    return inicio, fin


def _registro(etiqueta: str, registro: RegistroFacturacion) -> str:
    return f"{etiqueta}: nº {registro.secuencia}, {registro.num_serie}, huella {registro.huella}"


def _evento(etiqueta: str, evento: RegistroEvento) -> str:
    return f"{etiqueta}: nº {evento.secuencia}, tipo {evento.tipo_evento}, huella {evento.huella}"


def _periodo(desde: date, hasta: date) -> str:
    return f"Periodo: del {desde:%d/%m/%Y} al {hasta:%d/%m/%Y}, en hora de Madrid, ambos incluidos."


async def _facturacion(
    db: AsyncSession, zip_: _Zip, desde: date, hasta: date
) -> tuple[int, NuevoEvento | None, str]:
    inicio, fin = _limites(desde, hasta)
    primero: RegistroFacturacion | None = None
    ultimo: RegistroFacturacion | None = None
    altas = anulaciones = 0
    cuota = importe = Decimal(0)
    zip_.fila(CABECERA_FACTURACION)
    async for registro in registros_repo.stream_between(db, inicio, fin):
        primero = primero or registro
        ultimo = registro
        serie = registro.num_serie.replace("/", "-")
        zip_.escribir(
            f"facturacion/{registro.secuencia:07d}-{registro.tipo}-{serie}.xml", _xml(registro)
        )
        zip_.fila(
            (
                registro.secuencia,
                registro.tipo,
                registro.num_serie,
                registro.fecha_expedicion,
                registro.fecha_hora_huso_gen,
                registro.huella,
                registro.certificado_titular or "",
            )
        )
        if registro.tipo == TipoRegistro.ALTA:
            altas += 1
            cuota += registro.cuota_total or Decimal(0)
            importe += registro.importe_total or Decimal(0)
        else:
            anulaciones += 1
    if primero is None or ultimo is None:
        return 0, None, ""
    inicial, final = eventos_sif.con_huella(primero), eventos_sif.con_huella(ultimo)
    evento = NuevoEvento(
        TipoEventoSif.EXPORTACION_FACTURACION,
        datos_propios=eventos_dominio.exportacion_facturacion(
            inicio=format_timestamp(inicio),
            fin=format_timestamp(fin),
            inicial=inicial,
            final=final,
            altas=altas,
            suma_cuota=cuota,
            suma_importe=importe,
            anulaciones=anulaciones,
        ),
    )
    resumen = "\n".join(
        (
            "Exportación de registros de facturación (Orden HAC/1177/2024, art. 8)",
            _periodo(desde, hasta),
            _registro("Primer registro", primero),
            _registro("Último registro", ultimo),
            f"Registros de alta: {altas}",
            f"Registros de anulación: {anulaciones}",
            f"Suma de la cuota total de las altas: {format_amount(cuota)} EUR",
            f"Suma del importe total de las altas: {format_amount(importe)} EUR",
            CONSERVACION,
            "",
        )
    )
    return altas + anulaciones, evento, resumen


async def _eventos(
    db: AsyncSession, zip_: _Zip, desde: date, hasta: date
) -> tuple[int, NuevoEvento | None, str]:
    inicio, fin = _limites(desde, hasta)
    primero: RegistroEvento | None = None
    ultimo: RegistroEvento | None = None
    numero = 0
    zip_.fila(CABECERA_EVENTOS)
    async for evento in eventos_repo.stream_between(db, inicio, fin):
        primero = primero or evento
        ultimo = evento
        numero += 1
        zip_.escribir(
            f"eventos/{evento.secuencia:07d}-{evento.tipo_evento}.xml", evento.xml_firmado
        )
        zip_.fila(
            (
                evento.secuencia,
                evento.tipo_evento,
                evento.fecha_hora_huso_gen,
                evento.huella,
                evento.certificado_titular,
            )
        )
    if primero is None or ultimo is None:
        return 0, None, ""
    nuevo = NuevoEvento(
        TipoEventoSif.EXPORTACION_EVENTOS,
        datos_propios=eventos_dominio.exportacion_eventos(
            inicio=format_timestamp(inicio),
            fin=format_timestamp(fin),
            inicial=eventos_sif.referido(primero),
            final=eventos_sif.referido(ultimo),
            numero=numero,
        ),
    )
    resumen = "\n".join(
        (
            "Exportación de registros de evento (Orden HAC/1177/2024, arts. 8 y 9.3)",
            _periodo(desde, hasta),
            _evento("Primer evento", primero),
            _evento("Último evento", ultimo),
            f"Registros de evento: {numero}",
            CONSERVACION,
            "",
        )
    )
    return numero, nuevo, resumen


async def export_records(
    db: AsyncSession,
    *,
    tipo: TipoExportacion,
    desde: date,
    hasta: date,
    actor: Usuario | None = None,
    origen: Origen | None = None,
) -> Exportacion:
    """El ZIP del periodo y su evento (FR-022 a FR-024). Exige certificado: el evento se firma."""
    if desde > hasta:
        raise DatosNoValidos(errores=[CampoError("hasta", "No puede ser anterior a «desde».")])
    integridad.requires_certificate(accion="exportar")
    ruta = _temporal()
    try:
        with zipfile.ZipFile(ruta, "w", compression=zipfile.ZIP_DEFLATED) as archivo:
            zip_ = _Zip(archivo)
            recorrer = _facturacion if tipo == "facturacion" else _eventos
            numero, evento, resumen = await recorrer(db, zip_, desde, hasta)
            if evento is None:
                raise SinRegistros
            zip_.cerrar(resumen)
    except BaseException:
        ruta.unlink(missing_ok=True)
        raise
    huella = sha256(ruta.read_bytes()).hexdigest()
    await eventos_sif.record_evento(db, evento)
    await record_event(
        db,
        TipoEvento.REGISTROS_EXPORTADOS,
        origen=origen,
        actor=actor,
        actor_nombre_usuario=None if actor else ACTOR_CONSOLA,
        detalle={
            "tipo": tipo,
            "desde": desde.isoformat(),
            "hasta": hasta.isoformat(),
            "registros": numero,
            "sha256": huella,
        },
    )
    logger.info("Registros exportados", extra={"tipo": tipo, "registros": numero})
    return Exportacion(
        ruta=ruta, nombre=_nombre_fichero(tipo, desde, hasta), registros=numero, sha256=huella
    )
