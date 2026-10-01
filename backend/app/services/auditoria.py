"""Registro de eventos de auditoría (FR-020, FR-021).

Nunca se registran secretos: las claves sensibles se eliminan del detalle y del *diff*.
"""

import uuid
from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Final

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.http import Origen
from app.domain.tipos import TipoEvento
from app.models.evento_auditoria import EventoAuditoria
from app.models.usuario import Usuario
from app.repositories import auditoria as repo

ACTOR_CONSOLA: Final = "consola"
CLAVES_EXCLUIDAS: Final = frozenset(
    {"hash_contrasena", "contrasena", "contrasena_temporal", "token", "token_hash", "csrf_token"}
)

type ValorJson = str | int | float | bool | list["ValorJson"] | dict[str, "ValorJson"] | None


def to_json(valor: object) -> ValorJson:
    """Convierte valores de dominio a tipos JSON (UUID, fechas, enumeraciones y Decimal a texto)."""
    match valor:
        case None | bool() | int() | float() | str():
            return valor
        case Decimal():
            # Importes como texto decimal exacto, nunca como float (constitución II, FR-043).
            return format(valor, "f")
        case Enum():
            return to_json(valor.value)
        case uuid.UUID() | datetime() | date():
            return str(valor) if isinstance(valor, uuid.UUID) else valor.isoformat()
        case Mapping():
            return {str(k): to_json(v) for k, v in valor.items() if str(k) not in CLAVES_EXCLUIDAS}
        case list() | tuple() | set() | frozenset():
            return [to_json(v) for v in valor]
        case _:
            return str(valor)


def diff(antes: Mapping[str, object], despues: Mapping[str, object]) -> dict[str, ValorJson]:
    """Campos cambiados como `{campo: [antes, después]}`, sin claves sensibles."""
    cambios: dict[str, ValorJson] = {}
    for campo in sorted(set(antes) | set(despues)):
        if campo in CLAVES_EXCLUIDAS:
            continue
        a, d = antes.get(campo), despues.get(campo)
        if a != d:
            cambios[campo] = [to_json(a), to_json(d)]
    return cambios


async def record_event(
    session: AsyncSession,
    tipo: TipoEvento,
    *,
    origen: Origen | None,
    actor: Usuario | None = None,
    actor_nombre_usuario: str | None = None,
    usuario_afectado_id: uuid.UUID | None = None,
    cliente_id: uuid.UUID | None = None,
    detalle: Mapping[str, object] | None = None,
) -> None:
    detalle_json = {str(k): to_json(v) for k, v in (detalle or {}).items()}
    detalle_json = {k: v for k, v in detalle_json.items() if k not in CLAVES_EXCLUIDAS}
    await repo.insert_event(
        session,
        tipo=tipo,
        actor_id=actor.id if actor else None,
        actor_nombre_usuario=actor.nombre_usuario if actor else actor_nombre_usuario,
        origen_ip=origen.ip if origen else None,
        agente=origen.agente if origen else None,
        usuario_afectado_id=usuario_afectado_id,
        cliente_id=cliente_id,
        detalle=detalle_json,
    )


async def query_events(
    session: AsyncSession,
    *,
    desde: datetime | None = None,
    hasta: datetime | None = None,
    usuario_id: uuid.UUID | None = None,
    tipo: TipoEvento | None = None,
    cliente_id: uuid.UUID | None = None,
    pagina: int = 1,
    tamano: int = 25,
) -> tuple[list[EventoAuditoria], int]:
    return await repo.query_events(
        session,
        desde=desde,
        hasta=hasta,
        usuario_id=usuario_id,
        tipo=tipo,
        cliente_id=cliente_id,
        pagina=pagina,
        tamano=tamano,
    )
