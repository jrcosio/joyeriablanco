# Data Model — 002 Facturación con registro Verifactu

**Spec**: [spec.md](spec.md) · **Research**: [research.md](research.md) · **Base**:
[001 data-model](../001-cimientos-clientes/data-model.md)

## Convenciones

Se mantienen las de 001: nombres en español y `snake_case`, `id uuid DEFAULT uuidv7()`,
`timestamptz` y propiedad de `jb_owner`. Además:

- **Importes**: `NUMERIC(12,2)`, porque F-1 los define como `Decimal (12,2)`. Unidades
  `NUMERIC(9,2)`. Tipos de IVA `NUMERIC(5,2)`. **Nunca `float`** (constitución II).
- **Fechas de negocio**: `date`, en hora de España peninsular (`Europe/Madrid`).
- **Solo inserción**: las tablas marcadas con 🔒 tienen `REVOKE UPDATE, DELETE, TRUNCATE` para
  `jb_app` y triggers de `impedir_modificacion_facturacion()` que alcanzan también a `jb_owner`
  (R-8).
- **Migración de la feature**: `0005_facturacion`, escrita a mano. Amplía también el `CHECK` de
  `eventos_auditoria.tipo` (R-15), con la técnica de la 0004.
- **Ajuste de cierre** (2026-09-30): `0006_iva_libre_oro_iban`, también a mano y solo con DDL, sin
  ningún `UPDATE`. Ver la sección «Migración 0006» al final.

## Diagrama

```
configuracion_facturacion (fila única)
clientes 1───* borradores_factura 1───* lineas_borrador
clientes 1───* facturas🔒 (cliente_id, ON DELETE RESTRICT)
facturas🔒 1───* lineas_factura🔒
facturas🔒 1───* desgloses_factura🔒
facturas🔒 1───* correcciones_factura🔒 (factura_id: la corregida; como mucho una en vigor, R-8)
correcciones_factura🔒 ──> facturas🔒 (factura_nueva_id: reemisión o rectificativa, nullable)
facturas🔒 ──> facturas🔒 (factura_rectificada_id, solo en REC)
facturas🔒 1───* registros_facturacion🔒 (alta de la propia factura; anulación de la anulada)
registros_facturacion🔒: cadena lineal por `secuencia` (R-6)
contadores_factura (serie, anio): mutable solo al alza (R-7)
usuarios 1───* (borradores, facturas, correcciones): autores (lápidas, 001 R-21)
v_listado_facturas: vista de solo lectura (R-12)
```

---

## configuracion_facturacion

Fila única: `id smallint PK DEFAULT 1 CHECK (id = 1)`. La migración la crea con los valores
iniciales.

| Columna | Tipo | Restricciones | Notas |
|---|---|---|---|
| iva_por_defecto | numeric(5,2) | NOT NULL DEFAULT 21.00, CHECK `>= 0 AND < 100` | Libre de 0 a 99,99. Fuera de `allowed_rates(hoy)` exige `confirmar_tipo_iva` (R-20) |
| modalidad | varchar(20) | NULL, CHECK IN (`verifactu`, `no_verifactu`) | Sin valor inicial (Clarifications). Si es NULL, no se puede emitir (FR-004). No se puede cambiar si existe algún registro (FR-050, R-19) |
| emisor_nombre | varchar(120) | NULL | `NombreRazonEmisor` |
| emisor_nif | char(9) | NULL, CHECK `~ '^[0-9A-Z]{9}$'` | Validado con `domain/identificacion.py` (FR-002) |
| emisor_direccion | varchar(200) | NULL | F-6, art. 6.1.e |
| emisor_codigo_postal | char(5) | NULL | España. La provincia se deriva como en clientes |
| emisor_localidad | varchar(100) | NULL | |
| emisor_provincia_codigo | char(2) | NULL, FK provincias | |
| emisor_iban | varchar(34) | NULL, CHECK `~ '^[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}$'` | Opcional, no entra en `faltan`. Validado con `domain/iban.py` (R-22) |
| version | integer | NOT NULL DEFAULT 1 | Concurrencia optimista |
| actualizado_en | timestamptz | NOT NULL DEFAULT now() | |
| actualizado_por_id | uuid | NULL, FK usuarios | |

**Reglas**:
- **Emisión posible** cuando `modalidad`, `emisor_nombre`, `emisor_nif`, `emisor_direccion`,
  `emisor_codigo_postal` y `emisor_localidad` no son NULL. En producción hacen falta además
  `SIF_*` (R-5).
