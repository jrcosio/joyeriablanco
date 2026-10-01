---
description: "Tareas de implementación de la feature 002"
---

# Tasks: Facturación con registro Verifactu

**Input**: `specs/002-facturas/`:
- [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md) y [data-model.md](data-model.md).
- [contracts/openapi.yaml](contracts/openapi.yaml) y [contracts/ui-rutas.md](contracts/ui-rutas.md).
- [quickstart.md](quickstart.md).

**Prerequisites**: spec con clarify, plan, research con las fuentes F-1 a F-10, data-model,
contratos validados y checklists con su refinamiento. Todo en la rama `002-facturas`.

**Tests**: SÍ, con TDD igual que en 001. En cada historia, los tests se escriben primero y deben
fallar. Los que exige la constitución VII están marcados con ⚖️:
- Numeración bajo concurrencia.
- Importes y redondeos.
- Encadenamiento de huellas.

**Organization**: por historias de usuario, en el orden de dependencias del plan: US1 → US2 → US3
→ US4 → US5 → US6. US2 necesita la configuración de US1 para poder emitir.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: puede ir en paralelo (ficheros distintos y sin dependencias pendientes).
- **[Story]**: historia de la spec (US1–US6).
- Las rutas son relativas a la raíz del repositorio.

## Path Conventions

- **Backend**: `backend/app/…`, `backend/tests/…` y `backend/alembic/versions/…`.
- **Web**: `joyeriablanco_web/src/…` y `joyeriablanco_web/e2e/…`.
- **Reglas fiscales**: se toman **solo** de research (R-1 a R-23) y de sus fuentes F-n. Nunca de
  memoria (constitución IV).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: configuración del sistema informático, enumeraciones de dominio y test de contrato
preparado para la unión de contratos.

- [X] T001 Añadir a `backend/app/core/config.py` los campos `SIF_*` de research R-5, con los valores ficticios de desarrollo marcados como tales:
  - `sif_productor_nombre`, `sif_productor_nif`, `sif_nombre_sistema="Joyería Blanco Gestión"`, `sif_id_sistema="JB"` y `sif_numero_instalacion="1"`.
  - En `_exigir_seguridad_en_produccion`: si `entorno is PRODUCCION`, exigir productor nombre y NIF (validado con `app/domain/identificacion.py`). Validar siempre `sif_id_sistema` (`^[A-Z0-9]{2}$` sin Ñ) y las longitudes de F-1, hoja 5.
  - Añadir `__version__` en `backend/app/__init__.py`, que es la `Version` del registro.
  - Documentar las variables en `.env.example`.
  - Test `backend/tests/unit/test_config_sif.py`: en producción, sin productor o con un NIF no válido, `Settings` falla. Por tanto, `faltan` nunca informa del productor (research R-5).
- [X] T002 Generalizar `backend/tests/integration/test_contrato_openapi.py` (research R-14):
  - Leer la **unión** de `specs/*/contracts/openapi.yaml`, ordenados, y conservar el prefijo de `servers`.
  - Mantener estricto que toda operación de la API esté en algún contrato.
  - Para el sentido contrario, crear la lista `PENDIENTES_002` con las 14 operaciones de 002. Cada tarea de API la irá vaciando y T076 la eliminará.
  - Comprobar también los códigos de éxito, incluido el 200 de repetición idempotente (R-18).
- [X] T003 Ampliar `backend/app/domain/tipos.py`:
  - Enumeraciones nuevas `Serie` (FAC, REC), `TipoFactura` (F1, R1, R4), `TipoRectificativa` (S), `CausaRectificacion`, `MotivoModificacion`, `TipoCorreccion`, `TipoRegistro` (alta, anulacion), `Modalidad`, `EstadoRemision` (pendiente) y `EstadoFactura`.
  - Los tipos nuevos de `TipoEvento` de research R-15.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: dominio fiscal puro, migración con las garantías en la BD, generación de registros y
piezas web compartidas. Todas las historias dependen de esta fase.

### Tests ⚠️ (escribir primero, deben fallar)

- [X] T004 [P] ⚖️ Test `backend/tests/unit/domain/test_importes.py` (research R-10, SC-003). Tabla de casos calculados a mano:
  - **Medio céntimo exacto**, que distingue el redondeo alejado de cero del redondeo al par: línea `0.5 × 0.25 = 0.125 → 0.13`; cuota de una base de `0.50` al 21 % `= 0.105 → 0.11`.
  - **Captura**: 1 × 1200 + 2 × 45 → base 1290.00, cuota 270.90, total 1560.90.
  - **Suma**: la suma de las líneas redondeadas es igual a la base.
  - **Varios casos**: cantidades con decimales, importe máximo `Decimal(12,2)` y rechazo por encima de ese límite, desglose con varios tipos (la función lo admite aunque la UI use uno) y devolución total (sin líneas → desglose a 0).
  - **`TIPOS_IVA_S1`**:
    - Admite 0, 4, 10 y 21 en 2026.
    - Rechaza 5 y 22 en 2026.
    - Admite 5 el 15/08/2024 y 7,5 el 15/11/2024.
    - La fecha evaluada es la de la operación y, si no hay, la de expedición (F-3 §15.1, research R-10).
  - **Tipos**: ninguna función acepta ni devuelve `float`.
- [X] T005 [P] ⚖️ Test `backend/tests/unit/domain/test_huella.py` (research R-2):
  - Los tres vectores oficiales de F-2, con la cadena exacta y la huella en mayúsculas.
  - Espacios iniciales y finales recortados, campo vacío como `nombre=` y sin `&` final.
  - Importes siempre con dos decimales (`123.10`).
  - Cadena de N registros que mezcla altas y anulaciones, con cada huella anterior igual a la del previo.
  - Alterar un solo campo cambia la huella.
- [X] T006 [P] Test `backend/tests/unit/domain/test_numeracion.py`:
  - Formato `FAC-2026-0001`, `REC-2026-0001` y `FAC-2026-10000`.
  - Año tomado de la fecha de expedición.
  - Parseo inverso y validación de F-3 §3.1.3.1: ASCII 32–126 sin `" ' < > =` y longitud ≤ 60.
- [X] T007 [P] Test `backend/tests/unit/domain/test_registro.py` (research R-3, R-4, R-4b). Contenido `dict` según F-1, con los valores en texto:
  - **Alta F1**: `IDVersion 1.0`, `IDFactura`, `NombreRazonEmisor`, `TipoFactura`, `DescripcionOperacion`, `Destinatarios` (con NIF y con `IDOtro` para los tipos 02–06), `Desglose` (`ClaveRegimen 01`, `CalificacionOperacion S1`, `TipoImpositivo 21.00`), `CuotaTotal`, `ImporteTotal`, `Encadenamiento` (`PrimerRegistro S` o `RegistroAnterior`), `SistemaInformatico` completo, `FechaHoraHusoGenRegistro`, `TipoHuella 01` y `Huella`. Sin `Impuesto` ni los opcionales excluidos.
  - **Rectificativa R4-S y R1-S**: `TipoRectificativa S`, `FacturasRectificadas` e `ImporteRectificacion` con la base y la cuota de la original, `FechaOperacion` heredada, y desglose y totales corregidos.
  - **Devolución total R1**: un único `DetalleDesglose` a 0.
  - **Anulación**: `IDFactura` de la anulada, sin importes ni `SinRegistroPrevio`.
  - **`descripcion_operacion`** (FR-045): unión con «; », recorte a 500 terminando en «…» y texto «Devolución total de la factura X».
- [X] T008 [P] Test `backend/tests/unit/schemas/test_importes.py` (research R-10):
  - `Importe` y `Cantidad` aceptan `"45"`, `"1200.5"` y `"1200.50"`.
  - Rechazan números JSON (`45`, `45.5`), negativos, más de dos decimales y formatos con coma.
  - La salida serializa como cadena con dos decimales.
  - El esquema OpenAPI generado es `type: string` con `pattern`.
- [X] T009 Test `backend/tests/integration/test_facturacion_inalterable.py`, con el patrón de `test_auditoria_inalterable.py` (research R-8, SC-005):
  - **Con `jb_app`**: `UPDATE`, `DELETE` y `TRUNCATE` sobre `facturas`, `lineas_factura`, `desgloses_factura`, `correcciones_factura` y `registros_facturacion` fallan con 42501.
  - **Con `jb_owner`**: los mismos intentos fallan con el mensaje «Los documentos de facturación emitidos son inalterables».
  - **`contadores_factura`**: bajar `ultimo_numero` falla con 42501 (trigger `contador_solo_al_alza`), y `DELETE` falla para `jb_app`.
- [X] T010 Test `backend/tests/integration/test_cadena_registros.py` ⚖️ (research R-6, FR-029):
  - **Trigger `validar_encadenamiento`**: el primer registro exige `primer_registro` y `secuencia 1`. Un `INSERT` manual con secuencia no contigua, con `huella_anterior` que no coincide o con un segundo `primer_registro` se rechaza.
  - **`services/cadena.create_registro_alta` y `create_registro_anulacion`**: encadenan bien altas y anulaciones.
  - **Comprobación previa**: se detiene con `CadenaInconsistente` si el último registro está alterado (se simula con `jb_owner` usando `ALTER TABLE … DISABLE TRIGGER` dentro de la transacción de test) o si su hora es más de un minuto posterior a `ahora()`, que se congela con monkeypatch.
  - **Formato de la hora**: `YYYY-MM-DDThh:mm:ss+02:00` en verano y `+01:00` en invierno.

### Backend: implementación

- [X] T011 [P] Implementar `backend/app/domain/importes.py`, puro y con `Decimal` (research R-10). Los nombres van en inglés, salvo los términos de dominio (constitución VIII):
  - `round_amount`, `line_amount`, `compute_totals(lineas, tipo_iva) -> Totales` (desglose por tipo, `base_total`, `cuota_total`, `importe_total`) y los límites.
  - `TIPOS_IVA_S1` con sus ventanas de fechas, la cita de F-3 §15.1 y `is_rate_allowed(tipo_iva, fecha)`. `fecha` es la de la operación o, si no hay, la de expedición.
