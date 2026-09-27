"""Esquemas de usuario (contracts/openapi.yaml)."""

import uuid
from datetime import datetime

from app.core.tiempo import ahora
from app.domain.tipos import Rol
from app.models.usuario import Usuario
from app.schemas.comunes import SalidaBase


class UsuarioReferencia(SalidaBase):
    id: uuid.UUID
    nombre: str


class UsuarioSalida(SalidaBase):
    id: uuid.UUID
    nombre_usuario: str
    nombre: str
    rol: Rol
    activo: bool
    contrasena_temporal: bool
    bloqueado: bool
    ultimo_acceso_en: datetime | None
    creado_en: datetime

    @classmethod
    def from_model(cls, usuario: Usuario) -> "UsuarioSalida":
        return cls(
            id=usuario.id,
            nombre_usuario=usuario.nombre_usuario,
            nombre=usuario.nombre,
            rol=Rol(usuario.rol),
            activo=usuario.activo,
            contrasena_temporal=usuario.contrasena_temporal,
            bloqueado=usuario.bloqueado_hasta is not None and usuario.bloqueado_hasta > ahora(),
            ultimo_acceso_en=usuario.ultimo_acceso_en,
            creado_en=usuario.creado_en,
        )
