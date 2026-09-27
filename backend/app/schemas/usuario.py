"""Esquemas de usuario (contracts/openapi.yaml)."""

import uuid
from datetime import datetime

from pydantic import Field, model_validator

from app.core.tiempo import ahora
from app.domain.tipos import Rol
from app.models.usuario import Usuario
from app.schemas.comunes import EntradaBase, SalidaBase


class UsuarioReferencia(SalidaBase):
    id: uuid.UUID
    nombre: str
    eliminado: bool  # la web muestra «Nombre (eliminado)» (FR-061)

    @classmethod
    def from_model(cls, usuario: Usuario) -> "UsuarioReferencia":
        return cls(id=usuario.id, nombre=usuario.nombre, eliminado=usuario.eliminado)


class UsuarioSalida(SalidaBase):
    id: uuid.UUID
    nombre_usuario: str
    nombre: str
    rol: Rol
    activo: bool
    eliminado: bool
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
            eliminado=usuario.eliminado,
            contrasena_temporal=usuario.contrasena_temporal,
            bloqueado=usuario.bloqueado_hasta is not None and usuario.bloqueado_hasta > ahora(),
            ultimo_acceso_en=usuario.ultimo_acceso_en,
            creado_en=usuario.creado_en,
        )


class UsuarioAltaEntrada(EntradaBase):
    nombre_usuario: str = Field(pattern=r"^[a-zA-Z0-9._-]{3,50}$")
    nombre: str = Field(min_length=1, max_length=120)
    rol: Rol


class UsuarioEdicionEntrada(EntradaBase):
    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    rol: Rol | None = None

    @model_validator(mode="after")
    def _algun_cambio(self) -> "UsuarioEdicionEntrada":
        if self.nombre is None and self.rol is None:
            msg = "Indica al menos un cambio."
            raise ValueError(msg)
        return self


class UsuarioConContrasenaTemporalSalida(SalidaBase):
    usuario: UsuarioSalida
    contrasena_temporal: str
