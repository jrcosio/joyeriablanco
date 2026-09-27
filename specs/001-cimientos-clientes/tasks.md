---
description: "Tareas de implementación de la feature 001"
---

# Tasks: Cimientos del sistema, seguridad de acceso y gestión de clientes

**Input**: `specs/001-cimientos-clientes/` ([plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md))

**Prerequisites**: plan.md, spec.md, research.md, data-model.md y contracts/ generados y revisados.

**Tests**: SÍ. La spec los exige (FR-050, SC-012): dominio con TDD, integración contra PostgreSQL
real, componentes web y E2E con Playwright. En cada historia, los tests se escriben antes y deben
fallar antes de implementar.

**Organization**: por historias de usuario, en orden de prioridad. US1 es la base de autenticación
de las demás.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: puede ir en paralelo (ficheros distintos y sin dependencias pendientes).
- **[Story]**: historia de la spec (US1–US8).
- Las rutas son relativas a la raíz del repositorio.

## Path Conventions

- **Backend**: `backend/app/…`, `backend/tests/…`, `backend/alembic/…`.
- **Web**: `joyeriablanco_web/src/…`, `joyeriablanco_web/e2e/…`.
- **Infraestructura**: `docker-compose*.yml`, `infra/`, `deploy/`, `tools/` en la raíz.
- **No se toca** `joyeriablanco_android/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: esqueleto del monorepo, configuración y herramientas de calidad.

- [X] T001 Crear `tools/brand/fuente/` y copiar `temporal/2.png` a `tools/brand/fuente/logo-original.png`. `temporal/` no se borra (se pregunta al final, T117)
- [X] T002 Crear `.env.example` en la raíz con todas las variables de `backend/app/core/config.py` y valores de ejemplo, y ampliar `.gitignore`. Variables: `ENTORNO`, credenciales de `POSTGRES_*`, `jb_owner` y `jb_app`, `DATABASE_URL_APP`, `DATABASE_URL_OWNER`, `ORIGEN_PERMITIDO`, `SESION_*`, `BLOQUEO_*`, `LIMITE_ORIGEN_*`, `SESION_COOKIE_SEGURA`, `DOMINIO`, `TLS_MODO`. Entradas nuevas del `.gitignore`: `joyeriablanco_web/playwright-report/`, `joyeriablanco_web/test-results/`, `joyeriablanco_web/src/api/openapi.json`
- [X] T003 Crear `infra/db/init/01-roles.sh`, que crea los roles `jb_owner` (dueño del esquema) y `jb_app` (solo DML) y las bases `joyeriablanco`, `joyeriablanco_test` y `joyeriablanco_e2e`, con `REVOKE ALL ON SCHEMA public FROM PUBLIC` y los `GRANT` de uso a `jb_app` (research R-11)
- [X] T004 Crear `docker-compose.yml` (research R-15) con tres servicios:
  - `db`: `postgres:18.6-trixie`, volumen `pgdata`, `infra/db/init` montado, `127.0.0.1:5432` y healthcheck.
  - `api`: build `backend/` con target `dev`, código montado, `127.0.0.1:8000` y `depends_on` healthy.
  - `api-e2e`: perfil `e2e`, `127.0.0.1:8001`, BD `joyeriablanco_e2e`, `ENTORNO=e2e`, con sus propias `DATABASE_URL_APP` y `DATABASE_URL_OWNER`.
- [X] T005 Reescribir `backend/pyproject.toml` con las dependencias y versiones de research R-2, el grupo `dev`, `[project.scripts] joyeria = "app.cli:app"` y la configuración de `ruff` (lint y formato), `mypy --strict` (plugin pydantic) y `pytest` (asyncio). Eliminar `backend/main.py` y regenerar `backend/uv.lock` con `uv lock`
- [X] T006 Crear `backend/Dockerfile` multietapa: base `python:3.13.15-slim-trixie` más `ghcr.io/astral-sh/uv:0.12`; target `dev` con recarga en caliente; target `prod` con usuario sin privilegios, `uvicorn --workers 2 --proxy-headers` y healthcheck contra `/api/salud`
- [X] T007 [P] Crear el esqueleto de `joyeriablanco_web/`:
  - `package.json` con las versiones exactas de research R-3, `overrides` de `typescript` para `openapi-typescript` (R-4) y los scripts `dev`, `build`, `preview`, `lint`, `typecheck`, `test`, `gen:api`, `e2e` y `check:tokens`.
  - `vite.config.ts` con React y React Compiler, el plugin de TanStack Router, `@tailwindcss/vite` y el proxy de `/api` a `process.env.VITE_API_PROXY ?? http://localhost:8000`.
  - `tsconfig.json`, `tsconfig.app.json` y `tsconfig.node.json` en modo estricto.
  - `index.html` con `lang="es"`.
  - `src/main.tsx` mínimo.
- [X] T008 [P] Configurar la calidad web: `joyeriablanco_web/eslint.config.js` (typescript-eslint con tipos, react-hooks), `joyeriablanco_web/.prettierrc`, la sección `test` de Vitest en `vite.config.ts` (jsdom) con `joyeriablanco_web/src/test/setup.ts` (jest-dom y MSW) y `joyeriablanco_web/playwright.config.ts` base

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: núcleo del backend y la web del que dependen todas las historias. Incluye el esquema de
usuarios, sesiones y auditoría, porque cualquier operación se audita.

**⚠️ CRITICAL**: ninguna historia empieza hasta cerrar esta fase.

### Backend: núcleo

- [X] T009 Implementar `backend/app/core/config.py` (`Settings` de pydantic-settings con todas las variables de T002, valores por defecto de la spec y validación de `ENTORNO` ∈ {desarrollo, e2e, test, produccion})
- [X] T010 [P] Implementar `backend/app/core/db.py`: motor asíncrono psycopg con `DATABASE_URL_APP`, `async_sessionmaker` y dependencia `get_db` con transacción por petición
- [X] T011 [P] Implementar `backend/app/core/logging.py`: logs JSON a stdout (python-json-logger), `request_id` por petición y filtro de redacción de contraseñas, tokens, cookies y datos personales (FR-053)
- [X] T012 [P] Implementar `backend/app/core/errors.py`: excepciones de dominio (`ValidationError`, `NotFound`, `Conflict` con subtipos, `Forbidden`, `Unauthenticated`, `RateLimited`), respuesta RFC 9457 con el catálogo de `type` de `contracts/openapi.yaml`, manejadores de `RequestValidationError` (errores por campo en español) y un manejador genérico 500 sin trazas (FR-049)
- [X] T013 [P] Implementar `backend/app/core/http.py`: middleware de `request_id`, `Cache-Control: no-store` en `/api/v1/*`, extracción de la IP del cliente (respetando las cabeceras de proxy de uvicorn) y utilidad `check_origin(request)` contra `ORIGEN_PERMITIDO` (research R-6, R-8)
- [X] T014 Implementar `backend/app/models/base.py`: `DeclarativeBase` con `naming_convention`, tipo UUID con `server_default=text("uuidv7()")` y mixin de marcas `creado_en`/`actualizado_en` con `timestamptz`
- [X] T015 Configurar Alembic con `backend/alembic.ini` y `backend/alembic/env.py`, que conecta con `DATABASE_URL_OWNER` y usa `target_metadata` de `app.models`. Crear la migración `backend/alembic/versions/0001_extensiones_y_privilegios.py`:
  - Extensiones `unaccent` y `pg_trgm`.
  - Función `inmutable_unaccent(text)` IMMUTABLE.
  - `ALTER DEFAULT PRIVILEGES FOR ROLE jb_owner IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO jb_app` y `USAGE` en secuencias.