- [X] T012 [P] Implementar `backend/app/domain/huella.py` (research R-2): `format_amount`, `format_date` (dd-mm-yyyy), `format_timestamp` (Europe/Madrid, ISO 8601 con desfase), `build_alta_string`, `build_anulacion_string` y `compute_huella` (SHA-256, hexadecimal en mayúsculas).
- [X] T013 [P] Implementar `backend/app/domain/numeracion.py` (research R-7): `format_num_serie(serie, anio, numero)`, `year_of(fecha)` y `validate_num_serie`.
- [X] T014 Implementar `backend/app/domain/registro.py` (research R-3, R-4, R-4b): `build_contenido_alta(...)`, `build_contenido_anulacion(...)` y `build_descripcion_operacion(lineas, rectifica=None)`. Construye el contenido F-1 como `dict[str, object]` con valores en texto, a partir de dataclasses de entrada y del bloque `SistemaInformatico` de `Settings`.
- [X] T015 [P] Crear `backend/app/schemas/importes.py` con `Importe` y `Cantidad` para la entrada (`Annotated[Decimal, BeforeValidator(solo_texto), WithJsonSchema(...)]`) e `ImporteSalida` (research R-10).
- [X] T016 [P] Añadir a `backend/app/core/errors.py` los problemas de research R-14 y del contrato, con su `type`, estado y campos extra (`faltan`):
  - `EmisionNoDisponible`, `ClienteNoFacturable`, `FechaExpedicionNoValida`, `TipoIvaNoAdmitido` y `FacturaNoModificable`.
  - `ContadorNoAjustable`, `CadenaInconsistente`, `SinCambios` y `ModalidadBloqueada`.
- [X] T017 [P] Actualizar `backend/app/services/auditoria.py`: `to_json` serializa `Decimal` con `format(valor, "f")`, nunca como `float` (FR-043), con su test en `backend/tests/unit/test_auditoria_json.py`.
- [X] T018 Crear los modelos según data-model.md y registrarlos en `backend/app/models/__init__.py`: `configuracion_facturacion.py`, `contador_factura.py`, `borrador_factura.py` (con `LineaBorrador` y `version_id_col`), `factura.py` (con `LineaFactura`, `DesgloseFactura` y `texto_busqueda` generada), `correccion_factura.py` y `registro_facturacion.py`, todos en `backend/app/models/`.
- [X] T019 Crear la migración `backend/alembic/versions/0005_facturacion.py`, escrita a mano (data-model.md, research R-6 a R-8, R-12 y R-15):
  - **Tablas**: todas, con sus `CHECK`, `UNIQUE` (también `clave_idempotencia`, `operacion_idempotencia` y `origen_idempotencia`), FK `RESTRICT` e índices, incluido el GIN trigram de `texto_busqueda`. Los borradores llevan `tipo_iva_previsto` y totales previstos. Fila inicial de `configuracion_facturacion`.
  - **Inalterabilidad**:
    - `REVOKE UPDATE, DELETE, TRUNCATE` a `jb_app` en las tablas 🔒, y `REVOKE DELETE, TRUNCATE` en `contadores_factura`.
    - Función `impedir_modificacion_facturacion()` con sus triggers por fila y por sentencia.
  - **Función `estado_factura(uuid)`**: `STABLE`, con `EXISTS` (research R-8, R-12). Es la única implementación del estado derivado, incluida la reactivación de FR-048.
  - **Triggers de negocio**: `contador_solo_al_alza`, `validar_encadenamiento` y `validar_correccion`, este último con `estado_factura`.
  - **Vista**: `v_listado_facturas`, que usa `estado_factura` y los totales previstos **guardados** de los borradores, sin redondear nada en SQL.
  - **Auditoría**: ampliación del `CHECK` de `eventos_auditoria.tipo` con `sql_in(TipoEvento)`, igual que en la 0004.
  - **`downgrade`**: completo.
- [X] T020 Implementar los repositorios:
  - `backend/app/repositories/registros.py`: `lock_chain` (`pg_advisory_xact_lock`), `get_last`, `insert` y `list_in_order`.
  - `backend/app/repositories/contadores.py`: `assign_numero(serie, anio)` con `INSERT ON CONFLICT DO NOTHING` + `SELECT FOR UPDATE` + `UPDATE RETURNING`, `last_used` y `raise_next`.
  - `backend/app/repositories/configuracion_facturacion.py`: `get` y `update` con versión.
- [X] T021 Implementar `backend/app/services/cadena.py` (research R-6):
  - `create_registro_alta(db, factura, config) -> RegistroFacturacion` y `create_registro_anulacion(db, factura_anulada, config)`.
  - Se ejecutan con el cerrojo ya tomado. Hacen la comprobación previa de F-10, art. 7.i, construyen el contenido con `domain/registro.py`, calculan la huella e insertan con la `secuencia` siguiente.
  - Si la cadena no cuadra, dejan el evento `cadena_inconsistente` en una transacción aparte y lanzan `CadenaInconsistente`.

### Web: piezas compartidas

- [X] T022 [P] Test `joyeriablanco_web/src/lib/dinero.test.ts`:
  - `parsear` («1.200,50», «1200,5», «45», errores) y `aApi` (`"1200.50"`).
  - `formatear` («1.560,90 €»).
  - `calcularTotales`, que reproduce los casos de T004, incluido el medio céntimo.
  - No se usa `Number` ni `parseFloat` para los importes.
- [X] T023 [P] Implementar `joyeriablanco_web/src/lib/dinero.ts` con `BigInt`, escalado en céntimos y centésimas de unidad, y el redondeo del medio alejándose de cero (research R-11).
- [X] T024 [P] Crear `joyeriablanco_web/src/components/ui/ModalDocumento.tsx` con su test `ModalDocumento.test.tsx` (research R-13):
  - Construido sobre `ModalOverlay`/`Modal`/`Dialog` de react-aria: `max-w-5xl`, pantalla completa por debajo de 768 px, cabecera con título Bodoni `headline-md`, cuerpo desplazable y pie fijo.
  - Nivel 2 con tokens.
  - `onIntentarCerrar` para la guarda de cambios.
  - Test: foco atrapado y devuelto, Escape pasa por la guarda y la capa anidada cierra solo la de encima.
- [X] T025 [P] Crear `joyeriablanco_web/src/components/ui/CampoDecimal.tsx` con su test:
  - Símbolo € opcional, fijo, en `primary-container`, y cifras tabulares (DESIGN.md, «Monetary Inputs»).
  - Admite coma decimal y puntos de miles y muestra el error de formato en el campo (FR-049).
  - Usa `lib/dinero.ts`.
- [X] T026 [P] Extraer `CampoFecha` de `joyeriablanco_web/src/features/auditoria/AuditoriaPage.tsx` a `joyeriablanco_web/src/components/ui/CampoFecha.tsx`, con `min`/`max` opcionales. AuditoriaPage pasa a usarlo y sus tests siguen en verde.
- [X] T027 [P] Crear `joyeriablanco_web/src/lib/idempotencia.ts` con su test (research R-18). `useClaveOperacion()` devuelve un UUID estable, `renovar()` y `enCurso`. La clave se reutiliza en los reintentos y se renueva solo tras un éxito.

**Checkpoint**: el dominio fiscal está probado con los vectores oficiales, las garantías de la BD
están activas y las piezas web compartidas listas.

---

## Phase 3: User Story 1 - Configurar la facturación (Priority: P1)

**Goal**: el administrador fija el IVA por defecto (21 %), la clave de régimen, la modalidad y los
datos del emisor, y puede ajustar al alza el próximo número. Los empleados no acceden.

**Independent Test**:
1. Un administrador guarda la configuración y un empleado recibe 403.
2. `/v1/facturas/parametros` refleja el IVA y lo que falta para emitir.
3. El ajuste del contador simula el hueco, lo aplica con su motivo y rechaza los valores ya usados.

### Tests for User Story 1 ⚠️

- [X] T028 [P] [US1] Test `backend/tests/integration/test_configuracion_facturacion.py`:
  - **Lectura y permisos**: `GET` y `PUT` como administrador (valores iniciales: IVA 21.00, clave 01, modalidad nula y emisor vacío); como empleado, 403.
  - **Validaciones**: IVA 22 → 422 `tipo-iva-no-admitido`; clave fuera de L8A → 422; NIF de emisor no válido → 422; el código postal deriva la provincia.
  - **Concurrencia y auditoría**: versión desfasada → 409; evento `configuracion_facturacion_cambiada` con el diff y los importes en texto.
  - **Emisión posible**: `emision_posible` y `faltan`, que solo recoge emisor y modalidad (el productor lo exige `Settings` al arrancar, T001).
  - **Modalidad** (FR-050): con un registro ya existente, cambiarla → 409 `modalidad-bloqueada` y `modalidad_bloqueada = true`. El registro se crea en el fixture con `services/cadena.py` y los repositorios, sin depender de US2.
  - **Contador**:
    - `simular=true` devuelve el hueco sin auditar ni cambiar nada.
    - `simular=false` aplica el ajuste, deja `contador_ajustado` con el motivo, y `contadores.assign_numero` devuelve ese número. La emisión completa se prueba en T035.
    - Un valor ≤ último usado + 1 → 409 `contador-no-ajustable`.
    - Sin motivo → 422.
    - Solo afecta a FAC del año en curso.
  - **Parámetros**: `GET /v1/facturas/parametros` como empleado devuelve IVA, `emision_posible`, `faltan`, `proximo_numero`, `hoy` y `fecha_minima`.
- [X] T029 [P] [US1] Test web `joyeriablanco_web/src/features/configuracion/FacturacionPage.test.tsx` con MSW:
  - Solo se ofrecen los tipos de IVA admitidos, la lista L8A y la modalidad «Sin decidir» / VERI\*FACTU / no VERI\*FACTU.
  - La modalidad aparece bloqueada con su explicación cuando `modalidad_bloqueada`.
  - Aviso «no se puede emitir» con lo que falta.
  - Diálogo de ajuste: próximo número, números sin usar según la simulación, motivo obligatorio y confirmación.
  - Errores mapeados a sus campos y conflicto de versión.

