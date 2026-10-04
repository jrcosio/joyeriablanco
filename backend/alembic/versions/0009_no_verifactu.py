"""Modalidad No VERI*FACTU: registros firmados y registro de eventos (feature 004; data-model.md).

Se escribe en SQL, como la 0005 y la 0008, para controlar los nombres de las restricciones y
declarar las funciones y los triggers.

- `registros_facturacion` gana su XML firmado y el certificado con que se firmó. En `no_verifactu`
  la firma es obligatoria y el estado de remisión es `no_aplica` (R-4, R-14). Las restricciones se
  añaden `NOT VALID`: los registros anteriores no se tocan (constitución III).
- `registros_evento`: la cadena de eventos de F-17 (Orden, art. 9), de SOLO INSERCIÓN, con su
  trigger de encadenamiento como el de los registros de facturación (R-7).
- `comprobaciones_integridad`: cada comprobación lanzada, con su alcance y su resultado, de SOLO
  INSERCIÓN. Alimenta la alarma (R-11).
- La modalidad de la configuración pasa a `no_verifactu` si aún no se había fijado (R-14).

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-03
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# De la 0008: el CHECK de auditoría se rehace con los tipos de cada feature.
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
_TIPOS_0009 = "'registros_exportados', 'integridad_comprobada'"
# F-17, TipoEventoType y TipoAnomaliaType.
_TIPOS_EVENTO_SIF = "'01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '90'"
_TIPOS_ANOMALIA = (
    "'01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12', '13', '14', '15', '90'"
)
_FECHA_HORA = "'^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}[+-][0-9]{2}:[0-9]{2}$'"
_HUELLA = "'^[0-9A-F]{64}$'"
_TABLAS_INALTERABLES = ("registros_evento", "comprobaciones_integridad")

UPGRADE = f"""
-- ============================================== registros de facturación firmados (R-4) 🔒
ALTER TABLE registros_facturacion
    ADD COLUMN xml_firmado bytea,
    ADD COLUMN certificado_titular varchar(200),
    ADD COLUMN certificado_huella char(64);
ALTER TABLE registros_facturacion ADD CONSTRAINT ck_registros_facturacion_certificado_huella
    CHECK (certificado_huella ~ {_HUELLA});
ALTER TABLE registros_facturacion ADD CONSTRAINT ck_registros_facturacion_firma CHECK (
    modalidad <> 'no_verifactu'
    OR (xml_firmado IS NOT NULL AND certificado_titular IS NOT NULL
        AND certificado_huella IS NOT NULL)
) NOT VALID;
ALTER TABLE registros_facturacion DROP CONSTRAINT ck_registros_facturacion_estado_remision;
ALTER TABLE registros_facturacion ADD CONSTRAINT ck_registros_facturacion_estado_remision CHECK (
    estado_remision IN ('pendiente', 'no_aplica')
    AND (modalidad <> 'no_verifactu' OR estado_remision = 'no_aplica')
) NOT VALID;