- [X] T016 Crear los modelos `backend/app/models/usuario.py`, `backend/app/models/sesion.py` y `backend/app/models/evento_auditoria.py` según data-model.md (columnas, CHECK, índices, catálogo `tipo`) y exportarlos en `backend/app/models/__init__.py`
- [X] T017 Crear la migración `backend/alembic/versions/0002_usuarios_sesiones_auditoria.py` con las tablas, índices y el índice único `lower(nombre_usuario)`. En `eventos_auditoria`: `REVOKE UPDATE, DELETE, TRUNCATE … FROM jb_app`, trigger `BEFORE UPDATE OR DELETE` (por fila) y trigger `BEFORE TRUNCATE` (por sentencia), ambos con `RAISE EXCEPTION 'La auditoría es inalterable'` (FR-022, research R-10)
- [X] T018 Implementar `backend/app/repositories/auditoria.py` (`insert_event`) y `backend/app/services/auditoria.py`: `record_event(tipo, actor, origen, detalle, …)` con cálculo del *diff* `{campo: [antes, después]}` y exclusión de secretos (FR-020, FR-021)
- [X] T019 Implementar la factoría `backend/app/main.py` (routers, middlewares y manejadores de errores), `backend/app/api/salud.py` (`GET /api/salud`, que solo devuelve `{"estado":"ok"}` o 503 tras un ping a la BD, FR-049) y el comando `exportar-openapi` en `backend/app/cli.py` (Typer), que escribe `joyeriablanco_web/src/api/openapi.json`
- [X] T020 Crear `backend/tests/conftest.py`:
  - Settings de test apuntando a `joyeriablanco_test`, con `TEST_DATABASE_URL_APP` y `TEST_DATABASE_URL_OWNER` (por defecto `127.0.0.1:5432`, para ejecutar `uv run pytest` desde el host; sobrescribibles dentro del contenedor).
  - `alembic upgrade head` una vez por sesión como `jb_owner`.
  - Sesión de BD por test con *savepoint* revertido.
  - `httpx.AsyncClient` con `ASGITransport`.
  - Factorías de usuario y sesión.
  - Fixture `db_owner` y fixture `db_app` para tests de privilegios.
- [X] T021 [P] Test `backend/tests/integration/test_salud.py`: 200 `{"estado":"ok"}`, sin cabeceras de versión y sin autenticación
- [X] T022 [P] Test `backend/tests/integration/test_auditoria_inalterable.py`: `UPDATE`, `DELETE` y `TRUNCATE` sobre `eventos_auditoria` fallan como `jb_app` (privilegios) y como `jb_owner` (triggers). `jb_app` no puede `CREATE TABLE` ni `ALTER TABLE` (FR-022, FR-047, SC-007)

### Web: núcleo

- [X] T023 Crear `joyeriablanco_web/src/styles/tokens.css`, **la única definición de tokens** (constitución 1.1.0), a partir de `docs/DESIGN.md`:
  - `@theme` de Tailwind v4 con todos los colores del frontmatter (incluidos `success`, `warning` y `danger`).
  - Familias Bodoni Moda y Manrope.
  - Utilidades de la escala tipográfica (`headline-*`, `title-*`, `body-*`, `label-*`).
  - Espaciado (`space-*`, `gutter` y `margin`).
  - Radio global a 0 y sombra de nivel 2.
- [X] T024 Crear `joyeriablanco_web/src/styles/base.css`: importaciones de `@fontsource/bodoni-moda` y `@fontsource-variable/manrope`, `body` con `background` y `on-surface`, cifras tabulares donde procede y foco visible (contorno de 1 px en `tertiary` con 2 px de separación en controles no-campo, FR-052)
- [X] T025 Generar tipos con `joyeriablanco_web/src/api/schema.gen.ts` (script `gen:api`: `openapi-typescript src/api/openapi.json`) e implementar el cliente `joyeriablanco_web/src/api/client.ts` (openapi-fetch):
  - Middleware que añade `X-CSRF-Token` en POST, PUT, PATCH y DELETE.
  - Parseo de `application/problem+json` a un tipo `Problema`.
  - Gancho `onUnauthenticated` para 401 y para 403 con `type` `csrf` (FR-011).
- [X] T026 Crear `joyeriablanco_web/src/router.tsx`, `joyeriablanco_web/src/routes/__root.tsx` (con componente de 404, FR-041) y `joyeriablanco_web/src/main.tsx` con `QueryClientProvider` y `RouterProvider`
- [X] T027 [P] Crear las primitivas sobre react-aria-components con los estilos de `contracts/ui-rutas.md` §"Aplicación de DESIGN.md": `Button.tsx` (primario, secundario, ghost/destructivo), `TextField.tsx`, `Select.tsx` y `ComboBox.tsx`, en `joyeriablanco_web/src/components/ui/`
- [X] T028 [P] Crear `Dialog.tsx` y `Drawer.tsx` (nivel 2; pantalla completa por debajo de 768 px) y `Toast.tsx` (nivel 3, 5 s, se puede cerrar), en `joyeriablanco_web/src/components/ui/`
- [X] T029 [P] Crear `Chip.tsx` (success, warning, danger), `Card.tsx`, `Kpi.tsx`, `Skeleton.tsx`, `EmptyState.tsx`, `ErrorState.tsx` (con Reintentar) y `Pagination.tsx`, en `joyeriablanco_web/src/components/ui/`
- [X] T030 [P] Crear las utilidades en `joyeriablanco_web/src/lib/`, con sus tests `*.test.ts`:
  - `fechas.ts`: fecha larga es-ES en Europe/Madrid con la primera letra en mayúscula, y formato "27/05/2025, 14:32".
  - `texto.ts`: iniciales según FR-056.
  - `paises.ts`: `Intl.DisplayNames('es')`, orden alfabético con España primero (FR-060).

**Checkpoint**: la base está lista. `docker compose up -d`, las migraciones y `GET /api/salud` funcionan; la web compila.

