---
description: "Tareas de implementación de la feature 004"
---

# Tasks: Modalidad No VERI\*FACTU — registros firmados, registro de eventos y exportación

**Input**: `specs/004-no-verifactu/`:
- [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md) y [data-model.md](data-model.md).
- [contracts/openapi.yaml](contracts/openapi.yaml), [contracts/ui-rutas.md](contracts/ui-rutas.md),
  [contracts/exportacion.md](contracts/exportacion.md) y [contracts/cli.md](contracts/cli.md).
- [quickstart.md](quickstart.md).

**Prerequisites**: todo en la rama `004-no-verifactu`, sobre `main` con 005 fusionada:
- Constitución 2.4.0.
- Spec con clarify y el refinamiento tras las checklists.
- Plan con las fuentes F-14 a F-20 y el prototipo de firma.
- Checklists.

**Tests**: SÍ, con TDD como en 001 a 005. En cada historia, los tests se escriben primero y deben
fallar. Los obligatorios de la constitución VII (2.4.0) van marcados con ⚖️:
- Encadenamiento, también con firma.
- Firma de los registros.
- Cadena y firma de los eventos.
- XML contra XSD.

**Organization**: por historias de usuario, después de una fase fundacional con el XML, la firma,
el certificado y la migración:

```text
Fundacional (XML, firma, certificado, migración)
 └── US1 (registros firmados; P1, MVP)
      ├── US2 (registro de eventos; P1) ── US3 (integridad, alarma y cadena; P1) ── US4 (exportación; P2)
      └── US5 (configuración, certificado y declaración; P2)
```

## Format: `[ID] [P?] [Story] Description`

- **[P]**: puede ir en paralelo (ficheros distintos y sin dependencias pendientes).
- **[Story]**: historia de la spec (US1–US5).
- Las rutas son relativas a la raíz del repositorio.

## Path Conventions

- **Backend**: `backend/app/…`, `backend/tests/…` y `backend/alembic/versions/…`.
- **Web**: `joyeriablanco_web/src/…` y `joyeriablanco_web/e2e/…`.
- **Formatos**: solo los de F-14 a F-18 y F-2 §3.c. Nada se deduce de memoria (constitución IV).
- **Diseño**: solo tokens de `docs/DESIGN.md`. `check:tokens` sigue vigente.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: dependencias, copias oficiales de los esquemas y el test de contrato preparado para 004.

- [ ] T001 Dependencias en `backend/pyproject.toml`:
  - `signxml>=5.1,<6`, que trae `lxml` y `cryptography`;
  - `lxml-stubs` en desarrollo, si mypy lo necesita.

  Después, `uv lock` y `uv sync`, y comprobar que mypy estricto sigue en verde (sin `ignore` sin
  justificar).
- [ ] T002 [P] Copias oficiales en `backend/app/resources/aeat/xsd/`:
  - `SuministroInformacion.xsd`, `SuministroLR.xsd` y `EventosSIF.xsd` (F-15 a F-17);
  - `xmldsig-core-schema.xsd` (F-20), con su SHA-256;
  - `README.md` con la URL, la fecha y el SHA-256 de cada uno;
  - un test unitario, `backend/tests/unit/test_fuentes_aeat.py`, que comprueba los SHA-256 de
    research.md.
- [ ] T003 [P] Test de contrato en `backend/tests/integration/test_contrato_openapi.py`:
  - una lista `PENDIENTES_004` con las 8 operaciones de [contracts/openapi.yaml](contracts/openapi.yaml);
  - `test_hay_un_contrato_por_feature` incluye `004-no-verifactu`.

  Las tareas de cada ruta vacían la lista y T066 la elimina.
- [ ] T004 [P] `backend/app/__init__.py`: `__version__ = "0.4.0"` (research R-13).

**Checkpoint**: `uv run pytest` en verde, con el contrato pendiente declarado.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: el modelo de datos, el XML, la huella de los eventos, el certificado y la firma. Ninguna
historia empieza sin esto.

### Tests de la fase ⚠️

- [ ] T005 [P] ⚖️ Test `backend/tests/unit/domain/test_xml_registro.py`:
  - el XML de un alta ordinaria, de una rectificativa (con `FacturasRectificadas` e
    `ImporteRectificacion`), de una de oro de inversión y de una anulación es **válido contra
    F-15**;
  - el orden de los elementos es el del XSD aunque el diccionario de entrada venga desordenado
    (JSONB);
  - el XML de un evento de cada tipo (01, 02, 03, 04, 05, 06, 08, 09 y 10) es válido contra F-17;
  - el primer registro y el primer evento llevan `PrimerRegistro` y `PrimerEvento` «S».