### Implementation for User Story 1

- [X] T030 [US1] Implementar `backend/app/services/configuracion_facturacion.py`:
  - `get_config` y `update_config`, con validaciones, provincia derivada del CP, modalidad bloqueada si hay registros y auditoría con diff.
  - `missing_for_emission(config)`.
  - `adjust_counter(db, actor, proximo, motivo, simular)`: cerrojo de la cadena, luego contador y auditoría. Exige `proximo > último usado + 1`.
  - `get_parametros(db)`.
- [X] T031 [P] [US1] Crear `backend/app/schemas/configuracion_facturacion.py` según el contrato: `ConfiguracionFacturacionEntrada`/`Salida`, `AjusteContadorEntrada`/`Salida` y `ParametrosFacturacionSalida`.
- [X] T032 [US1] Implementar los endpoints y quitarlos de `PENDIENTES_002`:
  - `backend/app/api/v1/configuracion.py`: `GET` y `PUT /v1/configuracion/facturacion` y `POST /v1/configuracion/facturacion/contador`, con `AdminSession`.
  - `backend/app/api/v1/facturas.py` (nuevo): `GET /v1/facturas/parametros`, con sesión.
  - Registrar los routers en `backend/app/api/v1/__init__.py`.
- [X] T033 [US1] Regenerar los tipos con `exportar-openapi` + `gen:api` y crear `joyeriablanco_web/src/api/queries/configuracionFacturacion.ts` (configuración, parámetros y contador). Añadir los alias a `joyeriablanco_web/src/api/tipos.ts` y las etiquetas en español de los 10 tipos de evento nuevos a `joyeriablanco_web/src/features/auditoria/tipos-evento.ts` (research R-15). Sin ellas no pasa el typecheck.
- [X] T034 [US1] Crear la pestaña de configuración:
  - `joyeriablanco_web/src/features/configuracion/FacturacionPage.tsx` y `AjusteContadorDialog.tsx`.
  - La ruta `joyeriablanco_web/src/routes/_app/configuracion/facturacion.tsx`.
  - La pestaña «Facturación» en `joyeriablanco_web/src/routes/_app/configuracion.tsx`, con el subtítulo «Usuarios, auditoría y facturación».
  - DESIGN.md según contracts/ui-rutas.md.
  - E2E `joyeriablanco_web/e2e/configuracion-facturacion.spec.ts` (SC-010):
    - Como administrador, guardar el IVA y el emisor, y ajustar el contador con su aviso.
    - Como empleado, sin acceso a la pestaña.

**Checkpoint**: la facturación queda configurable y la emisión ya sabe si es posible.

---

## Phase 4: User Story 2 - Crear y emitir una factura en el modal (Priority: P1) 🎯 MVP

**Goal**: desde `/facturas`, «Nueva factura» abre el modal. Se elige o se da de alta el cliente, se
añaden líneas y se emite. El número `FAC-AAAA-NNNN` y el registro de alta encadenado se generan en
la misma transacción, y la operación es idempotente.

**Independent Test**:
1. Con el emisor configurado y un cliente activo, se emite una factura de varias líneas.
2. Se comprueba el número, los importes del servidor, las copias del emisor y el destinatario, el
   registro con su huella y la idempotencia.
3. Las 200 emisiones concurrentes no dejan huecos.

### Tests for User Story 2 ⚠️

- [X] T035 [P] [US2] Test `backend/tests/integration/test_emision.py`:
  - **Caso normal**: `POST /v1/facturas` → 201 con `FAC-2026-0001`, las líneas con `tipo_iva` e importe, el desglose, los totales (1290.00 / 270.90 / 1560.90) y las copias del emisor y del destinatario. El registro de alta es primer registro, su huella se recalcula igual y su `contenido` tiene las claves de R-3. Evento `factura_emitida`. Un empleado también puede emitir.
  - **Rechazos**:
    - Configuración incompleta → 409 `emision-no-disponible` con `faltan`.
    - Cliente inactivo o sin domicilio → 422 `cliente-no-facturable`.
    - Fecha futura o anterior a la última de la serie → 422 `fecha-expedicion`.
    - Tipo no admitido en la fecha → 422 `tipo-iva-no-admitido`.
    - Importes como número JSON → 422.
    - Totales en el cuerpo → 422 (`additionalProperties`).
    - Sin líneas → 422.
    - Sin `Idempotency-Key` → 422.
  - **Año y copias**: fecha del 01/01/2027 → `FAC-2027-0001`. Editar después el cliente no altera la factura (FR-016).
  - **Límites de fecha** (FR-018): del año anterior sí se admite; de dos años atrás o anterior al 28/10/2024 → 422 `fecha-expedicion`.
  - **Importe cero**: FAC con total 0 → 422.
  - **Registro**: guarda la `modalidad` de la configuración y `estado_remision = pendiente` (FR-030).
  - **Idempotencia**: repetir la misma `Idempotency-Key` → 200 con la misma factura, sin segundo registro ni número. La misma clave en otra operación u otro documento → 409 `idempotencia-conflicto` (research R-18).
  - **Cadena y borrado**: `cadena-inconsistente` → 409 y no se emite. Borrar un cliente con factura → 409 `cliente-con-documentos` (FR-042).
- [X] T036 [P] [US2] ⚖️ Test `backend/tests/integration/test_numeracion_concurrencia.py`, con el patrón de `test_usuarios.py::test_regla_del_ultimo_administrador_bajo_concurrencia` (sesiones reales con `AsyncSession(engine_app)`, `asyncio.gather` y limpieza con `engine_owner`), para SC-002 y research R-7:
  - **200 emisiones** repartidas en 10 sesiones: números 1..200 sin huecos ni duplicados; 200 registros con `secuencia` 1..200; cada huella anterior es la del registro previo.
  - **Fallo forzado**: una emisión que falla a propósito tras asignar número no lo consume.
  - **Ajuste del contador a la vez que las emisiones**: ningún duplicado y el contador nunca baja.
  - **Mismo `Idempotency-Key` en paralelo**: se emite una sola factura (SC-011).
- [X] T037 [P] [US2] Test web `joyeriablanco_web/src/features/facturas/FacturaModal.test.tsx` (modo nueva), con MSW:
  - **Estructura**: tres secciones. El número muestra «Se asigna al emitir» y el próximo previsto.
  - **Cliente**: el selector busca clientes activos y el resumen muestra identificación y domicilio.
  - **Líneas**: añadir y quitar, «Añade la primera línea» y límite de 100.
  - **Previsualización**: 1.290,00 / 270,90 / 1.560,90 con «IVA (21 %)».
  - **Emitir**: pide confirmación; el botón está deshabilitado con el motivo si `emision_posible = false` (con enlace a Configuración solo para un administrador); los errores del servidor van a su campo.
  - **Cierre**: confirmación al descartar cambios.
  - **Idempotencia**: la misma `Idempotency-Key` en un reintento tras un error de red.
  - **Resultado**: aviso «Factura … emitida» y cierre.
  - **Sesión caducada** (401): aviso y lo tecleado se descarta, como en 001. Ante un error de red, se conserva (spec, casos límite).
- [X] T038 [P] [US2] Test web `joyeriablanco_web/src/features/clientes/ClienteAltaPanel.test.tsx`:
  - Abierto sobre el modal, al guardar llama a `onCreado(cliente)`; al cancelar no cambia nada.
  - Escape cierra solo el panel.
  - Un duplicado se trata igual que en 001.
  - Los tests actuales de `ClientePanel` siguen en verde.

### Implementation for User Story 2

- [X] T039 [US2] Implementar `backend/app/repositories/facturas.py`:
  - `insert_emitida` (factura, líneas y desglose), `get_detalle` (con `estado_factura`), `get_by_idempotency_key` y `last_fecha_in_serie(serie, anio)`.
  - `has_documentos(cliente_id)`, que cuenta borradores y facturas.
- [X] T040 [US2] Implementar `emit_factura(db, actor, datos, clave, *, borrador=None)` en `backend/app/services/emision.py` (research R-6, R-7, R-9, R-18):
  1. Cerrojo de la cadena y búsqueda de la clave de idempotencia, con su operación y origen.
  2. Validaciones de configuración, cliente activo con domicilio (FR-017), fecha con todos los límites de FR-018, líneas, total > 0 y tipo de IVA (`is_rate_allowed`).
  3. `compute_totals`, contador, copias, descripción (FR-045) e inserción.
  4. `cadena.create_registro_alta` y auditoría.
  5. Logs sin datos personales ni importes (FR-051).
- [X] T041 [US2] Implementar `backend/app/services/facturas.py` → `get_factura(db, id)`: estado derivado, `rectifica_a`, `sustituye_a`, `vigente_actual`, `correcciones` con `en_vigor`, `registros` y autores con «(eliminado)» (001, FR-061).
- [X] T042 [P] [US2] Crear `backend/app/schemas/factura.py` según el contrato: `LineaEntrada`, `FacturaEntrada` (`extra="forbid"`), `LineaSalida`, `Desglose`, `Totales`, `ClienteFacturaSalida`, `FacturaSalida`, `FacturaReferencia`, `RegistroResumen` y `Correccion`.
- [X] T043 [US2] En `backend/app/api/v1/facturas.py`, implementar `POST /v1/facturas` (cabecera `Idempotency-Key` obligatoria; 201, o 200 si es repetición) y `GET /v1/facturas/{id}`, y quitarlos de `PENDIENTES_002`.
- [X] T044 [US2] Sustituir `SinDocumentos` por la implementación real en `backend/app/services/documentos.py`, usando `repositories/facturas.has_documentos`, y conectarla en `get_documentos_checker` (FR-042).
- [X] T045 [US2] Regenerar los tipos y crear `joyeriablanco_web/src/api/queries/facturas.ts` (emitir con `Idempotency-Key`, detalle e invalidación de `['facturas']`) y sus alias en `joyeriablanco_web/src/api/tipos.ts`.
- [X] T046 [US2] Extraer `joyeriablanco_web/src/features/clientes/ClienteAltaPanel.tsx` de `ClientePanel.tsx`, controlado por props (`isOpen`, `onCreado` y `onCerrar`) y con el mismo `ClienteForm`: envuelve a `ClientePanel` y, ante un duplicado, ofrece «Usar este cliente» o «Reactivar y usar» en lugar de «Ir al cliente» (FR-046, `contracts/ui-rutas.md`).
- [X] T047 [US2] Crear en `joyeriablanco_web/src/features/facturas/`, en modo nueva:
  - `factura-valores.ts` (Zod de forma, valores iniciales y `aCuerpo` sin totales).
  - `ResumenCliente.tsx` (con aviso si falta el domicilio), `LineasFactura.tsx` (tabla en escritorio y apilada en móvil) y `TotalesFactura.tsx` (DESIGN.md, «Totals Section»).
  - `FacturaForm.tsx`, `ConfirmarEmisionDialog.tsx` y `FacturaModal.tsx`, sobre `ModalDocumento`, con «Nuevo cliente» y `useClaveOperacion`.
