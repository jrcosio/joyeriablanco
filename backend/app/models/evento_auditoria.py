"""Evento de auditoría de solo inserción (data-model §eventos_auditoria, research R-10).

La inalterabilidad se impone en la BD: REVOKE al rol de aplicación y triggers que lanzan una
excepción ante UPDATE, DELETE o TRUNCATE (migración 0002).
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, func, text
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.tipos import TipoEvento, sql_in
from app.models.base import Base, UuidPkMixin


class EventoAuditoria(UuidPkMixin, Base):
    __tablename__ = "eventos_auditoria"

    ocurrido_en: Mapped[datetime] = mapped_column(server_default=func.now())
    tipo: Mapped[str] = mapped_column(String(40))
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    actor_nombre_usuario: Mapped[str | None] = mapped_column(String(50))
    origen_ip: Mapped[str | None] = mapped_column(INET)
    agente: Mapped[str | None] = mapped_column(String(500))
    usuario_afectado_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    cliente_id: Mapped[uuid.UUID | None]  # sin FK: sobrevive al borrado físico del cliente
    detalle: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))

    __table_args__ = (
        CheckConstraint(f"tipo IN {sql_in(TipoEvento)}", name="tipo"),
        Index("ix_eventos_auditoria_ocurrido_en", ocurrido_en.desc()),
        Index("ix_eventos_auditoria_origen", "origen_ip", "tipo", "ocurrido_en"),
        Index("ix_eventos_auditoria_actor", "actor_id", ocurrido_en.desc()),
        Index("ix_eventos_auditoria_cliente", "cliente_id", ocurrido_en.desc()),
        Index("ix_eventos_auditoria_tipo", "tipo", ocurrido_en.desc()),
    )
