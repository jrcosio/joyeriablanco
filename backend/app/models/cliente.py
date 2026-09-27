"""Cliente (data-model §clientes; FR-023 a FR-030)."""

import uuid
from datetime import datetime

from sqlalchemy import (
    CHAR,
    Boolean,
    CheckConstraint,
    Computed,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.tipos import TipoCliente, TipoIdentificacion, sql_in
from app.models.base import Base, UuidPkMixin
from app.models.provincia import Provincia
from app.models.usuario import Usuario

TEXTO_BUSQUEDA = (
    "inmutable_unaccent(lower(nombre || ' ' || identificacion_numero || ' ' || "
    "coalesce(localidad, '')))"
)


class Cliente(UuidPkMixin, Base):
    __tablename__ = "clientes"

    tipo: Mapped[str] = mapped_column(String(12))
    nombre: Mapped[str] = mapped_column(String(120))
    identificacion_pais: Mapped[str] = mapped_column(CHAR(2), server_default=text("'ES'"))
    identificacion_tipo: Mapped[str] = mapped_column(String(3))
    identificacion_numero: Mapped[str] = mapped_column(String(20))
    direccion: Mapped[str | None] = mapped_column(String(200))
    codigo_postal: Mapped[str | None] = mapped_column(String(10))
    localidad: Mapped[str | None] = mapped_column(String(100))
    provincia_codigo: Mapped[str | None] = mapped_column(ForeignKey("provincias.codigo"))
    provincia_texto: Mapped[str | None] = mapped_column(String(100))
    pais_residencia: Mapped[str] = mapped_column(CHAR(2), server_default=text("'ES'"))
    telefono: Mapped[str | None] = mapped_column(String(30))
    correo: Mapped[str | None] = mapped_column(String(254))
    observaciones: Mapped[str | None] = mapped_column(Text)
    activo: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(server_default=func.now())
    creado_por_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"))
    actualizado_en: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
    actualizado_por_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"))
    texto_busqueda: Mapped[str] = mapped_column(Text, Computed(TEXTO_BUSQUEDA, persisted=True))

    provincia: Mapped[Provincia | None] = relationship(lazy="joined")
    creado_por: Mapped[Usuario] = relationship(foreign_keys=[creado_por_id], lazy="joined")
    actualizado_por: Mapped[Usuario] = relationship(
        foreign_keys=[actualizado_por_id], lazy="joined"
    )

    __mapper_args__ = {"version_id_col": version}  # noqa: RUF012 — concurrencia optimista (FR-030)
    __table_args__ = (
        CheckConstraint(f"tipo IN {sql_in(TipoCliente)}", name="tipo"),
        CheckConstraint(
            f"identificacion_tipo IN {sql_in(TipoIdentificacion)}", name="identificacion_tipo"
        ),
        CheckConstraint("length(trim(nombre)) > 0", name="nombre_no_vacio"),
        CheckConstraint(
            "identificacion_tipo <> 'NIF' OR identificacion_pais = 'ES'", name="nif_solo_espana"
        ),
        CheckConstraint(
            "identificacion_pais <> 'ES' OR identificacion_tipo IN ('NIF', '03')",
            name="espana_nif_o_pasaporte",
        ),
        CheckConstraint(
            "identificacion_tipo <> 'NIF' OR identificacion_numero ~ '^[0-9A-Z]{9}$'",
            name="forma_nif",
        ),
        CheckConstraint(
            "pais_residencia = 'ES' OR provincia_codigo IS NULL", name="provincia_espana"
        ),
        CheckConstraint(
            "pais_residencia <> 'ES' OR provincia_texto IS NULL", name="provincia_texto_extranjero"
        ),
        CheckConstraint(
            "pais_residencia <> 'ES' OR codigo_postal IS NULL OR codigo_postal ~ '^[0-9]{5}$'",
            name="codigo_postal_espana",
        ),
        CheckConstraint("length(observaciones) <= 2000", name="observaciones_longitud"),
        UniqueConstraint(
            "identificacion_pais",
            "identificacion_tipo",
            "identificacion_numero",
            name="uq_clientes_identificacion",
        ),
        Index(
            "ix_clientes_texto_busqueda",
            "texto_busqueda",
            postgresql_using="gin",
            postgresql_ops={"texto_busqueda": "gin_trgm_ops"},
        ),
        Index("ix_clientes_activo_nombre", "activo", "nombre", "id"),
        Index("ix_clientes_provincia_codigo", "provincia_codigo"),
        Index("ix_clientes_tipo", "tipo"),
        Index("ix_clientes_creado_en", "creado_en", "id"),
    )
