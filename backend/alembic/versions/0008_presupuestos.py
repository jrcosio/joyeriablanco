"""Presupuestos con conversión en factura (feature 005; data-model.md, research R-1 a R-6, R-11).

Se escribe en SQL, como la 0005, para controlar los nombres de las restricciones y declarar las
funciones, los triggers y la vista.

Garantías en la BD (constitución 2.3.0, principio III):
- presupuestos, lineas_presupuesto, desgloses_presupuesto y cierres_presupuesto son de SOLO
  INSERCIÓN: REVOKE UPDATE/DELETE/TRUNCATE a jb_app y triggers que paran también a jb_owner.
- Como mucho un cierre por presupuesto (UNIQUE) y un borrador de factura vinculado (UNIQUE).
- Ni anulación ni sustitución con un borrador vinculado, ni vínculo con un presupuesto cerrado
  (triggers con nombre de restricción, que `core/errors.py` traduce).
- El estado guardado vive en UNA función, estado_presupuesto(). La caducidad no: depende de la
  fecha de hoy en la zona de la aplicación (research R-3).

Un presupuesto no genera registros de facturación ni huella: no toca la cadena (FR-005).

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-02
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# De la 0005: el CHECK de auditoría se rehace con los tipos de cada feature.
_TIPOS_0004 = (
    "'acceso_correcto', 'acceso_fallido', 'acceso_bloqueado', 'acceso_limitado', "
    "'cierre_sesion', 'contrasena_cambiada', 'contrasena_restablecida', 'usuario_creado', "
    "'usuario_rol_cambiado', 'usuario_desactivado', 'usuario_reactivado', 'cliente_creado', "
    "'cliente_editado', 'cliente_desactivado', 'cliente_reactivado', 'cliente_borrado', "
    "'usuario_eliminado'"
)
_TIPOS_0005 = (
    "'borrador_factura_creado', 'borrador_factura_editado', 'borrador_factura_eliminado', "
    "'factura_emitida', 'factura_anulada', 'factura_rectificada', "
    "'configuracion_facturacion_cambiada', 'contador_ajustado', 'cadena_verificada', "
    "'cadena_inconsistente'"
)
_TIPOS_0008 = (
    "'borrador_presupuesto_creado', 'borrador_presupuesto_editado', "
    "'borrador_presupuesto_eliminado', 'presupuesto_emitido', 'presupuesto_modificado', "
    "'presupuesto_anulado', 'presupuesto_convertido'"
)
# De la 0006.
_TIPO_EN_RANGO = "tipo_iva IS NULL OR (tipo_iva >= 0 AND tipo_iva < 100)"
_IBAN = "~ '^[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}$'"
_TABLAS_INALTERABLES = (
    "presupuestos",
    "lineas_presupuesto",
    "desgloses_presupuesto",
    "cierres_presupuesto",
)


def _sin_vacios(columna: str) -> str:
    return f"({columna} IS NULL OR ({columna} = btrim({columna}) AND {columna} <> ''))"


_CONTACTO_0007 = (
    f"{_sin_vacios('emisor_telefono')} AND {_sin_vacios('emisor_correo')} "
    f"AND {_sin_vacios('emisor_web')} AND {_sin_vacios('pie_factura')}"
)

UPGRADE = f"""
-- ====================================================================== 1. inalterabilidad
CREATE FUNCTION public.impedir_modificacion_presupuesto()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Los presupuestos emitidos son inalterables'
        USING ERRCODE = 'insufficient_privilege';
END
$$;