---

## Phase 3: User Story 1 - Acceso seguro y navegación por la aplicación (Priority: P1) 🎯 MVP

**Goal**: acceso con usuario y contraseña, sesiones seguras, cambio obligatorio de contraseña
temporal y shell completo de la aplicación con el menú a la izquierda.

**Independent Test**: con un administrador creado por consola, se inicia sesión, se cambia la
contraseña temporal, se navega por el shell, se cierra sesión y se comprueba que sin sesión no se
accede a nada. También los bloqueos, la caducidad y las pantallas 403 y 404.

### Tests for User Story 1 ⚠️ (escribir primero, deben fallar)

- [X] T031 [P] [US1] Test `backend/tests/unit/domain/test_contrasenas.py`:
  - Longitudes 11, 12, 128 y 129.
  - Contraseña de la lista común en mayúsculas o minúsculas.
  - Contraseña que contiene el usuario sin distinguir mayúsculas.
  - Ausencia de reglas de composición.
  - La temporal generada cumple la política (FR-008, FR-015).
- [X] T032 [P] [US1] Test `backend/tests/unit/test_security.py`: el hash Argon2id se verifica y se hace *rehash*; el token tiene 256 bits y su SHA-256 es estable; la comparación es en tiempo constante
- [X] T033 [P] [US1] Test `backend/tests/integration/test_sesion_login.py`:
  - **Login correcto**: cookie `HttpOnly` y `SameSite=Strict`, cuyo nombre depende de `SESION_COOKIE_SEGURA`. La respuesta trae `csrf_token`.
  - **Mensajes genéricos idénticos** para usuario inexistente, contraseña errónea, cuenta bloqueada, cuenta desactivada y temporal caducada (72 h).
  - **Bloqueo por cuenta**: el quinto fallo bloquea 15 minutos, también con la contraseña correcta. El contador se reinicia con un acceso correcto (FR-006, FR-007, FR-015).
  - **Límite por origen**: 20 fallos en 10 minutos → 429 `limite-origen` con mensaje propio y evento `acceso_limitado`, que no suma al límite.
  - **Origen**: `Origin` no permitido → 403 `origen`.
- [X] T034 [P] [US1] Test `backend/tests/integration/test_sesion_ciclo.py`:
  - **Sin sesión**: `GET /v1/sesion` → 401.
  - **Inactividad**: pasados 30 minutos, 401. La actividad se registra como mucho una vez por minuto.
  - **Caducidad absoluta**: a las 10 horas, 401.
  - **Cierre de sesión**: `DELETE /v1/sesion` invalida la sesión en el servidor.
  - **Contraseña temporal**: solo se permiten `GET/DELETE /v1/sesion` y `PUT /v1/cuenta/contrasena`; el resto → 403 `contrasena-temporal`.
  - **CSRF**: sin `X-CSRF-Token` o con uno erróneo → 403 `csrf`.
  - **Cambio de contraseña**: `PUT /v1/cuenta/contrasena` revoca las demás sesiones y conserva la actual.
  - **Auditoría**: se registran `acceso_correcto`, `acceso_fallido`, `acceso_bloqueado`, `cierre_sesion` y `contrasena_cambiada` (FR-003 a FR-005, FR-009, FR-011, FR-019, FR-020).
- [X] T035 [P] [US1] Test `backend/tests/integration/test_cli.py`:
  - `crear-admin`: crea un administrador con temporal de 72 h y muestra la contraseña una vez.
  - `restablecer-admin`: restablece y levanta el bloqueo.
  - `purgar-sesiones`: borra solo las caducadas o revocadas de más de 30 días.
  - Los eventos llevan `actor_nombre_usuario='consola'` (FR-018, FR-020, FR-054).
- [X] T036 [P] [US1] Tests web:
  - `joyeriablanco_web/src/features/acceso/LoginPage.test.tsx`: errores genéricos, mensaje de 429 y redirección a `volver`.
  - `joyeriablanco_web/src/components/layout/Sidebar.test.tsx`: Facturas y Presupuestos deshabilitados con "Próximamente"; Configuración solo para administradores.
  - `joyeriablanco_web/src/components/layout/UserMenu.test.tsx`: iniciales, nombre, rol y opciones.

### Implementation for User Story 1

- [X] T037 [P] [US1] Descargar la lista top 100k del NCSC (`PwnedPasswordsTop100k`, OGL v3) en `backend/app/resources/contrasenas_comunes.txt` y añadir las entradas propias (`joyeria`, `blanco`, `joyeriablanco`, `contraseña`…). Registrar la URL, la fecha y el SHA-256 en `backend/app/resources/README.md` y en research R-7
- [X] T038 [P] [US1] Implementar `backend/app/domain/contrasenas.py`: `validate_password(contrasena, nombre_usuario) -> list[str]` con mensajes en español y `generate_temporary_password()` (16 caracteres sin ambigüedades en grupos de 4)
- [X] T039 [P] [US1] Implementar `backend/app/core/security.py`: `PasswordHasher` Argon2id (parámetros por defecto de argon2-cffi), `hash_password`, `verify_password` con `needs_rehash`, `DUMMY_HASH`, `new_session_token()`, `token_fingerprint()` y `constant_time_equals()`
- [X] T040 [US1] Implementar `backend/app/repositories/usuarios.py` (búsqueda por `lower(nombre_usuario)`, contadores de fallos, bloqueo) y `backend/app/repositories/sesiones.py` (crear, buscar por huella, `touch` con umbral de 60 s, revocar una, revocar todas salvo una, purgar)
- [X] T041 [US1] Implementar `backend/app/services/auth.py` con `login`, `validate_session`, `logout` y `change_own_password`:
  - **Login**: límite por origen sobre la auditoría, verificación de la contraseña contra el hash (o contra `DUMMY_HASH` si el usuario no existe), bloqueo por cuenta, control de temporal caducada y rotación de la sesión.
  - **Validación**: ventanas de inactividad y absoluta, usuario activo.
  - **Auditoría**: un evento por cada caso.
- [X] T042 [US1] Implementar `backend/app/api/deps.py`:
  - `get_current_session`: lee la cookie, valida la sesión, aplica la regla de contraseña temporal y la puerta de `Origin` y CSRF en los métodos que modifican datos.
  - `require_admin`.
  - `get_client_origin` (IP y agente).
