"""Alarmas activas (004, research R-11; Orden, art. 6.f; FR-019). Es un estado derivado, sin tabla.

- **Integridad**: cada evento 04 o 06 (una anomalía detectada) la mantiene encendida hasta que una
  comprobación lanzada después garantiza los registros que siguen al afectado:
  - en facturación, empieza en el siguiente al afectado o antes y llega al final de la cadena;
  - en eventos, la cadena se comprueba siempre entera;
  - y no encuentra ninguna anomalía nueva posterior al afectado.
- **Certificado**: en No VERI*FACTU, mientras el certificado de firma no sea utilizable.

La ven todos los usuarios (Clarifications); el detalle es cosa del administrador.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.tiempo import ahora
from app.domain.tipos import Modalidad, MotivoNoUtilizable, TipoEventoSif
from app.models.comprobacion_integridad import ComprobacionIntegridad
from app.models.registro_evento import RegistroEvento
from app.repositories import comprobaciones, configuracion_facturacion
from app.repositories import eventos as eventos_repo
from app.services import certificado
from app.services.certificado import TEXTO_MOTIVO


@dataclass(frozen=True, slots=True)
class Alarma:
    tipo: Literal["integridad", "certificado"]
    mensaje: str
    desde: datetime
    secuencia_afectada: int | None = None


def _cubre(
    comprobacion: ComprobacionIntegridad, lanzamiento: int, anomalia: RegistroEvento
) -> bool:
    """Si la comprobación, lanzada después, garantiza lo que sigue a la anomalía."""
    if lanzamiento <= anomalia.secuencia:
        return False
    afectada = anomalia.secuencia_afectada
    if anomalia.tipo_evento == TipoEventoSif.ANOMALIA_EVENTOS:
        nueva = comprobacion.max_evento_anomalo
        return nueva is None or (afectada is not None and nueva <= afectada)
    if not comprobacion.llega_al_final:
        return False
    if afectada is None:
        return comprobacion.anomalias == 0 and comprobacion.desde_secuencia in (None, 1)
    desde = comprobacion.desde_secuencia
    nueva = comprobacion.max_secuencia_anomala
    return (desde is None or desde <= afectada + 1) and (nueva is None or nueva <= afectada)


def _cuando(evento: RegistroEvento) -> datetime:
    return datetime.fromisoformat(evento.fecha_hora_huso_gen)


async def active_alarms(db: AsyncSession) -> list[Alarma]:
    alarmas: list[Alarma] = []
    hechas = await comprobaciones.list_with_launch(db)
    pendientes = [
        anomalia
        for anomalia in await eventos_repo.list_anomalies(db)
        if not any(_cubre(c, lanzamiento, anomalia) for c, lanzamiento in hechas)
    ]
    if pendientes:
        primera = pendientes[0]
        zona = ZoneInfo(get_settings().zona_horaria)
        cuando = _cuando(primera).astimezone(zona).strftime("%d/%m/%Y %H:%M")
        alarmas.append(
            Alarma(
                tipo="integridad",
                mensaje=(
                    "Alarma de integridad: se ha detectado una anomalía en los registros el "
                    f"{cuando}"
                ),
                desde=_cuando(primera),
                secuencia_afectada=primera.secuencia_afectada,
            )
        )
    config = await configuracion_facturacion.get(db)
    estado = certificado.estado()
    if config.modalidad == Modalidad.NO_VERIFACTU and estado.motivo is not None:
        alarmas.append(
            Alarma(
                tipo="certificado",
                mensaje=(
                    "No se puede facturar: el certificado de firma no es utilizable "
                    f"({TEXTO_MOTIVO[estado.motivo]})"
                ),
                desde=(
                    estado.valido_hasta
                    if estado.motivo is MotivoNoUtilizable.CADUCADO and estado.valido_hasta
                    else ahora()
                ),
            )
        )
    return alarmas
