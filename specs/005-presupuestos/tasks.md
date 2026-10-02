---
description: "Tareas de implementación de la feature 005"
---

# Tasks: Presupuestos con conversión en factura

**Input**: `specs/005-presupuestos/`:
- [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md) y [data-model.md](data-model.md).
- [contracts/openapi.yaml](contracts/openapi.yaml), [contracts/ui-rutas.md](contracts/ui-rutas.md)
  y [contracts/documentos-pdf.md](contracts/documentos-pdf.md).
- [quickstart.md](quickstart.md).

**Prerequisites**: todo en la rama `005-presupuestos`, sobre `main` con 003 fusionada:
- Constitución 2.3.0.
- Spec con clarify y su refinamiento tras las checklists.
- Plan con research F-4, F-6 y F-13, data-model y contratos.
- DESIGN.md 1.3.
- Checklists.

**Tests**: SÍ, con TDD como en 001 a 003. En cada historia, los tests se escriben primero y deben
fallar. Esta feature toca los **cuatro tests obligatorios** de la constitución VII, y sus tareas
van marcadas con ⚖️:
- La numeración PRE bajo concurrencia.
- Los importes del presupuesto y de la factura convertida.
- El encadenamiento con conversiones.
- La conversión presupuesto → factura.

**Organization**: por historias de usuario, después de una fase fundacional que generaliza sin
cambiar el comportamiento:

```text
US1 (borrador, emisión, consulta y listado; P1, MVP)
 ├── US2 (PDF; P1)
 └── US3 (conversión; P1) → US4 (modificar y anular; P2) → US5 (listado impreso y datos de ejemplo; P3)
```

## Format: `[ID] [P?] [Story] Description`

- **[P]**: puede ir en paralelo (ficheros distintos y sin dependencias pendientes).
- **[Story]**: historia de la spec (US1–US5).
- Las rutas son relativas a la raíz del repositorio.

## Path Conventions

- **Backend**: `backend/app/…`, `backend/tests/…` y `backend/alembic/versions/…`.
- **Web**: `joyeriablanco_web/src/…` y `joyeriablanco_web/e2e/…`.
- **Reglas**: solo las de la spec, research R-1 a R-14 y data-model. Un presupuesto NUNCA genera
  registro, huella ni QR (FR-005, constitución 2.3.0).
- **Diseño**: solo tokens de `docs/DESIGN.md` 1.3. `check:tokens` y `test_tokens_papel.py`
  siguen vigentes.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: dejar el test de contrato preparado para 005 y los tipos de dominio que usa todo lo
demás.

- [ ] T001 Test de contrato para 005 (002 R-14) en `backend/tests/integration/test_contrato_openapi.py`:
  - Lista `PENDIENTES_005` con las 14 operaciones de [contracts/openapi.yaml](contracts/openapi.yaml), excluidas solo del sentido «contrato → API».
  - `test_hay_un_contrato_por_feature` incluye `005-presupuestos`: la lista esperada pasa a los cuatro primeros contratos.
  - Hoy el test está en rojo en la rama, porque ya recoge el contrato de 005 sin implementación. Ejecutarlo y dejarlo en verde. Las tareas T030, T041, T052, T060 y T067 vacían la lista, y T078 la elimina.
- [ ] T002 [P] Tipos de dominio (research R-3, R-4) en `backend/app/domain/tipos.py`:
  - `Serie.PRESUPUESTO = "PRE"`.
  - `EstadoPresupuesto`: `borrador`, `pendiente`, `caducado`, `en_facturacion`, `convertido`, `sustituido` y `anulado`.
  - `TipoCierrePresupuesto`: `anulacion`, `sustitucion` y `conversion`.
  - `TipoEvento`: `BORRADOR_PRESUPUESTO_CREADO`, `BORRADOR_PRESUPUESTO_EDITADO`, `BORRADOR_PRESUPUESTO_ELIMINADO`, `PRESUPUESTO_EMITIDO`, `PRESUPUESTO_MODIFICADO`, `PRESUPUESTO_ANULADO` y `PRESUPUESTO_CONVERTIDO`.
  - Comprobar con `grep` que ningún `CHECK` de migración usa `sql_in(Serie)`, de modo que ampliar la enumeración no altera la 0005.

**Checkpoint**: test de contrato en verde y tipos disponibles.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**:
- La migración 0008 y los modelos.
- La lógica pura de presupuestos.
- La configuración de validez y pie.
- La **generalización sin cambio de comportamiento** de líneas, listado, PDF y componentes web
  (research R-8 y R-13).

**⚠️ CRITICAL**: ninguna historia empieza antes de cerrar esta fase, y las suites de 002 y 003
deben quedar en verde (T020).

### Tests ⚠️ (escribir primero, deben fallar)

- [ ] T003 [P] Test `backend/tests/unit/domain/test_presupuestos.py` (R-3, FR-001, FR-009):
  - `validez_por_defecto(fecha, dias)`: suma días, incluido el cambio de mes y de año.
  - `estado_visible(estado, valido_hasta, hoy)`:
    - `pendiente` con `valido_hasta < hoy` → `caducado`.
    - `valido_hasta == hoy` → `pendiente`.
    - `en_facturacion` no se convierte en `caducado`.
    - Los terminales no cambian.
- [ ] T004 [P] Ampliar `backend/tests/unit/domain/test_numeracion.py` (R-4, FR-002):
  - `format_num_serie(Serie.PRESUPUESTO, 2026, 3) == "PRE-2026-0003"`.
  - `parse_num_serie("PRE-2026-0003")` funciona.
  - `PRE-2026-12345` crece en cifras.
  - Los casos FAC y REC siguen igual.
- [ ] T005 [P] Test `backend/tests/integration/test_presupuestos_inalterables.py` (R-2, R-6, FR-004, SC-006), con `conexion` y `conexion_owner` e inserciones SQL crudas en un nuevo `backend/tests/integration/presupuestos_sql.py`:
  - **Solo inserción**: UPDATE, DELETE y TRUNCATE en `presupuestos`, `lineas_presupuesto`, `desgloses_presupuesto` y `cierres_presupuesto` fallan con 42501 para `jb_app` y por trigger para `jb_owner`, con el mensaje «Los presupuestos emitidos son inalterables».
  - **Contador**: `contadores_factura` acepta la serie `PRE`, pero no otra, y la fila PRE solo sube.
  - **Cierres**: `uq_cierres_presupuesto_presupuesto_id` impide un segundo cierre. El `CHECK` por tipo rechaza las combinaciones no válidas de data-model.
  - **Trigger `cierres_presupuesto_validar`**: rechaza la anulación y la sustitución con un borrador de factura vinculado, con la restricción `tg_cierres_presupuesto_en_facturacion`.
  - **Trigger `borradores_factura_validar_vinculo`**: rechaza el vínculo con un presupuesto cerrado (`tg_borradores_factura_presupuesto_cerrado`). `uq_borradores_factura_presupuesto_id` impide dos borradores.
  - **`estado_presupuesto()`**: devuelve `pendiente`, `en_facturacion`, `convertido`, `sustituido` y `anulado` en los casos de data-model.
  - **Vista**: `v_listado_presupuestos` tiene las columnas de data-model.
  - **Migración**: la ida y vuelta (`downgrade base` y `upgrade head`) ya la hace `_esquema_limpio` de `tests/conftest.py` al empezar cada sesión, así que este test no la repite.

