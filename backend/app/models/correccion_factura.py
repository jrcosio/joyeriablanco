"""Corrección trazable de una factura emitida: SOLO INSERCIÓN (data-model §correcciones_factura).

Una factura puede acumular correcciones, pero solo una en vigor (R-8): el trigger
`validar_correccion` rechaza corregir una factura que no esté vigente según `estado_factura()`.
"""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UuidPkMixin
from app.models.usuario import Usuario


class CorreccionFactura(UuidPkMixin, Base):
    __tablename__ = "correcciones_factura"

    factura_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("facturas.id"))
    tipo: Mapped[str] = mapped_column(String(30))
    motivo: Mapped[str] = mapped_column(String(30))
    motivo_texto: Mapped[str] = mapped_column(String(500))
    factura_nueva_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("facturas.id"))
    registro_anulacion_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("registros_facturacion.id")
    )
    creada_por_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"))
    creada_en: Mapped[datetime] = mapped_column(server_default=func.now())
    clave_idempotencia: Mapped[uuid.UUID | None]
    operacion_idempotencia: Mapped[str | None] = mapped_column(String(20))

    creada_por: Mapped[Usuario] = relationship(lazy="joined", viewonly=True)
