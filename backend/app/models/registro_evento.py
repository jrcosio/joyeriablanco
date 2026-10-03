"""Registro de evento del sistema informático: SOLO INSERCIÓN (004, data-model; Orden, art. 9).

Forma su propia cadena por `secuencia`. El trigger `validar_encadenamiento_eventos` exige que cada
evento siga al último: secuencia + 1 y, del anterior, la huella, el tipo y la fecha (F-17,
`EventoAnterior`). `xml_firmado` es el `RegistroEvento` firmado tal cual se generó y se exporta.

`tipo_anomalia` y `secuencia_afectada` solo se informan en las detecciones (04 y 06) y no forman
parte del XML: sirven para la alarma (research R-11).
"""

from datetime import datetime
from typing import Any

from sqlalchemy import CHAR, BigInteger, Boolean, LargeBinary, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UuidPkMixin


class RegistroEvento(UuidPkMixin, Base):
    __tablename__ = "registros_evento"

    secuencia: Mapped[int] = mapped_column(BigInteger)
    tipo_evento: Mapped[str] = mapped_column(CHAR(2))
    fecha_hora_huso_gen: Mapped[str] = mapped_column(String(25))
    primer_evento: Mapped[bool] = mapped_column(Boolean)
    tipo_evento_anterior: Mapped[str | None] = mapped_column(CHAR(2))
    fecha_hora_huso_gen_anterior: Mapped[str | None] = mapped_column(String(25))
    huella_anterior: Mapped[str | None] = mapped_column(CHAR(64))
    tipo_huella: Mapped[str] = mapped_column(CHAR(2))
    huella: Mapped[str] = mapped_column(CHAR(64))
    tipo_anomalia: Mapped[str | None] = mapped_column(CHAR(2))
    secuencia_afectada: Mapped[int | None] = mapped_column(BigInteger)
    contenido: Mapped[dict[str, Any]] = mapped_column(JSONB)
    xml_firmado: Mapped[bytes] = mapped_column(LargeBinary)
    certificado_titular: Mapped[str] = mapped_column(String(200))
    certificado_huella: Mapped[str] = mapped_column(CHAR(64))
    generado_en: Mapped[datetime] = mapped_column(server_default=func.now())
