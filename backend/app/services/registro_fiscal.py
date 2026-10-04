"""Consulta del registro fiscal: eventos y cadena de registros (004; RRSIF, art. 8.3; Orden, 7.h).

- La lista de eventos va del más reciente al más antiguo, con filtros por tipo y por días
  completos de hora de Madrid (FR-016).
- El detalle de un evento o de un registro comprueba al momento su huella y su firma, y da los
  saltos al anterior y al siguiente de su cadena. Cada salto dice si el encadenamiento es correcto
  y si las fechas respetan el orden entre sí y con la hora actual (FR-020; Orden, art. 7.h).
"""

from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import CampoError, DatosNoValidos, NoEncontrado
from app.core.http import Origen
from app.core.tiempo import ahora
from app.domain import eventos
from app.models.registro_evento import RegistroEvento
from app.models.registro_facturacion import RegistroFacturacion
from app.models.usuario import Usuario
from app.repositories import eventos as eventos_repo
from app.repositories import registros as registros_repo
from app.services import cadena, eventos_sif, integridad


@dataclass(frozen=True, slots=True)
class Salto:
    secuencia: int
    encadenamiento_correcto: bool
    fechas_en_orden: bool


def day_bounds(desde: date | None, hasta: date | None) -> tuple[datetime | None, datetime | None]:
    """Días completos en hora de Madrid, con los dos extremos incluidos (FR-022)."""
    zona = ZoneInfo(get_settings().zona_horaria)
    inicio = datetime.combine(desde, time.min, zona) if desde else None
    fin = datetime.combine(hasta, time(23, 59, 59, 999999), zona) if hasta else None
    return inicio, fin


def _fechas_en_orden(previa: str, posterior: str) -> bool:
    limite = ahora() + cadena.MARGEN_HORA
    antes, despues = datetime.fromisoformat(previa), datetime.fromisoformat(posterior)
    return antes <= despues <= limite and antes <= limite


# --------------------------------------------------------------------------------- eventos


async def list_events(
    db: AsyncSession,
    *,
    tipo: str | None,
    desde: date | None,
    hasta: date | None,
    pagina: int,
    tamano: int,
) -> tuple[list[RegistroEvento], int]:
    inicio, fin = day_bounds(desde, hasta)
    return await eventos_repo.list_events(
        db, tipo=tipo, desde=inicio, hasta=fin, pagina=pagina, tamano=tamano
    )


def _salto_evento(previo: RegistroEvento, posterior: RegistroEvento, destino: int) -> Salto:
    return Salto(
        secuencia=destino,
        encadenamiento_correcto=(
            posterior.huella_anterior == previo.huella
            and posterior.tipo_evento_anterior == previo.tipo_evento
            and posterior.fecha_hora_huso_gen_anterior == previo.fecha_hora_huso_gen
        ),
        fechas_en_orden=_fechas_en_orden(previo.fecha_hora_huso_gen, posterior.fecha_hora_huso_gen),
    )


def event_fingerprint_ok(evento: RegistroEvento) -> bool:
    try:
        correcta = eventos_sif.recompute_huella(evento) == evento.huella
    except (KeyError, TypeError, AttributeError):
        return False
    return correcta and evento.contenido["Evento"].get("HuellaEvento") == evento.huella


@dataclass(frozen=True, slots=True)
class DetalleEvento:
    evento: RegistroEvento
    datos: dict[str, Any]
    huella_correcta: bool
    firma_correcta: bool
    anterior: Salto | None
    siguiente: Salto | None


async def get_event(db: AsyncSession, secuencia: int) -> DetalleEvento:
    evento = await eventos_repo.get_by_secuencia(db, secuencia)
    if evento is None:
        raise NoEncontrado("El evento no existe.")
    previo = await eventos_repo.get_by_secuencia(db, secuencia - 1) if secuencia > 1 else None
    posterior = await eventos_repo.get_by_secuencia(db, secuencia + 1)
    propio: dict[str, Any] = evento.contenido["Evento"]
    datos: dict[str, Any] = dict(propio.get("DatosPropiosEvento") or {})
    if otros := propio.get("OtrosDatosEvento"):
        datos["OtrosDatosEvento"] = otros
    return DetalleEvento(
        evento=evento,
        datos=datos,
        huella_correcta=event_fingerprint_ok(evento),
        firma_correcta=bool(
            integridad.check_signature(
                evento.xml_firmado, evento.certificado_huella, evento.fecha_hora_huso_gen
            )
        ),
        anterior=_salto_evento(previo, evento, previo.secuencia) if previo else None,
        siguiente=_salto_evento(evento, posterior, posterior.secuencia) if posterior else None,
    )


def describe(evento: RegistroEvento) -> str | None:
    try:
        return eventos.describe(evento.contenido)
    except (KeyError, TypeError, ValueError):
        return None


# ---------------------------------------------------------------------- registros (7.h)


def _salto_registro(
    previo: RegistroFacturacion, posterior: RegistroFacturacion, destino: int
) -> Salto:
    return Salto(
        secuencia=destino,
        encadenamiento_correcto=posterior.huella_anterior == previo.huella,
        fechas_en_orden=_fechas_en_orden(previo.fecha_hora_huso_gen, posterior.fecha_hora_huso_gen),
    )


@dataclass(frozen=True, slots=True)
class DetalleRegistro:
    registro: RegistroFacturacion
    comprobacion: integridad.ComprobacionRegistro
    anterior: Salto | None
    siguiente: Salto | None


async def get_record(db: AsyncSession, secuencia: int) -> DetalleRegistro:
    registro = await registros_repo.get_by_secuencia(db, secuencia)
    if registro is None:
        raise NoEncontrado("El registro no existe.")
    previo = await registros_repo.get_by_secuencia(db, secuencia - 1) if secuencia > 1 else None
    posterior = await registros_repo.get_by_secuencia(db, secuencia + 1)
    return DetalleRegistro(
        registro=registro,
        comprobacion=integridad.check_registro(registro),
        anterior=_salto_registro(previo, registro, previo.secuencia) if previo else None,
        siguiente=(
            _salto_registro(registro, posterior, posterior.secuencia) if posterior else None
        ),
    )


# ---------------------------------------------------------------------- comprobación (web)


async def check_integrity(
    db: AsyncSession,
    *,
    desde: int | None,
    hasta: int | None,
    actor: Usuario,
    origen: Origen,
) -> integridad.ResultadoIntegridad:
    """«Comprobar integridad» (FR-017): sus eventos se firman, así que exige certificado (409)."""
    if desde is not None and hasta is not None and desde > hasta:
        raise DatosNoValidos(
            errores=[CampoError("hasta_secuencia", "No puede ser menor que «desde».")]
        )
    integridad.requires_certificate()
    return await integridad.verify_chain(db, desde=desde, hasta=hasta, origen=origen, actor=actor)