- [ ] T006 [P] ⚖️ Test `backend/tests/unit/domain/test_huella_evento.py`: la cadena de F-2 §3.c,
  con el doble `NIF`, `ID=` vacío, sin `HuellaEvento` en el primero y SHA-256 en mayúsculas.
- [ ] T007 [P] Test `backend/tests/integration/test_certificado.py`, con certificados generados por
  `backend/tests/certificados.py`:
  - estado y datos de un certificado utilizable;
  - cada motivo de no utilizable: no instalado, ilegible (contraseña errónea), caducado, aún no
    válido, sin clave privada, `KeyUsage` sin firma y de pruebas en producción (R-6);
  - `caduca_pronto` con 30 días o menos;
  - la validez se comprueba en la fecha dada, no en la actual.
- [ ] T008 [P] ⚖️ Test `backend/tests/integration/test_firma.py`:
  - firmar el `ejemploRegistro.xml` de F-18 y un alta propia;
  - la firma se verifica;
  - lleva todos los elementos del ejemplo oficial (R-3): C14N inclusiva, `rsa-sha256`, referencia
    `URI=""` *enveloped*, `SigningCertificate` y `V2`, `SignaturePolicyIdentifier` con OID, hash y
    `SPURI`, y `DataObjectFormat` con `text/xml` y `UTF-8`;
  - la firma va en el nodo firmado;
  - el resultado sigue siendo válido contra el XSD;
  - cambiar un carácter del XML firmado hace fallar la verificación.
- [ ] T009 [P] Test `backend/tests/integration/test_registros_evento_inalterables.py`:
  - `jb_app` recibe 42501 al hacer UPDATE, DELETE o TRUNCATE sobre `registros_evento` y
    `comprobaciones_integridad`, y el trigger frena también a `jb_owner`;
  - el trigger de encadenamiento rechaza un hueco o una huella anterior incorrecta;
  - `registros_facturacion` exige `xml_firmado` en `no_verifactu` (CHECK).

### Implementación de la fase

- [ ] T010 Migración `backend/alembic/versions/0009_no_verifactu.py` (data-model), en SQL a mano y con
  *downgrade*:
  - las columnas de firma y los CHECK en `registros_facturacion`;
  - `estado_remision` admite `no_aplica`;
  - las tablas `registros_evento` y `comprobaciones_integridad`, con REVOKE y triggers
    (`impedir_modificacion_facturacion()`, `validar_encadenamiento_eventos()`);
  - el CHECK de `eventos_auditoria` con los tipos nuevos;
  - `configuracion_facturacion.modalidad = 'no_verifactu'` donde sea NULL.
- [ ] T011 [P] Enumeraciones en `backend/app/domain/tipos.py`:
  - `TipoEventoSif`, `TipoAnomalia` y `EstadoRemision.NO_APLICA`;
  - los `TipoEvento` de auditoría `REGISTROS_EXPORTADOS`, `INTEGRIDAD_COMPROBADA` y
    `CERTIFICADO_NO_UTILIZABLE`.
- [ ] T012 [P] Modelos:
  - `backend/app/models/registro_evento.py`;
  - `backend/app/models/comprobacion_integridad.py`;
  - columnas nuevas en `backend/app/models/registro_facturacion.py`;
  - registro en `models/__init__.py`.
- [ ] T013 [P] `backend/app/domain/huella.py`: `CamposHuellaEvento.cadena()` (F-2 §3.c). Hace pasar
  T006.
- [ ] T014 `backend/app/domain/xml_registro.py` (R-1): tablas de orden de los tres tipos sacadas de
  los XSD y conversión del `contenido` en elemento `lxml`. El contenido de cada tipo de evento va en
  `backend/app/domain/eventos.py`. Hace pasar T005.
- [ ] T015 Ajustes en `backend/app/core/config.py`:
  - `CERTIFICADO_RUTA` y `CERTIFICADO_CONTRASENA` (`SecretStr`);
  - `SIF_PRODUCTOR_DIRECCION`, `SIF_DECLARACION_FECHA` y `SIF_DECLARACION_LUGAR`, obligatorios en
    producción, como el productor;
  - ampliar `backend/tests/unit/test_config_sif.py`.
