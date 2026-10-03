# Data Model — 005 Presupuestos

**Fecha**: 2026-10-02 · **Spec**: [spec.md](spec.md) · **Research**: [research.md](research.md)

## Convenciones

Las de 002 (data-model, «Convenciones»):
- **Tipos**:
  - `NUMERIC(12,2)` para los importes, `NUMERIC(9,2)` para las unidades y `NUMERIC(5,2)` para el
    IVA.
  - Identificadores `uuidv7()`.
- **Nombres** con el `NAMING_CONVENTION` del proyecto: `pk_`, `fk_<tabla>_<col>_<ref>`, `ck_`,
  `uq_` e `ix_`.
- **Migración**: `0008_presupuestos.py`, escrita en SQL a mano como la 0005, con `downgrade`. Los
  `CHECK` que amplía se restauran `NOT VALID`, para que el `downgrade` nunca falle por los datos
  (patrón de 0005 y 0006).
- 🔒 marca una tabla de **solo inserción**:
  - `REVOKE UPDATE, DELETE, TRUNCATE ... FROM jb_app`.
  - Triggers `<tabla>_sin_modificaciones` (BEFORE UPDATE OR DELETE) y `<tabla>_sin_truncate`, que
    ejecutan `impedir_modificacion_presupuesto()` y paran también a `jb_owner` (R-2).
- El resto de tablas nuevas recibe SELECT, INSERT, UPDATE y DELETE para `jb_app` por los
  `ALTER DEFAULT PRIVILEGES` de la 0001.

## Diagrama

```text
clientes ─┬─< borradores_presupuesto ─< lineas_borrador_presupuesto
          │
          └─< presupuestos 🔒 ─┬─< lineas_presupuesto 🔒
                               ├─< desgloses_presupuesto 🔒
                               └── cierres_presupuesto 🔒 (0..1 por presupuesto)
                                     ├── presupuesto_nuevo_id → presupuestos   (sustitución)
                                     └── factura_id → facturas                  (conversión)

borradores_factura (002) ── presupuesto_id → presupuestos (0..1 por presupuesto, mutable)
contadores_factura (002): serie ∈ {FAC, REC, PRE}
configuracion_facturacion (002/003): + validez_presupuesto_dias, pie_presupuesto
```

## Cambios en tablas existentes

### `configuracion_facturacion` (fila única y mutable)

| Columna | Tipo | Restricciones | Notas |
|---|---|---|---|
| `validez_presupuesto_dias` | `smallint` | `NOT NULL DEFAULT 30`, `ck_config_validez_presupuesto CHECK (BETWEEN 1 AND 365)` | FR-031 |
| `pie_presupuesto` | `varchar(600)` | NULL. Se añade al `CHECK` de «sin vacíos» de la 0007, que se rehace como `ck_config_contacto_sin_vacios` | FR-031. Si es NULL, se imprime `pie_factura` |

En la aplicación, las dos columnas entran en `CAMPOS_AUDITADOS`
(`services/configuracion_facturacion.py`), de modo que sus cambios se auditan con
`configuracion_facturacion_cambiada`. Se conservan si la petición no las incluye.

### `contadores_factura`

- `ck_contadores_factura_serie` pasa a `CHECK (serie IN ('FAC', 'REC', 'PRE'))`.
- Los triggers `contador_solo_al_alza` y los de sin borrado no cambian y protegen también la fila
  PRE.
- El nombre de la tabla se mantiene por compatibilidad (R-4).

### `borradores_factura`

| Columna | Tipo | Restricciones | Notas |
|---|---|---|---|
| `presupuesto_id` | `uuid` | NULL, `fk_borradores_factura_presupuesto_id_presupuestos` `ON DELETE RESTRICT`, `uq_borradores_factura_presupuesto_id UNIQUE` | Borrador creado por «Convertir en factura» (FR-018). Como mucho uno por presupuesto, porque los NULL no chocan en el UNIQUE |

- **Trigger** `borradores_factura_validar_vinculo` (BEFORE INSERT OR UPDATE OF `presupuesto_id`):
  rechaza el vínculo si el presupuesto ya tiene un cierre (R-6).
- **Mensaje y código**: «El presupuesto ya está cerrado», con `ERRCODE` `check_violation` y
  `CONSTRAINT = 'tg_borradores_factura_presupuesto_cerrado'` (R-6), que es lo que traduce
  `core/errors.py`.

