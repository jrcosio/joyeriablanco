# Data model — 004 Modalidad No VERI\*FACTU

La migración `0009_no_verifactu.py` va escrita a mano en SQL, con el patrón de la 0005 y la 0008.
Las tablas de solo inserción se protegen con REVOKE a `jb_app` y con los triggers
`impedir_modificacion_facturacion()` de la 0005, que frenan también a `jb_owner`.

## `registros_facturacion` (002), ampliada

Columnas nuevas, añadidas con `ALTER TABLE … ADD COLUMN`. Las filas existentes no se tocan:

| Columna | Tipo | Notas |
|---|---|---|
| `xml_firmado` | `bytea` NULL | El XML UTF-8 del registro con su `ds:Signature`, tal cual se generó (R-4). Es lo que se exporta |
| `certificado_titular` | `varchar(200)` NULL | Para mostrarlo sin analizar el XML |
| `certificado_huella` | `char(64)` NULL | SHA-256, en hexadecimal mayúsculas, del certificado (DER) con que se firmó. La comprobación lo coteja (R-9) |

Restricciones:
- `ck_registros_facturacion_firma`: `modalidad <> 'no_verifactu'` o (`xml_firmado`,
  `certificado_titular` y `certificado_huella` NOT NULL).
- `ck_registros_facturacion_certificado_huella`: `certificado_huella ~ '^[0-9A-F]{64}$'` cuando no
  es NULL.
- `ck_registros_facturacion_estado_remision`: se rehace como `IN ('pendiente', 'no_aplica')`. En
  `no_verifactu` se exige `no_aplica`.

La huella, el encadenamiento y el trigger `validar_encadenamiento` no cambian. La firma no forma
parte de la huella (FR-009).

## `registros_evento` (nueva, solo inserción)

| Columna | Tipo | Notas |
|---|---|---|
| `id` | `uuid` PK, `uuidv7()` | |
| `secuencia` | `bigint` UNIQUE | 1, 2, 3…, sin huecos (trigger) |
| `tipo_evento` | `char(2)` | `01` a `10` y `90` (F-17, `TipoEventoType`) |
| `fecha_hora_huso_gen` | `varchar(25)` | `AAAA-MM-DDThh:mm:ss±hh:mm`, hora de Madrid. Mismo CHECK de formato que en 002 |
| `primer_evento` | `boolean` | Igual a `huella_anterior IS NULL` |
| `tipo_evento_anterior` | `char(2)` NULL | De `EventoAnterior` |
| `fecha_hora_huso_gen_anterior` | `varchar(25)` NULL | |
| `huella_anterior` | `char(64)` NULL | |
| `tipo_huella` | `char(2)` | `'01'` |
| `huella` | `char(64)` UNIQUE | SHA-256 (F-2 §3.c) |
| `tipo_anomalia` | `char(2)` NULL | Solo en 04 y 06: el `TipoAnomalia` (R-10) |
| `secuencia_afectada` | `bigint` NULL | Solo en 04 y 06: la secuencia del registro o del evento afectado. No está en el XML. Sirve para la alarma (R-11) y para no repetir una anomalía ya registrada (R-9) |
| `contenido` | `jsonb` | `{"IDVersion", "Evento"}` con todos los valores como texto: el `RegistroEvento` sin la firma |
| `xml_firmado` | `bytea` | `RegistroEvento` con `Evento/Signature` |
| `certificado_titular` | `varchar(200)` | |
| `certificado_huella` | `char(64)` | |
| `generado_en` | `timestamptz` DEFAULT `now()` | |

Restricciones y triggers:
- CHECK de `tipo_evento`, de los formatos de huella y fecha, y `primer_evento = (huella_anterior IS NULL)`.
- `registros_evento_encadenamiento` (BEFORE INSERT) llama a `public.validar_encadenamiento_eventos()`:
  - exige `secuencia = max + 1`;
  - exige `huella_anterior` igual a la huella del último y que el tipo y la fecha anteriores
    coincidan;
  - el primero lleva `secuencia = 1` y `primer_evento`.
- `registros_evento_sin_modificaciones` y `registros_evento_sin_truncate` llaman a
  `impedir_modificacion_facturacion()`, con REVOKE UPDATE, DELETE y TRUNCATE a `jb_app`.
- Cerrojo de la aplicación: `pg_advisory_xact_lock(0x4A42_4556_454E)`, «JBEVEN».

### `contenido.DatosPropiosEvento` según el tipo (F-17)