### Implementación

- [ ] T006 Migración `backend/alembic/versions/0008_presupuestos.py` (data-model completo), en SQL a mano y con el patrón de la 0005, **en este orden** (las funciones `LANGUAGE sql` se validan al crearlas):
  1. **Función** `impedir_modificacion_presupuesto()`.
  2. **Tablas nuevas**:
     - `borradores_presupuesto` y `lineas_borrador_presupuesto`.
     - `presupuestos`, `lineas_presupuesto`, `desgloses_presupuesto` y `cierres_presupuesto`, con sus `CHECK` e índices.
  3. **DDL sobre 002**:
     - `borradores_factura.presupuesto_id`, con su FK y su `UNIQUE`.
     - `ck_contadores_factura_serie` con `PRE`.
     - `configuracion_facturacion.validez_presupuesto_dias` y `pie_presupuesto`, con `ck_config_contacto_sin_vacios` rehecho.
     - `ck_eventos_auditoria_tipo` con `_TIPOS_0008`.
  4. **Funciones**: `estado_presupuesto()`, `validar_cierre_presupuesto()` y `validar_vinculo_presupuesto()`. Los triggers lanzan `check_violation` con `USING CONSTRAINT` (R-6).
  5. **Vista** `v_listado_presupuestos`.
  6. **Triggers**:
     - `cierres_presupuesto_validar` y `borradores_factura_validar_vinculo`.
     - Los de solo inserción y el REVOKE de las cuatro tablas, que van en un `_TABLAS_INALTERABLES` propio.
  7. **`downgrade`**: completo y en el orden inverso, con los `CHECK` de 002 restaurados `NOT VALID`.
- [ ] T007 [P] Modelos ORM (data-model, «Modelos ORM»):
  - `backend/app/models/presupuesto.py`: `Presupuesto`, `LineaPresupuesto` y `DesglosePresupuesto`.
  - `backend/app/models/borrador_presupuesto.py`: `BorradorPresupuesto` y `LineaBorradorPresupuesto`, con `version_id_col`.
  - `backend/app/models/cierre_presupuesto.py`: `CierrePresupuesto`.
  - Ampliaciones:
    - `backend/app/models/borrador_factura.py`: `presupuesto_id` y `presupuesto`, con `lazy="joined"`.
    - `backend/app/models/configuracion_facturacion.py`: las dos columnas.
  - Registro en `backend/app/models/__init__.py`.
  - `models/evento_auditoria.py` sigue alineado vía `sql_in(TipoEvento)`.
- [ ] T008 [P] Lógica pura:
  - `backend/app/domain/presupuestos.py`: `validez_por_defecto` y `estado_visible`.
  - `backend/app/domain/numeracion.py`: `_FORMATO = (FAC|REC|PRE)` y mensajes «Número de documento…».
  - Hacen pasar T003 y T004.
- [ ] T009 Configuración de validez y pie (FR-031, R-9, data-model):
  - `backend/app/schemas/configuracion_facturacion.py`: `validez_presupuesto_dias` (1 a 365) y `pie_presupuesto` (600, opcionales en la entrada) en `ConfiguracionFacturacionEntrada` y `ConfiguracionFacturacionSalida`.
  - `backend/app/services/configuracion_facturacion.py`:
    - Los dos campos en `CAMPOS_AUDITADOS`.
    - Normalización del pie con `domain/contacto.normalize_pie`.
    - Se conservan si no vienen.
  - Test `backend/tests/integration/test_configuracion_presupuestos.py`: validación, auditoría con el valor anterior y el nuevo, conservación por omisión, conflicto de versión y 403 para un empleado.
  - Actualizar en el mismo commit el contrato de 002, ya ampliado en el plan, si hiciera falta algún matiz.
- [ ] T010 Generalización del contenido (R-8.1), sin cambio de comportamiento:
  - Nuevo `backend/app/services/contenido.py` con `DatosLinea`, `check_lineas`, `normalize_lineas`, `previstos`, `copia_emisor(config)` y `copia_destinatario(cliente)`.
  - `backend/app/services/emision.py` y `backend/app/services/borradores.py` pasan a usarlo. `emision.py` reexporta `DatosLinea`.
  - Comprobar `uv run pytest tests/integration/test_emision.py tests/integration/test_borradores.py tests/integration/test_numeracion_concurrencia.py` en verde.
- [ ] T011 Generalización del listado (R-8.2), sin cambio de comportamiento:
  - Nuevo `backend/app/repositories/listado.py`: `filtros(v, *, q, anio, mes)`, `ordenes(v)` y `consulta_filas(v, columnas, condiciones, orden)`, parametrizados con un `table()`.
  - `backend/app/repositories/facturas.py` los usa con `v_listado_facturas`.
  - Comprobar `test_listado_facturas.py` y `test_pdf_listado.py` en verde.
- [ ] T012 Generalización de la impresión (R-8.3, R-8.4), sin cambio de comportamiento:
  - Nuevo `backend/app/services/impresion_comun.py`:
    - `DocumentoPdf`, `ParteImpresa`, `ContactoImpreso`, `LineaImpresa` y `DesgloseImpreso`.
    - `domicilio`, `contacto`, `lineas_impresas` y `desglose_impreso`.
    - `emisor` y `destinatario`, con el `Protocol` `CopiaPartes`.
  - `backend/app/services/impresion.py` lo usa.
  - Nuevo `backend/app/resources/pdf/_documento.html` con las macros de la cabecera del emisor, el cliente, la tabla de líneas, los totales, el pago y el pie. `factura.html` las usa y conserva el QR.
  - `backend/app/resources/pdf/papel.css`: `@page documento` y `.numero-documento`, con `body.doc-factura` y `body.doc-presupuesto` sobre esa página.
  - `listado.html`: los textos de 003 pasan a `l.textos` (`ListadoImpreso.textos`).
  - `backend/app/core/pdf/respuestas.py`: `_mensaje` según el documento de la ruta.
  - Comprobar `test_pdf_factura.py`, `test_pdf_listado.py`, `test_pdf_render.py` y `test_tokens_papel.py` en verde, con el texto extraído idéntico al anterior.
- [ ] T013 Ayudantes de prueba del backend:
  - `backend/tests/integration/facturacion_datos.py`: `configurar_facturacion` con validez, `cuerpo_presupuesto(...)`, `emitir_presupuesto(client, csrf, ...)` y `crear_borrador_presupuesto(...)`.
  - `limpiar_facturacion_confirmada`: sustituir el *slice* por índice por una lista explícita, en este orden por las FK:
    1. `cierres_presupuesto`.
    2. `correcciones_factura`, `registros_facturacion`, `desgloses_factura`, `lineas_factura` y `facturas`.
    3. `borradores_factura`.
    4. `desgloses_presupuesto`, `lineas_presupuesto` y `presupuestos`.
    5. `borradores_presupuesto`.
    6. `contadores_factura`.

    Desactivar los triggers de las tablas que los tengan (`_TABLAS_CON_TRIGGERS`, con las nuevas).
  - Restablecer también `validez_presupuesto_dias` y `pie_presupuesto` de la configuración.