- [X] T043 [P] [US1] Crear los esquemas `backend/app/schemas/comunes.py` (`Problema`, `Pagina[T]`), `backend/app/schemas/sesion.py` (`CredencialesEntrada`, `SesionSalida`, `CambioContrasenaEntrada`) y `backend/app/schemas/usuario.py` (`UsuarioSalida`, `UsuarioReferencia`) según `contracts/openapi.yaml`
- [X] T044 [US1] Implementar `backend/app/api/v1/sesion.py` (`POST`, `GET` y `DELETE /v1/sesion`, con `Set-Cookie` y borrado de la cookie) y `backend/app/api/v1/cuenta.py` (`PUT /v1/cuenta/contrasena`), sin lógica de negocio en el router (principio V)
- [X] T045 [US1] Añadir a `backend/app/cli.py` los comandos `crear-admin --usuario --nombre`, `restablecer-admin --usuario` y `purgar-sesiones`, auditados como consola. La purga también se ejecuta en el arranque de la API (FR-054)
- [X] T046 [P] [US1] Crear `tools/brand/procesar_logo.py` (PEP 723, Pillow) según research R-18:
  - Máscara circular antialiasada ×4.
  - Neutralización del bisel gris.
  - Recorte al contenido.
  - Exportación de `joyeriablanco_web/src/assets/brand/logo.png` (512 px) y en `joyeriablanco_web/public/` de `favicon.ico` (16/32/48), `favicon-32.png`, `apple-touch-icon.png` (180), `icon-192.png`, `icon-512.png` y `manifest.webmanifest`.

  Ejecutarlo y revisar visualmente el resultado.
- [X] T047 [US1] Regenerar los tipos (`uv run joyeria exportar-openapi` + `npm run gen:api`). Implementar `joyeriablanco_web/src/auth/session.ts`: query `useSession` sobre `GET /v1/sesion` y almacén del `csrf_token` para el cliente HTTP. Implementar `joyeriablanco_web/src/auth/guards.ts` con `requireSession`, `requireAdmin` y `requireTemporaryPasswordChange` para `beforeLoad`, y redirecciones a `/acceso?volver=`, `/cambiar-contrasena` y `/acceso-denegado`
- [X] T048 [US1] Conectar en `joyeriablanco_web/src/api/client.ts` el manejo global de 401 y de `csrf`: vaciar la caché, mostrar el aviso "Tu sesión ha caducado" y navegar a `/acceso?volver=<ruta>` sin conservar borradores, según el caso límite de la spec y `contracts/ui-rutas.md` (FR-004, FR-011)
- [X] T049 [US1] Crear `joyeriablanco_web/src/features/acceso/LoginPage.tsx` y la ruta `joyeriablanco_web/src/routes/acceso.tsx`: logo, formulario accesible, mensajes genéricos y de límite, redirección a `volver`. Sin shell
- [X] T050 [US1] Crear `joyeriablanco_web/src/features/cuenta/CambioContrasenaForm.tsx` (contraseña actual, nueva y confirmación, con los motivos de rechazo del servidor por campo) y la ruta `joyeriablanco_web/src/routes/cambiar-contrasena.tsx`, sin shell (FR-009, FR-056)
- [X] T051 [US1] Crear `joyeriablanco_web/src/components/layout/Sidebar.tsx`:
  - Logo con texto alternativo y "JOYERÍA BLANCO" con filete dorado.
  - Entradas activas, deshabilitadas con el chip "Próximamente", y Configuración solo para administradores.
  - Cajón accesible por teclado por debajo de 1024 px.
- [X] T052 [US1] Crear `joyeriablanco_web/src/components/layout/Header.tsx` (contexto "Gestión de facturación", fecha larga que se recalcula al cambiar de día y **sin campana de notificaciones**, FR-039), `joyeriablanco_web/src/components/layout/UserMenu.tsx` (iniciales, nombre, rol, Mi cuenta y Cerrar sesión con `DELETE /v1/sesion`) y `joyeriablanco_web/src/components/layout/AppShell.tsx`
- [X] T053 [US1] Crear las rutas protegidas:
  - `joyeriablanco_web/src/routes/_app.tsx`: layout con `requireSession` y AppShell.
  - `joyeriablanco_web/src/routes/_app/index.tsx`: redirige a `/clientes`.
  - `joyeriablanco_web/src/routes/_app/clientes.tsx`: provisional con el título "Clientes", el botón "Nuevo cliente" y `<Outlet/>` para los paneles de US2; se completa en US3.
  - `joyeriablanco_web/src/routes/acceso-denegado.tsx`: título, explicación y "Volver a Clientes" (FR-041).

**Checkpoint**: US1 funciona de forma independiente. Acceso, cambio de temporal, shell, cierre de sesión, bloqueos, caducidad y pantallas 403 y 404.

---

## Phase 4: User Story 2 - Alta y edición de clientes (Priority: P2)

**Goal**: dar de alta y editar clientes con la identificación fiscal validada según fuente oficial,
sin duplicados y con control de edición concurrente.

**Independent Test**: con sesión iniciada, se crean clientes de ambos tipos con NIF, NIF-IVA y
pasaporte, se edita uno y se comprueban los rechazos (carácter de control, duplicado, código postal
y provincia incoherentes) y el conflicto de versión.

### Tests for User Story 2 ⚠️

- [X] T054 [P] [US2] Test `backend/tests/unit/domain/test_identificacion.py` (research R-20):
  - **Normalización**: espacios, `-`, `.`, `/` y minúsculas.
  - **DNI**: `12345678Z` válido y `12345678A` inválido.
  - **NIE**: X, Y o Z con su letra.
  - **Estructura** de entidades (letras A–W admitidas; I, O, T rechazadas) y de K, L, M.
  - **NIF-IVA**: cada fila de la tabla oficial (`EL` para GR, `XI` para GB, RO sin ceros a la izquierda; ES rechazado) y adición del prefijo si falta.
  - **`allowed_identificacion_tipos`** para ES, un país UE y un país no UE.
- [X] T055 [P] [US2] Test `backend/tests/unit/domain/test_codigos_postales.py`: `29001` → 29 (Málaga); `51001` → Ceuta; `52001` → Melilla; `00123` y `53000` → error; formato distinto de 5 dígitos → error
- [X] T056 [P] [US2] Test `backend/tests/integration/test_clientes_alta_edicion.py`:
  - **Alta válida**: 201, con `creado_por` y evento `cliente_creado`.
  - **Validaciones**: 422 con errores por campo en español (NIF inválido, obligatorios vacíos tras recortar, correo, teléfono, nombre de más de 120, combinación de país y tipo no admitida).
  - **Duplicado**: 409 `duplicado` con `cliente_existente`.
  - **Código postal y provincia**: CP → provincia asignada; CP y provincia incoherentes → 422 en `provincia_codigo`; al cambiar de país se descarta la provincia que ya no aplica.
  - **Normalización**: correo en minúsculas y textos recortados.
  - **Edición**: `PUT` con versión correcta → 200 y `cliente_editado` con el *diff*; con versión desfasada → 409 `conflicto-version`.
  - **Referencias** (FR-023 a FR-030, FR-055).
