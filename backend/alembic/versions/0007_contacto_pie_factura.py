"""Feature 003: contacto y pie de factura en la configuración (data-model «Migración 0007»).

Research R-9: teléfono, correo, web y pie de factura de la joyería. Son datos NO fiscales: se leen
al imprimir y no se copian en la factura (FR-025). Solo DDL sobre la fila única y mutable de
`configuracion_facturacion`; no toca ninguna tabla de solo inserción (constitución III).

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-02
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _sin_vacios(columna: str) -> str:
    return f"({columna} IS NULL OR ({columna} = btrim({columna}) AND {columna} <> ''))"


UPGRADE = f"""
ALTER TABLE configuracion_facturacion
    ADD COLUMN emisor_telefono varchar(30),
    ADD COLUMN emisor_correo varchar(254),
    ADD COLUMN emisor_web varchar(200),
    ADD COLUMN pie_factura varchar(600);
ALTER TABLE configuracion_facturacion ADD CONSTRAINT ck_config_contacto_sin_vacios CHECK (
    {_sin_vacios("emisor_telefono")}
    AND {_sin_vacios("emisor_correo")}
    AND {_sin_vacios("emisor_web")}
    AND {_sin_vacios("pie_factura")}
);
"""

DOWNGRADE = """
ALTER TABLE configuracion_facturacion DROP CONSTRAINT ck_config_contacto_sin_vacios;
ALTER TABLE configuracion_facturacion
    DROP COLUMN pie_factura,
    DROP COLUMN emisor_web,
    DROP COLUMN emisor_correo,
    DROP COLUMN emisor_telefono;
"""


def upgrade() -> None:
    op.execute(UPGRADE)


def downgrade() -> None:
    op.execute(DOWNGRADE)