- [ ] T014 Generalización web (R-13), sin cambio de comportamiento:
  - Nuevo `joyeriablanco_web/src/features/documentos/` con lo que hoy está en `src/features/facturas/` y no es propio de la factura:
    - `LineasDocumento.tsx` (antes `LineasFactura`, tipado con `Control<{ lineas: ValorLinea[] }>`).
    - `TotalesDocumento.tsx`, `SelectorCliente.tsx` y `ResumenCliente.tsx` (aviso por props).
    - `CargandoModal.tsx`, `AvisoCambioIva.tsx` y `EnlaceImprimir.tsx`.
    - `documento-valores.ts`.
    - `FiltrosDocumentos.tsx` (placeholder y `aria-label` por props).
    - `TablaDocumentos.tsx` (celdas de número y acción por props, mismos anchos).
    - `CamposDocumento.tsx`.
    - `ImprimirListado.tsx` (+ test): el documento, los textos y la URL por props.
  - El esquema zod de búsqueda, hoy local en `src/routes/_app/facturas.tsx`, pasa a `src/lib/filtros-documentos.ts`.
  - `src/features/facturas/*` y `routes/_app/facturas.tsx` los importan.
  - Comprobar `npm run test`, `npm run typecheck` y `npm run check:tokens` en verde, y los E2E de facturas sin cambios.
- [ ] T015 `joyeriablanco_web/src/lib/impresion.ts` (+ `.test.ts`), después de T014, porque toca los mismos usos:
  - La base por tipo de documento: `urlPdfFactura` igual que hoy, `urlPdfPresupuesto(id, { iban })` y `urlPdfListado('facturas' | 'presupuestos', filtros)`.
  - Las llamadas de facturas, actualizadas.
- [ ] T016 [P] Ayudantes de prueba de la web:
  - `joyeriablanco_web/src/test/presupuestos.ts`: `PARAMETROS_PRESUPUESTO`, `crearPresupuesto(estado, …)` y `conPresupuestos`.
  - `joyeriablanco_web/e2e/helpers/presupuestos.ts`: `emitirPresupuestoPorLaApi`.
- [ ] T017 Regenerar los tipos: `uv --directory backend run joyeria exportar-openapi && npm --prefix joyeriablanco_web run gen:api`. Ajustar los usos de la configuración ampliada.
- [ ] T018 [P] `joyeriablanco_web/src/features/auditoria/tipos-evento.ts`: textos de los siete eventos nuevos. El `Record<TipoEvento,…>` obliga a añadirlos tras regenerar los tipos (T017).
- [ ] T019 [P] Configuración en la web (FR-031), en `joyeriablanco_web/src/features/configuracion/FacturacionPage.tsx` (+ test):
  - «Validez de los presupuestos (días)», un número de 1 a 365.
  - «Pie de presupuesto», multilínea con contador «n / 600» y la ayuda «Si está vacío, se imprime el pie de factura».
  - Se envían siempre, como el pie de factura de 003.
  - Ampliar `e2e/configuracion-facturacion.spec.ts`.
- [ ] T020 Puerta de la fase:
  - Backend: `uv run pytest`, `uv run ruff check . && uv run ruff format --check . && uv run mypy .`.
  - Web: `npm run lint && npm run typecheck && npm run test && npm run check:tokens`, y `npx playwright test e2e/facturas*.spec.ts e2e/impresion.spec.ts e2e/configuracion-facturacion.spec.ts`.
  - Todo en verde. **Si algo de 002 o 003 cambia de comportamiento, se para y se corrige la generalización** (constitución I).

**Checkpoint**: 0008 aplicada y protegida, generalización sin regresiones, y configuración
ampliada.

---

## Phase 3: User Story 1 - Crear, emitir y consultar presupuestos (Priority: P1) 🎯 MVP

**Goal**: «Presupuestos» en el menú, con su listado, su modal de borrador y emisión con número
`PRE`, y la consulta del presupuesto emitido.

**Independent Test**:
- Se crea, se edita y se emite un presupuesto. Recibe el siguiente PRE, sus importes los calcula
  el servidor, no hay ningún registro de facturación ni cambio en el contador FAC, y ya no se
  puede editar.
- Aparece en el listado con su marca de caducidad cuando procede.

### Tests for User Story 1 ⚠️

- [ ] T021 [P] [US1] Test `backend/tests/integration/test_presupuestos_borradores.py` (FR-012, FR-013, FR-034):
  - Crear incompleto, sin cliente o sin líneas.
  - Editar con versión y conflicto 409.
  - Cliente desactivado ya elegido que se conserva.
  - Borrar: definitivo y sin consumir número.
  - Auditoría: `borrador_presupuesto_creado`, `borrador_presupuesto_editado` (con su *diff*) y `borrador_presupuesto_eliminado`.
  - `valido_hasta < fecha` → 422 en el campo.
  - Fecha futura o anterior al 28/10/2024 → 422 en el campo.
- [ ] T022 [P] [US1] ⚖️ Test `backend/tests/integration/test_presupuestos_emision.py` (FR-002 a FR-011, FR-014, FR-028, SC-004):
  - **Emisión directa y desde borrador**: número `PRE-AAAA-0001` y siguientes. El borrador desaparece.
  - **Importes**: calculados con `compute_totals`, con medio céntimo, oro de inversión (cuota 0 y mención) y límites. Un total enviado → 422.
  - **Copias**: del emisor (IBAN incluido) y del destinatario. Editar la ficha después no cambia el presupuesto.
  - **Sin efectos fiscales**: ningún registro, el contador FAC igual y `verificar-cadena` sin cambios.
  - **Requisitos**:
    - Sin los datos del emisor → 409 `emision-no-disponible`, pero sin la modalidad se emite.
    - Cliente inactivo → 422 `cliente-no-facturable`.
    - Cliente sin domicilio → se emite con el domicilio a NULL.
    - Fecha futura, anterior al 28/10/2024, o validez anterior a la fecha → 422 en el campo.
  - **Idempotencia**: repetir con la misma clave → 200 y el mismo presupuesto. La clave en otra operación (también una de `anular`) → 409 `idempotencia-conflicto`.
  - **Sin ajuste de PRE** (FR-003): `POST /v1/configuracion/facturacion/contador` solo mueve la serie FAC, y el contador PRE no cambia.
  - **Auditoría**: `presupuesto_emitido`.
- [ ] T023 [P] [US1] ⚖️ Test `backend/tests/integration/test_numeracion_presupuestos.py` (FR-002, FR-003, SC-002), con commit real y `limpiar_facturacion_confirmada`, como `test_numeracion_concurrencia.py`:
  - 10 sesiones × 20 emisiones dan PRE 1 a 200, sin huecos ni duplicados.
  - Con emisiones FAC simultáneas, las dos series son correlativas e independientes.
  - Una emisión que falla no consume número.
  - La misma `Idempotency-Key` en paralelo da un solo presupuesto.
  - Con fecha del año siguiente, PRE del año siguiente desde 0001.
