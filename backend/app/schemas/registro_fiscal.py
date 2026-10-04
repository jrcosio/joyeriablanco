"""Esquemas del registro fiscal: eventos y cadena de registros (contracts/openapi.yaml de 004)."""

from typing import Annotated, Any

from pydantic import Field

from app.domain.tipos import TipoEventoSif
from app.schemas.comunes import SalidaBase


class Salto(SalidaBase):
    """Un salto de la cadena al anterior o al siguiente (Orden, art. 7.h)."""

    secuencia: int
    encadenamiento_correcto: bool
    fechas_en_orden: Annotated[bool, Field(description="Entre sí y con la hora actual")]


class EventoSifResumen(SalidaBase):
    secuencia: int
    tipo_evento: TipoEventoSif
    fecha_hora_huso_gen: str
    huella: str
    certificado_titular: str
    resumen: Annotated[str | None, Field(description="Una línea legible de sus datos propios")]


class EventoSifDetalle(EventoSifResumen):
    datos: Annotated[dict[str, Any], Field(description="DatosPropiosEvento (F-17)")]
    huella_correcta: bool
    firma_correcta: bool
    anterior: Salto | None
    siguiente: Salto | None
