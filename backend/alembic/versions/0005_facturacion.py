"""Facturación con registro Verifactu (feature 002; data-model.md, research R-6 a R-8, R-12, R-15).

Se escribe en SQL para controlar exactamente los nombres de las restricciones (ver la nota de
0004 sobre el doble prefijo) y para declarar funciones, triggers y la vista.

Garantías en la BD (constitución III, «no solo en la capa de aplicación»):
- facturas, lineas_factura, desgloses_factura, correcciones_factura y registros_facturacion son de
  SOLO INSERCIÓN: REVOKE UPDATE/DELETE/TRUNCATE a jb_app y triggers que paran también a jb_owner.
- La cadena de registros es lineal (trigger validar_encadenamiento).
- El contador de numeración solo avanza y no se borra (trigger contador_solo_al_alza).
- Solo se corrige una factura vigente (trigger validar_correccion con estado_factura()).
- El estado derivado vive en UNA función, estado_factura(), que usan la vista y el trigger.

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-29
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

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
# L8A de F-1 (DsRegistroVeriFactu.xlsx v1.0, hoja «6) Listas»).
_CLAVES_L8A = (
    "'01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '14', '15', '17', '18', "
    "'19', '20'"
)
# F-3 §15.1: tipos admitidos con S1 (las ventanas de fechas se validan en domain/importes.py).
_TIPOS_IVA = "0, 2, 4, 5, 7.5, 10, 21"
_TABLAS_INALTERABLES = (
    "facturas",
    "lineas_factura",
    "desgloses_factura",
    "registros_facturacion",
    "correcciones_factura",
)

UPGRADE = f"""
-- ============================================================== configuración (fila única)
CREATE TABLE configuracion_facturacion (
    id smallint NOT NULL DEFAULT 1,
    iva_por_defecto numeric(5,2) NOT NULL DEFAULT 21.00,
    clave_regimen char(2) NOT NULL DEFAULT '01',
    modalidad varchar(20),
    emisor_nombre varchar(120),
    emisor_nif char(9),
    emisor_direccion varchar(200),
    emisor_codigo_postal char(5),
    emisor_localidad varchar(100),
    emisor_provincia_codigo char(2),
    version integer NOT NULL DEFAULT 1,
    actualizado_en timestamptz NOT NULL DEFAULT now(),
    actualizado_por_id uuid,
    CONSTRAINT pk_configuracion_facturacion PRIMARY KEY (id),
    CONSTRAINT ck_configuracion_facturacion_fila_unica CHECK (id = 1),
    CONSTRAINT ck_configuracion_facturacion_iva CHECK (iva_por_defecto IN ({_TIPOS_IVA})),
    CONSTRAINT ck_configuracion_facturacion_clave_regimen CHECK (clave_regimen IN ({_CLAVES_L8A})),
    CONSTRAINT ck_configuracion_facturacion_modalidad
        CHECK (modalidad IN ('verifactu', 'no_verifactu')),
    CONSTRAINT ck_configuracion_facturacion_emisor_nif CHECK (emisor_nif ~ '^[0-9A-Z]{{9}}$'),
    CONSTRAINT ck_configuracion_facturacion_emisor_cp CHECK (emisor_codigo_postal ~ '^[0-9]{{5}}$'),
    CONSTRAINT ck_configuracion_facturacion_emisor_nombre CHECK (length(trim(emisor_nombre)) > 0),
    CONSTRAINT fk_configuracion_facturacion_emisor_provincia_codigo_provincias
        FOREIGN KEY (emisor_provincia_codigo) REFERENCES provincias (codigo),
    CONSTRAINT fk_configuracion_facturacion_actualizado_por_id_usuarios
        FOREIGN KEY (actualizado_por_id) REFERENCES usuarios (id)
);
INSERT INTO configuracion_facturacion (id) VALUES (1);
REVOKE INSERT, DELETE, TRUNCATE ON configuracion_facturacion FROM jb_app;

-- ====================================================================== inalterabilidad
CREATE FUNCTION public.impedir_modificacion_facturacion()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Los documentos de facturación emitidos son inalterables'
        USING ERRCODE = 'insufficient_privilege';
END
$$;