- **Auditoría**: cada `PUT` deja `configuracion_facturacion_cambiada` con el diff (FR-003), que
  incluye `emisor_iban` y, si se confirmó un tipo fuera de la lista, `tipo_iva_fuera_de_lista`
  (R-20).
- **Sin clave de régimen**: la columna `clave_regimen` se eliminó en la 0006 (R-23).

## contadores_factura

| Columna | Tipo | Restricciones | Notas |
|---|---|---|---|
| serie | varchar(3) | PK (con anio), CHECK IN (`FAC`, `REC`) | |
| anio | smallint | PK, CHECK 2024–9999 | Año de la fecha de expedición |
| ultimo_numero | integer | NOT NULL DEFAULT 0, CHECK ≥ 0 | |
| actualizado_en | timestamptz | NOT NULL DEFAULT now() | |

**Reglas**:
- **Defensa en la BD**: `REVOKE DELETE, TRUNCATE FROM jb_app`. El trigger
  `contador_solo_al_alza` (`BEFORE UPDATE`) lanza `42501` si `NEW.ultimo_numero <
  OLD.ultimo_numero`.
- **Asignación y ajuste**: R-7. El ajuste solo afecta a `FAC` del año en curso y exige que
  `proximo - 1 > ultimo_numero`.

## borradores_factura

| Columna | Tipo | Restricciones | Notas |
|---|---|---|---|
| id | uuid | PK | |
| cliente_id | uuid | NULL, FK clientes ON DELETE RESTRICT | Puede faltar en un borrador incompleto (FR-011) |
| fecha_expedicion | date | NOT NULL DEFAULT (hoy en Madrid) | Fecha propuesta |
| tipo_iva_previsto | numeric(5,2) | NOT NULL | IVA vigente al guardar (R-9). Sirve para el aviso de cambio de IVA |
| oro_inversion | boolean | NOT NULL DEFAULT false | «Sin IVA (oro de inversión)» (FR-052, R-21). Con `true`, los totales previstos van sin cuota |
| base_prevista, cuota_prevista, total_previsto | numeric(12,2) | NOT NULL DEFAULT 0 | Calculados con `domain/importes.py` al guardar. Los usa el listado (R-9, R-12) |
| version | integer | NOT NULL DEFAULT 1 | `version_id_col`, como en clientes (FR-020) |
| creado_en / actualizado_en | timestamptz | NOT NULL | |
| creado_por_id / actualizado_por_id | uuid | NOT NULL, FK usuarios | |

**Índice**: `(fecha_expedicion DESC, id)`.

## lineas_borrador

| Columna | Tipo | Restricciones | Notas |
|---|---|---|---|
| id | uuid | PK | |
| borrador_id | uuid | NOT NULL, FK borradores_factura ON DELETE CASCADE | |
| orden | smallint | NOT NULL, UNIQUE (borrador_id, orden), CHECK 1–100 | |
| unidades | numeric(9,2) | NOT NULL, CHECK > 0 | FR-012 |
| descripcion | varchar(500) | NOT NULL, CHECK `length(trim(descripcion)) > 0` | |
| precio_unitario | numeric(12,2) | NOT NULL, CHECK ≥ 0 | Sin IVA |

**Reglas**:
- Un `PUT` del borrador sustituye todas sus líneas.
- Un borrador guarda el IVA y los totales **previstos** del momento en que se guardó (R-9). Al
  emitir se recalcula todo con el IVA vigente.

## facturas 🔒

