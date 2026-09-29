"""Borrador de factura y sus líneas: mutables (data-model §borradores_factura; R-9).

Un borrador no es una factura expedida (constitución III): no tiene número ni registro. Guarda el
IVA y los totales PREVISTOS al guardarse, calculados con `domain/importes.py`, para el listado y
el aviso de cambio de IVA. Al emitir se recalcula todo con el IVA vigente.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Integer, Numeric, SmallInteger, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UuidPkMixin
from app.models.cliente import Cliente
from app.models.usuario import Usuario


class LineaBorrador(UuidPkMixin, Base):
    __tablename__ = "lineas_borrador"

    borrador_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("borradores_factura.id", ondelete="CASCADE")
    )
    orden: Mapped[int] = mapped_column(SmallInteger)
    unidades: Mapped[Decimal] = mapped_column(Numeric(9, 2))
    descripcion: Mapped[str] = mapped_column(String(500))
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(12, 2))


class BorradorFactura(UuidPkMixin, Base):
    __tablename__ = "borradores_factura"

    cliente_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("clientes.id"))
    fecha_expedicion: Mapped[date] = mapped_column(Date)
    tipo_iva_previsto: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    base_prevista: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    cuota_prevista: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    total_previsto: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(server_default=func.now())
    creado_por_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"))
    actualizado_en: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
    actualizado_por_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"))

    cliente: Mapped[Cliente | None] = relationship(lazy="joined")
    lineas: Mapped[list[LineaBorrador]] = relationship(
        order_by=LineaBorrador.orden, cascade="all, delete-orphan", lazy="selectin"
    )
    creado_por: Mapped[Usuario] = relationship(foreign_keys=[creado_por_id], lazy="joined")
    actualizado_por: Mapped[Usuario] = relationship(
        foreign_keys=[actualizado_por_id], lazy="joined"
    )

    __mapper_args__ = {"version_id_col": version}  # noqa: RUF012 — concurrencia optimista (FR-020)
