"""Configuración de facturación: fila única (data-model §configuracion_facturacion; FR-001)."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CHAR, ForeignKey, Integer, Numeric, SmallInteger, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.provincia import Provincia
from app.models.usuario import Usuario

ID_UNICO = 1


class ConfiguracionFacturacion(Base):
    __tablename__ = "configuracion_facturacion"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, server_default=text("1"))
    iva_por_defecto: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    modalidad: Mapped[str | None] = mapped_column(String(20))
    emisor_nombre: Mapped[str | None] = mapped_column(String(120))
    emisor_nif: Mapped[str | None] = mapped_column(CHAR(9))
    emisor_direccion: Mapped[str | None] = mapped_column(String(200))
    emisor_codigo_postal: Mapped[str | None] = mapped_column(CHAR(5))
    emisor_localidad: Mapped[str | None] = mapped_column(String(100))
    emisor_provincia_codigo: Mapped[str | None] = mapped_column(ForeignKey("provincias.codigo"))
    emisor_iban: Mapped[str | None] = mapped_column(String(34))  # opcional (R-22)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    actualizado_en: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
    actualizado_por_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))

    emisor_provincia: Mapped[Provincia | None] = relationship(lazy="joined")
    actualizado_por: Mapped[Usuario | None] = relationship(lazy="joined")

    __mapper_args__ = {"version_id_col": version}  # noqa: RUF012 — concurrencia optimista