-- ======================================================================= contadores (R-7)
CREATE TABLE contadores_factura (
    serie varchar(3) NOT NULL,
    anio smallint NOT NULL,
    ultimo_numero integer NOT NULL DEFAULT 0,
    actualizado_en timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT pk_contadores_factura PRIMARY KEY (serie, anio),
    CONSTRAINT ck_contadores_factura_serie CHECK (serie IN ('FAC', 'REC')),
    CONSTRAINT ck_contadores_factura_anio CHECK (anio BETWEEN 2024 AND 9999),
    CONSTRAINT ck_contadores_factura_no_negativo CHECK (ultimo_numero >= 0)
);
REVOKE DELETE, TRUNCATE ON contadores_factura FROM jb_app;

CREATE FUNCTION public.contador_solo_al_alza()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.serie <> OLD.serie OR NEW.anio <> OLD.anio OR NEW.ultimo_numero < OLD.ultimo_numero THEN
        RAISE EXCEPTION 'El contador de facturas solo puede avanzar'
            USING ERRCODE = 'insufficient_privilege';
    END IF;
    RETURN NEW;
END
$$;
CREATE TRIGGER contadores_factura_solo_al_alza
    BEFORE UPDATE ON contadores_factura
    FOR EACH ROW EXECUTE FUNCTION public.contador_solo_al_alza();
CREATE TRIGGER contadores_factura_sin_borrado
    BEFORE DELETE ON contadores_factura
    FOR EACH ROW EXECUTE FUNCTION public.impedir_modificacion_facturacion();
CREATE TRIGGER contadores_factura_sin_truncate
    BEFORE TRUNCATE ON contadores_factura
    FOR EACH STATEMENT EXECUTE FUNCTION public.impedir_modificacion_facturacion();

-- ========================================================================= borradores
CREATE TABLE borradores_factura (
    id uuid NOT NULL DEFAULT uuidv7(),
    cliente_id uuid,
    fecha_expedicion date NOT NULL,
    tipo_iva_previsto numeric(5,2) NOT NULL,
    base_prevista numeric(12,2) NOT NULL DEFAULT 0,
    cuota_prevista numeric(12,2) NOT NULL DEFAULT 0,
    total_previsto numeric(12,2) NOT NULL DEFAULT 0,
    version integer NOT NULL DEFAULT 1,
    creado_en timestamptz NOT NULL DEFAULT now(),
    creado_por_id uuid NOT NULL,
    actualizado_en timestamptz NOT NULL DEFAULT now(),
    actualizado_por_id uuid NOT NULL,
    CONSTRAINT pk_borradores_factura PRIMARY KEY (id),
    CONSTRAINT fk_borradores_factura_cliente_id_clientes
        FOREIGN KEY (cliente_id) REFERENCES clientes (id) ON DELETE RESTRICT,
    CONSTRAINT fk_borradores_factura_creado_por_id_usuarios
        FOREIGN KEY (creado_por_id) REFERENCES usuarios (id),
    CONSTRAINT fk_borradores_factura_actualizado_por_id_usuarios
        FOREIGN KEY (actualizado_por_id) REFERENCES usuarios (id)
);
CREATE INDEX ix_borradores_factura_fecha ON borradores_factura (fecha_expedicion DESC, id);
CREATE INDEX ix_borradores_factura_cliente_id ON borradores_factura (cliente_id);

CREATE TABLE lineas_borrador (
    id uuid NOT NULL DEFAULT uuidv7(),
    borrador_id uuid NOT NULL,
    orden smallint NOT NULL,
    unidades numeric(9,2) NOT NULL,
    descripcion varchar(500) NOT NULL,
    precio_unitario numeric(12,2) NOT NULL,
    CONSTRAINT pk_lineas_borrador PRIMARY KEY (id),
    CONSTRAINT fk_lineas_borrador_borrador_id_borradores_factura
        FOREIGN KEY (borrador_id) REFERENCES borradores_factura (id) ON DELETE CASCADE,
    CONSTRAINT uq_lineas_borrador_orden UNIQUE (borrador_id, orden),
    CONSTRAINT ck_lineas_borrador_orden CHECK (orden BETWEEN 1 AND 100),
    CONSTRAINT ck_lineas_borrador_unidades CHECK (unidades > 0),
    CONSTRAINT ck_lineas_borrador_descripcion CHECK (length(trim(descripcion)) > 0),
    CONSTRAINT ck_lineas_borrador_precio CHECK (precio_unitario >= 0)
);