- [X] T057 [P] [US2] Test web `joyeriablanco_web/src/features/clientes/ClienteForm.test.tsx` con MSW:
  - Tipos de identificación filtrados por país según `ambito`.
  - Errores del servidor mapeados a su campo.
  - Aviso de cambios sin guardar.
  - Diálogo de conflicto de versión (Recargar / Seguir editando).
  - Enlace al cliente existente ante un duplicado.

### Implementation for User Story 2

- [X] T058 [P] [US2] Implementar `backend/app/domain/identificacion.py`: `normalize_identificacion`, `classify_nif`, `validate_nif`, la tabla `NIF_IVA_ESTRUCTURAS` (literal de la nota 1, con referencia a F-3), `validate_nif_iva(pais, numero) -> canónico` y `allowed_identificacion_tipos(pais)`
- [X] T059 [P] [US2] Implementar `backend/app/domain/codigos_postales.py`: `provincia_from_codigo_postal(cp) -> str` (01–52; F-7 y R-20.3)
- [X] T060 [US2] Crear los modelos `backend/app/models/provincia.py` y `backend/app/models/cliente.py` según data-model.md (CHECK de país y tipo, forma del NIF, provincia según el país, CP español, `version_id_col`, `texto_busqueda` generada)
- [X] T061 [US2] Crear la migración `backend/alembic/versions/0003_provincias_clientes.py`:
  - Tabla `provincias` con los 52 registros de research R-20.3 (`nombre` literal INE y `nombre_visible`) y solo `SELECT` para `jb_app`.
  - Tabla `clientes` con restricciones, `UNIQUE` de la identificación y columna generada `texto_busqueda = inmutable_unaccent(lower(nombre || ' ' || identificacion_numero || ' ' || coalesce(localidad,'')))`.
  - Índices: GIN trigram, `(activo, nombre, id)`, `provincia_codigo`, `tipo` y `(creado_en, id)`.
- [X] T062 [US2] Implementar `backend/app/repositories/catalogos.py` (provincias), `backend/app/services/catalogos.py` (provincias, países de pycountry, `paises_nif_iva` y `tipos_identificacion` con `ambito`) y `backend/app/schemas/catalogos.py`
- [X] T063 [US2] Implementar `backend/app/repositories/clientes.py` con `get`, `get_by_identificacion`, `create` y `update` (captura `StaleDataError` y la convierte en conflicto de versión)
- [X] T064 [US2] Implementar `create_cliente` y `update_cliente` en `backend/app/services/clientes.py`:
  - Recorte de textos y conversión de vacíos en `None`, normalización y validaciones de dominio.
  - Derivación y coherencia de la provincia; limpieza según el país.
  - Detección de duplicados con `cliente_existente`.
  - Trazabilidad y auditoría con el *diff*.
- [X] T065 [P] [US2] Crear los esquemas `backend/app/schemas/cliente.py` (`ClienteEntrada`, `ClienteEdicionEntrada`, `ClienteResumenSalida`, `ClienteSalida`, `ProblemaDuplicado`) según el contrato, sin exponer modelos ORM
- [X] T066 [US2] Implementar `backend/app/api/v1/catalogos.py` (`GET /v1/catalogos`) y, en `backend/app/api/v1/clientes.py`, `POST /v1/clientes`, `GET /v1/clientes/{id}` y `PUT /v1/clientes/{id}`
- [X] T067 [US2] Regenerar los tipos (`exportar-openapi` + `gen:api`) y crear las queries y mutaciones de TanStack Query en `joyeriablanco_web/src/api/queries/catalogos.ts` y `joyeriablanco_web/src/api/queries/clientes.ts` (alta, ficha, edición, invalidaciones)
- [X] T068 [US2] Crear `joyeriablanco_web/src/features/clientes/ClienteForm.tsx` (React Hook Form + Zod de forma):
  - Selector de país con `lib/paises.ts` y tipos de identificación filtrados por `ambito`.
  - Provincia rellenada desde el CP con el catálogo, como previsualización; la verdad la decide el servidor.
  - Errores de servidor en su campo.
  - Guarda de cambios sin guardar.
  - Diálogo de conflicto (FR-030) y enlace al cliente existente ante un duplicado.
- [X] T069 [US2] Crear `joyeriablanco_web/src/features/clientes/ClientePanel.tsx` (Drawer de nivel 2, pantalla completa en móvil, sección de trazabilidad con fechas en formato es-ES, avisos al guardar) y las rutas `joyeriablanco_web/src/routes/_app/clientes/nuevo.tsx` y `joyeriablanco_web/src/routes/_app/clientes/$clienteId.tsx`

**Checkpoint**: US1 + US2. Se pueden crear y editar clientes válidos desde la web.

---

## Phase 5: User Story 3 - Consulta, búsqueda y filtrado de la cartera (Priority: P2)

**Goal**: listado paginado con búsqueda sin tildes ni mayúsculas, filtros, ordenación e
indicadores, fiel al mockup con el menú a la izquierda.

**Independent Test**: con datos cargados, se comprueban la búsqueda (también de NIF con
separadores), cada filtro y su combinación, las ordenaciones, la paginación y los indicadores.

### Tests for User Story 3 ⚠️

- [X] T070 [P] [US3] Test `backend/tests/integration/test_clientes_listado.py`:
  - **Búsqueda**: "maria lopez" encuentra "María López García"; `12.345.678-Z` encuentra `12345678Z`; `%` y `_` se buscan literalmente; término de más de 100 caracteres → 422.
  - **Filtros**: provincia, tipo y estado (activos por defecto), combinados con la búsqueda.
  - **Orden**: las cuatro ordenaciones, con desempate por `id` sin duplicados entre páginas.
  - **Paginación**: página posterior a la última → lista vacía con el total.
  - **Indicadores**: `activos` y `nuevos_este_anio` globales, con el límite de año en Europe/Madrid (FR-031 a FR-034).
- [X] T071 [P] [US3] Test web `joyeriablanco_web/src/features/clientes/ClientesPage.test.tsx` con MSW:
  - Esqueletos sin desplazamiento.
  - Estado vacío "no hay resultados" (con limpiar filtros) frente a "todavía no hay clientes".
  - Estado de error con Reintentar.
  - Filtros reflejados en la URL.
  - Tarjetas en móvil.

### Implementation for User Story 3