| Columna | Tipo | Restricciones | Notas |
|---|---|---|---|
| id | uuid | PK | |
| serie | varchar(3) | NOT NULL, CHECK IN (`FAC`, `REC`) | |
| anio | smallint | NOT NULL | = `extract(year from fecha_expedicion)` (CHECK) |
| numero | integer | NOT NULL, CHECK > 0 | UNIQUE (serie, anio, numero) |
| num_serie | varchar(60) | NOT NULL, UNIQUE | `FAC-2026-0001`. CHECK del formato `^(FAC|REC)-[0-9]{4}-[0-9]{4,}$` |
| tipo_factura | char(2) | NOT NULL, CHECK IN (`F1`, `R1`, `R4`) | L2. `REC` implica R1 o R4, y `FAC` implica F1 (CHECK) |
| tipo_rectificativa | char(1) | NULL, CHECK (`S`) | Obligatorio si R1 o R4 (CHECK) |
| causa_rectificacion | varchar(20) | NULL, CHECK IN (`devolucion_o_precio`, `error_datos`) | Da R1 o R4 (FR-024) |
| factura_rectificada_id | uuid | NULL, FK facturas | Obligatorio en REC (CHECK) |
| base_rectificada / cuota_rectificada | numeric(12,2) | NULL | `ImporteRectificacion` (R-4). Obligatorios en REC (CHECK) |
| fecha_expedicion | date | NOT NULL | FR-018 |
| fecha_operacion | date | NULL, CHECK `fecha_operacion <= fecha_expedicion` | Heredada en reemisiones y rectificativas |
| descripcion_operacion | varchar(500) | NOT NULL | FR-045 |
| emisor_nif, emisor_nombre, emisor_direccion, emisor_codigo_postal, emisor_localidad, emisor_provincia | varchar | NOT NULL | Copia al emitir (FR-016). La provincia va como nombre |
| emisor_iban | varchar(34) | NULL, CHECK de estructura | Copia al emitir (FR-016, R-22). NULL en las anteriores a la 0006 o si no había IBAN |
| cliente_id | uuid | NOT NULL, FK clientes ON DELETE RESTRICT | FR-042 |
| dest_nombre | varchar(120) | NOT NULL | Copia del cliente |
| dest_identificacion_pais | char(2) | NOT NULL | |
| dest_identificacion_tipo | varchar(3) | NOT NULL | `NIF` o L7 (001, FR-025) |
| dest_identificacion_numero | varchar(20) | NOT NULL | |
| dest_direccion, dest_codigo_postal, dest_localidad | varchar | NOT NULL | Exigidos al emitir (FR-017) |
| dest_provincia, dest_pais | varchar | NULL / NOT NULL | |
| clave_regimen | char(2) | NOT NULL, CHECK IN L8A | `01`, o `04` si es de oro de inversión (R-21, R-23). Antes de la 0006, copia de la configuración. La API deriva `oro_inversion` de `clave_regimen = '04'`. El `CHECK` se deja con toda la L8A a propósito: valida lo ya emitido, que pudo copiar otra clave de la configuración, y no endurece nada sobre datos fiscales |
| modalidad | varchar(20) | NOT NULL | Copia (constitución IV) |
| base_total, cuota_total, importe_total | numeric(12,2) | NOT NULL, CHECK ≥ 0; en FAC CHECK `importe_total > 0` | R-10 |
| emitida_por_id | uuid | NOT NULL, FK usuarios | |
| emitida_en | timestamptz | NOT NULL DEFAULT now() | |
| clave_idempotencia | uuid | NULL, UNIQUE | `Idempotency-Key` de la emisión o de la modificación que la creó (R-18) |
| operacion_idempotencia | varchar(20) | NULL, CHECK IN (`emitir`, `emitir_borrador`, `modificar`) | Ámbito de la clave. El origen es el borrador o la factura corregida (R-18) |
| origen_idempotencia | uuid | NULL | Id del borrador emitido o de la factura modificada, para detectar una clave reutilizada sobre otro documento |
| texto_busqueda | text | GENERATED ALWAYS AS (`inmutable_unaccent(lower(num_serie ‖ ' ' ‖ dest_nombre ‖ ' ' ‖ dest_identificacion_numero))`) STORED | GIN trigram (R-12) |

**Índices**:
- `(fecha_expedicion DESC, serie, numero DESC)`.
- GIN trigram sobre `texto_busqueda`.
- `(cliente_id)`.
- `(factura_rectificada_id)`.

## lineas_factura 🔒

| Columna | Tipo | Restricciones | Notas |
|---|---|---|---|
| id | uuid | PK | |
| factura_id | uuid | NOT NULL, FK facturas | Sin CASCADE: nunca se borran |
| orden | smallint | NOT NULL, UNIQUE (factura_id, orden) | |
| unidades | numeric(9,2) | NOT NULL, CHECK > 0 | |
| descripcion | varchar(500) | NOT NULL | |
| precio_unitario | numeric(12,2) | NOT NULL, CHECK ≥ 0 | |
| tipo_iva | numeric(5,2) | NULL, CHECK `IS NULL OR (>= 0 AND < 100)` | IVA vigente al emitir (FR-013, constitución II). NULL en una factura de oro de inversión (R-21) |
| importe | numeric(12,2) | NOT NULL | `redondear(unidades × precio)` (R-10) |

Una rectificativa de devolución total no tiene líneas (Clarifications de plan).

## desgloses_factura 🔒

Totales agregados por tipo (constitución II: «la cabecera almacena los totales agregados por
tipo»).