- [X] T048 [US2] Crear las rutas y activar el menú:
  - `joyeriablanco_web/src/routes/_app/facturas.tsx`: página con título, botón primario «Nueva factura» y `<Outlet/>`. El listado llega en US3.
  - `joyeriablanco_web/src/routes/_app/facturas/nueva.tsx` y `joyeriablanco_web/src/routes/_app/facturas/$facturaId.tsx`: consulta con datos, totales y registros.
  - En `joyeriablanco_web/src/components/layout/Sidebar.tsx`, activar Facturas y ampliar el tipo `to` (FR-041), con su test actualizado.
- [X] T049 [US2] Ampliar `backend/app/services/datos_ejemplo.py` y `reiniciar-bd-e2e` (research R-16):
  - Configuración demo: emisor ficticio con NIF válido y modalidad VERI\*FACTU.
  - Unas 50 facturas emitidas de los últimos 6 meses, con clientes de ejemplo y generadas **mediante `emision.emit_factura`**.
  - Sigue prohibido en producción.
- [X] T050 [US2] E2E `joyeriablanco_web/e2e/facturas.spec.ts`, parte 1: emitir una factura de dos líneas (número, aviso y detalle con registro) y «Nuevo cliente» desde el modal, que vuelve con el cliente elegido y las líneas intactas.

**Checkpoint**: MVP de negocio. Ya se pueden emitir facturas válidas y encadenadas.

---

## Phase 5: User Story 3 - Consultar y buscar facturas (Priority: P1)

**Goal**: listado paginado de borradores y facturas con la misma lógica que clientes, sin KPI ni
columna de estado, con marcas en el número y acciones siempre visibles.

**Independent Test**: con datos de ejemplo se prueban la búsqueda (número, cliente y NIF sin
tildes), los filtros de año y mes, los cuatro órdenes, la paginación estable, los estados vacíos y
las acciones visibles en todos los anchos.

### Tests for User Story 3 ⚠️

- [X] T051 [P] [US3] Test `backend/tests/integration/test_listado_facturas.py`:
  - **Contenido y filtros**: mezcla borradores y emitidas; por defecto, el año en curso; `anio=todos`; `mes`.
  - **Búsqueda**: `q` por «2026-0005», «maria lopez» sin tildes y NIF con separadores.
  - **Órdenes**: `recientes` (un borrador antes que las emitidas de su fecha), `antiguas`, `total_desc` y `total_asc`, con desempate estable. Recorrer todas las páginas no duplica ni omite nada.
  - **Totales de borradores**: se calculan con el IVA vigente.
  - **Casos límite**: una página posterior a la última devuelve lista vacía con el total real; parámetros no válidos → 422.
- [X] T052 [P] [US3] Test web `joyeriablanco_web/src/features/facturas/FacturasPage.test.tsx`:
  - **Estado en la URL**: con debounce de 300 ms y `replace`.
  - **Tabla**: columnas de FR-033, sin KPI ni columna de estado, marca «Borrador» en lugar del número y acciones con nombre accesible («Abrir borrador de…», «Ver factura…»).
  - **Estados vacíos**: «No hay facturas en {año}» con «Ver todos los años» y «Todavía no hay facturas». «Limpiar filtros» vuelve a los valores por defecto.
  - **Móvil**: tarjetas (FR-049).

### Implementation for User Story 3

- [X] T053 [US3] Añadir `list_facturas(filtros)` a `backend/app/repositories/facturas.py` sobre `v_listado_facturas`: `_filtros` con `_escapar_like` e `inmutable_unaccent`, normalización de la identificación como en clientes, `_ORDENES` con desempate por `id`, y conteo más página (research R-12).
- [X] T054 [US3] Crear `FiltrosFacturas` y `list_facturas` en `backend/app/services/facturas.py`, `FacturaResumenSalida` en `backend/app/schemas/factura.py` y `GET /v1/facturas` en `backend/app/api/v1/facturas.py`, y quitarlo de `PENDIENTES_002`.
- [X] T055 [US3] Crear el listado en la web:
  - Query `facturasListaQuery` en `joyeriablanco_web/src/api/queries/facturas.ts`, con `keepPreviousData` y 25 por página.
  - `joyeriablanco_web/src/features/facturas/FiltrosFacturas.tsx`, `TablaFacturas.tsx` (acciones fijas con `components/ui/tabla.ts`, tarjetas en móvil y marcas) y `FacturasPage.tsx`.
  - Esquema Zod de *search params* en `joyeriablanco_web/src/routes/_app/facturas.tsx`.
- [X] T056 [US3] Ampliar `joyeriablanco_web/e2e/acciones-visibles.spec.ts` con la tabla de facturas, midiendo una página completa a 768, 1024, 1280, 1440 y 1536 px (SC-008):
  - Primero se mide qué columnas caben junto al menú y se ocultan las necesarias, como en 001 R-22.
  - Los umbrales medidos se anotan en research (R-12) y en la spec (FR-033). Si difieren de lo especificado, **se corrige primero la spec**.
  - E2E `joyeriablanco_web/e2e/facturas-listado.spec.ts` (SC-010): búsqueda por número, por cliente sin tildes y por NIF; filtros de año y mes, con «Ver todos los años»; orden; paginación; y estado en la URL al recargar.

**Checkpoint**: US1–US3 completas, con el listado operativo.

---

## Phase 6: User Story 4 - Editar y borrar borradores (Priority: P2)

**Goal**: guardar borradores incompletos, retomarlos en el mismo modal, editarlos con concurrencia
optimista, borrarlos sin consumir número y emitirlos.

**Independent Test**: se crea un borrador sin cliente, se completa, se detecta un conflicto de
versión, se borra otro sin que se consuma número y se emite uno de forma idempotente.

### Tests for User Story 4 ⚠️

- [X] T057 [P] [US4] Test `backend/tests/integration/test_borradores.py`:
  - **CRUD**:
    - `POST` de un borrador incompleto → 201.
    - `GET` con `totales_previstos` y `tipo_iva_previsto` guardados al guardar, calculados con `domain/importes.py`.
    - Eventos `borrador_factura_creado` y `borrador_factura_editado` con su diff.
    - `PUT` sustituye las líneas; con versión desfasada → 409.
    - `DELETE` → 204 con evento `borrador_factura_eliminado`, sin número consumido ni registro.
  - **Emisión**:
    - `POST …/emision` → 201: el borrador deja de existir y se emite la factura.
    - Repetición con la misma clave → 200 con la misma factura.
    - Con otra clave → 404.
    - Cliente desactivado → 422 `cliente-no-facturable`.
    - Fecha antigua → 422 `fecha-expedicion`.
  - **Borrado de cliente**: un cliente con borrador → 409 `cliente-con-documentos`.
- [X] T058 [P] [US4] Test web del modo borrador en `joyeriablanco_web/src/features/facturas/FacturaModal.borrador.test.tsx`:
  - Botones «Eliminar borrador», «Guardar borrador» y «Emitir factura».
  - Diálogo de conflicto de versión.
  - Mensaje «Este borrador ya se ha emitido» ante un 404.
  - Aviso si cambió el IVA desde que se guardó: `tipo_iva_previsto` distinto del IVA de `parametros`.

### Implementation for User Story 4

- [X] T059 [US4] Implementar el backend de borradores:
  - `backend/app/repositories/borradores.py`.
  - `backend/app/services/borradores.py`: `create_borrador`, `get_borrador`, `update_borrador` con versión, `delete_borrador` y `emit_borrador`.
    - Al crear y editar se calculan y guardan `tipo_iva_previsto` y los totales previstos con `domain/importes.py`, y se deja su evento de auditoría.
    - `emit_borrador` llama a `emision.emit_factura(..., borrador=…)`, con `FOR UPDATE` sobre el borrador, que es mutable, y la comprobación de versión.
  - `backend/app/schemas/borrador.py`.
  - `backend/app/api/v1/borradores.py`, con las 5 operaciones, quitándolas de `PENDIENTES_002`.
- [X] T060 [US4] Crear la web de borradores:
  - Queries en `joyeriablanco_web/src/api/queries/borradores.ts`.
  - Modo borrador en `FacturaModal.tsx`.
  - Ruta `joyeriablanco_web/src/routes/_app/facturas/borradores/$borradorId.tsx`.
  - Acción de fila «Abrir borrador» en `TablaFacturas.tsx`.
  - «Guardar borrador» en el modo nueva.
- [X] T061 [US4] Añadir 5 borradores a `backend/app/services/datos_ejemplo.py`, uno de ellos sin cliente.
- [X] T062 [US4] E2E `joyeriablanco_web/e2e/facturas.spec.ts`, parte 2:
  1. Guardar borrador, reabrirlo desde el listado, editar y emitir.
  2. Eliminar otro borrador y comprobar que el siguiente número no cambia.

**Checkpoint**: flujo completo de borrador a emisión.

---

## Phase 7: User Story 5 - Modificar o anular una factura emitida (Priority: P2)