- [ ] T024 [P] [US1] Test `backend/tests/integration/test_listado_presupuestos.py` (FR-023 a FR-025):
  - Búsqueda sin tildes por número, cliente e identificación.
  - Año (por defecto el actual, o «todos») y mes.
  - Los cuatro órdenes, con desempate y sin duplicar ni omitir al paginar.
  - Borradores con el cliente de la ficha.
  - Estados y caducidad con `hoy` simulado (monkeypatch de `hoy()`).
  - 25 por página por defecto y 100 como máximo.
- [ ] T025 [P] [US1] Ampliar `backend/tests/integration/test_clientes_ciclo_vida.py` (FR-033): un cliente con solo un borrador de presupuesto, o con un presupuesto emitido, → 409 `cliente-con-documentos`.
- [ ] T026 [P] [US1] Tests web:
  - `joyeriablanco_web/src/features/presupuestos/PresupuestosPage.test.tsx`: listado, marcas con su tono y su texto, estados vacíos de FR-023, filtros en la URL y acciones con nombre accesible.
  - `PresupuestoModal.test.tsx`: nuevo, guardar borrador, emitir con confirmación, validez propuesta y recalculada, error de validez en el campo, aviso del cliente sin domicilio y que nunca se envían totales.
  - `PresupuestoModal.borrador.test.tsx`: editar, conflicto, descartar y eliminar.
  - `PresupuestoConsulta.test.tsx`: datos, validez y botones según el estado y el rol, sin conversión todavía.
  - `joyeriablanco_web/src/components/layout/Sidebar.test.tsx`: «Presupuestos» activo y sin «Próximamente».

### Implementation for User Story 1

- [ ] T027 [P] [US1] Repositorios:
  - `backend/app/repositories/borradores_presupuesto.py`: `get(for_update=)`, `save`, `delete` y `MENSAJE_CONFLICTO`.
  - `backend/app/repositories/presupuestos.py`:
    - `lock_presupuestos(db)`: un `pg_advisory_xact_lock` con clave constante (R-6).
    - `insert_emitido`, `get` y `get_by_idempotency_key`.
    - `estado` (la función SQL) y `has_documentos(cliente_id)`.
    - `v_listado`, `count_listado` y `list_presupuestos`, con `repositories/listado.py`.
  - `backend/app/repositories/cierres_presupuesto.py`: `insert`, `get_by_presupuesto`, `get_by_factura` y `get_by_idempotency_key`. Las lecturas las usan ya el detalle y el PDF.
- [ ] T028 [US1] Servicios (R-7):
  - `backend/app/services/presupuestos.py`:
    - `missing_for_presupuesto(config)` y `check_fecha_presupuesto(fecha, valido_hasta)`.
    - `find_previous_presupuesto(db, clave, operacion, origen)`, sobre presupuestos y cierres (R-7).
    - `emit_presupuesto(..., operacion, origen_id, bloqueado=False)`: `lock_presupuestos` antes de la clave, `contadores.assign_numero(Serie.PRESUPUESTO, …)`, copias con `contenido.py`, líneas, desglose y evento.
    - `get_presupuesto` → `DetallePresupuesto`: el estado visible, `sustituye_a`, `vigente_actual` (último de la cadena de sustituciones), el cierre con su factura y la factura vigente, y el borrador vinculado. Se lee de forma genérica, aunque los cierres no existan hasta US3 y US4.
    - `list_presupuestos`.
  - `backend/app/services/borradores_presupuesto.py`: CRUD con versión y `emit_borrador_presupuesto`, copiado del patrón de `services/borradores.py`, en el orden de R-7 (`lock_presupuestos` → clave → borrador `FOR UPDATE`).
- [ ] T029 [P] [US1] Esquemas `backend/app/schemas/presupuesto.py` y `backend/app/schemas/borrador_presupuesto.py`, según el contrato:
  - `PresupuestoEntrada`, `BorradorPresupuestoEntrada`, `BorradorPresupuestoEdicionEntrada`, `BorradorPresupuestoSalida`, `PresupuestoSalida`, `PresupuestoResumenSalida`, `PresupuestoReferencia` (con `fecha`), `CierrePresupuestoSalida` y `ParametrosPresupuestoSalida`.
  - Importes con `schemas/importes.py`.
- [ ] T030 [US1] Routers:
  - `backend/app/api/v1/presupuestos.py`: `GET /parametros` (declarado antes de `/{id}`), `GET ""`, `POST ""` con `Idempotency-Key` y `GET /{id}`.
  - `backend/app/api/v1/borradores_presupuesto.py`: CRUD y `POST /{id}/emision`.
  - Registro en `backend/app/api/v1/__init__.py`.
  - Quitar de `PENDIENTES_005` las 9 operaciones implementadas: 4 de presupuestos y 5 de borradores.
- [ ] T031 [US1] `backend/app/services/documentos.py`: `DocumentosDeFacturacion` suma `presupuestos.has_documentos` y los borradores de presupuesto. Hace pasar T025.
- [ ] T032 [US1] Regenerar los tipos (T017) y crear las queries:
  - `joyeriablanco_web/src/api/queries/presupuestos.ts`:
    - `PRESUPUESTOS_KEY`, `presupuestosListaQuery` (con `keepPreviousData`), `presupuestoQuery` y `parametrosPresupuestoQuery`.
    - `useEmitirPresupuesto` con `Idempotency-Key`.
    - Las invalidaciones de presupuestos y clientes.
  - `joyeriablanco_web/src/api/queries/borradoresPresupuesto.ts`: crear, guardar con versión, eliminar y emitir.
- [ ] T033 [US1] Rutas (contracts/ui-rutas.md):
  - `joyeriablanco_web/src/routes/_app/presupuestos.tsx`, con el esquema zod de búsqueda compartido con facturas.
  - `presupuestos/nuevo.tsx` y `presupuestos/borradores/$borradorId.tsx`, con `staleTime: 0`.
  - `presupuestos/$presupuestoId/index.tsx`.
  - Carga previa con `precargar()`.
- [ ] T034 [US1] Pantallas en `joyeriablanco_web/src/features/presupuestos/`:
  - **Listado**: `PresupuestosPage.tsx`, con `FiltrosDocumentos`, `TablaDocumentos`, `Pagination`, los estados vacíos y «Nuevo presupuesto».
  - **Marcas**: `MarcaPresupuesto.tsx`, con los tonos de ui-rutas y siempre con texto.
  - **Valores del formulario**: `presupuesto-valores.ts`, con zod, `aCuerpo`, `valoresDelBorrador` y la validez propuesta.
  - **Modal**: `CamposPresupuesto.tsx`, con fecha y «Válido hasta» que se recalcula si no se ha tocado.
    - `FormularioPresupuesto.tsx`, copiado del ciclo de `FormularioFactura`, con los botones de FR-027 y la confirmación de emisión.
    - `NuevoPresupuestoModal` y `BorradorPresupuestoModal`.
  - **Consulta**: `PresupuestoConsulta.tsx`, con los datos, la validez, las líneas en solo lectura, los totales y el bloque de historial, que se completa en US3 y US4.
  - Hace pasar T026.