La aplicación nunca cambia `presupuesto_id` después de crear el borrador: los `PUT` de 002 no lo
incluyen.

### `eventos_auditoria`

`ck_eventos_auditoria_tipo` se rehace con `_TIPOS_0004 + _TIPOS_0005 + _TIPOS_0008`. Los tipos
nuevos de la 0008 son:
- `borrador_presupuesto_creado`, `borrador_presupuesto_editado` y `borrador_presupuesto_eliminado`.
- `presupuesto_emitido`, `presupuesto_modificado`, `presupuesto_anulado` y
  `presupuesto_convertido`.

El modelo los toma de `TipoEvento`. La creación del borrador vinculado usa el
`borrador_factura_creado` de 002, con `presupuesto_id` en `detalle`.

## Tablas nuevas

### `borradores_presupuesto` (mutable)

Copia de `borradores_factura` con la validez:
- `id`.
- `cliente_id`: NULL, FK `ON DELETE RESTRICT`.
- `fecha` y `valido_hasta`: `date NOT NULL`.
- `tipo_iva_previsto`, `oro_inversion` (por defecto `false`), y `base_prevista`, `cuota_prevista`
  y `total_previsto` (por defecto 0).
- `version`: concurrencia optimista.
- `creado_en`, `creado_por_id`, `actualizado_en` y `actualizado_por_id`.

Restricciones:
- `ck_borradores_presupuesto_validez CHECK (valido_hasta >= fecha)`.
- Índices: `ix_borradores_presupuesto_fecha (fecha DESC, id)` y
  `ix_borradores_presupuesto_cliente_id`.

### `lineas_borrador_presupuesto` (mutable, en cascada)

Mismas columnas y restricciones que `lineas_borrador`:
- `borrador_id`: FK a `borradores_presupuesto`, `ON DELETE CASCADE`.
- `orden` entre 1 y 100, `unidades > 0`, descripción no vacía de hasta 500 y precio ≥ 0.
- `uq_lineas_borrador_presupuesto_orden (borrador_id, orden)`.

### `presupuestos` 🔒

| Columna | Tipo | Notas |
|---|---|---|
| `id` | `uuid` | PK |
| `serie` | `varchar(3)` | `ck_presupuestos_serie CHECK (serie = 'PRE')` |
| `anio`, `numero`, `num_serie` | `smallint`, `integer`, `varchar(60)` | Mismos `CHECK` que facturas: `anio` igual al año de `fecha`, `numero > 0` y el formato de `num_serie` con `lpad` a 4. `uq_presupuestos_numero (serie, anio, numero)` y `uq_presupuestos_num_serie` |
| `fecha` | `date` | `ck_presupuestos_fecha_minima CHECK (fecha >= DATE '2024-10-28')` (FR-008) |
| `valido_hasta` | `date` | `ck_presupuestos_validez CHECK (valido_hasta >= fecha)` |
| `emisor_nif`, `emisor_nombre`, `emisor_direccion`, `emisor_codigo_postal`, `emisor_localidad`, `emisor_provincia`, `emisor_iban` | Los tipos de `facturas` | Copia al emitir (FR-010). Mismo `CHECK` de NIF y de IBAN |
| `cliente_id` | `uuid` | FK `ON DELETE RESTRICT` |
| `dest_nombre`, `dest_identificacion_pais`, `dest_identificacion_tipo`, `dest_identificacion_numero`, `dest_pais` | Los de `facturas`, `NOT NULL` | Copia al emitir |
| `dest_direccion`, `dest_codigo_postal`, `dest_localidad`, `dest_provincia` | Los de `facturas`, **NULL** | El domicilio no se exige para un presupuesto (FR-011) |
| `oro_inversion` | `boolean NOT NULL` | Todo el presupuesto, sin IVA (FR-007) |
| `base_total`, `cuota_total`, `importe_total` | `numeric(12,2)` | `ck_presupuestos_total CHECK (importe_total = base_total + cuota_total)`, `ck_presupuestos_positivo CHECK (importe_total > 0)` y `cuota_total = 0` si `oro_inversion` |
| `emitido_por_id`, `emitido_en` | `uuid`, `timestamptz DEFAULT now()` | Autor y fecha de emisión |
| `clave_idempotencia` | `uuid` | `uq_presupuestos_clave_idempotencia` |
| `operacion_idempotencia` | `varchar(20)` | `CHECK IN ('emitir', 'emitir_borrador', 'modificar')` |
| `origen_idempotencia` | `uuid` | Borrador de presupuesto o presupuesto original, según la operación |
| `texto_busqueda` | `text GENERATED ALWAYS AS (inmutable_unaccent(lower(num_serie || ' ' || dest_nombre || ' ' || dest_identificacion_numero))) STORED` | La misma expresión que facturas |

