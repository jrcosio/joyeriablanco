"""Sesión de servidor (data-model §sesiones, research R-5)."""

import uuid
from datetime import datetime

from sqlalchemy import CHAR, ForeignKey, Index, String, func, text
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UuidPkMixin
from app.models.usuario import Usuario


class Sesion(UuidPkMixin, Base):
    __tablename__ = "sesiones"

    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(CHAR(64), unique=True)
    csrf_token: Mapped[str] = mapped_column(String(64))
    creada_en: Mapped[datetime] = mapped_column(server_default=func.now())
    ultima_actividad_en: Mapped[datetime] = mapped_column(server_default=func.now())
    expira_en: Mapped[datetime]
    revocada_en: Mapped[datetime | None]
    origen_ip: Mapped[str | None] = mapped_column(INET)
    agente: Mapped[str | None] = mapped_column(String(500))

    usuario: Mapped[Usuario] = relationship(lazy="joined")

    __table_args__ = (
        Index(
            "ix_sesiones_usuario_vigentes",
            "usuario_id",
            postgresql_where=text("revocada_en IS NULL"),
        ),
    )