- [ ] T035 [US1] `joyeriablanco_web/src/components/layout/Sidebar.tsx`: «Presupuestos» con `to: '/presupuestos'`. Se elimina la rama «Próximamente» si queda sin uso, y se actualiza `e2e/acceso.spec.ts:19` (0 «Próximamente»).
- [ ] T036 [US1] E2E `joyeriablanco_web/e2e/presupuestos.spec.ts`, primera parte: menú, nuevo borrador, editar, emitir (número PRE), consulta no editable, borrador eliminado sin consumir número, y búsqueda y filtro.

**Checkpoint**: MVP utilizable: presupuestos emitidos, numerados y consultables, sin efectos
fiscales.

---

## Phase 4: User Story 2 - Imprimir un presupuesto (Priority: P1)

**Goal**: «Imprimir» abre el PDF titulado «PRESUPUESTO», con la leyenda, la validez y el
contenido, sin QR.

**Independent Test**: se imprime un presupuesto de varias líneas y se comprueban el título, la
leyenda, la validez y el contenido, y que no hay ningún elemento fiscal.

### Tests for User Story 2 ⚠️

- [ ] T037 [P] [US2] Test `backend/tests/integration/test_pdf_presupuesto.py` (FR-029, SC-007), con el texto extraído con pypdf, como `test_pdf_factura.py`:
  - **Contenido**:
    - «PRESUPUESTO» y la leyenda literal «Documento sin validez fiscal. No es una factura.».
    - «Válido hasta: dd/mm/aaaa», el número y la fecha.
    - El emisor y el cliente de la copia, el contacto y las líneas.
    - El desglose y los totales al céntimo, y la mención si es de oro de inversión.
    - «PRE-… · Página 1 de 1».
  - **Ausencias**: ni `<svg`, ni «QR tributario», ni `FRASE_VERIFACTU` ni «VERI\*FACTU», ni `aeat.es` ni `agenciatributaria`.
  - **Marcas**: un pendiente y un caducado no llevan ninguna. Los demás estados se prueban en T045 y T056, cuando existen sus cierres.
  - **Variantes**:
    - IBAN solo con `iban=true` y si lo tiene.
    - Pie de presupuesto, o el de factura si está vacío.
    - Cliente sin domicilio, sin líneas vacías.
    - 60 líneas: varias páginas, la cabecera repetida y la leyenda solo en la primera.
  - **Errores**: borrador o inexistente → 404. Sin sesión → 401. Navegación → página HTML «El presupuesto no existe.» con un enlace a `/presupuestos`.
  - **Respuesta**: `Content-Disposition` con `PRE-AAAA-NNNN.pdf`, `Cache-Control: no-store` y la CSP de PDF.
  - **Permisos**: un empleado puede imprimir.
- [ ] T038 [P] [US2] Test web `joyeriablanco_web/src/features/presupuestos/ImprimirPresupuesto.test.tsx`: el enlace con `target=_blank` y su `href`, la casilla IBAN solo si lo tiene, sin «Duplicado», el nombre accesible «Imprimir presupuesto PRE-…» y «Preparando…» anunciado.

### Implementation for User Story 2

- [ ] T039 [US2] `backend/app/services/impresion_presupuestos.py` (R-10):
  - `PresupuestoImpreso`, **sin campo `qr`**.
  - `build_presupuesto_impreso(db, id, *, iban)`, con el pie de R-9 y las marcas de R-10 leídas con `services/presupuestos.get_presupuesto` (T028): «ANULADO», «SUSTITUIDO por {vigente_actual}» y «CONVERTIDO en {factura del cierre}».
  - `presupuesto_pdf`, con el limitador de documentos de 003 (`LIMITE_FACTURAS`, sin renombrar).
- [ ] T040 [US2] Plantilla `backend/app/resources/pdf/presupuesto.html` (contracts/documentos-pdf.md, «Presupuesto»):
  - Extiende `base.html`, usa las macros de `_documento.html` y no tiene bloque de QR.
  - El aviso va en `.aviso-no-fiscal`.
  - `backend/app/resources/pdf/papel.css`: `.aviso-no-fiscal` con tokens (DESIGN.md 1.3). `test_tokens_papel.py` debe seguir en verde.
- [ ] T041 [US2] Router: `GET /v1/presupuestos/{id}/pdf?iban=` en `backend/app/api/v1/presupuestos.py`, con `respuesta_pdf`. Quitarlo de `PENDIENTES_005`.
- [ ] T042 [US2] `deploy/caddy/Caddyfile:13`: la excepción de la CSP de la SPA pasa a `^/api/v1/(facturas|presupuestos)/(listado|[^/]+)/pdf$`. Comprobarlo contra Caddy, como en 003.
- [ ] T043 [US2] `joyeriablanco_web/src/features/presupuestos/ImprimirPresupuesto.tsx`, montado en el pie de `PresupuestoConsulta.tsx`, con `EnlaceImprimir` y `urlPdfPresupuesto`. Hace pasar T038.
- [ ] T044 [US2] E2E en `joyeriablanco_web/e2e/presupuestos.spec.ts`: el `href` del PDF y que la descarga empieza por `%PDF`, como `impresion.spec.ts`.

**Checkpoint**: presupuesto impreso conforme a la sección «Paper» y sin elementos fiscales.

---

## Phase 5: User Story 3 - Convertir un presupuesto en factura (Priority: P1)

**Goal**:
1. «Convertir en factura» crea un borrador de factura vinculado.
2. El presupuesto queda «En facturación».
3. Al emitir el borrador, en la misma operación, queda «Convertido en FAC-…».

**Independent Test**:
- Se convierte un presupuesto y se emite el borrador: la factura tiene el contenido, el número
  FAC y el registro encadenado, y los dos documentos se enlazan.
- Convertir o emitir a la vez produce un solo borrador y una sola factura.

### Tests for User Story 3 ⚠️