- [ ] T016 `backend/app/services/certificado.py` (R-6): carga del PKCS#12 con caché por proceso y
  recarga si cambia la fecha del fichero, `estado(en=…)` y `utilizable(en=…)`. Hace pasar T007.
- [ ] T017 `backend/app/services/firma.py` (R-2, R-3):
  - `validar(elemento, esquema)`, con los XSD locales y un resolvedor sin red;
  - `firmar(elemento, certificado)`, con la subclase de `XAdESSigner` (`SPURI`, `Encoding` y
    `SigningCertificate`), que devuelve los bytes UTF-8;
  - `verificar(xml_firmado)`, que devuelve si es válida y el certificado.

  Hace pasar T008.
- [ ] T018 [P] Ayuda de pruebas `backend/tests/certificados.py` (generación de PKCS#12 de prueba) y
  `backend/tests/conftest.py`:
  - un certificado de prueba de sesión, en una carpeta temporal, que se publica en
    `CERTIFICADO_RUTA` y `CERTIFICADO_CONTRASENA` antes de importar la aplicación;
  - `backend/tests/integration/facturacion_datos.configurar_facturacion` pasa a
    `modalidad="no_verifactu"` por defecto.
- [ ] T019 CLI `generar-certificado-pruebas` en `backend/app/cli.py` ([contracts/cli.md](contracts/cli.md)),
  con test en `backend/tests/integration/test_cli.py`. Se niega en producción.
- [ ] T020 Entorno de desarrollo y de E2E:
  - en `docker-compose.yml`, los servicios `api` y `api-e2e` llevan
    `CERTIFICADO_RUTA=/tmp/certificado-pruebas.p12` y `CERTIFICADO_CONTRASENA`;
  - `joyeriablanco_web/e2e/global-setup.ts` genera el certificado con `generar-certificado-pruebas`
    antes de reiniciar la BD;
  - `.env.example` documenta las variables nuevas.
- [ ] T021 Las suites de 002, 003 y 005 siguen en verde en `no_verifactu`, con el certificado de
  sesión: `uv run pytest`. Se ajustan las expectativas que dependían de `pendiente` o de
  «remisión»: `estado_remision` pasa a `no_aplica`.

**Checkpoint**: XML válido, firma verificable, certificado cargado y migración aplicada, con todo
lo anterior en verde.

---

## Phase 3: User Story 1 - Cada factura deja su registro firmado (Priority: P1) 🎯 MVP

**Goal**: cada alta y cada anulación se genera en XML, se valida y se firma antes de insertarla. Sin
certificado utilizable, no se emite.

**Independent Test**: se emite, se rectifica y se anula. Cada registro es válido contra el XSD y su
firma se verifica. Sin certificado, no se emite y no se consume número.

### Tests for User Story 1 ⚠️

- [ ] T022 [P] [US1] ⚖️ Test `backend/tests/integration/test_firma_registros.py`:
  - alta, rectificativa (alta REC), anulación y anulación con reemisión dejan registros con
    `xml_firmado` válido contra F-15, verificable, con `certificado_titular` y
    `certificado_huella`, y con `estado_remision` `no_aplica`;
  - la `Huella` del XML es la de la columna;
  - una conversión de presupuesto (005) también firma;
  - sin certificado, o con el certificado caducado, aún no válido o de pruebas en producción:
    - emitir, emitir un borrador, modificar y anular responden 409 `emision-no-disponible` con
      `faltan: ["certificado"]` y el `motivo`;
    - no hay factura, registro ni número consumido (contador);
  - los parámetros de facturación incluyen `certificado` en `faltan` y `certificado_caduca_el`;
  - en `verifactu` no se firma (el modelo sigue admitiendo las dos modalidades).
- [ ] T023 [P] [US1] ⚖️ Concurrencia: `backend/tests/integration/test_numeracion_concurrencia.py` (002)
  y el encadenamiento bajo concurrencia, en `no_verifactu` con firma: sin huecos y con cada
  registro firmado.
- [ ] T024 [P] [US1] Tests web:
  - `joyeriablanco_web/src/features/facturas/HistorialFactura.test.tsx`: «Firmado · titular», los
    chips de huella y firma, y «Sin firma (VERI\*FACTU)»; ya no aparece «Remisión: pendiente»;
  - `FacturaModal.test.tsx`: el aviso de certificado que falta o que caduca pronto.

### Implementation for User Story 1

- [ ] T025 [US1] `backend/app/services/cadena.py` (R-4): `create_registro_alta` y
  `create_registro_anulacion`, en `no_verifactu`, antes de `repo.insert`:
  1. comprueban el certificado utilizable en la fecha de generación;
  2. generan el XML, lo validan y lo firman;
  3. guardan `xml_firmado`, `certificado_titular` y `certificado_huella`, con `no_aplica`.

  Si algo falla, `EmisionNoDisponible(faltan=["certificado"], motivo=…)`.
- [ ] T026 [US1] `backend/app/services/configuracion_facturacion.py`:
  - `faltan` incluye `certificado` cuando no es utilizable;
  - `certificado_caduca_el` en los parámetros;
  - el bloque `certificado` en la salida;
  - `modalidad: verifactu` se rechaza con 422 en el campo;
  - el mensaje de `ModalidadBloqueada` se revisa (R-14).
- [ ] T027 [US1] Esquemas y API de 002, con el contrato «ampliado en 004»:
  - `backend/app/schemas/factura.py → RegistroResumen` (`firmado`, `certificado_titular`,
    `huella_correcta` y `firma_correcta`), calculado en `backend/app/services/facturas.get_factura`
    con `firma.verificar` y la huella recalculada;
  - `schemas/configuracion_facturacion.py`: `certificado` y `certificado_caduca_el`.
- [ ] T028 [US1] Web:
  - regenerar los tipos (`exportar-openapi` y `gen:api`);
  - `joyeriablanco_web/src/features/facturas/HistorialFactura.tsx`: firmado y chips;
  - `lib/facturacion.ts → textoFalta('certificado')`;
  - el aviso de caducidad en `FacturaModal.tsx`.

  Hace pasar T024.
- [ ] T029 [US1] E2E en `joyeriablanco_web/e2e/facturas.spec.ts`: la consulta de una factura emitida
  muestra «Firmado» y «Firma correcta».

**Checkpoint**: MVP. Toda factura nueva deja su registro firmado, y sin certificado no se factura.

---

## Phase 4: User Story 2 - Registro de eventos del sistema (Priority: P1)

**Goal**: la cadena de eventos de F-17, firmada e inalterable, con inicio y fin por arranque, un
resumen cada 6 horas y su pantalla.

**Independent Test**: arrancar, exportar y comprobar dejan sus eventos encadenados y firmados, y se
ven en «Registro fiscal → Eventos».

### Tests for User Story 2 ⚠️

- [ ] T030 [P] [US2] ⚖️ Test `backend/tests/integration/test_eventos_sif.py`:
  - `record_evento` encadena, calcula la huella de F-2 §3.c, valida contra F-17 y firma;
  - el primero lleva `PrimerEvento`;
  - 20 eventos simultáneos, en sesiones que confirman, dan una cadena sin huecos;
  - un evento se conserva aunque se deshaga la transacción de quien lo pidió (R-7);
  - el contenido del resumen: eventos por tipo, primer y último registro, altas, anulaciones y
    sumas `NUMERIC`;
  - sin certificado no se genera evento, se registra un aviso y la llamada no falla.
- [ ] T031 [P] [US2] Test `backend/tests/integration/test_eventos_lider.py` (R-8), con reloj
  simulado:
  - dos *lifespans* simultáneos generan un solo 01;
  - pasadas 6 horas, un 10, también sin eventos;
  - al cerrar, un 10 y un 02;
  - si el líder cae sin cerrar, el siguiente genera su 01 y el resumen cubre el intervalo.
- [ ] T032 [P] [US2] Test `backend/tests/integration/test_api_eventos.py`:
  - `GET /v1/registro-fiscal/eventos` con filtros por tipo y por fechas, y paginación;
  - el detalle con saltos al anterior y al siguiente;
  - un empleado recibe 403.
- [ ] T033 [P] [US2] Tests web, en `joyeriablanco_web/src/features/registro-fiscal/`:
  - `RegistroFiscalPage.test.tsx`: las pestañas;
  - `EventosTab.test.tsx`: lista, filtros en la URL, detalle y estados de carga, vacío y error;
  - `Sidebar.test.tsx`: «Registro fiscal» solo para administradores.

### Implementation for User Story 2

- [ ] T034 [P] [US2] `backend/app/repositories/eventos.py`:
  - el cerrojo «JBEVEN» y el último evento;
  - insertar, listar con filtros y obtener por secuencia;
  - el rango por fecha y los recuentos por tipo desde una secuencia.
- [ ] T035 [US2] `backend/app/services/eventos_sif.py` (R-7):
  - `record_evento(tipo, datos)`, en una sesión propia que confirma, con la comprobación previa
    del último evento por analogía con el 7.i;
  - el contenido del resumen;
  - `Lider`, con el cerrojo consultivo de sesión «JBSIFL», el inicio, la tarea periódica de 1
    minuto y el cierre.

  Hace pasar T030 y T031.
- [ ] T036 [US2] `backend/app/lifespan.py`: arrancar el líder (inicio) y pararlo al cerrar (resumen
  y fin). Nunca impide que la API arranque.
- [ ] T037 [US2] API `backend/app/api/v1/registro_fiscal.py` (solo `AdminSession`) con esquemas en
  `backend/app/schemas/registro_fiscal.py`:
  - `GET /v1/registro-fiscal/eventos`;
  - `GET /v1/registro-fiscal/eventos/{secuencia}`, con los saltos de R-9.

  Salen de `PENDIENTES_004`. Hace pasar T032.
- [ ] T038 [US2] Web:
  - la ruta `joyeriablanco_web/src/routes/_app/registro-fiscal.tsx`, con `requireAdmin` y la
    pestaña en la URL;
  - `features/registro-fiscal/RegistroFiscalPage.tsx` y `EventosTab.tsx`, con el modal de detalle;
  - queries en `api/queries/registroFiscal.ts`;
  - la entrada en `Sidebar.tsx`;
  - los textos de los tipos de evento en `lib/registro-fiscal.ts`.

  Hace pasar T033.
- [ ] T039 [US2] E2E en `joyeriablanco_web/e2e/registro-fiscal.spec.ts`: el administrador ve el
  evento de inicio del arranque de `api-e2e` y su detalle. Un empleado no ve la entrada.

**Checkpoint**: registro de eventos completo y consultable.

---

## Phase 5: User Story 3 - Comprobar la integridad y detectar anomalías (Priority: P1)

**Goal**:
- La comprobación bajo demanda de huellas, firmas, cadena y fechas, con sus eventos.
- La alarma para todos los usuarios.
- La navegación por la cadena (7.h).
- La emisión sin bloqueo ante una anomalía (F-4, p. 28).

**Independent Test**: una cadena íntegra da «Íntegra» y sus eventos. Una alteración hecha fuera del
sistema da su anomalía, su evento y la alarma.

### Tests for User Story 3 ⚠️

- [ ] T040 [P] [US3] ⚖️ Test `backend/tests/integration/test_integridad_anomalias.py`. Las
  alteraciones se hacen con `jb_owner`, desactivando los triggers, como en
  `test_verificar_cadena.py`.
  - Cadena íntegra: resultado íntegro, eventos 03 y 05 con los recuentos de las cuatro
    comprobaciones, y fila en `comprobaciones_integridad`.
  - Una anomalía por cada alteración, con su `TipoAnomalia` (R-10) y su evento 04 o 06:
    - huella cambiada: 01;
    - XML firmado alterado: 02;
    - columna distinta del XML: 03;
    - registro borrado: 04;
    - huella anterior cambiada: 08;
    - fecha desordenada: 11;
    - fecha futura: 13;
    - evento alterado: 06.
  - Comprobación de un rango parcial.
- [ ] T041 [P] [US3] Test `backend/tests/integration/test_alarmas.py` (R-11):
  - sin anomalías no hay alarma;
  - con una anomalía, la alarma está activa para cualquier sesión;
  - una comprobación posterior, desde después del registro afectado hasta el final, la apaga;
  - con el certificado no utilizable, la alarma de certificado;
  - un empleado ve la alarma.
- [ ] T042 [P] [US3] ⚖️ Test de la emisión ante una anomalía (FR-010), en
  `backend/tests/integration/test_cadena_registros.py` (002, ampliado):
  - en `no_verifactu`, con el último registro alterado, la factura **se emite**, se genera el
    evento 04 y la alarma, y el nuevo registro encadena con la huella guardada;
  - en `verifactu` se conserva el bloqueo de la 002.
- [ ] T043 [P] [US3] Test `backend/tests/integration/test_api_cadena.py`:
  - `GET /v1/registro-fiscal/registros/{secuencia}` con los saltos, el encadenamiento y las
    fechas;
  - el primero sin anterior y el último sin siguiente;
  - `POST /v1/registro-fiscal/comprobaciones` con y sin rango, con CSRF;
  - un empleado recibe 403.
- [ ] T044 [P] [US3] Test de la CLI en `backend/tests/integration/test_cli.py`: `verificar-cadena`
  devuelve el código 0 si está íntegra y 1 con una anomalía, y admite `--desde` y `--hasta`
  ([contracts/cli.md](contracts/cli.md)).
- [ ] T045 [P] [US3] Tests web:
  - `components/layout/BandaAlarma.test.tsx`: dos alarmas, enlace solo para administradores y
    `role="alert"`;
  - `features/registro-fiscal/CadenaTab.test.tsx` y `ComprobarTab.test.tsx`;
  - el enlace «Ver en la cadena» de la consulta de la factura.

### Implementation for User Story 3

- [ ] T046 [US3] `backend/app/services/integridad.py` (R-9, R-10):
  - amplía `verify_chain` con el rango, la firma y la comprobación de las columnas frente al XML;
  - comprueba también la cadena de eventos;
  - genera los eventos 03, 04, 05 y 06 con `eventos_sif.record_evento` y la fila de
    `comprobaciones_integridad`.

  Lo hace con `backend/app/repositories/comprobaciones.py`. Hace pasar T040.
- [ ] T047 [US3] `backend/app/services/cadena.verify_tail` (R-5): en `no_verifactu` genera el evento
  04, con una comprobación de origen `emision`, y continúa. En `verifactu`, sin cambios. Hace pasar
  T042.
- [ ] T048 [US3] `backend/app/services/alarmas.py` (R-11) y `GET /v1/alarmas` en
  `backend/app/api/v1/alarmas.py`, para cualquier sesión. Sale de `PENDIENTES_004`. Hace pasar T041.
- [ ] T049 [US3] API en `backend/app/api/v1/registro_fiscal.py`:
  - `GET /v1/registro-fiscal/registros/{secuencia}`;
  - `POST /v1/registro-fiscal/comprobaciones` (201), con el evento de auditoría
    `INTEGRIDAD_COMPROBADA`.

  Salen de `PENDIENTES_004`. Hace pasar T043.
- [ ] T050 [US3] CLI `verificar-cadena`, ampliada según [contracts/cli.md](contracts/cli.md). Hace
  pasar T044.
- [ ] T051 [US3] Web:
  - `components/layout/BandaAlarma.tsx` en el *layout*, con la query de alarmas al cambiar de ruta
    y cada 60 s;
  - `features/registro-fiscal/CadenaTab.tsx` y `ComprobarTab.tsx`;
  - «Ver en la cadena» en `HistorialFactura.tsx`.

  Hace pasar T045.
- [ ] T052 [US3] E2E en `joyeriablanco_web/e2e/registro-fiscal.spec.ts`:
  - «Comprobar integridad» da «Íntegra», con los eventos 03 y 05 en la lista;
  - la navegación por la cadena desde una factura;
  - ninguna banda de alarma.

**Checkpoint**: detección, alarma y trazabilidad completas.

---

## Phase 6: User Story 4 - Exportar los registros (Priority: P2)

**Goal**: el ZIP del periodo con cada registro tal como se firmó, más su evento.

**Independent Test**: se exporta un periodo con altas y anulaciones. El ZIP cumple
[exportacion.md](contracts/exportacion.md) y queda el evento 08.

### Tests for User Story 4 ⚠️

- [ ] T053 [P] [US4] Test `backend/tests/integration/test_exportacion.py`:
  - estructura del ZIP (nombres, orden, `indice.csv`, `manifiesto.sha256` y `resumen.txt`);
  - cada XML idéntico byte a byte a `xml_firmado` y verificable fuera de la BD;
  - el periodo en días completos, hora de Madrid y extremos incluidos;
  - el evento 08 con sus sumas `NUMERIC` y «N», y el 09 para los eventos;
  - un periodo vacío da 422 `sin-registros` sin evento, y «desde» posterior a «hasta», 422;
  - un empleado recibe 403;
  - el evento de auditoría `REGISTROS_EXPORTADOS`;
  - la CLI `exportar-registros`, con sus códigos.
- [ ] T054 [P] [US4] Test web `features/registro-fiscal/ExportarTab.test.tsx`: valores por defecto
  (el mes en curso), validación, `href` de la descarga y aviso de periodo vacío.

### Implementation for User Story 4

- [ ] T055 [US4] `backend/app/services/exportacion.py` (R-12), con las consultas por rango en
  `repositories/registros.py` y `eventos.py`: ZIP en un fichero temporal y evento 08 o 09 al
  terminar.
- [ ] T056 [US4] `GET /v1/registro-fiscal/exportacion` en `backend/app/api/v1/registro_fiscal.py`
  (`FileResponse`, `attachment`) y la CLI `exportar-registros`. Sale de `PENDIENTES_004`. Hace pasar
  T053.
- [ ] T057 [US4] Web: `features/registro-fiscal/ExportarTab.tsx`. Hace pasar T054.
- [ ] T058 [US4] E2E en `registro-fiscal.spec.ts`: exportar el día de hoy descarga un ZIP que empieza
  por `PK`, y el evento de exportación aparece en la lista.

**Checkpoint**: conservación y requerimientos cubiertos con la exportación.

---

## Phase 7: User Story 5 - Modalidad, certificado y declaración responsable (Priority: P2)

**Goal**: la modalidad fija, el estado del certificado y «Acerca del sistema» con la declaración del
art. 15.

**Independent Test**: en Configuración se ven la modalidad y el certificado. Desde cualquier pantalla
se abre «Acerca del sistema» y se descarga la declaración.

### Tests for User Story 5 ⚠️

- [ ] T059 [P] [US5] Test `backend/tests/integration/test_sistema.py`:
  - `GET /v1/sistema` para cualquier sesión, con los datos del sistema y la declaración (título
    literal, letras a a l en orden y con los textos del art. 15.1, e) y f) «No», g) XAdES
    Enveloped, productor de los ajustes);
  - el PDF, con su `Content-Disposition`;
  - la producción exige los ajustes nuevos (en el test de configuración);
  - la configuración devuelve el bloque `certificado`;
  - `datos_ejemplo`, en `backend/tests/integration/test_datos_ejemplo.py`, carga en `no_verifactu`
    con los registros firmados.