-- ====================================================================== facturas 🔒
CREATE TABLE facturas (
    id uuid NOT NULL DEFAULT uuidv7(),
    serie varchar(3) NOT NULL,
    anio smallint NOT NULL,
    numero integer NOT NULL,
    num_serie varchar(60) NOT NULL,
    tipo_factura char(2) NOT NULL,
    tipo_rectificativa char(1),
    causa_rectificacion varchar(20),
    factura_rectificada_id uuid,
    base_rectificada numeric(12,2),
    cuota_rectificada numeric(12,2),
    fecha_expedicion date NOT NULL,
    fecha_operacion date,
    descripcion_operacion varchar(500) NOT NULL,
    emisor_nif char(9) NOT NULL,
    emisor_nombre varchar(120) NOT NULL,
    emisor_direccion varchar(200) NOT NULL,
    emisor_codigo_postal char(5) NOT NULL,
    emisor_localidad varchar(100) NOT NULL,
    emisor_provincia varchar(100),
    cliente_id uuid NOT NULL,
    dest_nombre varchar(120) NOT NULL,
    dest_identificacion_pais char(2) NOT NULL,
    dest_identificacion_tipo varchar(3) NOT NULL,
    dest_identificacion_numero varchar(20) NOT NULL,
    dest_direccion varchar(200) NOT NULL,
    dest_codigo_postal varchar(10) NOT NULL,
    dest_localidad varchar(100) NOT NULL,
    dest_provincia varchar(100),
    dest_pais char(2) NOT NULL,
    clave_regimen char(2) NOT NULL,
    modalidad varchar(20) NOT NULL,
    base_total numeric(12,2) NOT NULL,
    cuota_total numeric(12,2) NOT NULL,
    importe_total numeric(12,2) NOT NULL,
    emitida_por_id uuid NOT NULL,
    emitida_en timestamptz NOT NULL DEFAULT now(),
    clave_idempotencia uuid,
    operacion_idempotencia varchar(20),
    origen_idempotencia uuid,
    texto_busqueda text GENERATED ALWAYS AS (
        inmutable_unaccent(lower(num_serie || ' ' || dest_nombre || ' ' || dest_identificacion_numero))
    ) STORED,
    CONSTRAINT pk_facturas PRIMARY KEY (id),
    CONSTRAINT uq_facturas_numero UNIQUE (serie, anio, numero),
    CONSTRAINT uq_facturas_num_serie UNIQUE (num_serie),
    CONSTRAINT uq_facturas_clave_idempotencia UNIQUE (clave_idempotencia),
    CONSTRAINT ck_facturas_serie CHECK (serie IN ('FAC', 'REC')),
    CONSTRAINT ck_facturas_numero CHECK (numero > 0),
    CONSTRAINT ck_facturas_anio CHECK (anio = EXTRACT(YEAR FROM fecha_expedicion)::int),
    CONSTRAINT ck_facturas_num_serie CHECK (
        num_serie = serie || '-' || anio::text || '-'
            || CASE WHEN numero < 10000 THEN lpad(numero::text, 4, '0') ELSE numero::text END
    ),
    CONSTRAINT ck_facturas_tipo_factura CHECK (
        (serie = 'FAC' AND tipo_factura = 'F1')
        OR (serie = 'REC' AND tipo_factura IN ('R1', 'R4'))
    ),
    CONSTRAINT ck_facturas_rectificativa CHECK (
        (serie = 'FAC' AND tipo_rectificativa IS NULL AND causa_rectificacion IS NULL
            AND factura_rectificada_id IS NULL AND base_rectificada IS NULL
            AND cuota_rectificada IS NULL)
        OR (serie = 'REC' AND tipo_rectificativa = 'S' AND factura_rectificada_id IS NOT NULL
            AND base_rectificada IS NOT NULL AND cuota_rectificada IS NOT NULL
            AND ((causa_rectificacion = 'devolucion_o_precio' AND tipo_factura = 'R1')
                OR (causa_rectificacion = 'error_datos' AND tipo_factura = 'R4')))
    ),
    CONSTRAINT ck_facturas_fecha_minima CHECK (fecha_expedicion >= DATE '2024-10-28'),
    CONSTRAINT ck_facturas_fecha_operacion
        CHECK (fecha_operacion IS NULL OR fecha_operacion <= fecha_expedicion),
    CONSTRAINT ck_facturas_descripcion CHECK (length(trim(descripcion_operacion)) > 0),
    CONSTRAINT ck_facturas_emisor_nif CHECK (emisor_nif ~ '^[0-9A-Z]{{9}}$'),
    CONSTRAINT ck_facturas_dest_identificacion_tipo
        CHECK (dest_identificacion_tipo IN ('NIF', '02', '03', '04', '05', '06')),
    CONSTRAINT ck_facturas_clave_regimen CHECK (clave_regimen IN ({_CLAVES_L8A})),
    CONSTRAINT ck_facturas_modalidad CHECK (modalidad IN ('verifactu', 'no_verifactu')),
    CONSTRAINT ck_facturas_importes_no_negativos
        CHECK (base_total >= 0 AND cuota_total >= 0 AND importe_total >= 0),
    CONSTRAINT ck_facturas_total CHECK (importe_total = base_total + cuota_total),
    CONSTRAINT ck_facturas_ordinaria_positiva CHECK (serie <> 'FAC' OR importe_total > 0),
    CONSTRAINT ck_facturas_operacion_idempotencia
        CHECK (operacion_idempotencia IN ('emitir', 'emitir_borrador', 'modificar')),
    CONSTRAINT fk_facturas_cliente_id_clientes
        FOREIGN KEY (cliente_id) REFERENCES clientes (id) ON DELETE RESTRICT,
    CONSTRAINT fk_facturas_factura_rectificada_id_facturas
        FOREIGN KEY (factura_rectificada_id) REFERENCES facturas (id),
    CONSTRAINT fk_facturas_emitida_por_id_usuarios
        FOREIGN KEY (emitida_por_id) REFERENCES usuarios (id)
);
CREATE INDEX ix_facturas_fecha ON facturas (fecha_expedicion DESC, serie, numero DESC);
CREATE INDEX ix_facturas_texto_busqueda ON facturas USING gin (texto_busqueda gin_trgm_ops);
CREATE INDEX ix_facturas_cliente_id ON facturas (cliente_id);
CREATE INDEX ix_facturas_factura_rectificada_id ON facturas (factura_rectificada_id);