- [ ] T045 [P] [US3] ⚖️ Test `backend/tests/integration/test_conversion_presupuesto.py` (FR-018 a FR-022, SC-003 a SC-005, R-5, R-6), con las pruebas de concurrencia en commit real:
  - **Crear el borrador**:
    - Precargado con el cliente, las líneas y `oro_inversion`, con la fecha de hoy y el IVA vigente.
    - Sin números consumidos y con el evento `borrador_factura_creado` con `presupuesto_id`.
    - El estado pasa a `en_facturacion`.
    - Con el cliente desactivado después de emitir el presupuesto, el borrador se crea igualmente con ese cliente, y su emisión responde `cliente-no-facturable`.
  - **Repetición**: devuelve 200 con el mismo borrador. **20 conversiones simultáneas** → un borrador.
  - **Cerrados**: convertir uno convertido, sustituido o anulado → 409 `presupuesto-no-modificable`.
  - **Caducado**: se convierte.
  - **Emitir el borrador** (`POST /v1/borradores-factura/{id}/emision`):
    - FAC siguiente, registro de alta encadenado y cierre `conversion` con la factura, en la misma transacción.
    - Eventos `factura_emitida` y `presupuesto_convertido`.
    - El borrador desaparece y el estado pasa a `convertido`.
    - `FacturaSalida.presupuesto_origen` y `PresupuestoSalida.cierre.factura`.
    - **PDF del presupuesto**: lleva «CONVERTIDO en {FAC del cierre}». Si después se anula y se reemite la factura, sigue mostrando la factura del cierre, y `cierre.factura_vigente` apunta a la nueva.
  - **20 emisiones simultáneas del borrador**, con la misma clave y con claves distintas: una sola factura, el contador FAC +1 y la cadena +1.
  - **Fecha**: anterior a la del presupuesto → 422 `fecha-expedicion`, sin número.
  - **Cliente y configuración**: cliente desactivado o sin domicilio, o sin modalidad → error, sin número, y el presupuesto sigue en facturación.
  - **Eliminar el borrador**: el presupuesto vuelve a `pendiente` y se puede volver a convertir.
  - **Carreras**, con un hilo cada una: conversión frente a anulación, y conversión frente a modificación. Solo una tiene efecto. También con el trigger y la unicidad, forzados con SQL directo.
  - **Importes** ⚖️:
    - Con el mismo IVA, la factura coincide al céntimo con el presupuesto.
    - Con el IVA por defecto cambiado, la misma base y la cuota recalculada.
    - Oro de inversión: factura exenta.
  - **Encadenamiento** ⚖️: con conversiones intercaladas entre emisiones directas, anulaciones y rectificativas, `services/integridad` (`verificar-cadena`) informa de una cadena íntegra.
- [ ] T046 [P] [US3] Tests web:
  - `joyeriablanco_web/src/features/presupuestos/ConvertirPresupuestoDialog.test.tsx`:
    - La confirmación y el aviso de caducado.
    - La navegación al borrador con el aviso.
    - Las invalidaciones de presupuestos, facturas y clientes.
    - Una respuesta 200 con el borrador existente navega a él.
    - Un 409 `presupuesto-no-modificable` muestra el aviso y recarga.
  - `PresupuestoConsulta.test.tsx`: el estado «En facturación», con el aviso, «Abrir borrador de factura» y sin Modificar ni Anular.
  - `joyeriablanco_web/src/features/facturas/FacturaModal.borrador.test.tsx` y `FacturaModal.consulta.test.tsx`:
    - «Procede del presupuesto PRE-…» con su enlace.
    - La fecha mínima del campo de fecha es la del presupuesto (`presupuesto_origen.fecha`).
    - El aviso tras emitir.
    - La invalidación de `['presupuestos']` al emitir y al eliminar.

### Implementation for User Story 3

- [ ] T047 [P] [US3] `backend/app/repositories/borradores.py`: `get_by_presupuesto(presupuesto_id)`. El cerrojo y los cierres ya están en T027.
- [ ] T048 [US3] `backend/app/core/errors.py`:
  - `PresupuestoNoModificable(estado, borrador_factura_id=None)`, 409 `presupuesto-no-modificable`.
  - Traducción **por el nombre de la restricción** a ese error, sin exponer detalles técnicos:
    - Las unicidades `uq_cierres_presupuesto_presupuesto_id` y `uq_borradores_factura_presupuesto_id`.
    - Los triggers, con `tg_cierres_presupuesto_en_facturacion` y `tg_borradores_factura_presupuesto_cerrado` (R-6).
- [ ] T049 [US3] `backend/app/services/conversion.py` (R-5, R-6):
  - `create_borrador_conversion(db, presupuesto_id, *, actor, origen) -> tuple[BorradorFactura, bool]`:
    - `lock_presupuestos` y estado.
    - El borrador existente, o uno nuevo creado **directamente** con el `cliente_id` del presupuesto, sin `_check_cliente`, aunque esté desactivado.
    - Auditoría.
  - `close_conversion(db, borrador, factura, *, actor, origen)`: inserta el cierre y el evento.
  - `check_fecha_conversion(borrador, fecha)`.
- [ ] T050 [US3] Enganche en 002, en `backend/app/services/borradores.py → emit_borrador`. Si `borrador.presupuesto_id`:
  - `check_fecha_conversion` antes de emitir.
  - `close_conversion` tras `emit_factura` y antes de borrar el borrador.

  El resto del flujo y su idempotencia no cambian. Comprobar `test_borradores.py` y `test_emision.py` en verde.
- [ ] T051 [US3] Ampliaciones de los esquemas y servicios de 002 (contrato «ampliado en 005»):
  - `backend/app/schemas/borrador.py` y `backend/app/api/v1/borradores.py → _salida`: `presupuesto_origen`.
  - `backend/app/schemas/factura.py`, `backend/app/services/facturas.py → get_factura` y `backend/app/api/v1/facturas.py → factura_salida`: `presupuesto_origen`, leído del cierre de conversión.
  - `backend/app/services/presupuestos.get_presupuesto`: el borrador vinculado, el cierre y la factura vigente, con `services/facturas`.
- [ ] T052 [US3] Router: `POST /v1/presupuestos/{id}/conversion` en `backend/app/api/v1/presupuestos.py`, con 201 o 200 y `BorradorSalida`. Quitarlo de `PENDIENTES_005`.
- [ ] T053 [US3] Queries web:
  - `joyeriablanco_web/src/api/queries/presupuestos.ts → useConvertirPresupuesto`: invalida presupuestos, facturas y clientes, y siembra `borradorQuery`.
  - `joyeriablanco_web/src/api/queries/borradores.ts`: emitir y eliminar invalidan también `PRESUPUESTOS_KEY`.
  - Regenerar los tipos.
- [ ] T054 [US3] Pantallas:
  - `joyeriablanco_web/src/features/presupuestos/ConvertirPresupuestoDialog.tsx`.
  - `PresupuestoConsulta.tsx`: «En facturación», «Abrir borrador de factura», el historial de la conversión con la factura y su vigente, y el tratamiento de `presupuesto-no-modificable` (ui-rutas, «Errores»).
  - Nuevo `joyeriablanco_web/src/features/facturas/EnlacePresupuesto.tsx`, en `FacturaModal.tsx` (borrador) y `FacturaConsulta.tsx`.
  - El aviso tras emitir un borrador vinculado: «Factura FAC-… emitida. PRE-… queda convertido».
  - Hace pasar T046.
- [ ] T055 [US3] E2E en `joyeriablanco_web/e2e/presupuestos.spec.ts`:
  - Convertir y abrir el borrador con «Procede del presupuesto».
  - Volver al presupuesto, que está «En facturación», y pulsar «Abrir borrador» para llegar al mismo.
  - Emitir: la factura tiene QR y el enlace, y el presupuesto queda «Convertido en FAC-…» con su enlace.
  - Otro presupuesto: convertir, eliminar el borrador y ver que vuelve a pendiente.

