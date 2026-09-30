"""Ajuste de cierre de 002: IVA libre, oro de inversión exento e IBAN (data-model «Migración 0006»).

Research R-20 (IVA de 0 a 99,99), R-21 (detalle exento con ClaveRegimen 04 y OperacionExenta E6),
R-22 (IBAN del emisor) y R-23 (sin clave de régimen en la configuración).

SOLO DDL: ningún UPDATE ni DELETE sobre facturas o registros (constitución III). Los triggers de
inalterabilidad son de fila (BEFORE UPDATE OR DELETE) y no se disparan. Las filas anteriores
cumplen la rama «sujeto» de los CHECK nuevos: S1, sin exención y con tipo; y cada factura tenía un
único detalle, así que `orden = 1` es correcto para todas.

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-30
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TIPO_EN_RANGO = "tipo_iva IS NULL OR (tipo_iva >= 0 AND tipo_iva < 100)"
_IBAN = "~ '^[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}$'"
# De la 0005, para el downgrade: F-1 L8A y F-3 §15.1.
_CLAVES_L8A = (
    "'01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '14', '15', '17', '18', "
    "'19', '20'"
)
_TIPOS_IVA_0005 = "0, 2, 4, 5, 7.5, 10, 21"

_VISTA = """
CREATE {reemplazo} VIEW v_listado_facturas AS
    SELECT 'borrador'::text AS tipo_documento,
           b.id,
           NULL::varchar AS num_serie,
           NULL::integer AS numero,
           b.fecha_expedicion AS fecha,
           c.nombre::text AS cliente_nombre,
           c.identificacion_numero::text AS identificacion,
           b.base_prevista AS base,
           b.cuota_prevista AS cuota,
           b.total_previsto AS total,
           'borrador'::text AS estado,
           coalesce(c.texto_busqueda, '') AS texto_busqueda{columna_borrador}
    FROM borradores_factura b
    LEFT JOIN clientes c ON c.id = b.cliente_id
    UNION ALL
    SELECT 'factura'::text,
           f.id,
           f.num_serie,
           f.numero,
           f.fecha_expedicion,
           f.dest_nombre::text,
           f.dest_identificacion_numero::text,
           f.base_total,
           f.cuota_total,
           f.importe_total,
           public.estado_factura(f.id),
           f.texto_busqueda{columna_factura}
    FROM facturas f;
"""

_VISTA_0006 = _VISTA.format(
    reemplazo="OR REPLACE",
    columna_borrador=",\n           b.oro_inversion",
    columna_factura=",\n           f.clave_regimen = '04'",
)
_VISTA_0005 = _VISTA.format(reemplazo="", columna_borrador="", columna_factura="")

UPGRADE = f"""
-- 1. Configuración: sin clave de régimen (R-23), IVA de 0 a 99,99 (R-20) e IBAN (R-22).
ALTER TABLE configuracion_facturacion DROP CONSTRAINT ck_configuracion_facturacion_clave_regimen;
ALTER TABLE configuracion_facturacion DROP COLUMN clave_regimen;
ALTER TABLE configuracion_facturacion DROP CONSTRAINT ck_configuracion_facturacion_iva;
ALTER TABLE configuracion_facturacion ADD CONSTRAINT ck_configuracion_facturacion_iva
    CHECK (iva_por_defecto >= 0 AND iva_por_defecto < 100);
ALTER TABLE configuracion_facturacion ADD COLUMN emisor_iban varchar(34);
ALTER TABLE configuracion_facturacion ADD CONSTRAINT ck_configuracion_facturacion_emisor_iban
    CHECK (emisor_iban {_IBAN});

-- 2. Facturas: copia del IBAN al emitir (FR-016). NULL en las anteriores.
ALTER TABLE facturas ADD COLUMN emisor_iban varchar(34);
ALTER TABLE facturas ADD CONSTRAINT ck_facturas_emisor_iban CHECK (emisor_iban {_IBAN});

-- 3. Líneas: sin tipo en la factura de oro de inversión (R-21).
ALTER TABLE lineas_factura ALTER COLUMN tipo_iva DROP NOT NULL;
ALTER TABLE lineas_factura DROP CONSTRAINT ck_lineas_factura_tipo_iva;
ALTER TABLE lineas_factura ADD CONSTRAINT ck_lineas_factura_tipo_iva CHECK ({_TIPO_EN_RANGO});

-- 4. Desgloses: detalle sujeto (S1) o exento (04 + E6), con su orden (F-1: de 1 a 12).
ALTER TABLE desgloses_factura ADD COLUMN orden smallint NOT NULL DEFAULT 1;
ALTER TABLE desgloses_factura ALTER COLUMN orden DROP DEFAULT;
ALTER TABLE desgloses_factura DROP CONSTRAINT pk_desgloses_factura;
ALTER TABLE desgloses_factura ADD CONSTRAINT pk_desgloses_factura PRIMARY KEY (factura_id, orden);
ALTER TABLE desgloses_factura ADD CONSTRAINT ck_desgloses_factura_orden
    CHECK (orden BETWEEN 1 AND 12);
ALTER TABLE desgloses_factura ADD CONSTRAINT uq_desgloses_factura_tipo
    UNIQUE NULLS NOT DISTINCT (factura_id, tipo_iva);