**Goal**: el administrador corrige facturas emitidas solo mediante corrección trazable:
- anulación y reemisión;
- rectificativa por sustitución R1/R4, con devoluciones;
- anulación sola;
- anulación de una rectificativa, que devuelve la original a vigente.

Todo con historial y sin tocar nunca el original.

**Independent Test**: sobre una factura emitida se hacen, una a una, las cuatro correcciones y se
comprueba lo siguiente:
- los registros encadenados;
- los enlaces y el historial;
- la reactivación de FR-048;
- que ningún número se reutiliza;
- que un empleado recibe 403.

### Tests for User Story 5 ⚠️

- [X] T063 [P] [US5] Test `backend/tests/integration/test_correcciones.py`, sobre research R-4, R-8, R-9 y R-18:
  - **Anular**:
    - Solo administrador; un empleado recibe 403, **tanto en `/anulacion` como en `/modificacion`** (SC-005).
    - Declaración obligatoria.
    - Registro de anulación encadenado.
    - Estado `anulada`.
    - El número no se reutiliza: la siguiente emisión recibe el siguiente.
    - Evento `factura_anulada`.
    - Idempotente por clave.
  - **Modificar «no debió emitirse»**:
    - Anulación más FAC nueva con el siguiente número.
    - `FechaOperacion` heredada.
    - Enlaces `sustituye_a` y `vigente_actual`.
    - Sin cambios, se admite.
  - **Modificar «factura entregada»**:
    - Causa `error_datos` → `REC-2026-0001` R4-S con `ImporteRectificacion` igual a los totales de la original, `FacturasRectificadas` y `FechaOperacion` heredada. El contenido sigue R-4.
    - Causa `devolucion_o_precio` sin líneas → R1 con total 0 y desglose a cero.
    - Rectificativa idéntica → 422 `sin-cambios`. En cambio, con las mismas líneas pero la configuración de IVA ya corregida (R1 «IVA mal aplicado»), se admite.
    - El tipo de IVA se valida con la fecha de operación heredada (F-3 §15.1).
    - Eventos de auditoría de cada operación según la tabla de research R-15.
    - Sin causa → 422.
    - Líneas vacías con `error_datos` → 422.
  - **Rectificativa**:
    - Se puede rectificar de nuevo (otra REC).
    - Al anularla, la original vuelve a estar `vigente` y se puede modificar de nuevo (FR-048).
    - «No debió emitirse» sobre una REC → 422.
  - **Rechazos generales**:
    - Factura no vigente → 409 `factura-no-modificable`.
    - Dos modificaciones concurrentes de la misma factura → una 201 y otra 409.
    - Un `INSERT` directo en `correcciones_factura` sobre una factura no vigente lo rechaza el trigger `validar_correccion`.
  - **Detalle**: el detalle muestra `correcciones` con `en_vigor`.
- [X] T064 [P] [US5] Tests web:
  - `joyeriablanco_web/src/features/facturas/MotivoModificacionDialog.test.tsx`:
    - El motivo y la causa, con lo que se va a generar.
    - En una REC solo se ofrece «ya entregada».
    - El aviso de IVA distinto.
  - `AnularFacturaDialog.test.tsx`:
    - La declaración y el motivo.
    - El aviso de reactivación en una REC.
  - `FacturaModal.consulta.test.tsx`:
    - Un empleado no ve acciones.
    - Anulada y rectificada: marca, enlace a la vigente y sin acciones.
    - El historial.
    - Tras modificar se muestra la factura nueva con el aviso de FR-049.

### Implementation for User Story 5

- [X] T065 [US5] Implementar en `backend/app/services/emision.py`, bajo el cerrojo de la cadena y con idempotencia:
  - `anular_factura(db, actor, factura_id, declaracion, motivo_texto, clave)`.
  - `modify_factura(db, actor, factura_id, datos, clave)`, que puede ser anulación más reemisión o rectificación por sustitución R1/R4, con devolución total.
  - Reglas de REC y de `sin-cambios`.
  - Orden de research R-9: primero los registros y las facturas nuevas, y **por último** la corrección, con sus referencias ya conocidas.
  - Registros mediante `services/cadena.py`.
  - Auditoría (`factura_anulada` y `factura_rectificada`).
  - Logs sin datos personales.
- [X] T066 [US5] Implementar `backend/app/repositories/correcciones.py` (insertar y listar por factura) y completar el historial en `repositories/facturas.get_detalle`. El estado sale siempre de `estado_factura` (research R-8, R-12). Test en `backend/tests/integration/test_estado_factura.py`: la función, la vista y el trigger coinciden en todos los casos de FR-048 (anulada, rectificada, rectificativa anulada que reactiva la original y rectificativa de una rectificativa).
- [X] T067 [US5] Añadir `AnulacionEntrada` y `ModificacionEntrada` en `backend/app/schemas/factura.py`, e implementar `POST /v1/facturas/{id}/anulacion` y `POST /v1/facturas/{id}/modificacion` con `AdminSession` e `Idempotency-Key`. Quitarlos de `PENDIENTES_002`.
- [X] T068 [US5] Web:
  - En `joyeriablanco_web/src/features/facturas/`: `MotivoModificacionDialog.tsx`, `AnularFacturaDialog.tsx`, `HistorialFactura.tsx` y los modos consulta y modificar de `FacturaModal.tsx`, con el aviso de IVA distinto y el resultado tras cada acción (FR-049).
  - La ruta `joyeriablanco_web/src/routes/_app/facturas/$facturaId/modificar.tsx`, solo para administradores.
  - Las marcas «Anulada» y «Rectificada» en `TablaFacturas.tsx`.
- [X] T069 [US5] Añadir a `backend/app/services/datos_ejemplo.py`, mediante `emision.anular_factura` y `modify_factura`, unas cuantas correcciones: una anulación, una reemisión, una rectificativa R4, una devolución total R1 y una rectificativa anulada.
- [X] T070 [US5] E2E `joyeriablanco_web/e2e/facturas.spec.ts`, parte 3, como administrador:
  1. Reemisión.
  2. Rectificativa R4.
  3. Anulación de una rectificativa, con la original vigente de nuevo.
  4. Anular una factura.
  5. Como empleado, sin acciones de corrección.

**Checkpoint**: correcciones trazables completas, sin `UPDATE` ni `DELETE`.

---

## Phase 8: User Story 6 - Integridad comprobable del registro de facturación (Priority: P3)

**Goal**: comprobar la cadena completa desde la consola e informar de la primera discrepancia.

**Independent Test**: tras emitir y corregir, la comprobación da la cadena por íntegra. Si se
altera un registro saltándose los triggers, señala ese registro.

- [X] T071 [P] [US6] Test `backend/tests/integration/test_verificar_cadena.py` (SC-004):
  - Cadena íntegra → «íntegra (N registros)» y código 0.
  - Alteraciones dentro de la transacción de test (`jb_owner` con `DISABLE TRIGGER` y `UPDATE`), cada una → se identifica el registro o la factura afectada y código 1:
    - un campo de la huella;
    - una línea de factura;
    - un desglose;
    - el `contenido` del registro;
    - la copia del destinatario.
  - Se generan los eventos `cadena_verificada` y `cadena_inconsistente`.
  - Se prueba también `services/integridad.py` sin CLI.
- [X] T072 [US6] Implementar la comprobación de integridad:
  - `backend/app/services/integridad.py`: `verify_chain(db) -> ResultadoIntegridad`. En orden de `secuencia`, hace para cada registro lo siguiente (research R-14):
    - Recalcula la huella y el enlace con el anterior.
    - Compara el `contenido` con el que reconstruye `domain/registro.py` desde la factura. El bloque `SistemaInformatico` y la hora se toman del propio registro.
    - Recalcula los totales y el desglose de la factura desde sus líneas.
  - El comando `joyeria verificar-cadena` en `backend/app/cli.py`, con su salida y código de salida (FR-031).

**Checkpoint**: todas las historias completas.

---

## Phase 9: Polish & Cross-Cutting Concerns

- [X] T073 [P] Test `backend/tests/integration/test_logs_facturacion.py` con `caplog` (FR-051). Tras emitir, modificar y anular, los logs no contienen el nombre ni la identificación del cliente, ni importes. Solo IDs, número y operación.
- [X] T074 [P] Crear `backend/scripts/medir_busqueda_facturas.py`, que genera 20.000 facturas en la BD e2e mediante los servicios y mide el p95 de 100 búsquedas y cambios de filtro (< 1 s, SC-007) y el p95 de la emisión (< 1 s, plan). Anotar el resultado en `specs/002-facturas/quickstart.md`.
- [X] T075 [P] E2E de teclado y adaptación:
  - Ampliar `joyeriablanco_web/e2e/teclado.spec.ts`: modal de factura solo con teclado, con dos capas, Escape y foco devuelto.
  - Ampliar `joyeriablanco_web/e2e/responsive.spec.ts`: listado y modal a 360, 768 y 1440 px sin desplazamiento horizontal, y modal a pantalla completa en móvil (SC-008).
- [X] T076 Cerrar el contrato: eliminar `PENDIENTES_002` de `backend/tests/integration/test_contrato_openapi.py`, que debía estar vacía, y comprobar que la API coincide exactamente con la unión de los contratos.
- [X] T077 Actualizar la documentación:
  - `README.md`: tabla de módulos, con Facturas y registro Verifactu ✅ y PDF/QR y remisión 🔜, y el comando `verificar-cadena`.
  - `CLAUDE.md`: comandos (`verificar-cadena`).
  - `specs/002-facturas/quickstart.md`: validado de principio a fin, con el resultado de las 17 validaciones manuales y el cronometraje de SC-001 (emitir una factura de tres líneas en menos de 2 minutos).
- [X] T078 Pasar las puertas de calidad completas:
  - Backend: `uv run ruff check . && uv run ruff format --check . && uv run mypy . && uv run pytest`.
  - Web: `npm run lint && npm run typecheck && npm run test && npm run build && npm run check:tokens` y `npx playwright test`.
  - Revisión de conformidad con DESIGN.md (SC-009).
  - Todo en verde antes de cerrar.