CREATE TABLE lineas_factura (
    id uuid NOT NULL DEFAULT uuidv7(),
    factura_id uuid NOT NULL,
    orden smallint NOT NULL,
    unidades numeric(9,2) NOT NULL,
    descripcion varchar(500) NOT NULL,
    precio_unitario numeric(12,2) NOT NULL,
    tipo_iva numeric(5,2) NOT NULL,
    importe numeric(12,2) NOT NULL,
    CONSTRAINT pk_lineas_factura PRIMARY KEY (id),
    CONSTRAINT fk_lineas_factura_factura_id_facturas
        FOREIGN KEY (factura_id) REFERENCES facturas (id),
    CONSTRAINT uq_lineas_factura_orden UNIQUE (factura_id, orden),
    CONSTRAINT ck_lineas_factura_orden CHECK (orden BETWEEN 1 AND 100),
    CONSTRAINT ck_lineas_factura_unidades CHECK (unidades > 0),
    CONSTRAINT ck_lineas_factura_descripcion CHECK (length(trim(descripcion)) > 0),
    CONSTRAINT ck_lineas_factura_precio CHECK (precio_unitario >= 0),
    CONSTRAINT ck_lineas_factura_tipo_iva CHECK (tipo_iva IN ({_TIPOS_IVA})),
    CONSTRAINT ck_lineas_factura_importe CHECK (importe >= 0)
);