- [X] T072 [US3] Añadir a `backend/app/repositories/clientes.py` los métodos `list_clientes` (ILIKE sobre `texto_busqueda` con el término normalizado y escapado, también en su variante sin separadores; filtros; orden con desempate `id`; *offset* y total) y `count_indicadores` (Europe/Madrid)
- [X] T073 [US3] Añadir `list_clientes` e `indicadores` a `backend/app/services/clientes.py`, y `GET /v1/clientes` y `GET /v1/clientes/indicadores` a `backend/app/api/v1/clientes.py`, registradas antes de `/{id}`
- [X] T074 [P] [US3] Crear `joyeriablanco_web/src/features/clientes/IndicadoresClientes.tsx`: dos Kpi (iconos Lucide `Users` y `UserPlus`, cifra en Bodoni `headline-lg`) con esqueleto
- [X] T075 [P] [US3] Crear `joyeriablanco_web/src/features/clientes/FiltrosClientes.tsx`: búsqueda con espera de 300 ms, provincia (`nombre_visible`), tipo, estado y orden. Todo vinculado a los *search params*; apilado en móvil
- [X] T076 [P] [US3] Crear `joyeriablanco_web/src/features/clientes/TablaClientes.tsx`:
  - Columnas de escritorio y tableta según FR-059, **sin columna "Facturas"** (FR-035); tarjetas en móvil.
  - Chip de estado y nombre en `title-md` con el tipo en `label-sm` color `primary`.
  - Acción de editar con etiqueta accesible "Editar cliente {nombre}" (FR-060).
- [X] T077 [US3] Crear `joyeriablanco_web/src/features/clientes/ClientesPage.tsx` (título Bodoni `headline-xl`, subtítulo, "Nuevo cliente", indicadores, filtros, tabla, paginación y los estados de FR-057) y completar `joyeriablanco_web/src/routes/_app/clientes.tsx` con `validateSearch` (Zod) y el `<Outlet/>` para los paneles

**Checkpoint**: US1–US3. La pantalla Clientes es completa y conforme al mockup, con las desviaciones justificadas.

---

## Phase 6: User Story 7 - Puesta en marcha del entorno de trabajo (Priority: P2)

**Goal**: entorno reproducible con datos de ejemplo e infraestructura E2E; primeros recorridos E2E
de US1–US3.

**Independent Test**: en un equipo limpio, se sigue quickstart §1 y se llega en menos de 15 minutos
a la aplicación en marcha con administrador y datos de ejemplo. Los E2E de US1–US3 pasan.

- [X] T078 [P] [US7] Test `backend/tests/integration/test_datos_ejemplo.py`: crea unos 40 clientes que superan las validaciones de dominio y los usuarios `admin.demo` y `empleado.demo`; es idempotente; se niega con `ENTORNO=produccion` (FR-045)
- [X] T079 [US7] Implementar en `backend/app/cli.py` los comandos:
  - `cargar-datos-ejemplo [--clientes N]`: Faker `es_ES`; particulares con DNI o NIE con la letra calculada según el algoritmo oficial, y empresas con NIF de entidad que solo cumple la estructura (research R-19); marcador de carga, "(EJEMPLO)" en observaciones, a través de los servicios, negativa en producción.
  - `reiniciar-bd-e2e`: solo con `ENTORNO=e2e`; reconstruye la BD con `alembic downgrade base` + `upgrade head` como `jb_owner`. No vacía la auditoría, que es inalterable.
- [X] T080 [US7] Crear `joyeriablanco_web/e2e/global-setup.ts` (`docker compose exec api-e2e` → `alembic upgrade head`, `reiniciar-bd-e2e` y `cargar-datos-ejemplo`; fija contraseñas conocidas de prueba) y `joyeriablanco_web/e2e/helpers/db.ts` (envejecer sesiones con `psql` en `db`). Completar `joyeriablanco_web/playwright.config.ts` (webServer Vite con `VITE_API_PROXY=http://localhost:8001` y Chromium)
- [X] T081 [P] [US7] E2E `joyeriablanco_web/e2e/acceso.spec.ts`: acceso y cambio de temporal; mensajes genéricos; cierre de sesión; sesión caducada que vuelve a la ruta; 404; 403 como empleado (US1)
- [X] T082 [P] [US7] E2E `joyeriablanco_web/e2e/clientes.spec.ts`: alta con NIF y CP → provincia; error de carácter de control; edición; búsqueda "maria lopez"; filtros y orden; conflicto de versión con dos contextos (US2, US3)
- [X] T083 [P] [US7] E2E `joyeriablanco_web/e2e/teclado.spec.ts`: recorrido completo solo con teclado, del inicio de sesión al alta de cliente, con foco siempre visible (FR-050, FR-052)
- [X] T084 [US7] Validar quickstart §1 desde cero (volúmenes eliminados), cronometrar SC-010 y corregir `specs/001-cimientos-clientes/quickstart.md` si algún paso no es exacto

**Checkpoint**: el entorno es reproducible y los E2E de US1–US3 están en verde.

---

## Phase 7: User Story 4 - Desactivar, reactivar y borrar clientes (Priority: P3)

**Goal**: ciclo de vida del cliente, con baja lógica y borrado definitivo restringido.

**Independent Test**: se desactiva, se encuentra con "Inactivos" y se reactiva. Se borra como
administrador un cliente sin documentos. Un empleado no puede borrar.

- [X] T085 [P] [US4] Test `backend/tests/integration/test_clientes_ciclo_vida.py`:
  - **Desactivar y reactivar**: idempotentes, sin evento duplicado, y cambian los indicadores.
  - **Borrado como administrador**: 204, con instantánea en la auditoría y `cliente_id` conservado sin FK.
  - **Borrado como empleado**: 403.
  - **Con documentos**: con `ClienteDocumentosChecker` falso que devuelve `True` → 409 `cliente-con-documentos` (FR-036, FR-037).
- [X] T086 [US4] Crear el puerto `backend/app/services/documentos.py` (`ClienteDocumentosChecker`, protocolo con una implementación nula que devuelve `False` e inyección por dependencia) e implementar `deactivate`, `reactivate` y `delete` en `backend/app/services/clientes.py` y `backend/app/repositories/clientes.py`
- [X] T087 [US4] Añadir `POST /v1/clientes/{id}/desactivacion`, `POST /v1/clientes/{id}/reactivacion` y `DELETE /v1/clientes/{id}` (con `require_admin`) en `backend/app/api/v1/clientes.py`
- [X] T088 [US4] Añadir a `ClientePanel.tsx` las acciones Desactivar (confirmación), Reactivar y Borrar (solo admin; confirmación reforzada escribiendo la identificación), con avisos. En `ClienteForm.tsx`, ante un duplicado inactivo, ofrecer "Reactivar" (FR-058). Tests en `joyeriablanco_web/src/features/clientes/ClientePanel.test.tsx`
- [X] T089 [P] [US4] E2E `joyeriablanco_web/e2e/clientes-ciclo-vida.spec.ts`: desactivar → sale del listado → aparece con "Inactivos" → reactivar; borrado reforzado como administrador; el empleado no ve Borrar

**Checkpoint**: US4 funciona de forma independiente.

---

## Phase 8: User Story 5 - Gestión de usuarios y consulta de auditoría (Priority: P3)

**Goal**: el administrador gestiona usuarios (alta con temporal, rol, desactivar, reactivar,
restablecer) con revocación inmediata de sesiones, y consulta la auditoría.