ALTER TABLE desgloses_factura ADD COLUMN operacion_exenta char(2);
ALTER TABLE desgloses_factura ALTER COLUMN tipo_iva DROP NOT NULL;
ALTER TABLE desgloses_factura ALTER COLUMN calificacion_operacion DROP NOT NULL;
ALTER TABLE desgloses_factura DROP CONSTRAINT ck_desgloses_factura_tipo_iva;
ALTER TABLE desgloses_factura ADD CONSTRAINT ck_desgloses_factura_tipo_iva
    CHECK ({_TIPO_EN_RANGO});
ALTER TABLE desgloses_factura DROP CONSTRAINT ck_desgloses_factura_calificacion;
-- A prueba de NULL: con `coalesce`, un detalle sin calificación ni exención da FALSE, no NULL
-- (un CHECK solo rechaza FALSE).
ALTER TABLE desgloses_factura ADD CONSTRAINT ck_desgloses_factura_calificacion CHECK (
    (coalesce(calificacion_operacion, '') = 'S1' AND operacion_exenta IS NULL
        AND tipo_iva IS NOT NULL)
    OR (calificacion_operacion IS NULL AND coalesce(operacion_exenta, '') = 'E6'
        AND clave_regimen = '04' AND tipo_iva IS NULL AND cuota = 0)
);

-- 5. Borradores: la casilla «Sin IVA (oro de inversión)».
ALTER TABLE borradores_factura ADD COLUMN oro_inversion boolean NOT NULL DEFAULT false;

-- 6. Listado: la marca de oro de inversión, al final (CREATE OR REPLACE solo añade columnas).
{_VISTA_0006}
"""

DOWNGRADE = f"""
-- Solo para reconstruir las BD de test y E2E: nunca debe fallar por los datos (data-model).
DROP VIEW v_listado_facturas;
{_VISTA_0005}
ALTER TABLE borradores_factura DROP COLUMN oro_inversion;

ALTER TABLE desgloses_factura DROP CONSTRAINT ck_desgloses_factura_calificacion;
ALTER TABLE desgloses_factura ADD CONSTRAINT ck_desgloses_factura_calificacion
    CHECK (calificacion_operacion = 'S1') NOT VALID;
ALTER TABLE desgloses_factura DROP CONSTRAINT ck_desgloses_factura_tipo_iva;
ALTER TABLE desgloses_factura ADD CONSTRAINT ck_desgloses_factura_tipo_iva
    CHECK (tipo_iva IN ({_TIPOS_IVA_0005})) NOT VALID;
ALTER TABLE lineas_factura DROP CONSTRAINT ck_lineas_factura_tipo_iva;
ALTER TABLE lineas_factura ADD CONSTRAINT ck_lineas_factura_tipo_iva
    CHECK (tipo_iva IN ({_TIPOS_IVA_0005})) NOT VALID;
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM desgloses_factura WHERE tipo_iva IS NULL)
       AND NOT EXISTS (SELECT 1 FROM lineas_factura WHERE tipo_iva IS NULL) THEN
        ALTER TABLE desgloses_factura DROP CONSTRAINT uq_desgloses_factura_tipo;
        ALTER TABLE desgloses_factura DROP CONSTRAINT pk_desgloses_factura;
        ALTER TABLE desgloses_factura ADD CONSTRAINT pk_desgloses_factura
            PRIMARY KEY (factura_id, tipo_iva);
        ALTER TABLE desgloses_factura DROP CONSTRAINT ck_desgloses_factura_orden;
        ALTER TABLE desgloses_factura DROP COLUMN orden;
        ALTER TABLE desgloses_factura DROP COLUMN operacion_exenta;
        ALTER TABLE desgloses_factura ALTER COLUMN tipo_iva SET NOT NULL;
        ALTER TABLE desgloses_factura ALTER COLUMN calificacion_operacion SET NOT NULL;
        ALTER TABLE lineas_factura ALTER COLUMN tipo_iva SET NOT NULL;
    END IF;
END $$;

ALTER TABLE facturas DROP CONSTRAINT ck_facturas_emisor_iban;
ALTER TABLE facturas DROP COLUMN emisor_iban;

ALTER TABLE configuracion_facturacion DROP CONSTRAINT ck_configuracion_facturacion_emisor_iban;
ALTER TABLE configuracion_facturacion DROP COLUMN emisor_iban;
ALTER TABLE configuracion_facturacion DROP CONSTRAINT ck_configuracion_facturacion_iva;
ALTER TABLE configuracion_facturacion ADD CONSTRAINT ck_configuracion_facturacion_iva
    CHECK (iva_por_defecto IN ({_TIPOS_IVA_0005})) NOT VALID;
ALTER TABLE configuracion_facturacion ADD COLUMN clave_regimen char(2) NOT NULL DEFAULT '01';
ALTER TABLE configuracion_facturacion ADD CONSTRAINT ck_configuracion_facturacion_clave_regimen
    CHECK (clave_regimen IN ({_CLAVES_L8A}));
"""  # noqa: S608 — solo constantes de este módulo, sin entrada externa


def upgrade() -> None:
    op.execute(UPGRADE)


def downgrade() -> None:
    op.execute(DOWNGRADE)
