# Data Model — 001 Cimientos, seguridad y clientes

**Spec**: [spec.md](spec.md) · **Research**: [research.md](research.md)

## Convenciones

- **Nombres**: tablas y columnas en español, `snake_case`, tablas en plural (principio VIII).
- **Claves primarias**: `id uuid DEFAULT uuidv7()` (R-12).
- **Marcas de tiempo**: `timestamptz`. La hora de negocio es `Europe/Madrid`.
- **Propiedad y permisos**: todas las tablas pertenecen a `jb_owner`. `jb_app` tiene DML salvo
  donde se indica (R-11).
- **Importes**: no hay en esta feature. La política `Decimal`/`NUMERIC` del principio II se
  aplicará a partir de la feature de facturas.

## Diagrama

```
usuarios 1───* sesiones
usuarios 1───* eventos_auditoria (actor_id, nullable)
usuarios 1───* clientes (creado_por_id, actualizado_por_id)
provincias 1───* clientes (provincia_codigo, nullable)
eventos_auditoria ···> clientes (cliente_id SIN FK: sobrevive al borrado físico)
```

---

## usuarios

| Columna | Tipo | Restricciones | Notas |
|---|---|---|---|
| id | uuid | PK | |
| nombre_usuario | varchar(50) | NOT NULL, único sobre `lower(nombre_usuario)` | Formato `^[a-z0-9._-]{3,50}$`, normalizado a minúsculas |
| nombre | varchar(120) | NOT NULL | Nombre visible; de él salen las iniciales del menú |
| rol | varchar(20) | NOT NULL, CHECK IN (`administrador`, `empleado`) | FR-012 |
| hash_contrasena | text | NOT NULL | Argon2id (R-7) |
| contrasena_temporal | boolean | NOT NULL DEFAULT true | Obliga a cambiarla (FR-009) |
| activo | boolean | NOT NULL DEFAULT true | |
| intentos_fallidos | smallint | NOT NULL DEFAULT 0, CHECK ≥ 0 | FR-006 |
| bloqueado_hasta | timestamptz | NULL | |
| ultimo_acceso_en | timestamptz | NULL | |
| creado_en | timestamptz | NOT NULL DEFAULT now() | |
| actualizado_en | timestamptz | NOT NULL DEFAULT now() | |

**Reglas**:
- **Último administrador** (FR-017): no puede quedar ningún momento sin al menos un
  `rol='administrador' AND activo`. Se aplica en el servicio con `SELECT … FOR UPDATE` (R-9).
- **Autodesactivación**: un administrador no puede desactivarse a sí mismo.
- **Restablecer la contraseña**: nuevo hash, `contrasena_temporal=true`, `intentos_fallidos=0`,
  `bloqueado_hasta=NULL` y revocación de todas sus sesiones.

**Estados**:

```
activo ──desactivar──> inactivo ──reactivar──> activo
(desactivar revoca todas las sesiones; el último admin y uno mismo no se pueden desactivar)
```

## sesiones

| Columna | Tipo | Restricciones | Notas |
|---|---|---|---|
| id | uuid | PK | |
| usuario_id | uuid | NOT NULL, FK → usuarios ON DELETE CASCADE | |
| token_hash | char(64) | NOT NULL, UNIQUE | SHA-256 hex del token de la cookie (R-5) |
| csrf_token | varchar(64) | NOT NULL | Token sincronizador (R-6) |
| creada_en | timestamptz | NOT NULL DEFAULT now() | |
| ultima_actividad_en | timestamptz | NOT NULL DEFAULT now() | Se actualiza a lo sumo una vez por minuto |
| expira_en | timestamptz | NOT NULL | `creada_en + duración absoluta` (10 h por defecto) |
| revocada_en | timestamptz | NULL | Cierre de sesión o revocación |
| origen_ip | inet | NULL | |
| agente | varchar(500) | NULL | |