-- ============================================================ 2. borradores de presupuesto
CREATE TABLE borradores_presupuesto (
    id uuid NOT NULL DEFAULT uuidv7(),
    cliente_id uuid,
    fecha date NOT NULL,
    valido_hasta date NOT NULL,
    tipo_iva_previsto numeric(5,2) NOT NULL,
    oro_inversion boolean NOT NULL DEFAULT false,
    base_prevista numeric(12,2) NOT NULL DEFAULT 0,
    cuota_prevista numeric(12,2) NOT NULL DEFAULT 0,
    total_previsto numeric(12,2) NOT NULL DEFAULT 0,
    version integer NOT NULL DEFAULT 1,
    creado_en timestamptz NOT NULL DEFAULT now(),
    creado_por_id uuid NOT NULL,
    actualizado_en timestamptz NOT NULL DEFAULT now(),
    actualizado_por_id uuid NOT NULL,
    CONSTRAINT pk_borradores_presupuesto PRIMARY KEY (id),
    CONSTRAINT ck_borradores_presupuesto_validez CHECK (valido_hasta >= fecha),
    CONSTRAINT fk_borradores_presupuesto_cliente_id_clientes
        FOREIGN KEY (cliente_id) REFERENCES clientes (id) ON DELETE RESTRICT,
    CONSTRAINT fk_borradores_presupuesto_creado_por_id_usuarios
        FOREIGN KEY (creado_por_id) REFERENCES usuarios (id),
    CONSTRAINT fk_borradores_presupuesto_actualizado_por_id_usuarios
        FOREIGN KEY (actualizado_por_id) REFERENCES usuarios (id)
);
CREATE INDEX ix_borradores_presupuesto_fecha ON borradores_presupuesto (fecha DESC, id);
CREATE INDEX ix_borradores_presupuesto_cliente_id ON borradores_presupuesto (cliente_id);

CREATE TABLE lineas_borrador_presupuesto (
    id uuid NOT NULL DEFAULT uuidv7(),
    borrador_id uuid NOT NULL,
    orden smallint NOT NULL,
    unidades numeric(9,2) NOT NULL,
    descripcion varchar(500) NOT NULL,
    precio_unitario numeric(12,2) NOT NULL,
    CONSTRAINT pk_lineas_borrador_presupuesto PRIMARY KEY (id),
    CONSTRAINT fk_lineas_borrador_presupuesto_borrador_id_borradores_presupuesto
        FOREIGN KEY (borrador_id) REFERENCES borradores_presupuesto (id) ON DELETE CASCADE,
    CONSTRAINT uq_lineas_borrador_presupuesto_orden UNIQUE (borrador_id, orden),
    CONSTRAINT ck_lineas_borrador_presupuesto_orden CHECK (orden BETWEEN 1 AND 100),
    CONSTRAINT ck_lineas_borrador_presupuesto_unidades CHECK (unidades > 0),
    CONSTRAINT ck_lineas_borrador_presupuesto_descripcion CHECK (length(trim(descripcion)) > 0),
    CONSTRAINT ck_lineas_borrador_presupuesto_precio CHECK (precio_unitario >= 0)
);