-- ============================================================= registros de evento (R-7) 🔒
CREATE TABLE registros_evento (
    id uuid NOT NULL DEFAULT uuidv7(),
    secuencia bigint NOT NULL,
    tipo_evento char(2) NOT NULL,
    fecha_hora_huso_gen varchar(25) NOT NULL,
    primer_evento boolean NOT NULL,
    tipo_evento_anterior char(2),
    fecha_hora_huso_gen_anterior varchar(25),
    huella_anterior char(64),
    tipo_huella char(2) NOT NULL DEFAULT '01',
    huella char(64) NOT NULL,
    -- Solo en las detecciones (04 y 06): el tipo de anomalía y la secuencia del registro o del
    -- evento afectado. No están en el XML (RegistroFacturacionAnomalo no lleva secuencia); sirven
    -- para la alarma (R-11) y para no repetir el evento de una anomalía ya registrada.
    tipo_anomalia char(2),
    secuencia_afectada bigint,
    contenido jsonb NOT NULL,
    xml_firmado bytea NOT NULL,
    certificado_titular varchar(200) NOT NULL,
    certificado_huella char(64) NOT NULL,
    generado_en timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT pk_registros_evento PRIMARY KEY (id),
    CONSTRAINT uq_registros_evento_secuencia UNIQUE (secuencia),
    CONSTRAINT uq_registros_evento_huella UNIQUE (huella),
    CONSTRAINT ck_registros_evento_secuencia CHECK (secuencia > 0),
    CONSTRAINT ck_registros_evento_tipo CHECK (tipo_evento IN ({_TIPOS_EVENTO_SIF})),
    CONSTRAINT ck_registros_evento_tipo_anterior
        CHECK (tipo_evento_anterior IN ({_TIPOS_EVENTO_SIF})),
    CONSTRAINT ck_registros_evento_fecha_hora CHECK (fecha_hora_huso_gen ~ {_FECHA_HORA}),
    CONSTRAINT ck_registros_evento_fecha_hora_anterior
        CHECK (fecha_hora_huso_gen_anterior ~ {_FECHA_HORA}),
    CONSTRAINT ck_registros_evento_primer_evento CHECK (
        primer_evento = (huella_anterior IS NULL)
        AND primer_evento = (tipo_evento_anterior IS NULL)
        AND primer_evento = (fecha_hora_huso_gen_anterior IS NULL)
    ),
    CONSTRAINT ck_registros_evento_huella_anterior CHECK (huella_anterior ~ {_HUELLA}),
    CONSTRAINT ck_registros_evento_tipo_huella CHECK (tipo_huella = '01'),
    CONSTRAINT ck_registros_evento_huella CHECK (huella ~ {_HUELLA}),
    CONSTRAINT ck_registros_evento_anomalia CHECK (
        (tipo_evento IN ('04', '06')) = (tipo_anomalia IS NOT NULL)
        AND (tipo_anomalia IS NOT NULL OR secuencia_afectada IS NULL)
    ),
    CONSTRAINT ck_registros_evento_tipo_anomalia CHECK (tipo_anomalia IN ({_TIPOS_ANOMALIA})),
    CONSTRAINT ck_registros_evento_certificado_huella CHECK (certificado_huella ~ {_HUELLA})
);
CREATE INDEX ix_registros_evento_tipo_evento ON registros_evento (tipo_evento, secuencia);

CREATE FUNCTION public.validar_encadenamiento_eventos()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    ultimo record;
BEGIN
    SELECT secuencia, tipo_evento, fecha_hora_huso_gen, huella INTO ultimo
    FROM registros_evento ORDER BY secuencia DESC LIMIT 1;
    IF NOT FOUND THEN
        IF NEW.secuencia <> 1 OR NOT NEW.primer_evento THEN
            RAISE EXCEPTION 'El primer evento de la cadena debe tener secuencia 1 y marcarse como primer evento'
                USING ERRCODE = 'integrity_constraint_violation';
        END IF;
    ELSIF NEW.primer_evento OR NEW.secuencia <> ultimo.secuencia + 1
          OR NEW.huella_anterior IS DISTINCT FROM ultimo.huella
          OR NEW.tipo_evento_anterior IS DISTINCT FROM ultimo.tipo_evento
          OR NEW.fecha_hora_huso_gen_anterior IS DISTINCT FROM ultimo.fecha_hora_huso_gen THEN
        RAISE EXCEPTION 'El evento no encadena con el anterior (secuencia %)', ultimo.secuencia
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NEW;
END
$$;
CREATE TRIGGER registros_evento_encadenamiento
    BEFORE INSERT ON registros_evento
    FOR EACH ROW EXECUTE FUNCTION public.validar_encadenamiento_eventos();