- [X] T079 Preguntar al responsable si se retira el contenido de `temporal/`, conservando la carpeta como en 001 (T117). Las capturas ya están copiadas en `specs/002-facturas/assets/`.

---

## Phase 10: Cambio tras la implementación — fecha de expedición libre (2026-09-29)

**Goal**: el responsable pone a cualquier factura la fecha que corresponda (se emiten a final de
semana o de mes). Solo quedan los límites que valida la AEAT (spec, Clarifications «cambio tras la
implementación»; FR-018).

**Independent Test**: se emite una factura con fecha anterior a la última de su serie y otra del año
anterior al pasado, se rectifica una con una fecha anterior a hoy, y se rechazan una futura, una
anterior al 28/10/2024 y una corrección anterior a su fecha de operación.

- [X] T080 [P] Tests `backend/tests/integration/test_emision.py` y `test_correcciones.py`:
  - Emitir con una fecha anterior a la última factura de la serie y con una de hace dos años → 201, con el número de la serie del año de esa fecha.
  - Futura (error 1112) y anterior al 28/10/2024 (error 1152) → 422 `fecha-expedicion`, también al emitir un borrador.
  - Modificar con `fecha_expedicion`: reemisión y rectificativa con fecha anterior a hoy → 201 con esa fecha; sin ella, la de hoy; anterior a la fecha de operación heredada (error 1146) → 422.
  - `GET /v1/facturas/parametros` devuelve `fecha_minima` = 28/10/2024.
- [X] T081 Backend: `check_fecha_expedicion` en `backend/app/services/emision.py` solo con los límites de la AEAT y el de la fecha de operación; `DatosModificacion.fecha_expedicion` y `ModificacionEntrada.fecha_expedicion` (opcional, por defecto hoy); `Parametros.fecha_minima` = 28/10/2024; retirar `repositories/facturas.last_fecha_in_serie` si queda sin uso.
- [X] T082 Web: fecha editable en «Modificar» (`CamposFactura` con mínimo propio y la fecha de la operación como ayuda) y envío de `fecha_expedicion`; tipos regenerados; tests de `FacturaModal.consulta.test.tsx` y E2E de correcciones con una fecha anterior a hoy.
- [X] T083 Documentación: quickstart (validación 3 bis) y puertas de calidad completas (backend, web y E2E).


---

## Phase 11: Ajuste de cierre — IVA libre, oro de inversión exento e IBAN (2026-09-30)

**Goal**: el responsable escribe el IVA por defecto que haya en cada momento (con aviso y
confirmación si no está en la lista de la AEAT), deja de ver la clave de régimen, añade el IBAN de
la joyería, que se copia en cada factura, y vende oro de inversión sin IVA con una casilla para toda
la factura (spec, Clarifications 2026-09-30; FR-001, FR-013, FR-016, FR-023, FR-033, FR-037,
FR-052, FR-053; research R-20 a R-23).

**Independent Test**:
- Configuración: se guarda 22 %, primero rechazado y después confirmado, y se vuelve a 21 %. Se
  guarda un IBAN válido y se rechaza uno erróneo.
- Se emite una factura de lingote «Sin IVA», con base = total y registro `04` + `E6`, y se
  rectifica a exenta una factura de lingote emitida con IVA.
- `verificar-cadena` da íntegra una cadena que mezcla facturas sujetas y exentas, incluidas las
  anteriores a la migración 0006 (SC-012, SC-013; quickstart 18 a 22).

**Fuentes**: solo research R-20 a R-23 y R-3, R-4, R-9 y R-10 actualizados (F-1, F-3, F-6 y F-11).
Nunca de memoria (constitución IV).

### Tests primero (deben fallar)

- [X] T084 [P] ⚖️ Tests de importes en `backend/tests/unit/domain/test_importes.py` (R-10, R-21):
  - Líneas con `tipo_iva=None` (exentas), p. ej. 1 × 7.450,00: un único desglose `tipo_iva=None`, base 7.450,00 y cuota 0,00, con total igual a la base.
  - Medio céntimo en el importe de una línea exenta (0,5 × 0,25 → 0,13).
  - Devolución total exenta: sin líneas y `tipo_iva_por_defecto=None` → un detalle exento a 0.
  - Los casos S1 existentes siguen dando lo mismo.
  - `allowed_rates` y `is_rate_allowed` quedan como información: hoy 0, 4, 10 y 21.
- [X] T085 [P] ⚖️ Tests del registro en `backend/tests/unit/domain/test_registro.py` (R-21):
  - El detalle exento es exactamente `{"ClaveRegimen": "04", "OperacionExenta": "E6", "BaseImponibleOimporteNoSujeto": "7450.00"}`, en ese orden y sin `CalificacionOperacion`, `TipoImpositivo` ni `CuotaRepercutida`.
  - `CuotaTotal` es `0.00` e `ImporteTotal` es la base.
  - **Regresión**: el `contenido` de un alta S1 es idéntico, clave a clave y en orden, al de antes del ajuste (fijado como literal en el test).
  - Adaptar el test de las líneas 118 a 124: `OperacionExenta` no aparece en un detalle S1.
  - `app/domain/exenciones.py` expone `04`, `E6` y la mención literal de FR-052.
- [X] T086 [P] Tests del IBAN en `backend/tests/unit/domain/test_iban.py`, en tabla (R-22):
  - Válidos: `ES9121000418450200051332` y `DE89370400440532013000`.
  - Se normalizan: `es91 2100 0418 4502 0005 1332` → `ES9121000418450200051332`.
  - Se rechazan, cada uno con su motivo: dígito de control erróneo (`…1333`), ES con 23 o 25 caracteres, ES con letras en la parte numérica, sin código de país, menos de 15 o más de 34 caracteres y caracteres no alfanuméricos.
- [X] T087 [P] [US1] Tests de integración en `backend/tests/integration/test_configuracion_facturacion.py` (R-20, R-22, R-23):
  - **IVA**:
    - 22 sin confirmar → 422 `tipo-iva-sin-confirmar` con `tipos_oficiales`, y no se guarda nada.
    - Con `confirmar_tipo_iva: true` → 200. La auditoría lleva el cambio y `tipo_iva_fuera_de_lista: true`.
    - Con 22 ya guardado, cambiar solo el emisor no pide confirmación. Pasar a 10 o a 21 tampoco.
    - `"100"`, `"22.555"` y el número JSON `22` → 422 `validacion`.
  - **Clave de régimen**: enviar `clave_regimen` → 422 (campo no admitido). La salida no la lleva y lleva `tipos_iva_oficiales`.
  - **IBAN**:
    - Uno válido con espacios y minúsculas se guarda normalizado.
    - Uno erróneo → 422 en `emisor.iban`.
    - Vacío → `null`, y no figura en `faltan`.
    - El cambio de IBAN queda en la auditoría.
  - Adaptar los tests que usaban `clave_regimen` y `tipo-iva-no-admitido` (líneas 59, 71 y 123 a 126).
- [X] T088 [P] [US2] Tests de integración en `backend/tests/integration/test_emision.py` (FR-052, FR-016, R-20, R-21):
  - **`POST /v1/facturas` con `oro_inversion: true`** → 201:
    - Salida: `oro_inversion: true`, `mencion_exencion` con el literal, líneas con `tipo_iva: null`, desglose `[{tipo_iva: null, base, cuota: "0.00"}]` e `importe_total` igual a la base.
    - En la BD: `facturas.clave_regimen = '04'` y un desglose con `clave_regimen='04'`, `operacion_exenta='E6'` y `calificacion_operacion` NULL.
    - El `contenido` del registro, con el detalle de T085.
  - **Sin la bandera**: `01`/`S1` como antes.
  - **IVA fuera de lista**: con el IVA de configuración a 5 o a 22, confirmado, se emite sin error. Sustituye el test de las líneas 228 a 237, que esperaba un rechazo por fecha.
  - **IBAN**: se copia en `facturas.emisor_iban` y sale en `emisor.iban`. Cambiarlo después no altera la factura. Sin IBAN, `null`.
  - **Parámetros**: `GET /v1/facturas/parametros` devuelve `mencion_exencion_oro_inversion`.
  - **Logs** (FR-051, R-22): ampliar `backend/tests/integration/test_logs_facturacion.py`. Tras guardar la configuración con IBAN y emitir una factura exenta, los logs no contienen el IBAN.
- [X] T089 [P] [US4] Tests de integración en `backend/tests/integration/test_borradores.py` (R-9, R-21):
  - Un borrador con `oro_inversion: true` tiene cuota prevista 0 y total igual a la base, y su salida lleva `oro_inversion` y `mencion_exencion`.
  - Editarlo cambia la bandera, y el diff de auditoría la incluye.
  - El `PUT` y la emisión del borrador sin `oro_inversion` → 422: es obligatoria en `BorradorEdicionEntrada`.
  - Al emitirlo, la factura es exenta.
  - Un borrador sin la bandera emite `01`/`S1`.
- [X] T090 [P] [US5] Tests de integración en `backend/tests/integration/test_correcciones.py` (R-4, R-9, R-21):
  - **Sujeta → exenta** (US5-9): «ya entregada», causa `devolucion_o_precio` y `oro_inversion: true` → REC R1 con `04`/`E6` y la base y cuota rectificadas de la original.
  - **Exenta → sujeta**: tipo de configuración y `01`/`S1`.
  - **Reemisión exenta**: `no_debio_emitirse` con la bandera.
  - **«Sin cambios»**:
    - Mismas líneas y cliente, solo con la bandera cambiada → se admite.
    - Exenta con las mismas líneas y la misma bandera → 422 `sin-cambios`.
  - **Devolución total exenta**: detalle exento a 0.
  - **Bandera obligatoria**: `ModificacionEntrada` sin `oro_inversion` → 422.
  - Adaptar el test de las líneas 469 a 495, sobre el tipo 7,5 validado contra la fecha heredada: ya no se revalida al emitir.
