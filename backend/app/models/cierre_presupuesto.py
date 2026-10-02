"""Cierre de un presupuesto emitido: SOLO INSERCIÓN (005, data-model §cierres_presupuesto).

Es su desenlace (sustitución, anulación o conversión) y alimenta el historial y el estado. Hay como
mucho uno por presupuesto (`uq_cierres_presupuesto_presupuesto_id`), y el trigger
`cierres_presupuesto_validar` rechaza anular o sustituir con un borrador de factura vinculado.
"""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UuidPkMixin
from app.models.usuario import Usuario


class CierrePresupuesto(UuidPkMixin, Base):
    __tablename__ = "cierres_presupuesto"

    presupuesto_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("presupuestos.id"))
    tipo: Mapped[str] = mapped_column(String(12))
    motivo_texto: Mapped[str | None] = mapped_column(String(500))
    presupuesto_nuevo_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("presupuestos.id"))
    factura_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("facturas.id"))
    creado_por_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"))
    creado_en: Mapped[datetime] = mapped_column(server_default=func.now())
    clave_idempotencia: Mapped[uuid.UUID | None]
    operacion_idempotencia: Mapped[str | None] = mapped_column(String(20))

    creado_por: Mapped[Usuario] = relationship(lazy="joined", viewonly=True)
