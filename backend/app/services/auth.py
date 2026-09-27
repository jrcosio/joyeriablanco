"""Autenticación y sesiones de servidor (US1; FR-003 a FR-011, FR-019; research R-5 a R-8)."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import NoReturn

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import (
    CampoError,
    CredencialesNoValidas,
    DatosNoValidos,
    LimiteOrigen,
    NoAutenticado,
)
from app.core.http import Origen
from app.core.security import (
    dummy_hash,
    hash_password,
    needs_rehash,
    new_csrf_token,
    new_session_token,
    token_fingerprint,
    verify_password,
)
from app.core.tiempo import ahora
from app.domain.contrasenas import validate_password
from app.domain.tipos import TipoEvento
from app.models.sesion import Sesion
from app.models.usuario import Usuario
from app.repositories import auditoria as auditoria_repo
from app.repositories import sesiones as sesiones_repo
from app.repositories import usuarios as usuarios_repo
from app.services.auditoria import record_event

MAX_NOMBRE_AUDITADO = 50


@dataclass(frozen=True, slots=True)
class SesionAbierta:
    sesion: Sesion
    token: str  # valor de la cookie; nunca se guarda en claro


async def _rechazar(
    db: AsyncSession,
    *,
    nombre_usuario: str,
    origen: Origen,
    motivo: str,
    usuario: Usuario | None = None,
) -> NoReturn:
    """Audita el fallo, lo persiste aunque la respuesta sea un error y responde genéricamente."""
    await record_event(
        db,
        TipoEvento.ACCESO_FALLIDO,
        origen=origen,
        actor_nombre_usuario=nombre_usuario[:MAX_NOMBRE_AUDITADO],
        usuario_afectado_id=usuario.id if usuario else None,
        detalle={"motivo": motivo},
    )
    await db.commit()
    raise CredencialesNoValidas


async def _comprobar_limite_origen(
    db: AsyncSession, *, nombre_usuario: str, origen: Origen, momento: datetime
) -> None:
    if origen.ip is None:
        return
    settings = get_settings()
    fallos = await auditoria_repo.count_by_origin_since(
        db,
        origen_ip=origen.ip,
        tipo=TipoEvento.ACCESO_FALLIDO,
        desde=momento - timedelta(minutes=settings.limite_origen_ventana_minutos),
    )
    if fallos >= settings.limite_origen_intentos:
        await record_event(
            db,
            TipoEvento.ACCESO_LIMITADO,
            origen=origen,
            actor_nombre_usuario=nombre_usuario[:MAX_NOMBRE_AUDITADO],
        )
        await db.commit()
        raise LimiteOrigen


async def login(
    db: AsyncSession, *, nombre_usuario: str, contrasena: str, origen: Origen
) -> SesionAbierta:
    settings = get_settings()
    momento = ahora()
    await _comprobar_limite_origen(
        db, nombre_usuario=nombre_usuario, origen=origen, momento=momento
    )

    usuario = await usuarios_repo.get_by_nombre_usuario(db, nombre_usuario)
    if usuario is None:
        verify_password(dummy_hash(), contrasena)  # mismo coste que un usuario real (FR-007)
        await _rechazar(
            db, nombre_usuario=nombre_usuario, origen=origen, motivo="usuario_inexistente"
        )

    correcta = verify_password(usuario.hash_contrasena, contrasena)

    if usuario.bloqueado_hasta is not None and usuario.bloqueado_hasta <= momento:
        usuario.bloqueado_hasta = None  # el bloqueo ha expirado: el contador se reinicia
        usuario.intentos_fallidos = 0
    if usuario.bloqueado_hasta is not None:
        await _rechazar(
            db,
            nombre_usuario=nombre_usuario,
            origen=origen,
            motivo="cuenta_bloqueada",
            usuario=usuario,
        )
    if not usuario.activo:
        await _rechazar(
            db,
            nombre_usuario=nombre_usuario,
            origen=origen,
            motivo="cuenta_desactivada",
            usuario=usuario,
        )
    if not correcta:
        usuario.intentos_fallidos += 1
        if usuario.intentos_fallidos >= settings.bloqueo_intentos:
            usuario.bloqueado_hasta = momento + timedelta(minutes=settings.bloqueo_minutos)
            await record_event(
                db,
                TipoEvento.ACCESO_BLOQUEADO,
                origen=origen,
                actor_nombre_usuario=usuario.nombre_usuario,
                usuario_afectado_id=usuario.id,
                detalle={"intentos": usuario.intentos_fallidos},
            )
        await _rechazar(
            db,
            nombre_usuario=nombre_usuario,
            origen=origen,
            motivo="contrasena_incorrecta",
            usuario=usuario,
        )
    if (
        usuario.contrasena_temporal
        and usuario.contrasena_temporal_expira_en is not None
        and usuario.contrasena_temporal_expira_en <= momento
    ):
        await _rechazar(
            db,
            nombre_usuario=nombre_usuario,
            origen=origen,
            motivo="contrasena_temporal_caducada",
            usuario=usuario,
        )

    usuario.intentos_fallidos = 0
    usuario.bloqueado_hasta = None
    usuario.ultimo_acceso_en = momento
    if needs_rehash(usuario.hash_contrasena):
        usuario.hash_contrasena = hash_password(contrasena)

    token = new_session_token()
    sesion = await sesiones_repo.create(
        db,
        usuario_id=usuario.id,
        token_hash=token_fingerprint(token),
        csrf_token=new_csrf_token(),
        expira_en=momento + settings.duracion_maxima,
        origen_ip=origen.ip,
        agente=origen.agente,
    )
    await record_event(db, TipoEvento.ACCESO_CORRECTO, origen=origen, actor=usuario)
    return SesionAbierta(sesion=sesion, token=token)


async def validate_session(db: AsyncSession, token: str | None) -> Sesion:
    """Devuelve la sesión vigente o lanza `NoAutenticado` (FR-003, FR-005, FR-016)."""
    if not token:
        raise NoAutenticado
    sesion = await sesiones_repo.get_by_fingerprint(db, token_fingerprint(token))
    momento = ahora()
    if (
        sesion is None
        or sesion.revocada_en is not None
        or momento >= sesion.expira_en
        or momento >= sesion.ultima_actividad_en + get_settings().inactividad
        or not sesion.usuario.activo
    ):
        raise NoAutenticado
    await sesiones_repo.touch(db, sesion, momento)
    return sesion


async def logout(db: AsyncSession, sesion: Sesion, origen: Origen) -> None:
    await sesiones_repo.revoke(db, sesion, ahora())
    await record_event(db, TipoEvento.CIERRE_SESION, origen=origen, actor=sesion.usuario)


async def change_own_password(
    db: AsyncSession, sesion: Sesion, *, actual: str, nueva: str, origen: Origen
) -> None:
    """Cambio de la propia contraseña: revoca las demás sesiones y conserva la actual (FR-019)."""
    usuario = sesion.usuario
    if not verify_password(usuario.hash_contrasena, actual):
        raise DatosNoValidos(
            errores=[CampoError("contrasena_actual", "La contraseña actual no es correcta.")]
        )
    motivos = validate_password(nueva, usuario.nombre_usuario)
    if nueva == actual:
        motivos.append("Debe ser distinta de la actual.")
    if motivos:
        raise DatosNoValidos(errores=[CampoError("contrasena_nueva", " ".join(motivos))])

    momento = ahora()
    usuario.hash_contrasena = hash_password(nueva)
    usuario.contrasena_temporal = False
    usuario.contrasena_temporal_expira_en = None
    await sesiones_repo.revoke_all(db, usuario.id, momento, excepto=sesion.id)
    await record_event(db, TipoEvento.CONTRASENA_CAMBIADA, origen=origen, actor=usuario)


async def purge_sessions(db: AsyncSession) -> int:
    limite = ahora() - timedelta(days=get_settings().sesion_purga_dias)
    return await sesiones_repo.purge(db, limite)