- [X] T091 [P] [US3] Tests de integración en `backend/tests/integration/test_listado_facturas.py`: `oro_inversion` en `FacturaResumenSalida`, tanto para borradores como para facturas exentas y sujetas (FR-033).
- [X] T092 [P] [US6] ⚖️ Tests de integración en `backend/tests/integration/test_cadena_registros.py` y `test_verificar_cadena.py` (FR-031, SC-013):
  - Una cadena que alterna facturas sujetas y exentas, con una rectificativa exenta y una anulación, sale íntegra.
  - Alterar, con `DISABLE TRIGGER USER` como en el resto, la base de un desglose exento, su `operacion_exenta` o el `tipo_iva` de una línea exenta → se detecta la factura o el registro.
- [X] T093 [P] Tests en BD en `backend/tests/integration/test_facturacion_inalterable.py` (data-model, «Migración 0006»):
  - La nueva `ck_desgloses_factura_calificacion` rechaza: exento con cuota > 0, exento con clave `01`, S1 con `E6`, S1 sin tipo, y detalle sin calificación ni exención.
  - `uq_desgloses_factura_tipo` impide dos detalles exentos en una factura.
  - `ck_configuracion_facturacion_iva` rechaza 100.
  - `UPDATE` y `DELETE` siguen bloqueados en `facturas`, `lineas_factura` y `desgloses_factura`, también sobre las columnas nuevas.
  - Adaptar las inserciones de `backend/tests/integration/facturacion_sql.py` y `facturacion_datos.py`: sin la clave en configuración, y con `orden` en el desglose.
- [X] T094 [P] Tests de la web en `joyeriablanco_web/src/` (ui-rutas, «IVA por defecto», «IBAN» y «Sin IVA»):
  - **Fixtures**: en `test/facturas.ts`, `oro_inversion`, `mencion_exencion`, `emisor.iban` y `tipos_iva_oficiales`.
  - **`features/configuracion/FacturacionPage.test.tsx`**:
    - Campo de IVA libre con «%», aviso mientras se escribe 22 y mensaje de fuera de rango.
    - Un 422 `tipo-iva-sin-confirmar` abre el diálogo. «Guardar igualmente» reenvía con `confirmar_tipo_iva: true`, y «Cancelar» no reenvía.
    - No hay clave de régimen, y el cuerpo del `PUT` no la lleva.
    - Campo IBAN, agrupado de cuatro en cuatro al salir del campo, con el error del servidor en el campo.
  - **`lib/dinero.test.ts`**: `calcularTotales` con tipo `null`, con cuota 0 y total igual a la base.
  - **`lib/facturacion.test.ts`**, nuevo: `formatearIban` agrupa de cuatro en cuatro y tolera espacios y minúsculas.
  - **`features/facturas/FacturaModal.test.tsx`**:
    - La casilla «Sin IVA (oro de inversión)» cambia la previsualización a «Base exenta 7.450,00 €», «IVA 0,00 €» y total 7.450,00 €, con la mención de los parámetros.
    - El `POST` lleva `oro_inversion: true`.
  - **`FacturaModal.borrador.test.tsx`**: carga la bandera, el `PUT` la envía y no hay aviso de cambio de IVA en un borrador exento.
  - **`FacturaModal.consulta.test.tsx`**:
    - Consulta de una exenta: la mención y el bloque «Pago» con el IBAN agrupado. Sin IBAN no hay bloque.
    - «Modificar» precarga la bandera de la original y el cuerpo la envía.
  - **`MotivoModificacionDialog.test.tsx`**: el aviso de IVA distinto solo aparece si la original y la corrección van con IVA.
  - **`FacturasPage.test.tsx`**: «Exenta» en la columna del IVA.

### Implementación

- [X] T095 Dominio puro (hace pasar T084 a T086):
  - **`backend/app/domain/exenciones.py`**: nuevo, con `CLAVE_REGIMEN_ORO_INVERSION = "04"` (L8A), `OPERACION_EXENTA_OTROS = "E6"` (L10) y `MENCION_EXENCION_ORO_INVERSION`, con el docstring de fuentes de R-21.
  - **`backend/app/domain/iban.py`**: nuevo, con `normalize_iban(texto) -> str` y `validate_iban(iban) -> str | None` (el motivo, como `validate_nif`). Sigue R-22.
  - **`backend/app/domain/importes.py`**:
    - `LineaCalculo.tipo_iva` y `DesgloseTipo.tipo_iva` pasan a `Decimal | None`, y `compute_totals(…, tipo_iva_por_defecto: Decimal | None)`. El grupo exento lleva cuota 0 y va después de los sujetos al ordenar.
    - El comentario de `TIPOS_IVA_S1` pasa a decir «informativa» (R-20).
  - **`backend/app/domain/registro.py`**:
    - `DetalleDesglose` (clave, calificación, exención, tipo, base y cuota) sustituye a `DatosAlta.clave_regimen` y a los `DesgloseTipo` del alta.
    - `_detalle` con la rama exenta.
    - Se actualiza el docstring de campos no informados.
  - **`backend/app/domain/tipos.py`**: se retira `CLAVES_REGIMEN_L8A` si queda sin uso y se mantiene `CLAVE_REGIMEN_GENERAL`.
- [X] T096 Migración y modelos (hace pasar T093):
  - **`backend/alembic/versions/0006_iva_libre_oro_iban.py`**: SQL a mano, solo DDL, en el orden de data-model («Migración 0006»), con el `downgrade` que nunca falla por los datos (bloque `DO`).
  - **Modelos**:
    - `backend/app/models/configuracion_facturacion.py`: sin `clave_regimen` y con `emisor_iban`.
    - `backend/app/models/factura.py`:
      - `LineaFactura.tipo_iva` opcional.
      - `DesgloseFactura`: PK `(factura_id, orden)`, `tipo_iva` y `calificacion_operacion` opcionales, y `operacion_exenta`.
      - `Factura.emisor_iban`, y la relación `desgloses` ordenada por `orden`.
    - `backend/app/models/borrador_factura.py`: `oro_inversion`.
  - Probar a mano `alembic downgrade 0005 && alembic upgrade head` sobre la BD de desarrollo con facturas.
- [X] T097 [US1] Configuración (hace pasar T087):
  - **`backend/app/core/errors.py`**: `TipoIvaSinConfirmar` (422 `tipo-iva-sin-confirmar`, con `tipos_oficiales`) sustituye a `TipoIvaNoAdmitido`.
  - **`backend/app/schemas/configuracion_facturacion.py`**:
    - `DatosEmisorEntrada.iban` (máximo 42) y `DatosEmisorSalida.iban`.
    - `ConfiguracionFacturacionEntrada.confirmar_tipo_iva: bool = False`, sin `clave_regimen`.
    - `ConfiguracionFacturacionSalida.tipos_iva_oficiales`, sin `clave_regimen`.
    - `ParametrosFacturacionSalida.mencion_exencion_oro_inversion`.
  - **`backend/app/services/configuracion_facturacion.py`**:
    - `_normalizar` con el IBAN y la regla de confirmación de R-20, que solo aplica si el tipo cambia.
    - `CAMPOS_AUDITADOS` sin la clave y con `emisor_iban`.
    - La marca `tipo_iva_fuera_de_lista` en el detalle de auditoría.
    - `get_parametros` con la mención.
  - **`backend/app/api/v1/configuracion.py`**: la correspondencia de la salida.
- [X] T098 [US2] Emisión (hace pasar T088):
  - **`backend/app/services/emision.py`**:
    - `DatosFactura.oro_inversion`, y `create_factura(…, oro_inversion)` con `tipo_iva=None` si es exenta.
    - `facturas.clave_regimen` y la del desglose: `01` o `04`. El desglose con `orden`, y S1 o `E6`.
    - `emisor_iban` copiado.
    - Se retira `is_rate_allowed` y `TipoIvaNoAdmitido`.
    - `_tipo_iva_de` pasa a devolver el tratamiento (`Decimal | None`).
  - **`backend/app/services/cadena.py`**: `datos_alta` construye los `DetalleDesglose` desde las filas de `desgloses_factura` (R-21).
  - **`backend/app/schemas/factura.py`**:
    - `FacturaEntrada.oro_inversion: bool = False`.
    - `ModificacionEntrada.oro_inversion: bool`, obligatorio.
    - `tipo_iva` opcional en `LineaSalida` y `DesgloseSalida`.
    - `FacturaSalida.oro_inversion` y `mencion_exencion`.
    - `FacturaResumenSalida.oro_inversion`.
  - **`backend/app/api/v1/facturas.py`**: la serialización. `oro_inversion` es `clave_regimen == CLAVE_REGIMEN_ORO_INVERSION`, y la mención y el IBAN van en el emisor.
  - **`backend/app/repositories/facturas.py`**: el listado lee la columna `oro_inversion` de la vista.
- [X] T099 [US4] Borradores (hace pasar T089):
  - `backend/app/services/borradores.py`:
    - `DatosBorrador.oro_inversion`.
    - `_previstos(lineas, tipo | None)`.
    - `_contenido` y `_contenido_nuevo` con la bandera.
    - `_aplicar`.
    - La emisión del borrador pasa la bandera.
  - `backend/app/schemas/borrador.py`:
    - `BorradorEntrada.oro_inversion: bool = False`, solo al crear.
    - `BorradorEdicionEntrada.oro_inversion: bool`, obligatorio (R-21).
    - `BorradorSalida.oro_inversion` y `mencion_exencion`.
  - `backend/app/api/v1/borradores.py`: la correspondencia.
- [X] T100 [US5] Correcciones (hace pasar T090):
  - En `backend/app/services/emision.py`:
    - `DatosModificacion.oro_inversion`.
    - `modify_factura` pasa la bandera a `create_factura`.
    - `_sin_cambios` compara el tratamiento: exenta, o sujeta y a qué tipo.
  - En `backend/app/api/v1/facturas.py`: la correspondencia de `ModificacionEntrada`.