-- ============================================================= comprobaciones (R-9, R-11) 🔒
CREATE TABLE comprobaciones_integridad (
    id uuid NOT NULL DEFAULT uuidv7(),
    lanzada_en timestamptz NOT NULL DEFAULT now(),
    origen varchar(10) NOT NULL,
    actor_id uuid,
    desde_secuencia bigint,
    hasta_secuencia bigint,
    llega_al_final boolean NOT NULL,
    registros integer NOT NULL,
    eventos integer NOT NULL,
    anomalias integer NOT NULL,
    max_secuencia_anomala bigint,
    max_evento_anomalo bigint,
    evento_lanzamiento_id uuid NOT NULL,
    CONSTRAINT pk_comprobaciones_integridad PRIMARY KEY (id),
    CONSTRAINT ck_comprobaciones_integridad_origen CHECK (origen IN ('web', 'consola')),
    CONSTRAINT ck_comprobaciones_integridad_actor CHECK ((origen = 'web') = (actor_id IS NOT NULL)),
    CONSTRAINT ck_comprobaciones_integridad_rango CHECK (
        desde_secuencia IS NULL OR hasta_secuencia IS NULL OR desde_secuencia <= hasta_secuencia
    ),
    CONSTRAINT ck_comprobaciones_integridad_recuentos
        CHECK (registros >= 0 AND eventos >= 0 AND anomalias >= 0),
    CONSTRAINT fk_comprobaciones_integridad_actor_id_usuarios
        FOREIGN KEY (actor_id) REFERENCES usuarios (id),
    CONSTRAINT fk_comprobaciones_integridad_evento_lanzamiento_id_registros_evento
        FOREIGN KEY (evento_lanzamiento_id) REFERENCES registros_evento (id)
);

-- ========================================================================== modalidad (R-14)
UPDATE configuracion_facturacion SET modalidad = 'no_verifactu' WHERE modalidad IS NULL;

-- ============================================================================ auditoría
ALTER TABLE eventos_auditoria DROP CONSTRAINT ck_eventos_auditoria_tipo;
ALTER TABLE eventos_auditoria ADD CONSTRAINT ck_eventos_auditoria_tipo
    CHECK (tipo IN ({_TIPOS_0004}, {_TIPOS_0005}, {_TIPOS_0008}, {_TIPOS_0009}));
"""  # noqa: S608 — solo constantes de este módulo, sin entrada externa

DOWNGRADE = f"""
-- Solo para reconstruir las BD de test y E2E: nunca debe fallar por los datos (data-model).
ALTER TABLE eventos_auditoria DROP CONSTRAINT ck_eventos_auditoria_tipo;
ALTER TABLE eventos_auditoria ADD CONSTRAINT ck_eventos_auditoria_tipo
    CHECK (tipo IN ({_TIPOS_0004}, {_TIPOS_0005}, {_TIPOS_0008})) NOT VALID;

DROP TABLE comprobaciones_integridad;
DROP TABLE registros_evento;
DROP FUNCTION public.validar_encadenamiento_eventos();

ALTER TABLE registros_facturacion DROP CONSTRAINT ck_registros_facturacion_estado_remision;
ALTER TABLE registros_facturacion ADD CONSTRAINT ck_registros_facturacion_estado_remision
    CHECK (estado_remision IN ('pendiente')) NOT VALID;
ALTER TABLE registros_facturacion DROP CONSTRAINT ck_registros_facturacion_firma;
ALTER TABLE registros_facturacion DROP CONSTRAINT ck_registros_facturacion_certificado_huella;
ALTER TABLE registros_facturacion
    DROP COLUMN xml_firmado,
    DROP COLUMN certificado_titular,
    DROP COLUMN certificado_huella;
"""


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

    Los eventos de auditoría de 004 no se pueden borrar: el CHECK anterior se restaura `NOT VALID`,
    como en 0005 y 0008. Al borrar las tablas de solo inserción se borran también sus triggers.
    La modalidad fijada en la configuración se conserva.
    """
    op.execute(DOWNGRADE)