-- =================================================================== 2. presupuestos 🔒
CREATE TABLE presupuestos (
    id uuid NOT NULL DEFAULT uuidv7(),
    serie varchar(3) NOT NULL,
    anio smallint NOT NULL,
    numero integer NOT NULL,
    num_serie varchar(60) NOT NULL,
    fecha date NOT NULL,
    valido_hasta date NOT NULL,
    emisor_nif char(9) NOT NULL,
    emisor_nombre varchar(120) NOT NULL,
    emisor_direccion varchar(200) NOT NULL,
    emisor_codigo_postal char(5) NOT NULL,
    emisor_localidad varchar(100) NOT NULL,
    emisor_provincia varchar(100),
    emisor_iban varchar(34),
    cliente_id uuid NOT NULL,
    dest_nombre varchar(120) NOT NULL,
    dest_identificacion_pais char(2) NOT NULL,
    dest_identificacion_tipo varchar(3) NOT NULL,
    dest_identificacion_numero varchar(20) NOT NULL,
    dest_direccion varchar(200),
    dest_codigo_postal varchar(10),
    dest_localidad varchar(100),
    dest_provincia varchar(100),
    dest_pais char(2) NOT NULL,
    oro_inversion boolean NOT NULL,
    base_total numeric(12,2) NOT NULL,
    cuota_total numeric(12,2) NOT NULL,
    importe_total numeric(12,2) NOT NULL,
    emitido_por_id uuid NOT NULL,
    emitido_en timestamptz NOT NULL DEFAULT now(),
    clave_idempotencia uuid,
    operacion_idempotencia varchar(20),
    origen_idempotencia uuid,
    texto_busqueda text GENERATED ALWAYS AS (
        inmutable_unaccent(lower(num_serie || ' ' || dest_nombre || ' ' || dest_identificacion_numero))
    ) STORED,
    CONSTRAINT pk_presupuestos PRIMARY KEY (id),
    CONSTRAINT uq_presupuestos_numero UNIQUE (serie, anio, numero),
    CONSTRAINT uq_presupuestos_num_serie UNIQUE (num_serie),
    CONSTRAINT uq_presupuestos_clave_idempotencia UNIQUE (clave_idempotencia),
    CONSTRAINT ck_presupuestos_serie CHECK (serie = 'PRE'),
    CONSTRAINT ck_presupuestos_numero CHECK (numero > 0),
    CONSTRAINT ck_presupuestos_anio CHECK (anio = EXTRACT(YEAR FROM fecha)::int),
    CONSTRAINT ck_presupuestos_num_serie CHECK (
        num_serie = serie || '-' || anio::text || '-'
            || CASE WHEN numero < 10000 THEN lpad(numero::text, 4, '0') ELSE numero::text END
    ),
    CONSTRAINT ck_presupuestos_fecha_minima CHECK (fecha >= DATE '2024-10-28'),
    CONSTRAINT ck_presupuestos_validez CHECK (valido_hasta >= fecha),
    CONSTRAINT ck_presupuestos_emisor_nif CHECK (emisor_nif ~ '^[0-9A-Z]{{9}}$'),
    CONSTRAINT ck_presupuestos_emisor_iban CHECK (emisor_iban {_IBAN}),
    CONSTRAINT ck_presupuestos_dest_identificacion_tipo
        CHECK (dest_identificacion_tipo IN ('NIF', '02', '03', '04', '05', '06')),
    CONSTRAINT ck_presupuestos_importes_no_negativos
        CHECK (base_total >= 0 AND cuota_total >= 0 AND importe_total >= 0),
    CONSTRAINT ck_presupuestos_total CHECK (importe_total = base_total + cuota_total),
    CONSTRAINT ck_presupuestos_positivo CHECK (importe_total > 0),
    CONSTRAINT ck_presupuestos_oro_inversion CHECK (NOT oro_inversion OR cuota_total = 0),
    CONSTRAINT ck_presupuestos_operacion_idempotencia
        CHECK (operacion_idempotencia IN ('emitir', 'emitir_borrador', 'modificar')),
    CONSTRAINT fk_presupuestos_cliente_id_clientes
        FOREIGN KEY (cliente_id) REFERENCES clientes (id) ON DELETE RESTRICT,
    CONSTRAINT fk_presupuestos_emitido_por_id_usuarios
        FOREIGN KEY (emitido_por_id) REFERENCES usuarios (id)
);
CREATE INDEX ix_presupuestos_fecha ON presupuestos (fecha DESC, numero DESC);
CREATE INDEX ix_presupuestos_texto_busqueda ON presupuestos USING gin (texto_busqueda gin_trgm_ops);
CREATE INDEX ix_presupuestos_cliente_id ON presupuestos (cliente_id);

CREATE TABLE lineas_presupuesto (
    id uuid NOT NULL DEFAULT uuidv7(),
    presupuesto_id uuid NOT NULL,
    orden smallint NOT NULL,
    unidades numeric(9,2) NOT NULL,
    descripcion varchar(500) NOT NULL,
    precio_unitario numeric(12,2) NOT NULL,
    tipo_iva numeric(5,2),
    importe numeric(12,2) NOT NULL,
    CONSTRAINT pk_lineas_presupuesto PRIMARY KEY (id),
    CONSTRAINT fk_lineas_presupuesto_presupuesto_id_presupuestos
        FOREIGN KEY (presupuesto_id) REFERENCES presupuestos (id),
    CONSTRAINT uq_lineas_presupuesto_orden UNIQUE (presupuesto_id, orden),
    CONSTRAINT ck_lineas_presupuesto_orden CHECK (orden BETWEEN 1 AND 100),
    CONSTRAINT ck_lineas_presupuesto_unidades CHECK (unidades > 0),
    CONSTRAINT ck_lineas_presupuesto_descripcion CHECK (length(trim(descripcion)) > 0),
    CONSTRAINT ck_lineas_presupuesto_precio CHECK (precio_unitario >= 0),
    CONSTRAINT ck_lineas_presupuesto_tipo_iva CHECK ({_TIPO_EN_RANGO}),
    CONSTRAINT ck_lineas_presupuesto_importe CHECK (importe >= 0)
);