Índices: `ix_presupuestos_fecha (fecha DESC, numero DESC)`, `ix_presupuestos_texto_busqueda`
(GIN `gin_trgm_ops`) e `ix_presupuestos_cliente_id`.

### `lineas_presupuesto` 🔒

Columnas de `lineas_factura`:
- `presupuesto_id`, `orden`, `unidades`, `descripcion` y `precio_unitario`.
- `tipo_iva`: NULL si es de oro de inversión, con el `CHECK` de la 0006 (0 a 99,99).
- `importe`.

`uq_lineas_presupuesto_orden (presupuesto_id, orden)`.

### `desgloses_presupuesto` 🔒

- PK `(presupuesto_id, orden)`.
- `tipo_iva`: NULL si es exento de oro de inversión.
- `base` y `cuota`.
- `ck_desgloses_presupuesto_exento CHECK (tipo_iva IS NOT NULL OR cuota = 0)`.

Sin `clave_regimen`, `calificacion_operacion` ni `operacion_exenta`, porque no es un registro
fiscal (R-1).

### `cierres_presupuesto` 🔒

| Columna | Tipo | Notas |
|---|---|---|
| `id` | `uuid` | PK |
| `presupuesto_id` | `uuid NOT NULL` | FK. **`uq_cierres_presupuesto_presupuesto_id UNIQUE`**: como mucho un cierre (R-6) |
| `tipo` | `varchar(12)` | `CHECK IN ('anulacion', 'sustitucion', 'conversion')` |
| `motivo_texto` | `varchar(500)` | Obligatorio en la anulación y la sustitución |
| `presupuesto_nuevo_id` | `uuid` | FK a `presupuestos`, `UNIQUE`. Solo en la sustitución |
| `factura_id` | `uuid` | FK a `facturas`, `UNIQUE`. Solo en la conversión |
| `creado_por_id`, `creado_en` | `uuid`, `timestamptz DEFAULT now()` | |
| `clave_idempotencia` | `uuid` | `UNIQUE`. Solo en la anulación (la sustitución la guarda en el presupuesto nuevo y la conversión, en la factura) |
| `operacion_idempotencia` | `varchar(20)` | `CHECK IN ('anular')` |

`ck_cierres_presupuesto_tipo` exige, según el tipo:

| Tipo | Motivo | `presupuesto_nuevo_id` | `factura_id` | Clave |
|---|---|---|---|---|
| `anulacion` | sí | NULL | NULL | sí |
| `sustitucion` | sí | sí, distinto de `presupuesto_id` | NULL | NULL |
| `conversion` | NULL | NULL | sí | NULL |

**Trigger** `cierres_presupuesto_validar` (BEFORE INSERT): rechaza una `anulacion` o una
`sustitucion` si existe un `borradores_factura` con ese `presupuesto_id` (FR-021). Mensaje: «El
presupuesto está en facturación». `ERRCODE`: `check_violation`, con
`CONSTRAINT = 'tg_cierres_presupuesto_en_facturacion'` (R-6).

## Estado derivado (R-3)

```sql
CREATE FUNCTION public.estado_presupuesto(p_presupuesto uuid)
RETURNS text LANGUAGE sql STABLE AS $$
    SELECT coalesce(
        (SELECT CASE c.tipo WHEN 'anulacion' THEN 'anulado'
                            WHEN 'sustitucion' THEN 'sustituido'
                            ELSE 'convertido' END
         FROM cierres_presupuesto c WHERE c.presupuesto_id = p_presupuesto),
        CASE WHEN EXISTS (SELECT 1 FROM borradores_factura b WHERE b.presupuesto_id = p_presupuesto)
             THEN 'en_facturacion' ELSE 'pendiente' END)
$$;
```

**Estado visible** (`domain/presupuestos.estado_visible`): el guardado, salvo un `pendiente` con
`valido_hasta < hoy`, que se muestra `caducado`.

```text
                ┌──────────── eliminar (no consume número) ────────────┐
   borrador ────┤                                                      ▼
                └─ emitir ─► pendiente ──(valido_hasta < hoy)──► caducado
                               │  ▲                                │
                               │  └── eliminar el borrador vinculado ┤
                               ▼                                   ▼
             «Convertir» ─► en_facturacion ── emitir el borrador ─► convertido
   pendiente/caducado ── Modificar (admin) ──► sustituido  (+ presupuesto nuevo, pendiente)
   pendiente/caducado ── Anular (admin) ─────► anulado
```

