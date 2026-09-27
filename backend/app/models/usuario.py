"""Usuario del sistema (data-model §usuarios).

Un usuario eliminado conserva su fila como lápida (`eliminado_en`): así siguen siendo válidas las
referencias desde la auditoría inalterable y desde lo que registró (FR-061, research R-21).
"""

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, Index, SmallInteger, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.tipos import Rol, sql_in
from app.models.base import Base, TimestampsMixin, UuidPkMixin


class Usuario(UuidPkMixin, TimestampsMixin, Base):
    __tablename__ = "usuarios"

    nombre_usuario: Mapped[str] = mapped_column(String(50))
    nombre: Mapped[str] = mapped_column(String(120))
    rol: Mapped[str] = mapped_column(String(20))
    hash_contrasena: Mapped[str] = mapped_column(Text)
    contrasena_temporal: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    contrasena_temporal_expira_en: Mapped[datetime | None]
    activo: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    eliminado_en: Mapped[datetime | None]
    intentos_fallidos: Mapped[int] = mapped_column(SmallInteger, server_default=text("0"))
    bloqueado_hasta: Mapped[datetime | None]
    ultimo_acceso_en: Mapped[datetime | None]

    __table_args__ = (
        CheckConstraint(f"rol IN {sql_in(Rol)}", name="rol"),
        CheckConstraint("intentos_fallidos >= 0", name="intentos_no_negativos"),
        CheckConstraint("nombre_usuario ~ '^[a-z0-9._-]{3,50}$'", name="formato_nombre_usuario"),
        CheckConstraint("length(trim(nombre)) > 0", name="nombre_no_vacio"),
        CheckConstraint("eliminado_en IS NULL OR NOT activo", name="eliminado_inactivo"),
        Index(
            "uq_usuarios_nombre_usuario_lower",
            func.lower(nombre_usuario),
            unique=True,
            postgresql_where=text("eliminado_en IS NULL"),
        ),
    )

    @property
    def es_admin(self) -> bool:
        return self.rol == Rol.ADMINISTRADOR

    @property
    def eliminado(self) -> bool:
        return self.eliminado_en is not None