**Independent Test**: el administrador crea un empleado, entra con él y comprueba sus límites; le
restablece la contraseña y lo desactiva con una sesión abierta, que deja de funcionar; filtra la
auditoría.

### Tests for User Story 5 ⚠️

- [X] T090 [P] [US5] Test `backend/tests/integration/test_usuarios.py`:
  - **Alta**: 201 con temporal devuelta una sola vez; nombre de usuario duplicado sin distinguir mayúsculas → 409.
  - **Revocación**: cambiar el rol, desactivar o restablecer revocan todas las sesiones del afectado; el restablecimiento levanta el bloqueo.
  - **Último administrador**: → 409 `ultimo-administrador`, también con dos peticiones concurrentes.
  - **Sobre la propia cuenta**: desactivarse o cambiarse el rol → 409 `autogestion`.
  - **Empleado**: 403 en todos los endpoints.
  - **Auditoría**: eventos de usuario (FR-012 a FR-017).
- [X] T091 [P] [US5] Test `backend/tests/integration/test_auditoria_consulta.py`: filtros por fechas, usuario (actor o afectado), tipo y cliente, combinables; orden descendente; paginación; empleado → 403 (FR-051)

### Implementation for User Story 5

- [X] T092 [US5] Implementar `backend/app/services/usuarios.py` (alta con temporal de 72 h, edición de nombre y rol, desactivar, reactivar y restablecer; regla del último administrador con `SELECT … FOR UPDATE` y regla de la propia cuenta; revocación de sesiones; auditoría) y ampliar `backend/app/repositories/usuarios.py` (listado y bloqueo de administradores activos)
- [X] T093 [P] [US5] Crear los esquemas `UsuarioAltaEntrada`, `UsuarioEdicionEntrada` y `UsuarioConContrasenaTemporalSalida` en `backend/app/schemas/usuario.py`
- [X] T094 [US5] Implementar `backend/app/api/v1/usuarios.py` (las seis operaciones del contrato con `require_admin`)
- [X] T095 [US5] Añadir la consulta paginada y filtrada a `backend/app/repositories/auditoria.py` y `backend/app/services/auditoria.py`, crear `backend/app/schemas/auditoria.py` (`EventoSalida`, `PaginaEventos`) e implementar `backend/app/api/v1/auditoria.py` con `require_admin`
- [X] T096 [US5] Regenerar los tipos (`exportar-openapi` + `gen:api`) y crear las queries en `joyeriablanco_web/src/api/queries/usuarios.ts` y `joyeriablanco_web/src/api/queries/auditoria.ts`
- [X] T097 [US5] Crear las rutas `joyeriablanco_web/src/routes/_app/configuracion.tsx` (layout con `requireAdmin` y navegación Usuarios/Auditoría) y `joyeriablanco_web/src/routes/_app/configuracion/index.tsx` (redirige a `usuarios`)
- [X] T098 [US5] Crear `joyeriablanco_web/src/features/usuarios/UsuariosPage.tsx`, `UsuarioAltaDialog.tsx` y `ContrasenaTemporalDialog.tsx` (se muestra una vez, botón copiar, aviso, cierre solo con confirmación explícita), con las acciones de rol, desactivar, reactivar y restablecer y sus confirmaciones y avisos. Ruta `joyeriablanco_web/src/routes/_app/configuracion/usuarios.tsx`
- [X] T099 [US5] Crear `joyeriablanco_web/src/features/auditoria/AuditoriaPage.tsx` (filtros, tabla con fechas es-ES, detalle del evento con el *diff* en un panel) y la ruta `joyeriablanco_web/src/routes/_app/configuracion/auditoria.tsx`
- [X] T100 [P] [US5] Tests web `joyeriablanco_web/src/features/usuarios/UsuariosPage.test.tsx` (temporal mostrada una vez; error de último administrador) y `joyeriablanco_web/src/features/auditoria/AuditoriaPage.test.tsx`
- [X] T101 [P] [US5] E2E `joyeriablanco_web/e2e/usuarios.spec.ts`: el administrador crea un empleado → el empleado entra y cambia la temporal → no ve Configuración → el administrador lo desactiva con la sesión del empleado abierta en otro contexto → la siguiente acción del empleado lo lleva al acceso; la auditoría muestra los eventos

**Checkpoint**: US5 funciona de forma independiente.

---

## Phase 9: User Story 8 - Despliegue seguro en producción (Priority: P3)

**Goal**: despliegue con HTTPS automático, cabeceras estrictas, BD sin exponer y secretos fuera
del repositorio.

**Independent Test**: se ejecuta quickstart §4 en local con `tls internal`. La redirección a HTTPS,
las cabeceras y la ausencia de puertos de BD se verifican con un script.

- [X] T102 [US8] Crear `deploy/caddy/Caddyfile` (research R-14):
  - `{$DOMINIO}` con `tls internal` si `TLS_MODO=internal`.
  - Redirección de HTTP a HTTPS.
  - Cabeceras HSTS, CSP, `nosniff`, `frame-ancestors 'none'`, `Referrer-Policy` y `Permissions-Policy`.
  - `reverse_proxy /api/* api:8000`.
  - `try_files {path} /index.html` para la SPA y caché larga de los recursos con hash.
- [X] T103 [US8] Crear `deploy/caddy/Dockerfile`: etapa `node:26-trixie-slim` con `npm ci` y `npm run build` de `joyeriablanco_web` → imagen `caddy:2.11-alpine` con `/srv`
- [X] T104 [US8] Crear `docker-compose.prod.yml` con cuatro servicios:
  - `db`: sin `ports`, volumen y healthcheck.
  - `migrate`: se ejecuta una vez, `alembic upgrade head` como `jb_owner`.
  - `api`: target `prod`, `ENTORNO=produccion`, `--forwarded-allow-ips` de la red interna y cookie segura.
  - `caddy`: puertos 80 y 443 (y 443/udp), volúmenes `caddy_data` y `caddy_config`.
- [X] T105 [US8] Crear `deploy/verificar-produccion.sh`: comprueba el 308 de HTTP a HTTPS, la presencia de HSTS, CSP, `nosniff`, `Referrer-Policy` y `frame-ancestors`, que `db` no tiene puertos publicados, que `/api/salud` responde y que `/api/v1/sesion` sin cookie da 401. Ejecutarlo contra la simulación local (quickstart §4, SC-011 local)
- [X] T106 [US8] Documentar en `specs/001-cimientos-clientes/quickstart.md` el despliegue en un VPS real (DNS, puertos, `.env` de producción) y el **procedimiento de cambio de contraseñas de la BD** (FR-048). Recordar que las copias de seguridad son un riesgo asumido antes de cargar datos reales, e indicar que SC-011 se valida en el servidor real con un análisis público de TLS

