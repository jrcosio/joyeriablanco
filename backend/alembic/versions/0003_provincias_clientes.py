"""Catálogo de provincias (INE 2026) y clientes (data-model §provincias y §clientes).

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# INE, "Relación de provincias con sus códigos" a 1 de enero de 2026 (research R-20.3):
# (código, literal oficial, nombre visible en orden natural)
PROVINCIAS: tuple[tuple[str, str, str], ...] = (
    ("01", "Araba/Álava", "Araba/Álava"),
    ("02", "Albacete", "Albacete"),
    ("03", "Alicante/Alacant", "Alicante/Alacant"),
    ("04", "Almería", "Almería"),
    ("05", "Ávila", "Ávila"),
    ("06", "Badajoz", "Badajoz"),
    ("07", "Balears, Illes", "Illes Balears"),
    ("08", "Barcelona", "Barcelona"),
    ("09", "Burgos", "Burgos"),
    ("10", "Cáceres", "Cáceres"),
    ("11", "Cádiz", "Cádiz"),
    ("12", "Castellón/Castelló", "Castellón/Castelló"),
    ("13", "Ciudad Real", "Ciudad Real"),
    ("14", "Córdoba", "Córdoba"),
    ("15", "Coruña, A", "A Coruña"),
    ("16", "Cuenca", "Cuenca"),
    ("17", "Girona", "Girona"),
    ("18", "Granada", "Granada"),
    ("19", "Guadalajara", "Guadalajara"),
    ("20", "Gipuzkoa", "Gipuzkoa"),
    ("21", "Huelva", "Huelva"),
    ("22", "Huesca", "Huesca"),
    ("23", "Jaén", "Jaén"),
    ("24", "León", "León"),
    ("25", "Lleida", "Lleida"),
    ("26", "Rioja, La", "La Rioja"),
    ("27", "Lugo", "Lugo"),
    ("28", "Madrid", "Madrid"),
    ("29", "Málaga", "Málaga"),
    ("30", "Murcia", "Murcia"),
    ("31", "Navarra", "Navarra"),
    ("32", "Ourense", "Ourense"),
    ("33", "Asturias", "Asturias"),
    ("34", "Palencia", "Palencia"),
    ("35", "Palmas, Las", "Las Palmas"),
    ("36", "Pontevedra", "Pontevedra"),
    ("37", "Salamanca", "Salamanca"),
    ("38", "Santa Cruz de Tenerife", "Santa Cruz de Tenerife"),
    ("39", "Cantabria", "Cantabria"),
    ("40", "Segovia", "Segovia"),
    ("41", "Sevilla", "Sevilla"),
    ("42", "Soria", "Soria"),
    ("43", "Tarragona", "Tarragona"),
    ("44", "Teruel", "Teruel"),
    ("45", "Toledo", "Toledo"),
    ("46", "Valencia/València", "Valencia/València"),
    ("47", "Valladolid", "Valladolid"),
    ("48", "Bizkaia", "Bizkaia"),
    ("49", "Zamora", "Zamora"),
    ("50", "Zaragoza", "Zaragoza"),
    ("51", "Ceuta", "Ceuta"),
    ("52", "Melilla", "Melilla"),
)

TEXTO_BUSQUEDA = (
    "inmutable_unaccent(lower(nombre || ' ' || identificacion_numero || ' ' || "
    "coalesce(localidad, '')))"
)


def upgrade() -> None:
    provincias = op.create_table(
        "provincias",
        sa.Column("codigo", sa.CHAR(2), nullable=False),
        sa.Column("nombre", sa.String(60), nullable=False),
        sa.Column("nombre_visible", sa.String(60), nullable=False),
        sa.PrimaryKeyConstraint("codigo", name="pk_provincias"),
        sa.CheckConstraint("codigo ~ '^[0-9]{2}$'", name="ck_provincias_formato_codigo"),
    )
    op.bulk_insert(
        provincias,
        [{"codigo": c, "nombre": n, "nombre_visible": v} for c, n, v in PROVINCIAS],
    )
    # Catálogo de solo lectura para la aplicación.
    op.execute("REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON provincias FROM jb_app")

    op.create_table(
        "clientes",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuidv7()"), nullable=False
        ),
        sa.Column("tipo", sa.String(12), nullable=False),
        sa.Column("nombre", sa.String(120), nullable=False),
        sa.Column("identificacion_pais", sa.CHAR(2), server_default="ES", nullable=False),
        sa.Column("identificacion_tipo", sa.String(3), nullable=False),
        sa.Column("identificacion_numero", sa.String(20), nullable=False),
        sa.Column("direccion", sa.String(200), nullable=True),
        sa.Column("codigo_postal", sa.String(10), nullable=True),
        sa.Column("localidad", sa.String(100), nullable=True),
        sa.Column("provincia_codigo", sa.CHAR(2), nullable=True),
        sa.Column("provincia_texto", sa.String(100), nullable=True),
        sa.Column("pais_residencia", sa.CHAR(2), server_default="ES", nullable=False),
        sa.Column("telefono", sa.String(30), nullable=True),
        sa.Column("correo", sa.String(254), nullable=True),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column("activo", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("creado_por_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("actualizado_por_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("texto_busqueda", sa.Text(), sa.Computed(TEXTO_BUSQUEDA, persisted=True)),
        sa.PrimaryKeyConstraint("id", name="pk_clientes"),
        sa.ForeignKeyConstraint(
            ["provincia_codigo"],
            ["provincias.codigo"],
            name="fk_clientes_provincia_codigo_provincias",
        ),
        sa.ForeignKeyConstraint(
            ["creado_por_id"], ["usuarios.id"], name="fk_clientes_creado_por_id_usuarios"
        ),
        sa.ForeignKeyConstraint(
            ["actualizado_por_id"], ["usuarios.id"], name="fk_clientes_actualizado_por_id_usuarios"
        ),
        sa.UniqueConstraint(
            "identificacion_pais",
            "identificacion_tipo",
            "identificacion_numero",
            name="uq_clientes_identificacion",
        ),
        sa.CheckConstraint("tipo IN ('particular', 'empresa')", name="ck_clientes_tipo"),
        sa.CheckConstraint(
            "identificacion_tipo IN ('NIF', '02', '03', '04', '05', '06')",
            name="ck_clientes_identificacion_tipo",
        ),
        sa.CheckConstraint("length(trim(nombre)) > 0", name="ck_clientes_nombre_no_vacio"),
        sa.CheckConstraint(
            "identificacion_tipo <> 'NIF' OR identificacion_pais = 'ES'",
            name="ck_clientes_nif_solo_espana",
        ),
        sa.CheckConstraint(
            "identificacion_pais <> 'ES' OR identificacion_tipo IN ('NIF', '03')",
            name="ck_clientes_espana_nif_o_pasaporte",
        ),
        sa.CheckConstraint(
            "identificacion_tipo <> 'NIF' OR identificacion_numero ~ '^[0-9A-Z]{9}$'",
            name="ck_clientes_forma_nif",
        ),
        sa.CheckConstraint(
            "pais_residencia = 'ES' OR provincia_codigo IS NULL",
            name="ck_clientes_provincia_espana",
        ),
        sa.CheckConstraint(
            "pais_residencia <> 'ES' OR provincia_texto IS NULL",
            name="ck_clientes_provincia_texto_extranjero",
        ),
        sa.CheckConstraint(
            "pais_residencia <> 'ES' OR codigo_postal IS NULL OR codigo_postal ~ '^[0-9]{5}$'",
            name="ck_clientes_codigo_postal_espana",
        ),
        sa.CheckConstraint(
            "length(observaciones) <= 2000", name="ck_clientes_observaciones_longitud"
        ),
    )
    op.create_index(
        "ix_clientes_texto_busqueda",
        "clientes",
        ["texto_busqueda"],
        postgresql_using="gin",
        postgresql_ops={"texto_busqueda": "gin_trgm_ops"},
    )
    op.create_index("ix_clientes_activo_nombre", "clientes", ["activo", "nombre", "id"])
    op.create_index("ix_clientes_provincia_codigo", "clientes", ["provincia_codigo"])
    op.create_index("ix_clientes_tipo", "clientes", ["tipo"])
    op.create_index("ix_clientes_creado_en", "clientes", ["creado_en", "id"])


def downgrade() -> None:
    op.drop_table("clientes")
    op.drop_table("provincias")