- [ ] T060 [P] [US5] Tests web:
  - `features/sistema/AcercaPage.test.tsx`;
  - el enlace en el menú de usuario y en el pie del menú lateral;
  - `features/configuracion/FacturacionPage.test.tsx`: modalidad fija, VERI\*FACTU desactivada y
    tarjeta del certificado en cada estado.

### Implementation for User Story 5

- [ ] T061 [US5] `backend/app/services/sistema.py` (R-13), la plantilla
  `backend/app/resources/pdf/declaracion.html` («Paper») y la API `backend/app/api/v1/sistema.py`:
  - `GET /v1/sistema`;
  - `GET /v1/sistema/declaracion-responsable/pdf`, con la CSP de los PDF y la excepción del
    `Caddyfile` ampliada a `/api/v1/sistema/declaracion-responsable/pdf`.

  Salen de `PENDIENTES_004`. Hace pasar T059.
- [ ] T062 [US5] `backend/app/services/datos_ejemplo.py`: carga en `no_verifactu` con el certificado
  de `CERTIFICADO_RUTA`. Si no hay ninguno, genera uno de prueba temporal (R-14).
- [ ] T063 [US5] Web:
  - `features/sistema/AcercaPage.tsx` y la ruta `routes/_app/acerca.tsx`;
  - los enlaces en `UserMenu` y en el pie de `Sidebar`;
  - en `FacturacionPage.tsx`, la modalidad fija y la tarjeta «Certificado de firma».

  Hace pasar T060.