**Checkpoint**: la producción simulada en local supera `verificar-produccion.sh`.

---

## Phase 10: User Story 6 - Mi cuenta (Priority: P4)

**Goal**: el usuario cambia su contraseña desde "Mi cuenta".

**Independent Test**: se cambia la contraseña; la antigua deja de valer; las otras sesiones se
cierran y la actual sigue.

- [X] T107 [US6] Crear `joyeriablanco_web/src/features/cuenta/MiCuentaPage.tsx` (reutiliza `CambioContrasenaForm` y avisa al guardar) y la ruta `joyeriablanco_web/src/routes/_app/cuenta.tsx`. Test en `joyeriablanco_web/src/features/cuenta/MiCuentaPage.test.tsx`
- [X] T108 [P] [US6] E2E `joyeriablanco_web/e2e/cuenta.spec.ts`: cambio de contraseña con dos contextos abiertos → el otro contexto vuelve al acceso; la contraseña antigua es rechazada; política con mensajes

**Checkpoint**: todas las historias funcionan de forma independiente.

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: calidad transversal, conformidad y cierre de la feature.

- [ ] T109 [P] Test de contrato `backend/tests/integration/test_contrato_openapi.py`: cada ruta y método de `specs/001-cimientos-clientes/contracts/openapi.yaml` existe en `app.openapi()`, con los mismos códigos de estado documentados
- [ ] T110 [P] Test `backend/tests/integration/test_logs_sin_datos_personales.py`: se captura la salida de logs durante el login y el alta y edición de cliente, y no aparecen contraseñas, tokens, cookies, NIF, correo, teléfono ni dirección (FR-053)
- [ ] T111 [P] Implementar `npm run check:tokens` (`joyeriablanco_web/scripts/check-tokens.mjs`): falla si hay colores hex, `rgb()` o `rounded-*` distinto de 0 fuera de `src/styles/tokens.css` (SC-009, constitución "Sistema de diseño")
- [ ] T112 [P] E2E `joyeriablanco_web/e2e/responsive.spec.ts`: a 360, 768 y 1440 px no hay desplazamiento horizontal en acceso, clientes, panel y usuarios, y el menú es cajón por debajo de 1024 px (SC-008)
- [ ] T113 Medir SC-003: `cargar-datos-ejemplo --clientes 10000` en la pila `api-e2e` y script `backend/scripts/medir_busqueda.py` (100 búsquedas variadas; informa del p95) sobre esa misma pila. Medir también el tiempo de login, cuyo objetivo es menos de 1 s. Registrar el resultado en `specs/001-cimientos-clientes/quickstart.md`
- [ ] T114 Actualizar `CLAUDE.md`, sección "Comandos de desarrollo", con los comandos reales fijados en la feature 001 (compose, `uv run joyeria …`, `npm run …`, e2e, producción) y quitar la nota "intención, no referencia"
- [ ] T115 Ejecutar las puertas de calidad completas: `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy .`, `uv run pytest`, `npm run lint`, `npm run typecheck`, `npm run test`, `npm run build`, `npm run check:tokens` y `npx playwright test`. Todo en verde (constitución IX, SC-012)
- [ ] T116 Revisión final de conformidad: recorrer quickstart §2 (10 validaciones manuales), cronometrar SC-001 (localizar un cliente en menos de 10 s) y SC-002 (alta en menos de 2 min) y comparar la pantalla Clientes con `specs/001-cimientos-clientes/assets/mockup-clientes.png` y con la tabla de desviaciones de la spec
- [ ] T117 Preguntar al responsable si se puede eliminar `temporal/` (su contenido ya está en `tools/brand/fuente/` y `specs/001-cimientos-clientes/assets/`)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (F1)**: sin dependencias.
- **Foundational (F2)**: depende de F1 y bloquea todas las historias.
- **US1 (F3)**: depende de F2. Es el **prerrequisito de autenticación** de US2–US8: todas las operaciones exigen sesión.
- **US2 (F4)**: depende de US1.
- **US3 (F5)**: depende de US2 (usa el modelo y la migración de clientes).
- **US7 (F6)**: depende de US3 para los datos de ejemplo y los E2E de clientes. La parte de entorno (T002–T006) ya está en F1.
- **US4 (F7)**: depende de US2; su E2E depende de F6.
- **US5 (F8)**: depende de US1; su E2E depende de F6. Puede ir en paralelo con US2–US4.
- **US8 (F9)**: depende de F2 y de que la web compile; conviene hacerla tras US3.
- **US6 (F10)**: depende de US1 (el formulario ya existe desde T050).
- **Polish (F11)**: depende de todas las historias.

### Within Each User Story

- Los tests se escriben primero y deben fallar.
- Orden: dominio → modelos y migración → repositorios → servicios → esquemas y routers → web → E2E.
- Commit atómico al cerrar cada grupo lógico de tareas.

### Parallel Opportunities

- F1: T007 y T008 en paralelo con T003–T006.
- F2: T010–T013 en paralelo; T021 y T022 en paralelo; T027–T030 en paralelo.
- US1: T031–T036 (tests) en paralelo; T037–T039, T043 y T046 en paralelo.
- US2: T054–T057 en paralelo; T058, T059, T065 y T067 en paralelo.
- US5 puede hacerse en paralelo con US2–US4 una vez cerrada US1.

---

## Parallel Example: User Story 2

```bash
# Tests primero (en paralelo):
Task: "T054 test_identificacion.py"
Task: "T055 test_codigos_postales.py"
Task: "T056 test_clientes_alta_edicion.py"
Task: "T057 ClienteForm.test.tsx"

# Dominio y esquemas (en paralelo):
Task: "T058 app/domain/identificacion.py"
Task: "T059 app/domain/codigos_postales.py"
Task: "T065 app/schemas/cliente.py"
Task: "T067 api/queries/*.ts"
```

---

## Implementation Strategy

### MVP First

1. F1 Setup → F2 Foundational.
2. F3 US1 (acceso seguro y shell) → **validar** US1 de forma independiente.
3. F4 + F5 (US2 + US3) → primer valor de negocio: la cartera de clientes operativa.

### Incremental Delivery

1. F1 + F2: base lista.
2. US1: acceso seguro (MVP técnico).
3. US2 + US3: clientes (MVP de negocio).
4. US7: entorno reproducible y E2E.
5. US4 → US5 → US8 → US6.
6. Polish y cierre con todo en verde.

---

## Notes

- [P] = ficheros distintos y sin dependencias pendientes.
- Las etiquetas [USx] trazan cada tarea a su historia de la spec.
- Si durante la implementación algo contradice la spec, **se para y se corrige la spec primero**
  (constitución, principio I).
- Constitución VII: ninguno de los cuatro tests obligatorios aplica a esta feature (no hay
  numeración, importes, huellas ni conversión).
