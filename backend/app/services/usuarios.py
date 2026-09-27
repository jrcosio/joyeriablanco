"""Gestión de usuarios (US1: operaciones de consola; US5: gestión por el administrador)."""

import re
import uuid
from datetime import timedelta
from typing import Final

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import (
    Autogestion,
    CampoError,
    DatosNoValidos,
    Duplicado,
    NoEncontrado,
    UltimoAdministrador,
)
from app.core.http import Origen
from app.core.security import hash_password
from app.core.tiempo import ahora
from app.domain.contrasenas import generate_temporary_password
from app.domain.tipos import Rol, TipoEvento
from app.models.usuario import Usuario
from app.repositories import sesiones as sesiones_repo
from app.repositories import usuarios as usuarios_repo
from app.services.auditoria import ACTOR_CONSOLA, record_event

FORMATO_NOMBRE_USUARIO: Final = re.compile(r"^[a-z0-9._-]{3,50}$")
DETALLE_CONSOLA: Final = {"origen": "consola"}


def normalize_nombre_usuario(nombre_usuario: str) -> str:
    normalizado = nombre_usuario.strip().lower()
    if not FORMATO_NOMBRE_USUARIO.fullmatch(normalizado):
        raise DatosNoValidos(
            errores=[
                CampoError(
                    "nombre_usuario",
                    "De 3 a 50 caracteres: letras sin tildes, números, punto, guion o guion bajo.",
                )
            ]
        )
    return normalizado


def _asignar_temporal(usuario: Usuario) -> str:
    temporal = generate_temporary_password()
    usuario.hash_contrasena = hash_password(temporal)
    usuario.contrasena_temporal = True
    usuario.contrasena_temporal_expira_en = ahora() + timedelta(
        hours=get_settings().contrasena_temporal_horas
    )
    return temporal


async def _crear(
    db: AsyncSession,
    *,
    nombre_usuario: str,
    nombre: str,
    rol: Rol,
    actor: Usuario | None,
    origen: Origen | None,
) -> tuple[Usuario, str]:
    normalizado = normalize_nombre_usuario(nombre_usuario)
    nombre_limpio = nombre.strip()
    if not nombre_limpio:
        raise DatosNoValidos(errores=[CampoError("nombre", "Campo obligatorio.")])
    if await usuarios_repo.get_by_nombre_usuario(db, normalizado) is not None:
        raise Duplicado("Ya existe un usuario con ese nombre de usuario.")
    usuario = Usuario(nombre_usuario=normalizado, nombre=nombre_limpio, rol=rol.value)
    temporal = _asignar_temporal(usuario)
    await usuarios_repo.add(db, usuario)
    await record_event(
        db,
        TipoEvento.USUARIO_CREADO,
        origen=origen,
        actor=actor,
        actor_nombre_usuario=None if actor else ACTOR_CONSOLA,
        usuario_afectado_id=usuario.id,
        detalle={"nombre_usuario": normalizado, "rol": rol, **({} if actor else DETALLE_CONSOLA)},
    )
    return usuario, temporal


async def _restablecer(
    db: AsyncSession, usuario: Usuario, *, actor: Usuario | None, origen: Origen | None
) -> str:
    """Contraseña temporal nueva, bloqueo levantado y todas las sesiones revocadas (FR-016)."""
    temporal = _asignar_temporal(usuario)
    usuario.intentos_fallidos = 0
    usuario.bloqueado_hasta = None
    await sesiones_repo.revoke_all(db, usuario.id, ahora())
    await record_event(
        db,
        TipoEvento.CONTRASENA_RESTABLECIDA,
        origen=origen,
        actor=actor,
        actor_nombre_usuario=None if actor else ACTOR_CONSOLA,
        usuario_afectado_id=usuario.id,
        detalle={} if actor else DETALLE_CONSOLA,
    )
    await db.flush()
    return temporal


# ------------------------------------------------------------------ consola (FR-018)


async def create_first_admin(
    db: AsyncSession, *, nombre_usuario: str, nombre: str
) -> tuple[Usuario, str]:
    return await _crear(
        db,
        nombre_usuario=nombre_usuario,
        nombre=nombre,
        rol=Rol.ADMINISTRADOR,
        actor=None,
        origen=None,
    )