**Checkpoint**: conversión completa, atómica y única, con los tests obligatorios de conversión,
importes y encadenamiento en verde.

---

## Phase 6: User Story 4 - Modificar o anular un presupuesto emitido (Priority: P2)

**Goal**: un administrador sustituye un presupuesto por uno nuevo, o lo anula con un motivo, y el
historial queda visible en los dos.

**Independent Test**: se modifica y se anula. El original sigue intacto, el nuevo tiene el
siguiente número, los dos se enlazan y no se reutiliza ningún número.

### Tests for User Story 4 ⚠️

- [ ] T056 [P] [US4] Test `backend/tests/integration/test_presupuestos_cierres.py` (FR-005, FR-015 a FR-017, FR-021, FR-028, SC-010):
  - **Modificar**:
    - Siguiente PRE, original `sustituido` con su cierre y su motivo, y el nuevo con `sustituye_a`.
    - `vigente_actual` en cadenas de dos sustituciones.
    - **`sin-cambios`** (Clarifications, analyze): solo con la fecha cambiada → 422. Con cualquier cambio del cliente copiado, las líneas, el oro de inversión, el IVA que se aplicaría o «Válido hasta» → se emite.
    - Desde un caducado, ampliando la validez.
    - La fecha fuera de límites o la validez anterior a la fecha → 422 en el campo.
  - **Anular**: con motivo y estado `anulado`. Sin motivo → 422.
  - **Sin efectos fiscales**: modificar y anular no cambian la cadena de registros ni el contador FAC.
  - **Permisos y estados**:
    - Un empleado → 403.
    - Sobre uno cerrado → 409.
    - Sobre uno en facturación → 409 con `borrador_factura_id`.
  - **Idempotencia**:
    - Repetir con la misma clave **después del commit** devuelve 200 con el mismo resultado, no un 409.
    - El doble envío simultáneo con la misma clave da un solo presupuesto nuevo o un solo cierre.
    - La clave de `anular` reutilizada en `modificar` → 409 `idempotencia-conflicto`.
  - **PDF**: «SUSTITUIDO por {último de la cadena}» y «ANULADO», con el número correcto.
  - **Auditoría**: `presupuesto_modificado` y `presupuesto_anulado`.
- [ ] T057 [P] [US4] Tests web:
  - `joyeriablanco_web/src/features/presupuestos/ModificarPresupuestoModal.test.tsx`:
    - La precarga y la fecha de hoy.
    - La validez propuesta del sustituto (FR-015): la del original, o la fecha más la validez por defecto si la del original es anterior.
    - El motivo obligatorio.
    - El aviso y la navegación al nuevo.
    - `sin-cambios`.
  - `AnularPresupuestoDialog.test.tsx`: motivo obligatorio y estado tras anular.
  - `HistorialPresupuesto.test.tsx`: las tres clases de cierre y «Sustituye a».

### Implementation for User Story 4

- [ ] T058 [US4] `backend/app/services/presupuestos.py` (R-7), en el orden `lock_presupuestos` → `find_previous_presupuesto` (si hay resultado previo, se devuelve) → estado → borrador vinculado → cierre:
  - `modify_presupuesto`: `AdminSession`, `sin-cambios` con la regla de R-7 (la fecha no cuenta), `emit_presupuesto(…, operacion=modificar, bloqueado=True)`, cierre `sustitucion` y evento.
  - `annul_presupuesto`: cierre `anulacion` con su clave y evento.
  - Orden de lectura de R-6: primero el borrador vinculado y después el cierre.
- [ ] T059 [P] [US4] Esquemas `ModificacionPresupuestoEntrada` y `AnulacionPresupuestoEntrada`, en `backend/app/schemas/presupuesto.py`.
- [ ] T060 [US4] Routers en `backend/app/api/v1/presupuestos.py`: `POST /{id}/modificacion` (201 o 200) y `POST /{id}/anulacion` (200), solo `AdminSession` y con `Idempotency-Key`. Quitarlos de `PENDIENTES_005`.
- [ ] T061 [US4] Pantallas:
  - `joyeriablanco_web/src/routes/_app/presupuestos/$presupuestoId/modificar.tsx`, con `requireAdmin`.
  - `joyeriablanco_web/src/features/presupuestos/ModificarPresupuestoModal.tsx`, con el diálogo de motivo.
  - `AnularPresupuestoDialog.tsx`.
  - `HistorialPresupuesto.tsx`, en la consulta.
  - Queries `useModificarPresupuesto` y `useAnularPresupuesto`, con `useClaveOperacion`.
  - Hace pasar T057.
- [ ] T062 [US4] E2E en `joyeriablanco_web/e2e/presupuestos.spec.ts`:
  - Como administrador: modificar una línea y ver el nuevo PRE y el historial en los dos. Anular con motivo y ver «ANULADO».
  - Como empleado: no ve Modificar ni Anular.

**Checkpoint**: ciclo completo del presupuesto con sustitución y anulación trazables.

---

## Phase 7: User Story 5 - Listado impreso y datos de ejemplo (Priority: P3)

**Goal**: «Imprimir listado» de presupuestos con totales por tipo de IVA, y datos de ejemplo en
todos los estados.

**Independent Test**: con más de 100 presupuestos en un filtro, el PDF tiene todas las filas en
orden y los totales cuadran al céntimo. Los datos de ejemplo cubren todos los estados.

### Tests for User Story 5 ⚠️

- [ ] T063 [P] [US5] Test `backend/tests/integration/test_pdf_listado_presupuestos.py` (FR-030, SC-011), como `test_pdf_listado.py`:
  - 105 filas en los cuatro órdenes, filtros y la cabecera con el filtro.
  - Las marcas.
  - **Totales**: los de pendientes, caducados, en facturación y convertidos, por tipo de IVA y al céntimo con los desgloses. «No se suman: …» con los borradores, los sustituidos y los anulados.
  - Sin resultados → «No hay presupuestos con este filtro».
  - Más de 5.000, con el límite reducido por `monkeypatch` → 422 `listado-demasiado-grande`, también en HTML.
  - Nombre del fichero `presupuestos-…`.
- [ ] T064 [P] [US5] Ampliar `backend/tests/integration/test_datos_ejemplo.py` (FR-036):
  - Presupuestos en todos los estados, con sus facturas y borradores vinculados.
  - Idempotencia de la carga.
  - Prohibida en producción.
- [ ] T065 [P] [US5] Test web: ampliar `joyeriablanco_web/src/features/documentos/ImprimirListado.test.tsx` (movido en T014) con el caso de presupuestos: su `href`, y desactivado con 0 filas o con más de 5.000, con su motivo.

### Implementation for User Story 5

- [ ] T066 [US5] Listado impreso en el backend:
  - `backend/app/repositories/presupuestos.py`: `list_presupuestos_impresion` y `totales_presupuestos`, con la SQL de `totales_vigentes` sobre `desgloses_presupuesto`.
  - `backend/app/services/impresion_presupuestos.py`: `build_listado_presupuestos` y `listado_presupuestos_pdf`, por bloques como en 003, con los textos de documentos-pdf.md.