CREATE TABLE desgloses_factura (
    factura_id uuid NOT NULL,
    tipo_iva numeric(5,2) NOT NULL,
    clave_regimen char(2) NOT NULL,
    calificacion_operacion char(2) NOT NULL,
    base numeric(12,2) NOT NULL,
    cuota numeric(12,2) NOT NULL,
    CONSTRAINT pk_desgloses_factura PRIMARY KEY (factura_id, tipo_iva),
    CONSTRAINT fk_desgloses_factura_factura_id_facturas
        FOREIGN KEY (factura_id) REFERENCES facturas (id),
    CONSTRAINT ck_desgloses_factura_tipo_iva CHECK (tipo_iva IN ({_TIPOS_IVA})),
    CONSTRAINT ck_desgloses_factura_calificacion CHECK (calificacion_operacion = 'S1'),
    CONSTRAINT ck_desgloses_factura_importes CHECK (base >= 0 AND cuota >= 0)
);

-- ============================================================ registros de facturación 🔒
CREATE TABLE registros_facturacion (
    id uuid NOT NULL DEFAULT uuidv7(),
    secuencia bigint NOT NULL,
    tipo varchar(10) NOT NULL,
    factura_id uuid NOT NULL,
    modalidad varchar(20) NOT NULL,
    id_emisor char(9) NOT NULL,
    num_serie varchar(60) NOT NULL,
    fecha_expedicion char(10) NOT NULL,
    tipo_factura char(2),
    cuota_total numeric(12,2),
    importe_total numeric(12,2),
    primer_registro boolean NOT NULL,
    huella_anterior char(64),
    fecha_hora_huso_gen varchar(25) NOT NULL,
    tipo_huella char(2) NOT NULL DEFAULT '01',
    huella char(64) NOT NULL,
    contenido jsonb NOT NULL,
    estado_remision varchar(20) NOT NULL DEFAULT 'pendiente',
    generado_en timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT pk_registros_facturacion PRIMARY KEY (id),
    CONSTRAINT uq_registros_facturacion_secuencia UNIQUE (secuencia),
    CONSTRAINT uq_registros_facturacion_huella UNIQUE (huella),
    CONSTRAINT ck_registros_facturacion_secuencia CHECK (secuencia > 0),
    CONSTRAINT ck_registros_facturacion_tipo CHECK (tipo IN ('alta', 'anulacion')),
    CONSTRAINT ck_registros_facturacion_campos_tipo CHECK (
        (tipo = 'alta' AND tipo_factura IS NOT NULL AND cuota_total IS NOT NULL
            AND importe_total IS NOT NULL)
        OR (tipo = 'anulacion' AND tipo_factura IS NULL AND cuota_total IS NULL
            AND importe_total IS NULL)
    ),
    CONSTRAINT ck_registros_facturacion_modalidad
        CHECK (modalidad IN ('verifactu', 'no_verifactu')),
    CONSTRAINT ck_registros_facturacion_fecha
        CHECK (fecha_expedicion ~ '^[0-9]{{2}}-[0-9]{{2}}-[0-9]{{4}}$'),
    CONSTRAINT ck_registros_facturacion_primer_registro
        CHECK (primer_registro = (huella_anterior IS NULL)),
    CONSTRAINT ck_registros_facturacion_huella_anterior
        CHECK (huella_anterior ~ '^[0-9A-F]{{64}}$'),
    CONSTRAINT ck_registros_facturacion_fecha_hora CHECK (
        fecha_hora_huso_gen ~ '^[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}T[0-9]{{2}}:[0-9]{{2}}:[0-9]{{2}}[+-][0-9]{{2}}:[0-9]{{2}}$'
    ),
    CONSTRAINT ck_registros_facturacion_tipo_huella CHECK (tipo_huella = '01'),
    CONSTRAINT ck_registros_facturacion_huella CHECK (huella ~ '^[0-9A-F]{{64}}$'),
    CONSTRAINT ck_registros_facturacion_estado_remision CHECK (estado_remision IN ('pendiente')),
    CONSTRAINT fk_registros_facturacion_factura_id_facturas
        FOREIGN KEY (factura_id) REFERENCES facturas (id)
);
CREATE INDEX ix_registros_facturacion_factura_id ON registros_facturacion (factura_id);