async def reset_admin_from_console(db: AsyncSession, *, nombre_usuario: str) -> str:
    usuario = await usuarios_repo.get_by_nombre_usuario(db, nombre_usuario.strip())
    if usuario is None or not usuario.es_admin:
        raise NoEncontrado("No existe ningún administrador con ese nombre de usuario.")
    return await _restablecer(db, usuario, actor=None, origen=None)


async def create_usuario(
    db: AsyncSession,
    *,
    nombre_usuario: str,
    nombre: str,
    rol: Rol,
    actor: Usuario | None,
    origen: Origen | None,
) -> tuple[Usuario, str]:
    """Alta de usuario con contraseña temporal generada (FR-014, FR-015)."""
    return await _crear(
        db, nombre_usuario=nombre_usuario, nombre=nombre, rol=rol, actor=actor, origen=origen
    )


# ------------------------------------------------------------------ gestión por el administrador


async def list_usuarios(db: AsyncSession) -> list[Usuario]:
    return await usuarios_repo.list_usuarios(db)


async def get_usuario(db: AsyncSession, usuario_id: uuid.UUID) -> Usuario:
    usuario = await usuarios_repo.get(db, usuario_id)
    if usuario is None:
        raise NoEncontrado("El usuario no existe.")
    return usuario


async def _exigir_otro_administrador(db: AsyncSession, usuario: Usuario) -> None:
    """Regla del último administrador (FR-017), segura frente a concurrencia (FOR UPDATE)."""
    activos = await usuarios_repo.lock_active_admins(db)
    await db.refresh(usuario)  # relee el estado tras obtener el bloqueo
    if usuario.id in activos and len(activos) <= 1:
        raise UltimoAdministrador


async def update_usuario(
    db: AsyncSession,
    usuario_id: uuid.UUID,
    *,
    nombre: str | None = None,
    rol: Rol | None = None,
    actor: Usuario,
    origen: Origen,
) -> Usuario:
    usuario = await get_usuario(db, usuario_id)
    if nombre is not None:
        nombre_limpio = nombre.strip()
        if not nombre_limpio:
            raise DatosNoValidos(errores=[CampoError("nombre", "Campo obligatorio.")])
        usuario.nombre = nombre_limpio
    if rol is not None and rol != usuario.rol:
        if usuario.id == actor.id:
            raise Autogestion
        if usuario.rol == Rol.ADMINISTRADOR:
            await _exigir_otro_administrador(db, usuario)
        rol_anterior = usuario.rol
        usuario.rol = rol.value
        await sesiones_repo.revoke_all(db, usuario.id, ahora())  # FR-016
        await record_event(
            db,
            TipoEvento.USUARIO_ROL_CAMBIADO,
            origen=origen,
            actor=actor,
            usuario_afectado_id=usuario.id,
            detalle={"rol": [rol_anterior, rol.value]},
        )
    await db.flush()
    await db.refresh(usuario)
    return usuario


async def deactivate_usuario(
    db: AsyncSession, usuario_id: uuid.UUID, *, actor: Usuario, origen: Origen
) -> Usuario:
    usuario = await get_usuario(db, usuario_id)
    if usuario.id == actor.id:
        raise Autogestion
    if not usuario.activo:
        return usuario
    if usuario.rol == Rol.ADMINISTRADOR:
        await _exigir_otro_administrador(db, usuario)
    usuario.activo = False
    await sesiones_repo.revoke_all(db, usuario.id, ahora())  # FR-016
    await record_event(
        db,
        TipoEvento.USUARIO_DESACTIVADO,
        origen=origen,
        actor=actor,
        usuario_afectado_id=usuario.id,
    )
    await db.flush()
    return usuario


async def reactivate_usuario(
    db: AsyncSession, usuario_id: uuid.UUID, *, actor: Usuario, origen: Origen
) -> Usuario:
    usuario = await get_usuario(db, usuario_id)
    if usuario.activo:
        return usuario
    usuario.activo = True
    await record_event(
        db,
        TipoEvento.USUARIO_REACTIVADO,
        origen=origen,
        actor=actor,
        usuario_afectado_id=usuario.id,
    )
    await db.flush()
    return usuario


async def reset_password(
    db: AsyncSession, usuario_id: uuid.UUID, *, actor: Usuario, origen: Origen
) -> tuple[Usuario, str]:
    usuario = await get_usuario(db, usuario_id)
    temporal = await _restablecer(db, usuario, actor=actor, origen=origen)
    return usuario, temporal