- [X] T101 [US6] Integridad (hace pasar T092), en `backend/app/services/integridad.py`:
  - `_problema_de_totales` con líneas de `tipo_iva` NULL.
  - Coherencia: todas las líneas sin tipo si y solo si `clave_regimen = '04'`, con un único detalle exento.
  - El `tipo_iva_por_defecto` sale del desglose guardado.
- [X] T102 [P] Datos de ejemplo en `backend/app/services/datos_ejemplo.py` (R-16):
  - Configuración demo sin clave y con el IBAN `ES9121000418450200051332`.
  - Al menos dos facturas de oro de inversión exentas («Lingote de oro 50 g», «Moneda de oro Krugerrand 1 oz») y un borrador exento.
  - Adaptar `backend/tests/integration/test_datos_ejemplo.py` si cuenta tipos.
- [X] T103 Contrato y tipos:
  - Pasar `backend/tests/integration/test_contrato_openapi.py`: no hay operaciones nuevas.
  - Regenerar con `uv --directory backend run joyeria exportar-openapi` (actualiza `joyeriablanco_web/src/api/openapi.json`) y `npm run gen:api` en `joyeriablanco_web/` (`src/api/schema.gen.ts`).
  - Revisar los alias de `joyeriablanco_web/src/api/tipos.ts`.
- [X] T104 [US1] Web de configuración (hace pasar su parte de T094):
  - **`joyeriablanco_web/src/features/configuracion/FacturacionPage.tsx`**:
    - IVA con `CampoDecimal` y sufijo «%», validado con zod de 0 a 99,99.
    - Aviso contra `tipos_iva_oficiales` mientras se escribe.
    - Diálogo de confirmación con `ConfirmDialog` ante el 422 `tipo-iva-sin-confirmar`, que reenvía con `confirmar_tipo_iva`.
    - Se retira el `Select` de clave.
    - Campo IBAN en «Datos del emisor», con `CAMPO_DEL_SERVIDOR['emisor.iban']`, `valoresIniciales` y `aCuerpo`.
  - **`joyeriablanco_web/src/lib/facturacion.ts`**: se retira `CLAVES_REGIMEN` y se añade `formatearIban`, que agrupa de 4 en 4 y cuyo test está en T094.
  - **`joyeriablanco_web/src/api/queries/configuracionFacturacion.ts`**: si hace falta, la confirmación en la mutación.
- [X] T105 [US2] Web del modal (hace pasar su parte de T094):
  - **`joyeriablanco_web/src/lib/dinero.ts`**: `calcularTotales(lineas, tipo: bigint | null)`.
  - **`joyeriablanco_web/src/features/facturas/factura-valores.ts`**: `oro_inversion` en el esquema zod, en los valores iniciales de nueva, borrador y modificar, y en los cuerpos.
  - **`CamposFactura.tsx`**: `Casilla` «Sin IVA (oro de inversión)» antes de los totales, con el orden de foco de ui-rutas y a ancho completo en móvil.
  - **`TotalesFactura.tsx`**: «Base exenta», «IVA 0,00 €» y la mención de `parametros.mencion_exencion_oro_inversion`, en `body-sm` `on-surface-variant`.
  - **`FacturaModal.tsx`**: `AvisoCambioIva` solo en borradores sujetos.
  - **`ModificarFacturaModal.tsx` y `MotivoModificacionDialog.tsx`**: se precarga la bandera, y el aviso de IVA distinto solo sale si las dos van con IVA.
  - **`lib/facturacion.ts`**: `tipoIvaDe` devuelve `null` si es exenta.
- [X] T106 [US3] Web de la consulta y el listado (hace pasar su parte de T094):
  - **`joyeriablanco_web/src/features/facturas/FacturaConsulta.tsx`**:
    - La mención junto a los totales si `mencion_exencion` no es `null`.
    - El bloque «Pago» con el IBAN agrupado si `emisor.iban` no es `null` (FR-053, ui-rutas).
    - Los totales con «Base exenta».
  - **`TablaFacturas.tsx`**: «Exenta» en la columna del IVA si `oro_inversion`. Las tarjetas de móvil no cambian.
- [X] T107 E2E en `joyeriablanco_web/e2e/`:
  - **`configuracion-facturacion.spec.ts`**:
    - IVA: 22 → aviso → diálogo → confirmar → guardado → vuelta a 21 sin diálogo. Ya no se usan las opciones del `Select`.
    - IBAN: uno erróneo y otro válido, agrupado.
  - **`facturas.spec.ts`**:
    - Nueva factura de lingote «Sin IVA», con la previsualización, la emisión, la consulta con la mención y el IBAN, y el listado con «Exenta».
    - Rectificación a exenta de una factura de lingote con IVA (US5-9).
  - **`teclado.spec.ts`**: orden de foco con la casilla.
  - **`responsive.spec.ts`**: modal con la casilla marcada a 360 px, sin desplazamiento horizontal.
- [X] T108 Documentación:
  - `specs/002-facturas/quickstart.md`: validaciones 18 a 22 con su resultado, y la tabla «Resultado de la validación» ampliada.
  - `README.md`, si describe la configuración de facturación: IVA libre, IBAN y oro de inversión.
  - Marcar T084 a T108 en este `tasks.md`.
- [X] T109 Puertas de calidad y verificación final:
  - Backend: `uv run ruff check . && uv run ruff format --check . && uv run mypy . && uv run pytest`. Incluye los tests ⚖️ de numeración bajo concurrencia, que no cambian.
  - Web: `npm run lint && npm run typecheck && npm run test && npm run build && npm run check:tokens` y `npx playwright test`.
  - A mano en desarrollo (quickstart 22): con datos anteriores al ajuste, `alembic upgrade head`, `joyeria verificar-cadena` íntegra, emitir las facturas de los pasos 20 y 21, y `verificar-cadena` íntegra otra vez.
  - Revisión de conformidad con DESIGN.md (SC-009).

**Checkpoint**: ajuste de cierre completo, con todos los tests en verde.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (F1)**: sin dependencias.
- **Foundational (F2)**: depende de F1 y bloquea todas las historias. T019 depende de T018, que depende de T003. T021 depende de T012, T014 y T020.
- **US1 (F3)**: depende de F2.
- **US2 (F4)**: depende de US1, porque emitir exige la configuración. Es el **MVP de negocio**.
- **US3 (F5)**: depende de US2, que aporta la ruta `/facturas`, las facturas y los datos de ejemplo.
- **US4 (F6)**: depende de US2 (`emision.emit_factura`) y de US3 (acción de fila del listado).
- **US5 (F7)**: depende de US2. Sus marcas en el listado dependen de US3.
- **US6 (F8)**: depende de F2. Tiene más sentido con US5, por las anulaciones en la cadena.
- **Polish (F9)**: depende de todas.
- **Cambio (F10)**: depende de F9.
- **Ajuste de cierre (F11)**: depende de F10.
  - Orden: tests T084–T094 → T095 (dominio) → T096 (migración y modelos) → T097 a T101 (servicios, API e integridad) → T102 y T103 → web T104 a T106 → T107 → T108 y T109.
  - Los tests T084–T094 van en paralelo, y T102 en paralelo con T104–T106.

### Within Each User Story

- Los tests se escriben primero y deben fallar.
- El orden es: dominio → modelos y migración → repositorios → servicios → esquemas y routers →
  tipos generados → web → E2E.
- Cada tarea de API vacía su parte de `PENDIENTES_002` y deja el test de contrato en verde.
- Se hace un commit atómico al cerrar cada grupo lógico de tareas. **Una fase no se cierra sin sus
  tests en verde.**

### Parallel Opportunities

- **F2**:
  - Tests T004–T008 en paralelo.
  - T011, T012, T013, T015, T016 y T017 en paralelo.
  - Web T022–T027 en paralelo con todo el backend.
- **US1**: T028 y T029 en paralelo; T031 en paralelo con T030.
- **US2**: T035–T038 en paralelo; T042 en paralelo con T039–T041.
- **US3**: T051 y T052 en paralelo.
- **US4**: T057 y T058 en paralelo.
- **US5**: T063 y T064 en paralelo.
- **US6**: T071 puede escribirse en cuanto exista F2.
- **Polish**: T073, T074 y T075 en paralelo.

---

## Parallel Example: Foundational

```bash
# Tests obligatorios y de dominio (en paralelo):
Task: "T004 ⚖️ test_importes.py"
Task: "T005 ⚖️ test_huella.py (vectores F-2)"
Task: "T006 test_numeracion.py"
Task: "T007 test_registro.py"
Task: "T008 test_importes (esquemas)"

# Dominio puro (en paralelo):
Task: "T011 domain/importes.py"
Task: "T012 domain/huella.py"
Task: "T013 domain/numeracion.py"
Task: "T015 schemas/importes.py"

# Web compartida (en paralelo con el backend):
Task: "T022/T023 lib/dinero.ts"
Task: "T024 ModalDocumento"
Task: "T025 CampoDecimal"
Task: "T027 lib/idempotencia.ts"
```

---

## Implementation Strategy

### MVP First

1. F1 Setup → F2 Foundational, con los tests obligatorios en verde.
2. F3 US1 (configuración) → F4 US2 (emisión) → **validar**: se emiten facturas válidas, numeradas y
   encadenadas.
3. F5 US3 (listado): primer uso diario completo.

### Incremental Delivery

1. F1 + F2: dominio fiscal y garantías de la BD.
2. US1 + US2: emitir (MVP de negocio).
3. US3: listado.
4. US4: borradores.
5. US5: correcciones trazables.
6. US6: integridad.
7. Polish y cierre, con todo en verde.

---

## Notes

- [P] = ficheros distintos y sin dependencias pendientes.
- Si durante la implementación algo contradice la spec, **se para y se corrige la spec primero**
  (constitución, principio I).
- **Constitución VII**: aplican los tests de numeración (T036), importes (T004) y huellas (T005 y
  T010), marcados con ⚖️. La conversión de presupuesto a factura llega en la 005.
- Cualquier dato fiscal (campos, listas, formatos o tolerancias) que no esté en research se
  **investiga en fuente oficial y se añade a research antes de implementarlo**. Nunca se deduce.
