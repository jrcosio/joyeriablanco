"""Registro de facturación de alta o de anulación: SOLO INSERCIÓN (research R-3, R-4b, R-6).

Forma una cadena lineal por `secuencia`. El trigger `validar_encadenamiento` exige que cada
registro nuevo siga al último (secuencia + 1 y huella anterior = huella del último), y que solo
el primero de la cadena se marque como `primer_registro` (F-10, art. 7).

Las columnas `id_emisor`, `num_serie`, `fecha_expedicion`, `tipo_factura`, `cuota_total`,
`importe_total`, `huella_anterior` y `fecha_hora_huso_gen` son exactamente los campos de la huella
(F-2): permiten recalcularla sin interpretar `contenido`.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import CHAR, BigInteger, Boolean, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UuidPkMixin


class RegistroFacturacion(UuidPkMixin, Base):
    __tablename__ = "registros_facturacion"

    secuencia: Mapped[int] = mapped_column(BigInteger)
    tipo: Mapped[str] = mapped_column(String(10))
    factura_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("facturas.id"))
    modalidad: Mapped[str] = mapped_column(String(20))
    id_emisor: Mapped[str] = mapped_column(CHAR(9))
    num_serie: Mapped[str] = mapped_column(String(60))
    fecha_expedicion: Mapped[str] = mapped_column(CHAR(10))
    tipo_factura: Mapped[str | None] = mapped_column(CHAR(2))
    cuota_total: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    importe_total: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    primer_registro: Mapped[bool] = mapped_column(Boolean)
    huella_anterior: Mapped[str | None] = mapped_column(CHAR(64))
    fecha_hora_huso_gen: Mapped[str] = mapped_column(String(25))
    tipo_huella: Mapped[str] = mapped_column(CHAR(2))
    huella: Mapped[str] = mapped_column(CHAR(64))
    contenido: Mapped[dict[str, Any]] = mapped_column(JSONB)
    estado_remision: Mapped[str] = mapped_column(String(20))
    generado_en: Mapped[datetime] = mapped_column(server_default=func.now())