| Columna | Tipo | Restricciones | Notas |
|---|---|---|---|
| factura_id | uuid | PK (con orden), FK facturas | |
| orden | smallint | PK, CHECK 1–12 | Orden del detalle en el registro. F-1 admite de 1 a 12 detalles. Las filas anteriores a la 0006 tienen 1: cada factura tenía un solo tipo |
| tipo_iva | numeric(5,2) | NULL, CHECK `IS NULL OR (>= 0 AND < 100)`, UNIQUE NULLS NOT DISTINCT (factura_id, tipo_iva) | NULL en el detalle exento |
| clave_regimen | char(2) | NOT NULL | `ClaveRegimen` del detalle (L8A): `01` o `04` |
| calificacion_operacion | char(2) | NULL | L9: `S1` en el detalle sujeto |
| operacion_exenta | char(2) | NULL | L10: `E6` en el detalle exento (R-21) |
| base | numeric(12,2) | NOT NULL, CHECK ≥ 0 | |
| cuota | numeric(12,2) | NOT NULL, CHECK ≥ 0 | `redondear(base × tipo / 100)`. 0 en el detalle exento |

**CHECK `ck_desgloses_factura_calificacion`** (F-1: `CalificacionOperacion` y `OperacionExenta`
son «obligatorios y alternativos»; F-3 §15.5 y §15.6.3):
- **Sujeto**: `calificacion_operacion = 'S1' AND operacion_exenta IS NULL AND tipo_iva IS NOT NULL`.
- **Exento**: `calificacion_operacion IS NULL AND operacion_exenta = 'E6' AND clave_regimen = '04'
  AND tipo_iva IS NULL AND cuota = 0`.

**Reglas**:
- Toda factura tiene al menos un desglose. La devolución total lleva uno a 0 (R-4).
- Una factura de oro de inversión tiene un único detalle, el exento, y todas sus líneas con
  `tipo_iva` NULL. La coherencia entre líneas, desglose y `facturas.clave_regimen` la garantiza el
  servicio, y la revisa la comprobación de integridad (FR-031).
- `Σ base = base_total`, `Σ cuota = cuota_total` y `importe_total = base_total + cuota_total`. Lo
  comprueba el servicio y lo cubren los tests de importes.

## correcciones_factura 🔒

| Columna | Tipo | Restricciones | Notas |
|---|---|---|---|
| id | uuid | PK | |
| factura_id | uuid | NOT NULL, FK facturas | La corregida. Una factura puede acumular correcciones, pero solo tiene una en vigor (R-8). Índice único parcial `WHERE tipo LIKE 'anulacion%'` |
| tipo | varchar(30) | NOT NULL, CHECK IN (`anulacion`, `anulacion_y_reemision`, `rectificacion_sustitucion`) | |
| motivo | varchar(30) | NOT NULL, CHECK IN (`no_debio_emitirse`, `factura_entregada`) | Declaración de FR-024 y FR-025. `anulacion*` implica `no_debio_emitirse` (CHECK) |
| motivo_texto | varchar(500) | NOT NULL, CHECK no vacío | |
| factura_nueva_id | uuid | NULL, UNIQUE, FK facturas | Reemisión o rectificativa. NULL solo en `anulacion` (CHECK) |
| registro_anulacion_id | uuid | NULL, FK registros_facturacion | En `anulacion*` (CHECK) |
| creada_por_id | uuid | NOT NULL, FK usuarios | Administrador (FR-023) |
| clave_idempotencia | uuid | NULL, UNIQUE | `Idempotency-Key` de la anulación o modificación (R-18) |
| operacion_idempotencia | varchar(20) | NULL, CHECK IN (`modificar`, `anular`) | Ámbito de la clave (R-18) |
| creada_en | timestamptz | NOT NULL DEFAULT now() | |

**Estado derivado de una factura F** (R-8, sin columnas mutables):
- `anulada`: existe una corrección `anulacion*` sobre F. Es definitivo.
- `rectificada`: existe una corrección `rectificacion_sustitucion` sobre F cuya `factura_nueva` no
  está `anulada`.
- `vigente`: en cualquier otro caso. Por eso, al anular la rectificativa, la original **vuelve a
  estar vigente** (FR-048).

Solo una factura `vigente` se puede anular o modificar (FR-026). Lo garantiza el trigger `BEFORE
INSERT` `validar_correccion`, que llama a `estado_factura(NEW.factura_id)` y lanza `42501` si no es
`vigente`. Esa garantía está en la BD, además de en el servicio.

