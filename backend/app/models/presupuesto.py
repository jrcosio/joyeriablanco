"""Presupuesto emitido, sus líneas y su desglose: SOLO INSERCIÓN (005, data-model §presupuestos).

La inalterabilidad está en la BD (constitución 2.3.0, principio III): REVOKE de UPDATE, DELETE y
TRUNCATE a `jb_app` y triggers que también paran a `jb_owner` (migración 0008). El estado no es una
columna: lo deriva `estado_presupuesto()` a partir de los cierres y del borrador de factura
vinculado. Un presupuesto no genera registros de facturación ni huella (FR-005).

Las copias `emisor_*` y `dest_*` tienen los mismos nombres que en `Factura`, para que la impresión
las trate igual (research R-8, R-9). El domicilio del destinatario puede faltar (FR-011).
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CHAR,
    Boolean,
    Computed,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UuidPkMixin
from app.models.factura import TEXTO_BUSQUEDA
from app.models.usuario import Usuario


class LineaPresupuesto(UuidPkMixin, Base):
    __tablename__ = "lineas_presupuesto"

    presupuesto_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("presupuestos.id"))
    orden: Mapped[int] = mapped_column(SmallInteger)
    unidades: Mapped[Decimal] = mapped_column(Numeric(9, 2))
    descripcion: Mapped[str] = mapped_column(String(500))
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    tipo_iva: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))  # NULL: oro de inversión
    importe: Mapped[Decimal] = mapped_column(Numeric(12, 2))


class DesglosePresupuesto(Base):
    """Totales por tipo de IVA (constitución II). Sin claves fiscales: no es un registro."""

    __tablename__ = "desgloses_presupuesto"

    presupuesto_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("presupuestos.id"), primary_key=True
    )
    orden: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    tipo_iva: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    base: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    cuota: Mapped[Decimal] = mapped_column(Numeric(12, 2))


class Presupuesto(UuidPkMixin, Base):
    __tablename__ = "presupuestos"

    serie: Mapped[str] = mapped_column(String(3))
    anio: Mapped[int] = mapped_column(SmallInteger)
    numero: Mapped[int] = mapped_column(Integer)
    num_serie: Mapped[str] = mapped_column(String(60))
    fecha: Mapped[date] = mapped_column(Date)
    valido_hasta: Mapped[date] = mapped_column(Date)
    # Copia del emisor al emitir (FR-010)
    emisor_nif: Mapped[str] = mapped_column(CHAR(9))
    emisor_nombre: Mapped[str] = mapped_column(String(120))
    emisor_direccion: Mapped[str] = mapped_column(String(200))
    emisor_codigo_postal: Mapped[str] = mapped_column(CHAR(5))
    emisor_localidad: Mapped[str] = mapped_column(String(100))
    emisor_provincia: Mapped[str | None] = mapped_column(String(100))
    emisor_iban: Mapped[str | None] = mapped_column(String(34))
    # Copia del destinatario al emitir (FR-010); el domicilio no se exige (FR-011)
    cliente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clientes.id"))
    dest_nombre: Mapped[str] = mapped_column(String(120))
    dest_identificacion_pais: Mapped[str] = mapped_column(CHAR(2))
    dest_identificacion_tipo: Mapped[str] = mapped_column(String(3))
    dest_identificacion_numero: Mapped[str] = mapped_column(String(20))
    dest_direccion: Mapped[str | None] = mapped_column(String(200))
    dest_codigo_postal: Mapped[str | None] = mapped_column(String(10))
    dest_localidad: Mapped[str | None] = mapped_column(String(100))
    dest_provincia: Mapped[str | None] = mapped_column(String(100))
    dest_pais: Mapped[str] = mapped_column(CHAR(2))
    oro_inversion: Mapped[bool] = mapped_column(Boolean)
    base_total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    cuota_total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    importe_total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    emitido_por_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"))
    emitido_en: Mapped[datetime] = mapped_column(server_default=func.now())
    clave_idempotencia: Mapped[uuid.UUID | None]
    operacion_idempotencia: Mapped[str | None] = mapped_column(String(20))
    origen_idempotencia: Mapped[uuid.UUID | None]
    texto_busqueda: Mapped[str] = mapped_column(Text, Computed(TEXTO_BUSQUEDA, persisted=True))

    lineas: Mapped[list[LineaPresupuesto]] = relationship(
        order_by=LineaPresupuesto.orden, lazy="selectin", viewonly=True
    )
    desgloses: Mapped[list[DesglosePresupuesto]] = relationship(
        order_by=DesglosePresupuesto.orden, lazy="selectin", viewonly=True
    )
    emitido_por: Mapped[Usuario] = relationship(lazy="joined", viewonly=True)
