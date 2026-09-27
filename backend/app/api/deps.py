"""Dependencias de la API: BD, sesión, CSRF, origen y roles (research R-6, R-9).

Denegación por defecto: todo router de /api/v1 salvo el de sesión monta `get_current_session`.
"""

from typing import Annotated, Final

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_db
from app.core.errors import ContrasenaTemporalPendiente, CsrfNoValido, SinPermiso
from app.core.http import Origen, check_origin, request_origin
from app.core.security import constant_time_equals
from app.models.sesion import Sesion
from app.services import auth

METODOS_MUTANTES: Final = frozenset({"POST", "PUT", "PATCH", "DELETE"})

DbDep = Annotated[AsyncSession, Depends(get_db)]


def get_origin(request: Request) -> Origen:
    return request_origin(request)


OrigenDep = Annotated[Origen, Depends(get_origin)]


def require_origin(request: Request) -> None:
    check_origin(request)


async def _sesion_verificada(request: Request, db: AsyncSession) -> Sesion:
    token = request.cookies.get(get_settings().cookie_sesion)
    sesion = await auth.validate_session(db, token)
    if request.method in METODOS_MUTANTES:
        check_origin(request)
        csrf = request.headers.get("x-csrf-token")
        if not csrf or not constant_time_equals(csrf, sesion.csrf_token):
            raise CsrfNoValido
    return sesion


async def get_session_allowing_temporary(request: Request, db: DbDep) -> Sesion:
    """Sesión válida aunque la contraseña sea temporal (ver sesión, cerrarla, cambiarla)."""
    return await _sesion_verificada(request, db)


async def get_current_session(request: Request, db: DbDep) -> Sesion:
    """Sesión válida y sin contraseña temporal pendiente (FR-009)."""
    sesion = await _sesion_verificada(request, db)
    if sesion.usuario.contrasena_temporal:
        raise ContrasenaTemporalPendiente
    return sesion


SessionAllowingTemporary = Annotated[Sesion, Depends(get_session_allowing_temporary)]
CurrentSession = Annotated[Sesion, Depends(get_current_session)]


async def require_admin(sesion: CurrentSession) -> Sesion:
    if not sesion.usuario.es_admin:
        raise SinPermiso
    return sesion


AdminSession = Annotated[Sesion, Depends(require_admin)]
