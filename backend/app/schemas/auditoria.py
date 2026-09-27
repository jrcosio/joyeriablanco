"""Esquemas de la consulta de auditoría (contracts/openapi.yaml §EventoSalida)."""

import uuid
from datetime import datetime
from typing import Any

from app.domain.tipos import TipoEvento
from app.models.evento_auditoria import EventoAuditoria
from app.models.usuario import Usuario
from app.schemas.comunes import SalidaBase
from app.schemas.usuario import UsuarioReferencia


class EventoSalida(SalidaBase):
    id: uuid.UUID
    ocurrido_en: datetime
    tipo: TipoEvento
    actor: UsuarioReferencia | None
    actor_nombre_usuario: str | None
    origen_ip: str | None
    agente: str | None
    usuario_afectado: UsuarioReferencia | None
    cliente_id: uuid.UUID | None
    detalle: dict[str, Any]

    @classmethod
    def from_model(cls, evento: EventoAuditoria) -> "EventoSalida":
        def ref(usuario: Usuario | None) -> UsuarioReferencia | None:
            return UsuarioReferencia.from_model(usuario) if usuario else None

        return cls(
            id=evento.id,
            ocurrido_en=evento.ocurrido_en,
            tipo=TipoEvento(evento.tipo),
            actor=ref(evento.actor),
            actor_nombre_usuario=evento.actor_nombre_usuario,
            origen_ip=evento.origen_ip,
            agente=evento.agente,
            usuario_afectado=ref(evento.usuario_afectado),
            cliente_id=evento.cliente_id,
            detalle=evento.detalle,
        )
