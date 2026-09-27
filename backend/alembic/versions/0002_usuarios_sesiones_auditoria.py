"""Usuarios, sesiones y auditoría inalterable (data-model, research R-10).

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ROLES = "('administrador', 'empleado')"
TIPOS_EVENTO = (
    "('acceso_correcto', 'acceso_fallido', 'acceso_bloqueado', 'acceso_limitado', "
    "'cierre_sesion', 'contrasena_cambiada', 'contrasena_restablecida', 'usuario_creado', "
    "'usuario_rol_cambiado', 'usuario_desactivado', 'usuario_reactivado', 'cliente_creado', "
    "'cliente_editado', 'cliente_desactivado', 'cliente_reactivado', 'cliente_borrado')"
)


def _uuid_pk() -> sa.Column[object]:
    return sa.Column(
        "id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuidv7()"), nullable=False
    )


def _ts(nombre: str, *, nullable: bool = False, ahora: bool = False) -> sa.Column[object]:
    return sa.Column(
        nombre,
        sa.DateTime(timezone=True),
        server_default=sa.func.now() if ahora else None,
        nullable=nullable,
    )


def upgrade() -> None:
    # ------------------------------------------------------------------ usuarios
    op.create_table(
        "usuarios",
        _uuid_pk(),
        sa.Column("nombre_usuario", sa.String(50), nullable=False),
        sa.Column("nombre", sa.String(120), nullable=False),
        sa.Column("rol", sa.String(20), nullable=False),
        sa.Column("hash_contrasena", sa.Text(), nullable=False),
        sa.Column("contrasena_temporal", sa.Boolean(), server_default=sa.true(), nullable=False),
        _ts("contrasena_temporal_expira_en", nullable=True),
        sa.Column("activo", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("intentos_fallidos", sa.SmallInteger(), server_default="0", nullable=False),
        _ts("bloqueado_hasta", nullable=True),
        _ts("ultimo_acceso_en", nullable=True),
        _ts("creado_en", ahora=True),
        _ts("actualizado_en", ahora=True),
        sa.PrimaryKeyConstraint("id", name="pk_usuarios"),
        sa.CheckConstraint(f"rol IN {ROLES}", name="ck_usuarios_rol"),
        sa.CheckConstraint("intentos_fallidos >= 0", name="ck_usuarios_intentos_no_negativos"),
        sa.CheckConstraint(
            "nombre_usuario ~ '^[a-z0-9._-]{3,50}$'", name="ck_usuarios_formato_nombre_usuario"
        ),
        sa.CheckConstraint("length(trim(nombre)) > 0", name="ck_usuarios_nombre_no_vacio"),
    )
    op.create_index(
        "uq_usuarios_nombre_usuario_lower",
        "usuarios",
        [sa.text("lower(nombre_usuario)")],
        unique=True,
    )

    # ------------------------------------------------------------------ sesiones
    op.create_table(
        "sesiones",
        _uuid_pk(),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.CHAR(64), nullable=False),
        sa.Column("csrf_token", sa.String(64), nullable=False),
        _ts("creada_en", ahora=True),
        _ts("ultima_actividad_en", ahora=True),
        _ts("expira_en"),
        _ts("revocada_en", nullable=True),
        sa.Column("origen_ip", postgresql.INET(), nullable=True),
        sa.Column("agente", sa.String(500), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_sesiones"),
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            ["usuarios.id"],
            name="fk_sesiones_usuario_id_usuarios",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("token_hash", name="uq_sesiones_token_hash"),
    )
    op.create_index(
        "ix_sesiones_usuario_vigentes",
        "sesiones",
        ["usuario_id"],
        postgresql_where=sa.text("revocada_en IS NULL"),
    )

    # --------------------------------------------------------- eventos_auditoria
    op.create_table(
        "eventos_auditoria",
        _uuid_pk(),
        _ts("ocurrido_en", ahora=True),
        sa.Column("tipo", sa.String(40), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_nombre_usuario", sa.String(50), nullable=True),
        sa.Column("origen_ip", postgresql.INET(), nullable=True),
        sa.Column("agente", sa.String(500), nullable=True),
        sa.Column("usuario_afectado_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cliente_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "detalle",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_eventos_auditoria"),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["usuarios.id"], name="fk_eventos_auditoria_actor_id_usuarios"
        ),
        sa.ForeignKeyConstraint(
            ["usuario_afectado_id"],
            ["usuarios.id"],
            name="fk_eventos_auditoria_usuario_afectado_id_usuarios",
        ),
        sa.CheckConstraint(f"tipo IN {TIPOS_EVENTO}", name="ck_eventos_auditoria_tipo"),
    )
    op.create_index(
        "ix_eventos_auditoria_ocurrido_en", "eventos_auditoria", [sa.text("ocurrido_en DESC")]
    )
    op.create_index(
        "ix_eventos_auditoria_origen", "eventos_auditoria", ["origen_ip", "tipo", "ocurrido_en"]
    )
    op.create_index(
        "ix_eventos_auditoria_actor", "eventos_auditoria", ["actor_id", sa.text("ocurrido_en DESC")]
    )
    op.create_index(
        "ix_eventos_auditoria_cliente",
        "eventos_auditoria",
        ["cliente_id", sa.text("ocurrido_en DESC")],
    )
    op.create_index(
        "ix_eventos_auditoria_tipo", "eventos_auditoria", ["tipo", sa.text("ocurrido_en DESC")]
    )

    # Inalterabilidad (FR-022): privilegios + triggers, que afectan también a jb_owner.
    op.execute("REVOKE UPDATE, DELETE, TRUNCATE ON eventos_auditoria FROM jb_app")
    op.execute(
        """
        CREATE FUNCTION public.impedir_modificacion_auditoria()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'La auditoría es inalterable'
                USING ERRCODE = 'insufficient_privilege';
        END
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER eventos_auditoria_sin_modificaciones
        BEFORE UPDATE OR DELETE ON eventos_auditoria
        FOR EACH ROW EXECUTE FUNCTION public.impedir_modificacion_auditoria()
        """
    )
    op.execute(
        """
        CREATE TRIGGER eventos_auditoria_sin_truncate
        BEFORE TRUNCATE ON eventos_auditoria
        FOR EACH STATEMENT EXECUTE FUNCTION public.impedir_modificacion_auditoria()
        """
    )


def downgrade() -> None:
    op.drop_table("eventos_auditoria")
    op.execute("DROP FUNCTION public.impedir_modificacion_auditoria()")
    op.drop_table("sesiones")
    op.drop_table("usuarios")