| Tipo | Agrupación | Datos |
|---|---|---|
| 01 y 02 | — | Sin datos propios. El `OtrosDatosEvento` opcional lleva el motivo del fin: «parada ordenada» |
| 03 | `LanzamientoProcesoDeteccionAnomaliasRegFacturacion` | `RealizadoProceso…` (S/N) y `NumeroDeRegistros…`, de huellas, firmas, cadena y fechas |
| 04 | `DeteccionAnomaliasRegFacturacion` | `TipoAnomalia`, `OtrosDatosAnomalia` y `RegistroFacturacionAnomalo` (IDFactura) |
| 05 | `LanzamientoProcesoDeteccionAnomaliasRegEvento` | Lo mismo, de los eventos |
| 06 | `DeteccionAnomaliasRegEvento` | `TipoAnomalia`, `OtrosDatosAnomalia` y `RegEventoAnomalo` (tipo, fecha y huella) |
| 08 | `ExportacionRegFacturacionPeriodo` | Inicio y fin del periodo, registro inicial y final (IDFactura y huella), número de altas, `SumaCuotaTotalAlta`, `SumaImporteTotalAlta`, número de anulaciones y `RegistrosFacturacionExportadosDejanDeConservarse` = `N` |
| 09 | `ExportacionRegEventoPeriodo` | Inicio y fin, evento inicial y final, número exportados y `RegEventoExportadosDejanDeConservarse` = `N` |
| 10 | `ResumenEventos` | `TipoEvento[]` (tipo y número, como mucho 20), registro inicial y final, número de altas, sumas y número de anulaciones |

## `comprobaciones_integridad` (nueva, solo inserción)

Cada comprobación lanzada, con su resultado. Alimenta la alarma (R-11).

| Columna | Tipo | Notas |
|---|---|---|
| `id` | `uuid` PK | |
| `lanzada_en` | `timestamptz` DEFAULT `now()` | |
| `origen` | `varchar(10)` | `web` o `consola`. La comprobación previa de cada emisión (7.i) no se guarda aquí |
| `actor_id` | `uuid` NULL, FK `usuarios` | Solo en `web` (CHECK) |
| `desde_secuencia` | `bigint` NULL | El primer registro de facturación comprobado. NULL si no había ninguno |
| `hasta_secuencia` | `bigint` NULL | El último |
| `llega_al_final` | `boolean` | Si la comprobación llega al final de la cadena de facturación. La de eventos se comprueba siempre entera |
| `registros` / `eventos` | `integer` | Cuántos se procesaron |
| `anomalias` | `integer` | 0 si todo está bien |
| `max_secuencia_anomala` / `max_evento_anomalo` | `bigint` NULL | La secuencia más alta con anomalía en cada cadena. Con ellas se apaga la alarma (R-11) |
| `evento_lanzamiento_id` | `uuid` FK `registros_evento` | El 03 de la comprobación |

## Sin tabla

- **Certificado**: lo carga `services/certificado.py` desde `CERTIFICADO_RUTA`. Solo su estado sale
  por la API.
- **Alarma**: se deriva de `registros_evento` (04 y 06), de `comprobaciones_integridad` y del
  estado del certificado.
- **Declaración responsable**: se construye desde los ajustes `SIF_*`. El PDF de cada versión lo
  archiva el productor en `docs/declaraciones/`.

## Enumeraciones (`domain/tipos.py`)

- `EstadoRemision`: + `NO_APLICA = "no_aplica"`.
- `TipoEventoSif`: `INICIO "01"`, `FIN "02"`, `LANZAMIENTO_ANOMALIAS_FACTURACION "03"`,
  `ANOMALIA_FACTURACION "04"`, `LANZAMIENTO_ANOMALIAS_EVENTOS "05"`, `ANOMALIA_EVENTOS "06"`,
  `EXPORTACION_FACTURACION "08"`, `EXPORTACION_EVENTOS "09"` y `RESUMEN "10"`.
- `TipoAnomalia`: `01`, `02`, `03`, `04`, `05`, `07`, `08`, `11` y `13` (R-10).
- `TipoEvento` de auditoría: + `REGISTROS_EXPORTADOS` e `INTEGRIDAD_COMPROBADA`. Hay que rehacer
  el CHECK de `eventos_auditoria`, como en 0005 y 0008. Un certificado no utilizable no se audita:
  lo señala la alarma (R-11).

## Configuración (002), ampliada

- **Salida** (`ConfiguracionFacturacionSalida`): + `certificado`, con:
  - `estado` (`utilizable` o `no_utilizable`) y `motivo`;
  - `titular`, `identificacion` y `emisor`;
  - `valido_desde`, `valido_hasta` y `dias_restantes`;
  - `caduca_pronto`.
- **Parámetros** (`ParametrosFacturacionSalida`): `faltan` incluye `certificado` cuando no es
  utilizable; + `certificado_caduca_el` cuando caduca pronto.
- **Entrada**: `modalidad` solo admite `no_verifactu`; `verifactu` se rechaza con 422.

## Ajustes nuevos (`core/config.py`)

| Ajuste | Obligatorio en producción | Notas |
|---|---|---|
| `CERTIFICADO_RUTA` | Sí | Ruta del PKCS#12 |
| `CERTIFICADO_CONTRASENA` | Sí | `SecretStr` |
| `SIF_PRODUCTOR_DIRECCION` | Sí | Declaración, letra j) |
| `SIF_DECLARACION_FECHA` | Sí | Letra l) |
| `SIF_DECLARACION_LUGAR` | Sí | Letra l): localidad y país |