Los estados `convertido`, `sustituido` y `anulado` son terminales. Desde `en_facturacion` solo se
sale emitiendo la factura o eliminando el borrador vinculado.

## Vista `v_listado_presupuestos`

```sql
CREATE VIEW v_listado_presupuestos AS
    SELECT 'borrador'::text AS tipo_documento, b.id, NULL::varchar AS num_serie,
           NULL::integer AS numero, b.fecha, b.valido_hasta,
           c.nombre::text AS cliente_nombre, c.identificacion_numero::text AS identificacion,
           b.base_prevista AS base, b.cuota_prevista AS cuota, b.total_previsto AS total,
           'borrador'::text AS estado, coalesce(c.texto_busqueda, '') AS texto_busqueda,
           b.oro_inversion
    FROM borradores_presupuesto b LEFT JOIN clientes c ON c.id = b.cliente_id
    UNION ALL
    SELECT 'presupuesto', p.id, p.num_serie, p.numero, p.fecha, p.valido_hasta,
           p.dest_nombre::text, p.dest_identificacion_numero::text,
           p.base_total, p.cuota_total, p.importe_total,
           public.estado_presupuesto(p.id), p.texto_busqueda, p.oro_inversion
    FROM presupuestos p;
```

Tiene las mismas columnas y el mismo orden que `v_listado_facturas`, salvo `valido_hasta`, de modo
que `repositories/listado.py` sirve para las dos (R-8).

**Totales del listado impreso** (FR-030):
- Suman las filas con `tipo_documento = 'presupuesto' AND estado IN ('pendiente',
  'en_facturacion', 'convertido')`.
- El desglose por tipo de IVA hace `JOIN desgloses_presupuesto` y se agrupa por `tipo_iva`, con
  la misma SQL que `totales_vigentes` de 003.
- Se cuentan aparte `borrador`, `sustituido` y `anulado`.

## Modelos ORM y de vista

**ORM**:
- `models/presupuesto.py`: `Presupuesto`, `LineaPresupuesto` y `DesglosePresupuesto`, con
  relaciones `selectin` y `viewonly`, como `Factura`.
- `models/borrador_presupuesto.py`: `BorradorPresupuesto` y `LineaBorradorPresupuesto`, con
  `version_id_col`.
- `models/cierre_presupuesto.py`: `CierrePresupuesto`.
- `models/borrador_factura.py`: añade `presupuesto_id` y una relación `presupuesto` en
  `lazy="joined"` para la referencia.
- `models/configuracion_facturacion.py`: añade `validez_presupuesto_dias` y `pie_presupuesto`.

**Dominio** (`domain/tipos.py`):
- `Serie.PRESUPUESTO = "PRE"`.
- `EstadoPresupuesto`: `borrador`, `pendiente`, `caducado`, `en_facturacion`, `convertido`,
  `sustituido` y `anulado`.
- `TipoCierrePresupuesto`: `anulacion`, `sustitucion` y `conversion`.
- Los `TipoEvento` nuevos.

**Modelo de vista** (`services/impresion_presupuestos.py`):
- `PresupuestoImpreso`: `titulo`, `aviso_no_fiscal`, `num_serie`, `fecha`, `valido_hasta`,
  `marcas`, `emisor`, `contacto`, `destinatario`, `lineas`, `desglose`, los totales,
  `mencion_exencion`, `iban` y `pie`.
- **No tiene `qr`** (R-10).
- `ListadoImpreso` se reutiliza con `textos` (R-8).

## Datos de ejemplo (FR-036)

`services/datos_ejemplo.py → _cargar_presupuestos`, dentro de la misma carga que la facturación,
con `ResumenCarga.presupuestos` y `ResumenCarga.borradores_presupuesto`. Siembra presupuestos de
varios meses:
- Unos 30 emitidos: pendientes, varios caducados (con la validez en el pasado), dos en facturación
  con su borrador de factura y tres convertidos con su factura emitida.
- Dos sustituidos con su sustituto, dos anulados y tres borradores.

Las conversiones crean facturas. `e2e/facturas-listado.spec.ts` cuenta las facturas sembradas, así
que sus recuentos se ajustan en la misma tarea.
