"""Factura emitida, sus líneas y su desglose: SOLO INSERCIÓN (data-model §facturas; R-8).

La inalterabilidad está en la BD (constitución III): REVOKE de UPDATE/DELETE/TRUNCATE a `jb_app` y
triggers que también paran a `jb_owner` (migración 0005). El estado (vigente, anulada o
rectificada) no es una columna: lo deriva `estado_factura()` a partir de `correcciones_factura`.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CHAR,
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
from app.models.usuario import Usuario

TEXTO_BUSQUEDA = (
    "inmutable_unaccent(lower(num_serie || ' ' || dest_nombre || ' ' || "
    "dest_identificacion_numero))"
)


class LineaFactura(UuidPkMixin, Base):
    __tablename__ = "lineas_factura"

    factura_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("facturas.id"))
    orden: Mapped[int] = mapped_column(SmallInteger)
    unidades: Mapped[Decimal] = mapped_column(Numeric(9, 2))
    descripcion: Mapped[str] = mapped_column(String(500))
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    # NULL en una factura de oro de inversión: exenta, sin tipo (research R-21)
    tipo_iva: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    importe: Mapped[Decimal] = mapped_column(Numeric(12, 2))


class DesgloseFactura(Base):
    """Totales agregados por tipo de IVA (constitución II): un `DetalleDesglose` de F-1.

    Sujeto (`S1`, con tipo) o exento (`OperacionExenta` `E6` y clave `04`, sin tipo y con cuota
    0), según el CHECK `ck_desgloses_factura_calificacion` de la migración 0006 (R-21).
    """

    __tablename__ = "desgloses_factura"

    factura_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("facturas.id"), primary_key=True)
    orden: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    tipo_iva: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    clave_regimen: Mapped[str] = mapped_column(CHAR(2))
    calificacion_operacion: Mapped[str | None] = mapped_column(CHAR(2))
    operacion_exenta: Mapped[str | None] = mapped_column(CHAR(2))
    base: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    cuota: Mapped[Decimal] = mapped_column(Numeric(12, 2))


class Factura(UuidPkMixin, Base):
    __tablename__ = "facturas"

    serie: Mapped[str] = mapped_column(String(3))
    anio: Mapped[int] = mapped_column(SmallInteger)
    numero: Mapped[int] = mapped_column(Integer)
    num_serie: Mapped[str] = mapped_column(String(60))
    tipo_factura: Mapped[str] = mapped_column(CHAR(2))
    tipo_rectificativa: Mapped[str | None] = mapped_column(CHAR(1))
    causa_rectificacion: Mapped[str | None] = mapped_column(String(20))
    factura_rectificada_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("facturas.id"))
    base_rectificada: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    cuota_rectificada: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    fecha_expedicion: Mapped[date] = mapped_column(Date)
    fecha_operacion: Mapped[date | None] = mapped_column(Date)
    descripcion_operacion: Mapped[str] = mapped_column(String(500))
    # Copia del emisor al emitir (FR-016)
    emisor_nif: Mapped[str] = mapped_column(CHAR(9))
    emisor_nombre: Mapped[str] = mapped_column(String(120))
    emisor_direccion: Mapped[str] = mapped_column(String(200))
    emisor_codigo_postal: Mapped[str] = mapped_column(CHAR(5))
    emisor_localidad: Mapped[str] = mapped_column(String(100))
    emisor_provincia: Mapped[str | None] = mapped_column(String(100))
    emisor_iban: Mapped[str | None] = mapped_column(String(34))  # NULL antes de la 0006 (R-22)
    # Copia del destinatario al emitir (FR-016)
    cliente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clientes.id"))
    dest_nombre: Mapped[str] = mapped_column(String(120))
    dest_identificacion_pais: Mapped[str] = mapped_column(CHAR(2))
    dest_identificacion_tipo: Mapped[str] = mapped_column(String(3))
    dest_identificacion_numero: Mapped[str] = mapped_column(String(20))
    dest_direccion: Mapped[str] = mapped_column(String(200))
    dest_codigo_postal: Mapped[str] = mapped_column(String(10))
    dest_localidad: Mapped[str] = mapped_column(String(100))
    dest_provincia: Mapped[str | None] = mapped_column(String(100))
    dest_pais: Mapped[str] = mapped_column(CHAR(2))
    clave_regimen: Mapped[str] = mapped_column(CHAR(2))  # 01, o 04 si es de oro de inversión
    modalidad: Mapped[str] = mapped_column(String(20))
    base_total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    cuota_total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    importe_total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    emitida_por_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"))
    emitida_en: Mapped[datetime] = mapped_column(server_default=func.now())
    clave_idempotencia: Mapped[uuid.UUID | None]
    operacion_idempotencia: Mapped[str | None] = mapped_column(String(20))
    origen_idempotencia: Mapped[uuid.UUID | None]
    texto_busqueda: Mapped[str] = mapped_column(Text, Computed(TEXTO_BUSQUEDA, persisted=True))

    lineas: Mapped[list[LineaFactura]] = relationship(
        order_by=LineaFactura.orden, lazy="selectin", viewonly=True
    )
    desgloses: Mapped[list[DesgloseFactura]] = relationship(
        order_by=DesgloseFactura.orden, lazy="selectin", viewonly=True
    )
    emitida_por: Mapped[Usuario] = relationship(lazy="joined", viewonly=True)