- [ ] T064 [US5] Producción:
  - `docker-compose.prod.yml`, con el *secret* del certificado en solo lectura y la ruta;
  - la CLI `estado-certificado` ([contracts/cli.md](contracts/cli.md)) y su comprobación en
    `deploy/verificar-produccion.sh`;
  - `docs/declaraciones/README.md`, con el procedimiento de archivo (RRSIF 13.3).
- [ ] T065 [US5] E2E en `joyeriablanco_web/e2e/acerca.spec.ts`:
  - el empleado abre «Acerca del sistema» y descarga el PDF;
  - en `configuracion-facturacion.spec.ts`, el administrador ve el certificado de prueba.

**Checkpoint**: las cinco historias completas.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [ ] T066 Contrato completo: eliminar `PENDIENTES_004` de `test_contrato_openapi.py`, con el test en
  verde.
- [ ] T067 [P] Logs (FR-033), en `backend/tests/integration/test_logs_facturacion.py`:
  - firmar, generar eventos, comprobar y exportar no dejan en los registros de actividad la
    contraseña, la clave, datos personales ni importes;
  - solo quedan números, tipos y recuentos.
- [ ] T068 [P] Test lento `backend/tests/integration/test_no_verifactu_rendimiento.py`
  (`@pytest.mark.lento`):
  - SC-007: p95 de la emisión con firma por debajo de 1 s;
  - SC-005: exportación de 20.000 registros en menos de 1 minuto;
  - SC-006: comprobación de 20.000 en menos de 3 minutos.

  Si no se llega, paralelizar la verificación (R-9). Anotar los resultados en el quickstart.