CREATE TABLE desgloses_presupuesto (
    presupuesto_id uuid NOT NULL,
    orden smallint NOT NULL,
    tipo_iva numeric(5,2),
    base numeric(12,2) NOT NULL,
    cuota numeric(12,2) NOT NULL,
    CONSTRAINT pk_desgloses_presupuesto PRIMARY KEY (presupuesto_id, orden),
    CONSTRAINT fk_desgloses_presupuesto_presupuesto_id_presupuestos
        FOREIGN KEY (presupuesto_id) REFERENCES presupuestos (id),
    CONSTRAINT uq_desgloses_presupuesto_tipo UNIQUE NULLS NOT DISTINCT (presupuesto_id, tipo_iva),
    CONSTRAINT ck_desgloses_presupuesto_orden CHECK (orden BETWEEN 1 AND 12),
    CONSTRAINT ck_desgloses_presupuesto_tipo_iva CHECK ({_TIPO_EN_RANGO}),
    CONSTRAINT ck_desgloses_presupuesto_importes CHECK (base >= 0 AND cuota >= 0),
    CONSTRAINT ck_desgloses_presupuesto_exento CHECK (tipo_iva IS NOT NULL OR cuota = 0)
);

-- ======================================================================= 2. cierres 🔒
CREATE TABLE cierres_presupuesto (
    id uuid NOT NULL DEFAULT uuidv7(),
    presupuesto_id uuid NOT NULL,
    tipo varchar(12) NOT NULL,
    motivo_texto varchar(500),
    presupuesto_nuevo_id uuid,
    factura_id uuid,
    creado_por_id uuid NOT NULL,
    creado_en timestamptz NOT NULL DEFAULT now(),
    clave_idempotencia uuid,
    operacion_idempotencia varchar(20),
    CONSTRAINT pk_cierres_presupuesto PRIMARY KEY (id),
    CONSTRAINT uq_cierres_presupuesto_presupuesto_id UNIQUE (presupuesto_id),
    CONSTRAINT uq_cierres_presupuesto_presupuesto_nuevo_id UNIQUE (presupuesto_nuevo_id),
    CONSTRAINT uq_cierres_presupuesto_factura_id UNIQUE (factura_id),
    CONSTRAINT uq_cierres_presupuesto_clave_idempotencia UNIQUE (clave_idempotencia),
    CONSTRAINT ck_cierres_presupuesto_tipo CHECK (
        (tipo = 'anulacion' AND motivo_texto IS NOT NULL AND presupuesto_nuevo_id IS NULL
            AND factura_id IS NULL AND clave_idempotencia IS NOT NULL)
        OR (tipo = 'sustitucion' AND motivo_texto IS NOT NULL
            AND presupuesto_nuevo_id IS NOT NULL AND presupuesto_nuevo_id <> presupuesto_id
            AND factura_id IS NULL AND clave_idempotencia IS NULL)
        OR (tipo = 'conversion' AND motivo_texto IS NULL AND presupuesto_nuevo_id IS NULL
            AND factura_id IS NOT NULL AND clave_idempotencia IS NULL)
    ),
    CONSTRAINT ck_cierres_presupuesto_motivo_texto
        CHECK (motivo_texto IS NULL OR length(trim(motivo_texto)) > 0),
    CONSTRAINT ck_cierres_presupuesto_operacion_idempotencia
        CHECK (operacion_idempotencia IN ('anular')),
    CONSTRAINT fk_cierres_presupuesto_presupuesto_id_presupuestos
        FOREIGN KEY (presupuesto_id) REFERENCES presupuestos (id),
    CONSTRAINT fk_cierres_presupuesto_presupuesto_nuevo_id_presupuestos
        FOREIGN KEY (presupuesto_nuevo_id) REFERENCES presupuestos (id),
    CONSTRAINT fk_cierres_presupuesto_factura_id_facturas
        FOREIGN KEY (factura_id) REFERENCES facturas (id),
    CONSTRAINT fk_cierres_presupuesto_creado_por_id_usuarios
        FOREIGN KEY (creado_por_id) REFERENCES usuarios (id)
);

-- ========================================================================= 3. DDL sobre 002
ALTER TABLE borradores_factura ADD COLUMN presupuesto_id uuid;
ALTER TABLE borradores_factura ADD CONSTRAINT fk_borradores_factura_presupuesto_id_presupuestos
    FOREIGN KEY (presupuesto_id) REFERENCES presupuestos (id) ON DELETE RESTRICT;