CREATE FUNCTION public.validar_encadenamiento()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    ultimo record;
BEGIN
    SELECT secuencia, huella INTO ultimo
    FROM registros_facturacion ORDER BY secuencia DESC LIMIT 1;
    IF NOT FOUND THEN
        IF NEW.secuencia <> 1 OR NOT NEW.primer_registro THEN
            RAISE EXCEPTION 'El primer registro de la cadena debe tener secuencia 1 y marcarse como primer registro'
                USING ERRCODE = 'integrity_constraint_violation';
        END IF;
    ELSIF NEW.primer_registro OR NEW.secuencia <> ultimo.secuencia + 1
          OR NEW.huella_anterior IS DISTINCT FROM ultimo.huella THEN
        RAISE EXCEPTION 'El registro no encadena con el anterior (secuencia %)', ultimo.secuencia
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NEW;
END
$$;
CREATE TRIGGER registros_facturacion_encadenamiento
    BEFORE INSERT ON registros_facturacion
    FOR EACH ROW EXECUTE FUNCTION public.validar_encadenamiento();

-- ======================================================================= correcciones 🔒
CREATE TABLE correcciones_factura (
    id uuid NOT NULL DEFAULT uuidv7(),
    factura_id uuid NOT NULL,
    tipo varchar(30) NOT NULL,
    motivo varchar(30) NOT NULL,
    motivo_texto varchar(500) NOT NULL,
    factura_nueva_id uuid,
    registro_anulacion_id uuid,
    creada_por_id uuid NOT NULL,
    creada_en timestamptz NOT NULL DEFAULT now(),
    clave_idempotencia uuid,
    operacion_idempotencia varchar(20),
    CONSTRAINT pk_correcciones_factura PRIMARY KEY (id),
    CONSTRAINT uq_correcciones_factura_factura_nueva_id UNIQUE (factura_nueva_id),
    CONSTRAINT uq_correcciones_factura_clave_idempotencia UNIQUE (clave_idempotencia),
    CONSTRAINT ck_correcciones_factura_tipo CHECK (
        (tipo = 'anulacion' AND motivo = 'no_debio_emitirse'
            AND factura_nueva_id IS NULL AND registro_anulacion_id IS NOT NULL)
        OR (tipo = 'anulacion_y_reemision' AND motivo = 'no_debio_emitirse'
            AND factura_nueva_id IS NOT NULL AND registro_anulacion_id IS NOT NULL)
        OR (tipo = 'rectificacion_sustitucion' AND motivo = 'factura_entregada'
            AND factura_nueva_id IS NOT NULL AND registro_anulacion_id IS NULL)
    ),
    CONSTRAINT ck_correcciones_factura_motivo_texto CHECK (length(trim(motivo_texto)) > 0),
    CONSTRAINT ck_correcciones_factura_operacion_idempotencia
        CHECK (operacion_idempotencia IN ('modificar', 'anular')),
    CONSTRAINT fk_correcciones_factura_factura_id_facturas
        FOREIGN KEY (factura_id) REFERENCES facturas (id),
    CONSTRAINT fk_correcciones_factura_factura_nueva_id_facturas
        FOREIGN KEY (factura_nueva_id) REFERENCES facturas (id),
    CONSTRAINT fk_correcciones_factura_registro_anulacion_id_registros_facturacion
        FOREIGN KEY (registro_anulacion_id) REFERENCES registros_facturacion (id),
    CONSTRAINT fk_correcciones_factura_creada_por_id_usuarios
        FOREIGN KEY (creada_por_id) REFERENCES usuarios (id)
);
CREATE INDEX ix_correcciones_factura_factura_id ON correcciones_factura (factura_id);
-- Una anulación es definitiva: como mucho una por factura.
CREATE UNIQUE INDEX uq_correcciones_factura_una_anulacion ON correcciones_factura (factura_id)
    WHERE tipo IN ('anulacion', 'anulacion_y_reemision');

-- Estado derivado (research R-8): ÚNICA implementación, usada por la vista y el trigger.
CREATE FUNCTION public.estado_factura(p_factura uuid)
RETURNS text LANGUAGE sql STABLE AS $$
    SELECT CASE
        WHEN EXISTS (
            SELECT 1 FROM correcciones_factura c
            WHERE c.factura_id = p_factura AND c.tipo IN ('anulacion', 'anulacion_y_reemision')
        ) THEN 'anulada'
        WHEN EXISTS (
            SELECT 1 FROM correcciones_factura c
            WHERE c.factura_id = p_factura AND c.tipo = 'rectificacion_sustitucion'
              AND NOT EXISTS (
                  SELECT 1 FROM correcciones_factura a
                  WHERE a.factura_id = c.factura_nueva_id
                    AND a.tipo IN ('anulacion', 'anulacion_y_reemision')
              )
        ) THEN 'rectificada'
        ELSE 'vigente'
    END
