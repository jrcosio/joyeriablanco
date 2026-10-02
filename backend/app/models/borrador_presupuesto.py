"""Borrador de presupuesto y sus líneas: mutables (005, data-model §borradores_presupuesto).

Como el borrador de factura (002, R-9): no tiene número, se guarda incompleto, se edita con
concurrencia optimista y se borra sin consumir número. Guarda el IVA y los totales PREVISTOS para
el listado y el aviso de cambio de IVA. Al emitir se recalcula todo con el IVA vigente.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    false,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UuidPkMixin
from app.models.cliente import Cliente
from app.models.usuario import Usuario


class LineaBorradorPresupuesto(UuidPkMixin, Base):
    __tablename__ = "lineas_borrador_presupuesto"

    borrador_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("borradores_presupuesto.id", ondelete="CASCADE")
    )
    orden: Mapped[int] = mapped_column(SmallInteger)
    unidades: Mapped[Decimal] = mapped_column(Numeric(9, 2))
    descripcion: Mapped[str] = mapped_column(String(500))
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(12, 2))


class BorradorPresupuesto(UuidPkMixin, Base):
    __tablename__ = "borradores_presupuesto"

    cliente_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("clientes.id"))
    fecha: Mapped[date] = mapped_column(Date)
    valido_hasta: Mapped[date] = mapped_column(Date)
    tipo_iva_previsto: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    oro_inversion: Mapped[bool] = mapped_column(Boolean, server_default=false())
    base_prevista: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    cuota_prevista: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    total_previsto: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(server_default=func.now())
    creado_por_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"))
    actualizado_en: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
    actualizado_por_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"))

    cliente: Mapped[Cliente | None] = relationship(lazy="joined")
    lineas: Mapped[list[LineaBorradorPresupuesto]] = relationship(
        order_by=LineaBorradorPresupuesto.orden, cascade="all, delete-orphan", lazy="selectin"
    )
    creado_por: Mapped[Usuario] = relationship(foreign_keys=[creado_por_id], lazy="joined")
    actualizado_por: Mapped[Usuario] = relationship(
        foreign_keys=[actualizado_por_id], lazy="joined"
    )

    __mapper_args__ = {"version_id_col": version}  # noqa: RUF012 — concurrencia optimista (FR-013)
