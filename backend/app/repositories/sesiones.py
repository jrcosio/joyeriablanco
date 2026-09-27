"""Acceso a `sesiones` (research R-5)."""

import uuid
from datetime import datetime, timedelta

from sqlalchemy import delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sesion import Sesion

UMBRAL_ACTIVIDAD = timedelta(seconds=60)


async def create(
    session: AsyncSession,
    *,
    usuario_id: uuid.UUID,
    token_hash: str,
    csrf_token: str,
    expira_en: datetime,
    origen_ip: str | None,
    agente: str | None,
) -> Sesion:
    sesion = Sesion(
        usuario_id=usuario_id,
        token_hash=token_hash,
        csrf_token=csrf_token,
        expira_en=expira_en,
        origen_ip=origen_ip,
        agente=agente,
    )
    session.add(sesion)
    await session.flush()
    await session.refresh(sesion)
    return sesion


async def get_by_fingerprint(session: AsyncSession, token_hash: str) -> Sesion | None:
    stmt = select(Sesion).where(Sesion.token_hash == token_hash)
    return (await session.execute(stmt)).unique().scalar_one_or_none()


async def touch(session: AsyncSession, sesion: Sesion, momento: datetime) -> None:
    """Registra actividad a lo sumo una vez por minuto para no escribir en cada petición."""
    if momento - sesion.ultima_actividad_en >= UMBRAL_ACTIVIDAD:
        sesion.ultima_actividad_en = momento
        await session.flush()


async def revoke(session: AsyncSession, sesion: Sesion, momento: datetime) -> None:
    sesion.revocada_en = momento
    await session.flush()


async def revoke_all(
    session: AsyncSession,
    usuario_id: uuid.UUID,
    momento: datetime,
    *,
    excepto: uuid.UUID | None = None,
) -> int:
    stmt = (
        update(Sesion)
        .where(Sesion.usuario_id == usuario_id, Sesion.revocada_en.is_(None))
        .values(revocada_en=momento)
    )
    if excepto is not None:
        stmt = stmt.where(Sesion.id != excepto)
    resultado = await session.execute(stmt.execution_options(synchronize_session="fetch"))
    return int(getattr(resultado, "rowcount", 0) or 0)


async def purge(session: AsyncSession, limite: datetime) -> int:
    """Borra las sesiones revocadas o caducadas antes de `limite` (FR-054)."""
    stmt = delete(Sesion).where(
        or_(
            Sesion.revocada_en < limite,
            Sesion.expira_en < limite,
            Sesion.ultima_actividad_en < limite,
        )
    )
    resultado = await session.execute(stmt)
    return int(getattr(resultado, "rowcount", 0) or 0)
