"""Acceso a `eventos_auditoria`: solo inserción y consultas (la BD impide modificarlos)."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.tipos import TipoEvento
from app.models.evento_auditoria import EventoAuditoria


async def insert_event(
    session: AsyncSession,
    *,
    tipo: TipoEvento,
    actor_id: uuid.UUID | None,
    actor_nombre_usuario: str | None,
    origen_ip: str | None,
    agente: str | None,
    usuario_afectado_id: uuid.UUID | None,
    cliente_id: uuid.UUID | None,
    detalle: dict[str, Any],
) -> EventoAuditoria:
    evento = EventoAuditoria(
        tipo=tipo.value,
        actor_id=actor_id,
        actor_nombre_usuario=actor_nombre_usuario,
        origen_ip=origen_ip,
        agente=agente,
        usuario_afectado_id=usuario_afectado_id,
        cliente_id=cliente_id,
        detalle=detalle,
    )
    session.add(evento)
    await session.flush()
    return evento


async def count_by_origin_since(
    session: AsyncSession, *, origen_ip: str, tipo: TipoEvento, desde: datetime
) -> int:
    stmt = select(func.count()).where(
        EventoAuditoria.origen_ip == origen_ip,
        EventoAuditoria.tipo == tipo.value,
        EventoAuditoria.ocurrido_en >= desde,
    )
    return int((await session.execute(stmt)).scalar_one())
