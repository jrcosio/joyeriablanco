"""Esquemas de sesión y cuenta (contracts/openapi.yaml)."""

from datetime import datetime

from pydantic import Field

from app.core.config import get_settings
from app.models.sesion import Sesion
from app.schemas.comunes import EntradaBase, SalidaBase
from app.schemas.usuario import UsuarioSalida


class CredencialesEntrada(EntradaBase):
    nombre_usuario: str = Field(min_length=1, max_length=50)
    contrasena: str = Field(min_length=1, max_length=128)


class CambioContrasenaEntrada(EntradaBase):
    contrasena_actual: str = Field(min_length=1, max_length=128)
    contrasena_nueva: str = Field(min_length=12, max_length=128)


class SesionSalida(SalidaBase):
    usuario: UsuarioSalida
    csrf_token: str
    expira_en: datetime
    inactividad_segundos: int

    @classmethod
    def from_model(cls, sesion: Sesion) -> "SesionSalida":
        return cls(
            usuario=UsuarioSalida.from_model(sesion.usuario),
            csrf_token=sesion.csrf_token,
            expira_en=sesion.expira_en,
            inactividad_segundos=int(get_settings().inactividad.total_seconds()),
        )
