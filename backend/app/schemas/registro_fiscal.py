"""Esquemas del registro fiscal: eventos y cadena de registros (contracts/openapi.yaml de 004)."""

import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import Field

from app.domain.tipos import TipoEventoSif
from app.schemas.comunes import EntradaBase, SalidaBase


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


class RegistroCadenaDetalle(SalidaBase):
    secuencia: int
    tipo: Literal["alta", "anulacion"]
    num_serie: str
    factura_id: uuid.UUID
    fecha_hora_huso_gen: str
    huella: str
    certificado_titular: str | None
    huella_correcta: bool
    firma_correcta: Annotated[
        bool | None, Field(description="Nulo si el registro no lleva firma (VERI*FACTU)")
    ]
    anterior: Salto | None
    siguiente: Salto | None


class ComprobacionEntrada(EntradaBase):
    desde_secuencia: Annotated[
        int | None, Field(ge=1, description="Sin valor: desde el primero")
    ] = None
    hasta_secuencia: Annotated[
        int | None, Field(ge=1, description="Sin valor: hasta el último")
    ] = None


class AnomaliaSalida(SalidaBase):
    cadena: Literal["facturacion", "eventos"]
    tipo_anomalia: Annotated[str, Field(description="F-17, TipoAnomaliaType (research R-10)")]
    descripcion: str
    secuencia: int | None


class ComprobacionSalida(SalidaBase):
    integra: bool
    registros: int
    eventos: int
    anomalias: list[AnomaliaSalida]


class Alarma(SalidaBase):
    tipo: Literal["integridad", "certificado"]
    mensaje: str
    desde: datetime
    secuencia_afectada: int | None


class AlarmasSalida(SalidaBase):
    alarmas: list[Alarma]