ALTER TABLE borradores_factura ADD CONSTRAINT uq_borradores_factura_presupuesto_id
    UNIQUE (presupuesto_id);

ALTER TABLE contadores_factura DROP CONSTRAINT ck_contadores_factura_serie;
ALTER TABLE contadores_factura ADD CONSTRAINT ck_contadores_factura_serie
    CHECK (serie IN ('FAC', 'REC', 'PRE'));

ALTER TABLE configuracion_facturacion
    ADD COLUMN validez_presupuesto_dias smallint NOT NULL DEFAULT 30,
    ADD COLUMN pie_presupuesto varchar(600);
ALTER TABLE configuracion_facturacion ADD CONSTRAINT ck_config_validez_presupuesto
    CHECK (validez_presupuesto_dias BETWEEN 1 AND 365);
ALTER TABLE configuracion_facturacion DROP CONSTRAINT ck_config_contacto_sin_vacios;
ALTER TABLE configuracion_facturacion ADD CONSTRAINT ck_config_contacto_sin_vacios
    CHECK ({_CONTACTO_0007} AND {_sin_vacios("pie_presupuesto")});

ALTER TABLE eventos_auditoria DROP CONSTRAINT ck_eventos_auditoria_tipo;
ALTER TABLE eventos_auditoria ADD CONSTRAINT ck_eventos_auditoria_tipo
    CHECK (tipo IN ({_TIPOS_0004}, {_TIPOS_0005}, {_TIPOS_0008}));

-- =========================================================================== 4. funciones
-- Estado guardado (research R-3): ÚNICA implementación, usada por la vista y los servicios.
CREATE FUNCTION public.estado_presupuesto(p_presupuesto uuid)
RETURNS text LANGUAGE sql STABLE AS $$
    SELECT coalesce(
        (SELECT CASE c.tipo WHEN 'anulacion' THEN 'anulado'
                            WHEN 'sustitucion' THEN 'sustituido'
                            ELSE 'convertido' END
         FROM cierres_presupuesto c WHERE c.presupuesto_id = p_presupuesto),
        CASE WHEN EXISTS (
                SELECT 1 FROM borradores_factura b WHERE b.presupuesto_id = p_presupuesto)
             THEN 'en_facturacion' ELSE 'pendiente' END)
$$;

-- Ni anulación ni sustitución mientras haya un borrador de factura vinculado (FR-021).
CREATE FUNCTION public.validar_cierre_presupuesto()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.tipo IN ('anulacion', 'sustitucion') AND EXISTS (
        SELECT 1 FROM borradores_factura b WHERE b.presupuesto_id = NEW.presupuesto_id
    ) THEN
        RAISE EXCEPTION 'El presupuesto está en facturación'
            USING ERRCODE = 'check_violation',
                  CONSTRAINT = 'tg_cierres_presupuesto_en_facturacion';
    END IF;
    RETURN NEW;
END
$$;

-- Un borrador de factura no se vincula a un presupuesto ya cerrado (FR-020).
CREATE FUNCTION public.validar_vinculo_presupuesto()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.presupuesto_id IS NOT NULL AND EXISTS (
        SELECT 1 FROM cierres_presupuesto c WHERE c.presupuesto_id = NEW.presupuesto_id
    ) THEN
        RAISE EXCEPTION 'El presupuesto ya está cerrado'
            USING ERRCODE = 'check_violation',
                  CONSTRAINT = 'tg_borradores_factura_presupuesto_cerrado';
    END IF;
    RETURN NEW;
END
$$;

-- ============================================================================== 5. vista
CREATE VIEW v_listado_presupuestos AS
    SELECT 'borrador'::text AS tipo_documento,
           b.id,
           NULL::varchar AS num_serie,
           NULL::integer AS numero,
           b.fecha,
           c.nombre::text AS cliente_nombre,
           c.identificacion_numero::text AS identificacion,
           b.base_prevista AS base,
           b.cuota_prevista AS cuota,
           b.total_previsto AS total,
           'borrador'::text AS estado,
           coalesce(c.texto_busqueda, '') AS texto_busqueda,
           b.oro_inversion,
           b.valido_hasta
    FROM borradores_presupuesto b
    LEFT JOIN clientes c ON c.id = b.cliente_id
    UNION ALL
    SELECT 'presupuesto'::text,
           p.id,
           p.num_serie,
           p.numero,
           p.fecha,
           p.dest_nombre::text,
           p.dest_identificacion_numero::text,
           p.base_total,
           p.cuota_total,
           p.importe_total,
           public.estado_presupuesto(p.id),
           p.texto_busqueda,
           p.oro_inversion,
           p.valido_hasta
    FROM presupuestos p;