**Orden de inserción** (R-9): la corrección se inserta **al final**, cuando ya existen el registro de
anulación y la factura nueva que referencia.

En una rectificativa (`REC`), `motivo = no_debio_emitirse` solo se admite con `tipo = anulacion`,
es decir, sin reemisión (spec, casos límite).

## registros_facturacion 🔒

| Columna | Tipo | Restricciones | Notas |
|---|---|---|---|
| id | uuid | PK | |
| secuencia | bigint | NOT NULL, UNIQUE, CHECK > 0 | Orden de la cadena (R-6) |
| tipo | varchar(10) | NOT NULL, CHECK IN (`alta`, `anulacion`) | |
| factura_id | uuid | NOT NULL, FK facturas | En un alta, la propia factura; en una anulación, la anulada |
| modalidad | varchar(20) | NOT NULL | FR-030 |
| id_emisor | char(9) | NOT NULL | Campos de la huella (R-2) |
| num_serie | varchar(60) | NOT NULL | |
| fecha_expedicion | char(10) | NOT NULL, CHECK `dd-mm-yyyy` | Tal como entra en la huella |
| tipo_factura | char(2) | NULL en anulación | |
| cuota_total, importe_total | numeric(12,2) | NULL en anulación | Se formatean con 2 decimales (R-2) |
| primer_registro | boolean | NOT NULL | |
| huella_anterior | char(64) | NULL si primer_registro (CHECK) | |
| fecha_hora_huso_gen | varchar(25) | NOT NULL, CHECK ISO 8601 con desfase | Texto exacto usado en la huella |
| tipo_huella | char(2) | NOT NULL DEFAULT '01' | L12 |
| huella | char(64) | NOT NULL, UNIQUE, CHECK `~ '^[0-9A-F]{64}$'` | |
| contenido | jsonb | NOT NULL | Registro completo según F-1, con los valores en texto (R-3, R-4b) |
| estado_remision | varchar(20) | NOT NULL DEFAULT 'pendiente', CHECK IN (`pendiente`) | La 004 ampliará los estados. No se actualiza: el estado de remisión se llevará en una tabla propia de la 004 |
| generado_en | timestamptz | NOT NULL DEFAULT now() | |

**Reglas**:
- **Encadenamiento** (trigger `BEFORE INSERT` `validar_encadenamiento`, R-6):
  - Si la tabla está vacía: `primer_registro` y `secuencia = 1`.
  - Si no: `secuencia = max + 1` y `huella_anterior` igual a la huella del registro `max`.
- **Integridad**: `huella = sha256(cadena(...))` con los campos de la fila. La comprobación de
  FR-031 la recalcula para toda la cadena en orden de `secuencia`.
- **`estado_remision`**: en esta feature siempre vale `pendiente`. Como la tabla es inalterable, la
  004 guardará el resultado de cada remisión en una tabla propia de solo inserción, no aquí.

## v_listado_facturas (vista)

La vista hace `UNION ALL` de:
- `borradores_factura`, unida a `clientes`, con sus totales previstos guardados. No calcula nada:
  el redondeo solo vive en `domain/importes.py`.
- `facturas`, con `estado_factura(id)`.

**Función `estado_factura(uuid) RETURNS text`**: `STABLE` y escrita con `EXISTS`, aplica la regla de
R-8. La usan la vista y el trigger `validar_correccion`: es la única implementación del estado
derivado.

| Columna | Tipo | Notas |
|---|---|---|
| tipo_documento | text | `borrador` o `factura` |
| id | uuid | |
| num_serie | text | NULL en un borrador |
| fecha | date | |
| cliente_nombre, identificacion | text | |
| base, cuota, total | numeric(12,2) | |
| estado | text | `borrador`, `vigente`, `anulada` o `rectificada` |
| texto_busqueda | text | |
| oro_inversion | boolean | Añadida al final en la 0006: `b.oro_inversion` o `f.clave_regimen = '04'`. La web muestra «Exenta» en la columna del IVA (FR-033) |

Se usa solo para el listado (R-12). El detalle se lee de las tablas.

## Transiciones

