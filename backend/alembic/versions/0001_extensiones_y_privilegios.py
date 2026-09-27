"""Extensiones de búsqueda, función unaccent inmutable y privilegios por defecto de jb_app.

Revision ID: 0001
Revises:
Create Date: 2026-09-27
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Las crea infra/db/init/01-roles.sh como superusuario; aquí solo se garantiza su existencia.
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent SCHEMA public")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm SCHEMA public")

    # unaccent() no es IMMUTABLE; esta envoltura con diccionario explícito permite indexarla
    # en una columna generada (research R-12).
    op.execute(
        """
        CREATE FUNCTION public.inmutable_unaccent(texto text)
        RETURNS text
        LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT
        AS $$ SELECT public.unaccent('public.unaccent'::regdictionary, texto) $$
        """
    )

    # Toda tabla que cree jb_owner será accesible por jb_app solo con DML (research R-11).
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE jb_owner IN SCHEMA public "
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO jb_app"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE jb_owner IN SCHEMA public "
        "GRANT USAGE, SELECT ON SEQUENCES TO jb_app"
    )


def downgrade() -> None:
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE jb_owner IN SCHEMA public "
        "REVOKE USAGE, SELECT ON SEQUENCES FROM jb_app"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE jb_owner IN SCHEMA public "
        "REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM jb_app"
    )
    op.execute("DROP FUNCTION public.inmutable_unaccent(text)")