- [ ] T067 [US5] Router `GET /v1/presupuestos/listado/pdf`, declarado antes de `/{id}`. Quitarlo de `PENDIENTES_005`. Ampliar `deploy/verificar-produccion.sh` con la comprobación del listado de presupuestos (401 y CSP de la API).
- [ ] T068 [US5] Web: «Imprimir listado» en `PresupuestosPage.tsx`, con el `ImprimirListado` parametrizado y `urlPdfListado('presupuestos', filtros)`. Hace pasar T065.
- [ ] T069 [US5] Datos de ejemplo (data-model, «Datos de ejemplo»):
  - `backend/app/services/datos_ejemplo.py → _cargar_presupuestos`, enganchado en `_cargar_facturacion`, con `ResumenCarga.presupuestos` y `borradores_presupuesto`.
  - Usa los servicios reales (emitir, convertir, emitir el borrador, modificar y anular), con fechas pasadas para los caducados.
  - `backend/app/cli.py`: el resumen impreso. Hace pasar T064.
- [ ] T070 [US5] E2E:
  - `joyeriablanco_web/e2e/presupuestos-listado.spec.ts`: búsqueda, año, mes, orden, paginación, marcas sembradas y el `href` del listado impreso.
  - Ajustar los recuentos de `e2e/facturas-listado.spec.ts` por las facturas que crean las conversiones de ejemplo.

**Checkpoint**: las cinco historias completas.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [ ] T071 [P] Ampliar `backend/tests/integration/test_logs_facturacion.py` y `test_logs_sin_datos_personales.py` (FR-035): emitir, modificar, anular, convertir e imprimir presupuestos no deja nombres, NIF ni importes en los registros, solo números y operaciones.
- [ ] T072 [P] Test lento `backend/tests/integration/test_presupuestos_rendimiento.py` (`@pytest.mark.lento`):
  - SC-008: 20.000 presupuestos sintéticos, con el p95 de la búsqueda y de los cambios de filtro por debajo de 1 s.
  - El PDF de un presupuesto de 20 líneas, por debajo de 3 s.
  - Anotar los resultados en el quickstart.
- [ ] T073 [P] E2E transversales, con las secciones de presupuestos:
  - `e2e/acciones-visibles.spec.ts`: acciones visibles a 768, 1024, 1280, 1440 y 1536 px.
  - `e2e/responsive.spec.ts`: 360 px sin desplazamiento horizontal.
  - `e2e/teclado.spec.ts`: el modal y los diálogos con teclado y Escape (SC-009).
- [ ] T074 [P] Revisión de conformidad con `docs/DESIGN.md` 1.3 (SC-012):
  - Pantallas: chips, modal, tabla y diálogos.
  - PDF: aviso no fiscal, marcas y tokens.
  - Anotar en el quickstart.
- [ ] T075 [P] Documentación:
  - `README.md`: Presupuestos ✅.
  - `backend/app/resources/README.md`: las plantillas nuevas y las macros.
  - `CLAUDE.md`, si algún comando cambia.
  - [quickstart.md](quickstart.md): la sección «Resultado de la validación».
- [ ] T076 Puertas de calidad completas antes de cerrar:
  - **Backend**: `uv run pytest`, `uv run pytest -m lento`, `uv run ruff check . && uv run ruff format --check . && uv run mypy .` y `uv run joyeria verificar-cadena` sobre los datos de ejemplo.
  - **Web**: `npm run lint && npm run typecheck && npm run test && npm run build && npm run check:tokens` y `npx playwright test`.
- [ ] T077 Validación manual del [quickstart](quickstart.md) §2 (pasos 1 a 18), con el paso cronometrado de SC-001. La revisión visual del papel, el visor de PDF de cada navegador y la vista a 360 px quedan **pendientes del responsable** si no se pueden hacer en el entorno.
- [ ] T078 Contrato completo: eliminar `PENDIENTES_005` de `backend/tests/integration/test_contrato_openapi.py` y dejar el test en verde. Debe quedar vacía tras T067.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (fase 1)**: sin dependencias.
- **Foundational (fase 2)**: depende de Setup y bloquea todas las historias. T020 es su puerta.
- **US1 (fase 3)**: depende de Foundational.
- **US2 (fase 4)**: depende de US1, que necesita presupuestos emitidos. Es independiente de US3.
- **US3 (fase 5)**: depende de US1. Puede ir en paralelo con US2.
- **US4 (fase 6)**: depende de US1 y de US3, porque modificar y anular deben respetar el estado
  «en facturación» (FR-021).
- **US5 (fase 7)**: depende de US2, por la infraestructura de PDF, y de US3 y US4, porque los datos
  de ejemplo cubren todos los estados.
- **Polish (fase 8)**: depende de todas las historias.

### Within Each User Story

- Los tests se escriben primero y deben fallar.
- Después van los repositorios y los esquemas, luego los servicios y los routers, y por último la
  web y los E2E.
- Cada historia se cierra con un commit `feat(005): USn — …` y sus tests en verde.

### Parallel Opportunities

- **Fase 2**:
  - T003, T004 y T005 (tests).
  - T007 y T008.
  - T014 y T016, que son de la web, mientras avanza el backend T010 a T013. T015 va después de T014, y T018 y T019 después de T017.
- **US1**: los tests T021 a T026 en paralelo. T027 y T029 en paralelo.
- **US2 y US3**: pueden avanzar en paralelo tras US1, porque tocan ficheros distintos salvo
  `api/v1/presupuestos.py`, en el que hay que coordinar los commits.
- **Polish**: T071 a T075 en paralelo.

---

## Parallel Example: User Story 1

```bash
# Tests de US1, a la vez:
Task: "T021 test_presupuestos_borradores.py"
Task: "T022 test_presupuestos_emision.py"
Task: "T023 test_numeracion_presupuestos.py"
Task: "T024 test_listado_presupuestos.py"
Task: "T026 tests web de presupuestos"

# Implementación independiente:
Task: "T027 repositorios"
Task: "T029 esquemas"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Fases 1 y 2, con la puerta T020: 002 y 003 sin regresiones.
2. Fase 3 (US1): presupuestos emitidos, numerados y consultables.
3. **Parar y validar**: los pasos 1 a 3 del quickstart.

### Incremental Delivery

1. US1 → MVP.
2. US2 (PDF) y US3 (conversión), los dos P1, completan lo que pidió el responsable.
3. US4 → negociación trazable.
4. US5 → listado impreso y datos de ejemplo.
5. Polish → puertas, validación y documentación.

---

## Notes

- ⚖️ marca los tests de cobertura obligatoria (constitución VII): T022, T023 y T045.
- Si durante la implementación algo contradice la spec, **se para y se corrige la spec primero**
  (constitución I), con su commit `docs(005): corrección … durante implement`.
- La fase fundacional cambia código de 002 y 003. Si sus suites no quedan idénticas en verde, la
  generalización está mal hecha y se revisa antes de seguir.
- Commits: uno por fase (`feat(005): fase 1 — …` y `fase 2 — …`) y uno por historia
  (`feat(005): USn — …`). Sin push.