$$;

CREATE FUNCTION public.validar_correccion()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    serie_corregida varchar(3);
BEGIN
    IF public.estado_factura(NEW.factura_id) <> 'vigente' THEN
        RAISE EXCEPTION 'Solo se puede corregir una factura vigente'
            USING ERRCODE = 'insufficient_privilege';
    END IF;
    SELECT serie INTO serie_corregida FROM facturas WHERE id = NEW.factura_id;
    IF serie_corregida = 'REC' AND NEW.tipo = 'anulacion_y_reemision' THEN
        RAISE EXCEPTION 'Una rectificativa se anula sin reemitirla'
            USING ERRCODE = 'insufficient_privilege';
    END IF;
    IF NEW.registro_anulacion_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM registros_facturacion r
        WHERE r.id = NEW.registro_anulacion_id AND r.tipo = 'anulacion'
          AND r.factura_id = NEW.factura_id
    ) THEN
        RAISE EXCEPTION 'El registro de anulación no corresponde a la factura corregida'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NEW;
END
$$;
CREATE TRIGGER correcciones_factura_validar
    BEFORE INSERT ON correcciones_factura
    FOR EACH ROW EXECUTE FUNCTION public.validar_correccion();

-- ==================================================================== listado (R-12)
CREATE VIEW v_listado_facturas AS
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
           coalesce(c.texto_busqueda, '') AS texto_busqueda
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
           f.texto_busqueda
    FROM facturas f;

-- ============================================================================ auditoría
ALTER TABLE eventos_auditoria DROP CONSTRAINT ck_eventos_auditoria_tipo;
ALTER TABLE eventos_auditoria ADD CONSTRAINT ck_eventos_auditoria_tipo
    CHECK (tipo IN ({_TIPOS_0004}, {_TIPOS_0005}));
"""  # noqa: S608 — solo constantes de este módulo, sin entrada externa


def upgrade() -> None:
    op.execute(UPGRADE)
    for tabla in _TABLAS_INALTERABLES:
        op.execute(f"REVOKE UPDATE, DELETE, TRUNCATE ON {tabla} FROM jb_app")
        op.execute(
            f"CREATE TRIGGER {tabla}_sin_modificaciones BEFORE UPDATE OR DELETE ON {tabla} "
            "FOR EACH ROW EXECUTE FUNCTION public.impedir_modificacion_facturacion()"
        )
        op.execute(
            f"CREATE TRIGGER {tabla}_sin_truncate BEFORE TRUNCATE ON {tabla} "
            "FOR EACH STATEMENT EXECUTE FUNCTION public.impedir_modificacion_facturacion()"
        )


def downgrade() -> None:
    """Vuelta atrás (p. ej. al reconstruir la BD de test o de E2E).

    Los eventos de auditoría de facturación no se pueden borrar: el CHECK anterior se restaura
    `NOT VALID`, como en 0004.
    """
    op.execute(
        f"""
        ALTER TABLE eventos_auditoria DROP CONSTRAINT ck_eventos_auditoria_tipo;
        ALTER TABLE eventos_auditoria ADD CONSTRAINT ck_eventos_auditoria_tipo
            CHECK (tipo IN ({_TIPOS_0004})) NOT VALID;
        DROP VIEW v_listado_facturas;
        DROP TABLE correcciones_factura;
        DROP FUNCTION public.validar_correccion();
        DROP FUNCTION public.estado_factura(uuid);
        DROP TABLE registros_facturacion;
        DROP FUNCTION public.validar_encadenamiento();
        DROP TABLE desgloses_factura;
        DROP TABLE lineas_factura;
        DROP TABLE facturas;
        DROP TABLE lineas_borrador;
        DROP TABLE borradores_factura;
        DROP TABLE contadores_factura;
        DROP FUNCTION public.contador_solo_al_alza();
        DROP FUNCTION public.impedir_modificacion_facturacion();
        DROP TABLE configuracion_facturacion;
        """
    )