**Vigencia** (FR-003, FR-005): una sesión vale si `revocada_en IS NULL`, `now() < expira_en`,
`now() < ultima_actividad_en + inactividad` (30 min por defecto) y el usuario está activo.

**Índices**: `(usuario_id) WHERE revocada_en IS NULL`.

**Limpieza**: las sesiones caducadas o revocadas con más de 30 días se purgan en el arranque de la
API y con la CLI. No son registros fiscales ni de auditoría.

## eventos_auditoria (solo inserción)

| Columna | Tipo | Restricciones | Notas |
|---|---|---|---|
| id | uuid | PK | |
| ocurrido_en | timestamptz | NOT NULL DEFAULT now() | |
| tipo | varchar(40) | NOT NULL, CHECK IN (catálogo) | Ver catálogo abajo |
| actor_id | uuid | NULL, FK → usuarios | NULL en accesos fallidos y en eventos de la CLI |
| actor_nombre_usuario | varchar(50) | NULL | El actor o el nombre de usuario intentado (FR-021) |
| origen_ip | inet | NULL | |
| agente | varchar(500) | NULL | |
| usuario_afectado_id | uuid | NULL, FK → usuarios | En los eventos de gestión de usuarios |
| cliente_id | uuid | NULL, **sin FK** | Sobrevive al borrado físico (R-10) |
| detalle | jsonb | NOT NULL DEFAULT '{}' | Campos cambiados `{campo: [antes, después]}` o instantánea del cliente borrado. Nunca contraseñas |

**Catálogo `tipo`**:
- **Acceso**: `acceso_correcto`, `acceso_fallido`, `acceso_bloqueado`, `cierre_sesion`.
- **Contraseñas**: `contrasena_cambiada`, `contrasena_restablecida`.
- **Usuarios**: `usuario_creado`, `usuario_rol_cambiado`, `usuario_desactivado`,
  `usuario_reactivado`.
- **Clientes**: `cliente_creado`, `cliente_editado`, `cliente_desactivado`, `cliente_reactivado`,
  `cliente_borrado`.

**Inalterabilidad** (FR-022):
- `REVOKE UPDATE, DELETE, TRUNCATE ON eventos_auditoria FROM jb_app`.
- Trigger `BEFORE UPDATE OR DELETE` → `RAISE EXCEPTION 'La auditoría es inalterable'`.

**Índices**:
- `(ocurrido_en DESC)`.
- `(origen_ip, tipo, ocurrido_en)` para el límite por origen (R-8).
- `(actor_id, ocurrido_en DESC)`.
- `(cliente_id, ocurrido_en DESC)`.
- `(tipo, ocurrido_en DESC)`.

## provincias (catálogo)

| Columna | Tipo | Restricciones | Notas |
|---|---|---|---|
| codigo | char(2) | PK, CHECK `^[0-9]{2}$` | Código INE (01–52) |
| nombre | varchar(60) | NOT NULL | Denominación oficial INE (ver research R-20) |

Se carga en la migración con los 52 registros verificados. El rol de aplicación solo tiene
`SELECT`.

## clientes

