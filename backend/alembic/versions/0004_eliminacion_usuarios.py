"""Eliminación de usuarios desactivados con lápida (FR-061, research R-21).

También normaliza los nombres de las restricciones CHECK de 0002 y 0003: la convención de nombres
del `MetaData` les antepuso el prefijo por segunda vez (`ck_usuarios_ck_usuarios_rol`). Pasan a
llamarse como los declara el modelo (`ck_usuarios_rol`). Es un cambio solo de catálogo.

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TIPOS_0002 = (
    "'acceso_correcto', 'acceso_fallido', 'acceso_bloqueado', 'acceso_limitado', "
    "'cierre_sesion', 'contrasena_cambiada', 'contrasena_restablecida', 'usuario_creado', "
    "'usuario_rol_cambiado', 'usuario_desactivado', 'usuario_reactivado', 'cliente_creado', "
    "'cliente_editado', 'cliente_desactivado', 'cliente_reactivado', 'cliente_borrado'"
)
TIPOS_EVENTO = f"({_TIPOS_0002}, 'usuario_eliminado')"
TIPOS_EVENTO_ANTERIORES = f"({_TIPOS_0002})"

CHECKS_DUPLICADOS: dict[str, tuple[str, ...]] = {
    "usuarios": ("rol", "intentos_no_negativos", "formato_nombre_usuario", "nombre_no_vacio"),
    "eventos_auditoria": ("tipo",),
    "provincias": ("formato_codigo",),
    "clientes": (
        "tipo",
        "identificacion_tipo",
        "nombre_no_vacio",
        "nif_solo_espana",
        "espana_nif_o_pasaporte",
        "forma_nif",
        "provincia_espana",
        "provincia_texto_extranjero",
        "codigo_postal_espana",
        "observaciones_longitud",
    ),
}


def _renombrar_checks(*, normalizar: bool) -> None:
    for tabla, nombres in CHECKS_DUPLICADOS.items():
        for nombre in nombres:
            correcto = f"ck_{tabla}_{nombre}"
            duplicado = f"ck_{tabla}_{correcto}"
            origen, destino = (duplicado, correcto) if normalizar else (correcto, duplicado)
            op.execute(f"ALTER TABLE {tabla} RENAME CONSTRAINT {origen} TO {destino}")


def upgrade() -> None:
    _renombrar_checks(normalizar=True)
    op.add_column("usuarios", sa.Column("eliminado_en", sa.DateTime(timezone=True), nullable=True))
    op.execute(
        "ALTER TABLE usuarios ADD CONSTRAINT ck_usuarios_eliminado_inactivo "
        "CHECK (eliminado_en IS NULL OR NOT activo)"
    )
    # El nombre de usuario de un eliminado queda libre (clarificación del 2026-09-28).
    op.execute("DROP INDEX uq_usuarios_nombre_usuario_lower")
    op.execute(
        "CREATE UNIQUE INDEX uq_usuarios_nombre_usuario_lower ON usuarios "
        "(lower(nombre_usuario)) WHERE eliminado_en IS NULL"
    )
    # Sustituir el CHECK no modifica filas: la auditoría sigue inalterable.
    op.execute("ALTER TABLE eventos_auditoria DROP CONSTRAINT ck_eventos_auditoria_tipo")
    op.execute(
        "ALTER TABLE eventos_auditoria ADD CONSTRAINT ck_eventos_auditoria_tipo "
        f"CHECK (tipo IN {TIPOS_EVENTO})"
    )


def downgrade() -> None:
    """Vuelta atrás posible aunque haya habido eliminaciones (p. ej. al reiniciar la BD de E2E).

    Los eliminados pasan a ser usuarios inactivos con el nombre de usuario sufijado, para que el
    índice único total vuelva a caber. Los eventos `usuario_eliminado` no se pueden borrar: el
    CHECK anterior se restaura `NOT VALID`, de modo que solo rige para las filas nuevas.
    """
    op.execute("ALTER TABLE eventos_auditoria DROP CONSTRAINT ck_eventos_auditoria_tipo")
    op.execute(
        "ALTER TABLE eventos_auditoria ADD CONSTRAINT ck_eventos_auditoria_tipo "
        f"CHECK (tipo IN {TIPOS_EVENTO_ANTERIORES}) NOT VALID"
    )
    op.execute(
        "UPDATE usuarios SET nombre_usuario = "
        "left(nombre_usuario, 41) || '.' || left(md5(id::text), 8) WHERE eliminado_en IS NOT NULL"
    )
    op.execute("DROP INDEX uq_usuarios_nombre_usuario_lower")
    op.execute(
        "CREATE UNIQUE INDEX uq_usuarios_nombre_usuario_lower ON usuarios (lower(nombre_usuario))"
    )
    op.execute("ALTER TABLE usuarios DROP CONSTRAINT ck_usuarios_eliminado_inactivo")
    op.drop_column("usuarios", "eliminado_en")
    _renombrar_checks(normalizar=False)