- [ ] T069 [P] E2E transversales:
  - `acciones-visibles.spec.ts`: las tablas de «Registro fiscal»;
  - `responsive.spec.ts`: «Registro fiscal», «Acerca del sistema» y la banda a 360 px;
  - `teclado.spec.ts`: las pestañas y el modal de detalle.
- [ ] T070 [P] Imagen de producción: `docker compose -f docker-compose.prod.yml build api` y, en el
  contenedor `read_only` y sin root, firmar un registro con un certificado de prueba montado
  (comprobación manual de humo, anotada en el quickstart).
- [ ] T071 [P] Documentación:
  - `README.md`: módulo «Firma y registro de eventos (No VERI\*FACTU)» ✅ y los comandos nuevos;
  - `CLAUDE.md`: la lista de la CLI;
  - `backend/app/resources/README.md`: `aeat/xsd` y la declaración;
  - `specs/002-facturas/research.md`, R-17: Q-3, Q-8 y Q-11 cerradas como «no aplica».
- [ ] T072 Puertas completas:
  - backend: `uv run pytest`, `-m lento`, ruff, mypy y `verificar-cadena`;
  - web: `lint`, `typecheck`, `test`, `build`, `check:tokens` y `npx playwright test`.
- [ ] T073 Validación manual del [quickstart](quickstart.md) §2 (pasos 1 a 10). La validación con
  VALIDe y la instalación del certificado real quedan **pendientes del responsable** si no se
  pueden hacer en el entorno.

