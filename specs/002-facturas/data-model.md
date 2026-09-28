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
- **Migración única nueva**: `0005_facturacion`, escrita a mano. Amplía también el `CHECK` de
  `eventos_auditoria.tipo` (R-15), con la técnica de la 0004.

## Diagrama

```
configuracion_facturacion (fila única)
clientes 1───* borradores_factura 1───* lineas_borrador
clientes 1───* facturas🔒 (cliente_id, ON DELETE RESTRICT)
facturas🔒 1───* lineas_factura🔒
facturas🔒 1───* desgloses_factura🔒
facturas🔒 0..1──1 correcciones_factura🔒 (factura_id UNIQUE: la original)
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
| iva_por_defecto | numeric(5,2) | NOT NULL DEFAULT 21.00 | Validado en el servicio contra `TIPOS_IVA_S1` y la fecha actual (R-10). La BD admite `CHECK (iva_por_defecto IN (0,2,4,5,7.5,10,21))` |
| clave_regimen | char(2) | NOT NULL DEFAULT '01', CHECK IN L8A | FR-001. Lista L8A de F-1 |
| modalidad | varchar(20) | NULL, CHECK IN (`verifactu`, `no_verifactu`) | Sin valor inicial (Clarifications). Si es NULL, no se puede emitir (FR-004) |
| emisor_nombre | varchar(120) | NULL | `NombreRazonEmisor` |
| emisor_nif | char(9) | NULL, CHECK `~ '^[0-9A-Z]{9}$'` | Validado con `domain/identificacion.py` (FR-002) |
| emisor_direccion | varchar(200) | NULL | F-6, art. 6.1.e |
| emisor_codigo_postal | char(5) | NULL | España. La provincia se deriva como en clientes |
| emisor_localidad | varchar(100) | NULL | |
| emisor_provincia_codigo | char(2) | NULL, FK provincias | |
| version | integer | NOT NULL DEFAULT 1 | Concurrencia optimista |
| actualizado_en | timestamptz | NOT NULL DEFAULT now() | |
| actualizado_por_id | uuid | NULL, FK usuarios | |

**Reglas**:
- **Emisión posible** cuando `modalidad`, `emisor_nombre`, `emisor_nif`, `emisor_direccion`,
  `emisor_codigo_postal` y `emisor_localidad` no son NULL. En producción hacen falta además
  `SIF_*` (R-5).
- **Auditoría**: cada `PUT` deja `configuracion_facturacion_cambiada` con el diff (FR-003).

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
- Un borrador no guarda el IVA ni los importes. Se calculan al vuelo con el IVA vigente para
  mostrarlos, y se fijan al emitir.

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
| cliente_id | uuid | NOT NULL, FK clientes ON DELETE RESTRICT | FR-042 |
| dest_nombre | varchar(120) | NOT NULL | Copia del cliente |
| dest_identificacion_pais | char(2) | NOT NULL | |
| dest_identificacion_tipo | varchar(3) | NOT NULL | `NIF` o L7 (001, FR-025) |
| dest_identificacion_numero | varchar(20) | NOT NULL | |
| dest_direccion, dest_codigo_postal, dest_localidad | varchar | NOT NULL | Exigidos al emitir (FR-017) |
| dest_provincia, dest_pais | varchar | NULL / NOT NULL | |
| clave_regimen | char(2) | NOT NULL | Copia de la configuración |
| modalidad | varchar(20) | NOT NULL | Copia (constitución IV) |
| base_total, cuota_total, importe_total | numeric(12,2) | NOT NULL, CHECK ≥ 0; en FAC CHECK `importe_total > 0` | R-10 |
| emitida_por_id | uuid | NOT NULL, FK usuarios | |
| emitida_en | timestamptz | NOT NULL DEFAULT now() | |
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
| tipo_iva | numeric(5,2) | NOT NULL | IVA vigente al emitir (FR-013, constitución II) |
| importe | numeric(12,2) | NOT NULL | `redondear(unidades × precio)` (R-10) |

Una rectificativa de devolución total no tiene líneas (Clarifications de plan).

## desgloses_factura 🔒

Totales agregados por tipo (constitución II: «la cabecera almacena los totales agregados por
tipo»).

| Columna | Tipo | Restricciones | Notas |
|---|---|---|---|
| factura_id | uuid | PK (con tipo_iva), FK facturas | |
| tipo_iva | numeric(5,2) | PK | |
| clave_regimen | char(2) | NOT NULL | |
| calificacion_operacion | char(2) | NOT NULL, CHECK (`S1`) | L9 |
| base | numeric(12,2) | NOT NULL, CHECK ≥ 0 | |
| cuota | numeric(12,2) | NOT NULL, CHECK ≥ 0 | `redondear(base × tipo / 100)` |

**Reglas**:
- Toda factura tiene al menos un desglose. La devolución total lleva uno a 0 (R-4).
- `Σ base = base_total`, `Σ cuota = cuota_total` y `importe_total = base_total + cuota_total`. Lo
  comprueba el servicio y lo cubren los tests de importes.

## correcciones_factura 🔒

| Columna | Tipo | Restricciones | Notas |
|---|---|---|---|
| id | uuid | PK | |
| factura_id | uuid | NOT NULL, **UNIQUE**, FK facturas | La corregida. Solo una corrección por factura (R-8) |
| tipo | varchar(30) | NOT NULL, CHECK IN (`anulacion`, `anulacion_y_reemision`, `rectificacion_sustitucion`) | |
| motivo | varchar(30) | NOT NULL, CHECK IN (`no_debio_emitirse`, `factura_entregada`) | Declaración de FR-024 y FR-025. `anulacion*` implica `no_debio_emitirse` (CHECK) |
| motivo_texto | varchar(500) | NOT NULL, CHECK no vacío | |
| factura_nueva_id | uuid | NULL, UNIQUE, FK facturas | Reemisión o rectificativa. NULL solo en `anulacion` (CHECK) |
| registro_anulacion_id | uuid | NULL, FK registros_facturacion | En `anulacion*` (CHECK) |
| creada_por_id | uuid | NOT NULL, FK usuarios | Administrador (FR-023) |
| creada_en | timestamptz | NOT NULL DEFAULT now() | |

**Estado derivado de una factura** (sin columnas mutables):
- `anulada`: existe una corrección `anulacion*`.
- `rectificada`: existe `rectificacion_sustitucion`.
- `vigente`: no tiene ninguna corrección.

Solo una factura `vigente` se puede anular o modificar (FR-026).

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
- `borradores_factura`, unida a `clientes`, con los totales calculados al vuelo con la
  configuración vigente.
- `facturas`, unida por `LEFT JOIN` a `correcciones_factura`.

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
anulada / rectificada: solo consulta (FR-026)
```