```
(nuevo) ──Guardar borrador──> borrador ──Editar──> borrador
                                 │  └──Eliminar──> (nada; sin número ni registro)
                                 └──Emitir──> factura FAC vigente + registro de alta
(nuevo) ──Emitir──────────────────────────> factura FAC vigente + registro de alta

factura vigente ──Anular (admin)──> anulada + registro de anulación
factura vigente ──Modificar «no debió emitirse» (admin)──> anulada + registro de anulación
                                               └─> factura FAC nueva vigente + registro de alta
factura vigente ──Modificar «ya entregada» (admin)──> rectificada
                                               └─> factura REC (R1/R4, S) vigente + registro de alta
REC vigente ──Anular (admin)──> REC anulada + registro de anulación
                           └─> la factura que rectificaba vuelve a estar vigente (FR-048), sin registro nuevo
anulada / rectificada: solo consulta (FR-026)
```

## Migración 0006 (ajuste de cierre, 2026-09-30)

`0006_iva_libre_oro_iban`, en SQL escrito a mano. Solo contiene DDL, así que no dispara los
triggers de inalterabilidad ni necesita ningún `UPDATE` (constitución III). En orden:

1. **Configuración**:
   - `DROP CONSTRAINT ck_configuracion_facturacion_clave_regimen` y `DROP COLUMN clave_regimen`
     (R-23).
   - `ck_configuracion_facturacion_iva` pasa a `iva_por_defecto >= 0 AND iva_por_defecto < 100`
     (R-20).
   - `ADD COLUMN emisor_iban varchar(34)` con `ck_configuracion_facturacion_emisor_iban` (R-22).
2. **Facturas**: `ADD COLUMN emisor_iban varchar(34)` con `ck_facturas_emisor_iban`.
3. **Líneas de factura**: `ALTER COLUMN tipo_iva DROP NOT NULL`. `ck_lineas_factura_tipo_iva` pasa
   a `tipo_iva IS NULL OR (tipo_iva >= 0 AND tipo_iva < 100)`.
4. **Desgloses**:
   - `ADD COLUMN orden smallint NOT NULL DEFAULT 1`. PostgreSQL guarda el valor por defecto en el
     catálogo, sin reescribir filas. Después se hace `DROP DEFAULT`.
   - `DROP CONSTRAINT pk_desgloses_factura` y `ADD CONSTRAINT pk_desgloses_factura PRIMARY KEY
     (factura_id, orden)`, con `ck_desgloses_factura_orden CHECK (orden BETWEEN 1 AND 12)`.
   - `ADD CONSTRAINT uq_desgloses_factura_tipo UNIQUE NULLS NOT DISTINCT (factura_id, tipo_iva)`.
   - `ADD COLUMN operacion_exenta char(2)`. `ALTER COLUMN tipo_iva DROP NOT NULL` y `ALTER COLUMN
     calificacion_operacion DROP NOT NULL`.
   - Nuevos `ck_desgloses_factura_tipo_iva` (rango o NULL) y `ck_desgloses_factura_calificacion`
     (sujeto o exento, arriba).
5. **Borradores**: `ADD COLUMN oro_inversion boolean NOT NULL DEFAULT false`.
6. **Vista**: `CREATE OR REPLACE VIEW v_listado_facturas` con la columna `oro_inversion` al final.

**Seguridad de la migración**:
- Cada `CHECK` nuevo se valida contra las filas existentes. Todas las facturas anteriores cumplen
  la rama «sujeto»: `S1`, sin exención y con tipo.
- Los triggers `*_sin_modificaciones` son `BEFORE UPDATE OR DELETE` de fila, y ningún paso escribe
  filas.
- Las columnas nuevas de `jb_owner` heredan los privilegios de `jb_app` por tabla, así que no hace
  falta ningún `GRANT`.

**`downgrade`**: solo sirve para reconstruir las BD de test y E2E. `tests/conftest.py` hace
`downgrade base` + `upgrade head` al empezar cada sesión, sobre la BD que dejó la anterior, así que
el `downgrade` **nunca debe fallar por los datos**:
- Hace `DROP` y `CREATE` de la vista sin `oro_inversion`, quita `borradores_factura.oro_inversion`
  y el IBAN de facturas y configuración, y restaura `clave_regimen char(2) NOT NULL DEFAULT '01'`
  en configuración.
- Los `CHECK` anteriores (`IN (0, 2, 4, 5, 7.5, 10, 21)` y `= 'S1'`) vuelven `NOT VALID`, como en
  la 0004 y la 0005.
- `NOT NULL` en `tipo_iva` y `calificacion_operacion`, la PK `(factura_id, tipo_iva)` y la retirada
  de `orden` y `operacion_exenta` solo se aplican, en un bloque `DO`, si no hay filas exentas. Si
  las hay, esas columnas se quedan como en la 0006, porque el siguiente `downgrade`, el de la 0005,
  elimina las tablas.