-- ============================================================================ 6. triggers
CREATE TRIGGER cierres_presupuesto_validar
    BEFORE INSERT ON cierres_presupuesto
    FOR EACH ROW EXECUTE FUNCTION public.validar_cierre_presupuesto();
CREATE TRIGGER borradores_factura_validar_vinculo
    BEFORE INSERT OR UPDATE OF presupuesto_id ON borradores_factura
    FOR EACH ROW EXECUTE FUNCTION public.validar_vinculo_presupuesto();
"""  # noqa: S608 — solo constantes de este módulo, sin entrada externa

DOWNGRADE = f"""
-- Solo para reconstruir las BD de test y E2E: nunca debe fallar por los datos (data-model).
DROP TRIGGER borradores_factura_validar_vinculo ON borradores_factura;
DROP VIEW v_listado_presupuestos;
DROP FUNCTION public.estado_presupuesto(uuid);

ALTER TABLE eventos_auditoria DROP CONSTRAINT ck_eventos_auditoria_tipo;
ALTER TABLE eventos_auditoria ADD CONSTRAINT ck_eventos_auditoria_tipo
    CHECK (tipo IN ({_TIPOS_0004}, {_TIPOS_0005})) NOT VALID;

ALTER TABLE configuracion_facturacion DROP CONSTRAINT ck_config_contacto_sin_vacios;
ALTER TABLE configuracion_facturacion ADD CONSTRAINT ck_config_contacto_sin_vacios
    CHECK ({_CONTACTO_0007});
ALTER TABLE configuracion_facturacion DROP CONSTRAINT ck_config_validez_presupuesto;
ALTER TABLE configuracion_facturacion
    DROP COLUMN pie_presupuesto,
    DROP COLUMN validez_presupuesto_dias;

ALTER TABLE contadores_factura DROP CONSTRAINT ck_contadores_factura_serie;
ALTER TABLE contadores_factura ADD CONSTRAINT ck_contadores_factura_serie
    CHECK (serie IN ('FAC', 'REC')) NOT VALID;

ALTER TABLE borradores_factura DROP CONSTRAINT uq_borradores_factura_presupuesto_id;
ALTER TABLE borradores_factura DROP CONSTRAINT fk_borradores_factura_presupuesto_id_presupuestos;
ALTER TABLE borradores_factura DROP COLUMN presupuesto_id;

DROP TABLE cierres_presupuesto;
DROP TABLE desgloses_presupuesto;
DROP TABLE lineas_presupuesto;
DROP TABLE presupuestos;
DROP TABLE lineas_borrador_presupuesto;
DROP TABLE borradores_presupuesto;
DROP FUNCTION public.validar_vinculo_presupuesto();
DROP FUNCTION public.validar_cierre_presupuesto();
DROP FUNCTION public.impedir_modificacion_presupuesto();
"""


def upgrade() -> None:
    op.execute(UPGRADE)
    for tabla in _TABLAS_INALTERABLES:
        op.execute(f"REVOKE UPDATE, DELETE, TRUNCATE ON {tabla} FROM jb_app")
        op.execute(
            f"CREATE TRIGGER {tabla}_sin_modificaciones BEFORE UPDATE OR DELETE ON {tabla} "
            "FOR EACH ROW EXECUTE FUNCTION public.impedir_modificacion_presupuesto()"
        )
        op.execute(
            f"CREATE TRIGGER {tabla}_sin_truncate BEFORE TRUNCATE ON {tabla} "
            "FOR EACH STATEMENT EXECUTE FUNCTION public.impedir_modificacion_presupuesto()"
        )


def downgrade() -> None:
    """Vuelta atrás (p. ej. al reconstruir la BD de test o de E2E).

    Los eventos de auditoría de presupuestos no se pueden borrar, y puede haber contadores PRE: los
    CHECK anteriores se restauran `NOT VALID`, como en 0005 y 0006. Al borrar las tablas de solo
    inserción se borran también sus triggers.
    """
    op.execute(DOWNGRADE)