---

## Dependencies & Execution Order

- **Setup (T001–T004)**: sin dependencias. T002, T003 y T004 en paralelo tras T001.
- **Foundational (T005–T021)**:
  - los tests T005–T009, en paralelo;
  - T010–T013, en paralelo;
  - T014 depende de T011 y T013;
  - T016 depende de T015;
  - T017 depende de T014 y T016;
  - T018–T020 dependen de T016 y T017;
  - T021 depende de todo lo anterior.
- **US1 (T022–T029)**: depende de la fundacional. Es el MVP.
- **US2 (T030–T039)**: depende de la fundacional (firma y XML de eventos). Es independiente de US1
  salvo el resumen, que cuenta registros.
- **US3 (T040–T052)**: depende de US1 (registros firmados) y de US2 (eventos).
- **US4 (T053–T058)**: depende de US1 y de US2 (evento de exportación).
- **US5 (T059–T065)**: depende de US1 (certificado en la configuración). Va en paralelo con US2–US4.
- **Polish (T066–T073)**: al final.

### Parallel Opportunities

- Fase 2: los cinco tests T005–T009 a la vez. Después, T011, T012 y T013.
- En cada historia, los tests marcados [P] a la vez, y backend y web por separado.
- US5 en paralelo con US2, US3 y US4, una vez cerrada US1.

### Parallel Example: User Story 3

```text
Tests a la vez: T040 (integridad), T041 (alarmas), T042 (emisión ante anomalía), T043 (API de la cadena), T044 (CLI), T045 (web)
Después: T046 → T047 → T048 / T049 / T050 → T051 → T052
```

## Implementation Strategy

### MVP First (User Story 1)

1. Setup y fundacional: XML, firma, certificado y migración.
2. US1: toda factura firmada y bloqueo sin certificado.
3. **Parar y validar**: emitir y verificar una firma. Después, T029.

### Incremental Delivery

1. US1, el MVP de cumplimiento mínimo.
2. US2 (eventos) → US3 (integridad y alarma) → US4 (exportación). Con eso se cumplen los arts. 6 a
   9 de la Orden.
3. US5 (declaración y configuración), en paralelo, que cierra el art. 15.
4. Polish y puertas, con un commit por fase o historia (`feat(004): …`). Sin push.