| Columna | Tipo | Restricciones | Notas |
|---|---|---|---|
| id | uuid | PK | |
| tipo | varchar(12) | NOT NULL, CHECK IN (`particular`, `empresa`) | |
| nombre | varchar(120) | NOT NULL, CHECK `length(trim(nombre)) > 0` | `NombreRazon`, alfanumérico (120) (F-1) |
| identificacion_pais | char(2) | NOT NULL DEFAULT 'ES' | ISO 3166-1 alfa-2, validado contra pycountry |
| identificacion_tipo | varchar(3) | NOT NULL, CHECK IN (`NIF`, `02`, `03`, `04`, `05`, `06`) | `NIF` o clave L7 (F-2). `07` excluido (supuesto de la spec) |
| identificacion_numero | varchar(20) | NOT NULL | Normalizado: mayúsculas, sin espacios, guiones ni puntos |
| direccion | varchar(200) | NULL | |
| codigo_postal | varchar(10) | NULL | España: `^[0-9]{5}$` |
| localidad | varchar(100) | NULL | |
| provincia_codigo | char(2) | NULL, FK → provincias | Solo si `pais_residencia='ES'` |
| provincia_texto | varchar(100) | NULL | Solo si `pais_residencia<>'ES'` |
| pais_residencia | char(2) | NOT NULL DEFAULT 'ES' | ISO 3166-1 alfa-2 |
| telefono | varchar(30) | NULL | Formato libre: dígitos, espacios, `+`, `(`, `)` y `-` |
| correo | varchar(254) | NULL | Validado como correo electrónico |
| observaciones | text | NULL, CHECK `length ≤ 2000` | |
| activo | boolean | NOT NULL DEFAULT true | |
| version | integer | NOT NULL DEFAULT 1 | Concurrencia optimista (FR-030) |
| creado_en / creado_por_id | timestamptz / uuid | NOT NULL / NOT NULL FK → usuarios | FR-029 |
| actualizado_en / actualizado_por_id | timestamptz / uuid | NOT NULL / NOT NULL FK → usuarios | FR-029 |
| texto_busqueda | text | GENERATED ALWAYS AS (…) STORED | R-12 |

**Restricciones de tabla**:
- **Identificación única** (FR-026 y clarificación del 2026-09-27): `UNIQUE (identificacion_pais,
  identificacion_tipo, identificacion_numero)`.
- **Coherencia del NIF**: `CHECK ((identificacion_pais = 'ES') = (identificacion_tipo = 'NIF'))`.
  Si el país es España el tipo es NIF, y viceversa (FR-024 y FR-025), sujeto a lo que confirme
  R-20.
- **Longitud del NIF**: `CHECK (identificacion_tipo <> 'NIF' OR identificacion_numero ~
  '^[0-9A-Z]{9}$')`. El carácter de control se valida en el dominio (R-20).
- **Provincia según el país**: `CHECK (pais_residencia = 'ES' OR provincia_codigo IS NULL)` y
  `CHECK (pais_residencia <> 'ES' OR provincia_texto IS NULL)`.
- **Código postal español**: `CHECK (pais_residencia <> 'ES' OR codigo_postal IS NULL OR
  codigo_postal ~ '^[0-9]{5}$')`.

**Reglas de dominio**, en `app/domain/`, puras y testables sin HTTP:
- `normalize_identificacion(texto)`: mayúsculas y sin espacios, guiones ni puntos.
- `validate_nif(numero)`: distingue DNI, NIE y NIF de entidad y valida el carácter de control con
  el algoritmo verificado en R-20.
- `provincia_from_codigo_postal(cp)`: devuelve la provincia de los dos primeros dígitos (01–52) o
  error. La regla está pendiente de verificación en R-20.

**Estados**:

```
activo ──desactivar──> inactivo ──reactivar──> activo
  └──────────── borrar (solo admin, sin documentos) ───────────> (eliminado; queda instantánea en auditoría)
```

- **"Sin documentos"** (FR-037): en esta feature se implementa como un puerto
  `ClienteDocumentosChecker` en el servicio, que ahora devuelve siempre `False`. Las features de
  facturas y presupuestos lo implementarán con sus tablas. Además, las futuras FK desde facturas y
  presupuestos serán `ON DELETE RESTRICT`, como segunda barrera en la BD.

**Indicadores** (FR-034):
- `activos = COUNT(*) WHERE activo`.
- `nuevos_este_anio = COUNT(*) WHERE creado_en >= date_trunc('year', now() AT TIME ZONE
  'Europe/Madrid') AT TIME ZONE 'Europe/Madrid'`.

**Índices**:
- GIN trigram sobre `texto_busqueda`.
- `(activo, nombre)`.
- `(provincia_codigo)`.
- `(tipo)`.
- `(creado_en)`.
