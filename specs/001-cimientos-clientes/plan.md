# Implementation Plan: Cimientos del sistema, seguridad de acceso y gestión de clientes

**Branch**: `001-cimientos-clientes` | **Date**: 2026-09-27 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-cimientos-clientes/spec.md`

## Summary

Se monta el monorepo operativo sobre tres piezas:

- **API REST** FastAPI (Python 3.13) sobre PostgreSQL 18, en Docker.
- **SPA** React 19 + TypeScript + Vite 8 con el sistema de diseño `docs/DESIGN.md`.
- **Despliegue de producción** con Caddy: mismo origen, HTTPS automático y cabeceras estrictas.

Sobre esa base se entregan:

- **Control de acceso**: sesiones de servidor en una cookie `__Host-` `HttpOnly` y
  `SameSite=Strict`, token CSRF sincronizador, Argon2id, bloqueo por cuenta y por origen, y dos
  roles.
- **Gestión de usuarios** y **auditoría** inalterable, con doble cierre en la BD y consulta para
  administradores.
- **Gestión de clientes**: identificación fiscal validada y alineada con el diseño de registro
  oficial de la AEAT, búsqueda sin tildes, indicadores, concurrencia optimista y baja lógica.

Decisiones y versiones en [research.md](research.md).

## Technical Context

**Language/Version**:
- Backend: Python 3.13.
- Web: TypeScript 6.0.3 (R-4) sobre Node.js 26.

**Primary Dependencies**:
- Backend: FastAPI 0.141, SQLAlchemy 2.1 (async, psycopg 3.3), Alembic 1.20, Pydantic 2.13,
  argon2-cffi 25.1, Typer 0.27.
- Web: React 19.3 + React Compiler 1.0, Vite 8.3, TanStack Router 1.170 y Query 5.104,
  React Hook Form 7.89 + Zod 4.6, Tailwind CSS 4.3, React Aria Components 1.21,
  openapi-typescript 7.13 y openapi-fetch 0.17.
- Infraestructura: Caddy 2.11.

**Storage**: PostgreSQL 18.6, con las extensiones `unaccent` y `pg_trgm`, `uuidv7()` nativo y roles
`jb_owner`/`jb_app` (R-11).

**Testing**: pytest 9 contra la BD de test aislada, Vitest 5 + Testing Library + MSW y
Playwright 1.63 (R-16).

**Target Platform**:
- Servidor Linux (VPS) con Docker Compose.
- Navegadores de escritorio y móviles actuales (Chrome, Edge, Firefox y Safari en sus dos últimas
  versiones).

**Project Type**: aplicación web (API + SPA) en monorepo.

**Performance Goals**: el 95 % de las búsquedas y filtrados responden en menos de 1 s con 10.000
clientes (SC-003). El login responde en menos de 1 s, incluido el coste de Argon2id.

**Constraints**:
- Sin `float` en importes, aunque esta feature no tiene importes.
- Mismo origen, sin CORS.
- CSP `'self'` en producción, sin `unsafe-inline`.
- Tipografías autoalojadas.
- Secretos fuera del repositorio.
- La BD no se expone en producción.

**Scale/Scope**: menos de 10 usuarios simultáneos, del orden de 10.000 clientes, unas 10 pantallas y
15 rutas de API.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio / restricción (v2.0.0) | Cómo se cumple | Estado |
|---|---|---|
| **I. SDD** | Rama `001-cimientos-clientes`, ciclo completo con clarify ya hecho y analyze previsto. Las fases se encadenan y hay un commit por fase | ✅ |
| **II. Integridad monetaria** | No hay importes en esta feature. La política `Decimal`/`NUMERIC` queda para la feature de facturas | ✅ N/A |
| **III. Inalterabilidad** | No hay facturas todavía. La **auditoría** aplica ya la misma técnica: `REVOKE` + trigger, probada en la BD (R-10), sobre los roles `jb_owner`/`jb_app` que usará el principio III (R-11) | ✅ |
| **IV. Verifactu por diseño** | Los campos identificativos del cliente salen de `DsRegistroVeriFactu.xlsx` v1.0, citado con URL, pestaña, filas y SHA-256 (spec F-1, F-2). Las reglas no verificadas (carácter de control del NIF, `IDOtro`, provincias y CP) se verifican en R-20 o quedan como preguntas abiertas | ✅ (R-20) |
| **V. Capas** | `routers → services → repositories`. Reglas de dominio puras en `app/domain/`. Esquemas `*Entrada`/`*Salida` separados; nunca se devuelve un modelo ORM | ✅ |
| **VI. Servidor como fuente de verdad** | La web solo valida la forma (Zod). El carácter de control, la unicidad, la provincia derivada del CP, los indicadores y los permisos los decide la API | ✅ |
| **VII. Tests obligatorios** | Ninguno de los cuatro aplica (no hay numeración, importes, huellas ni conversión). Se cubren las reglas de esta feature (FR-050) | ✅ N/A |
| **VIII. Español en el dominio** | Tablas, columnas, rutas (`/v1/clientes`, `/v1/sesion`…), mensajes y UI en español. Código en inglés salvo entidades y términos de dominio (R-17) | ✅ |
| **IX. Calidad automatizada** | `ruff` (lint y formato) y `mypy --strict` obligatorios en el backend. En la web, ESLint con typescript-eslint tipado, `tsc --noEmit` estricto y Prettier | ✅ |
| **Restricciones técnicas: backend** | Python 3.13, uv, FastAPI, SQLAlchemy 2.x con declarativo tipado (2.1 mantiene la API 2.0, R-2), Pydantic v2, Alembic y pytest con BD aislada | ✅ |
| **Restricciones técnicas: ejecución** | `docker-compose.yml` con `api` y `db` (volumen persistente), `.env` y `.env.example` versionado | ✅ |
| **Restricciones técnicas: web** | React + TypeScript + Vite | ✅ |
| **Sistema de diseño** | Tokens de DESIGN.md definidos una sola vez en `src/styles/tokens.css` (`@theme` de Tailwind), radio 0 global y fuentes autoalojadas. Desviaciones del mockup justificadas en la spec; ninguna desviación de DESIGN.md | ✅ |

**Re-check post-diseño** (tras data-model, contracts y quickstart): sin violaciones nuevas. La tabla
de complejidad queda vacía.

## Project Structure

### Documentation (this feature)

```text
specs/001-cimientos-clientes/
├── spec.md              # Especificación (con Clarifications 2026-09-27)
├── plan.md              # Este fichero
├── research.md          # Fase 0: decisiones, versiones y fuentes oficiales (R-20)
├── data-model.md        # Fase 1: tablas, restricciones y estados
├── quickstart.md        # Fase 1: puesta en marcha y validación
├── contracts/
│   ├── openapi.yaml     # Contrato de la API (OpenAPI 3.1, validado)
│   └── ui-rutas.md      # Rutas de la SPA, acceso y endpoints consumidos
├── checklists/          # requirements.md (+ los de /speckit.checklist)
├── assets/              # mockup-clientes.png (orientativo)
└── tasks.md             # Fase 2 (/speckit.tasks)
```

### Source Code (repository root)

```text
.env.example                         # Plantilla de configuración (sin secretos reales)
docker-compose.yml                   # Desarrollo: db, api, api-e2e (perfil e2e)
docker-compose.prod.yml              # Producción: db, migrate, api, caddy
infra/
└── db/init/01-roles.sh              # Roles jb_owner/jb_app y BD dev/test/e2e
deploy/
└── caddy/
    ├── Dockerfile                   # Etapa Node (build de la SPA) → imagen Caddy con /srv
    └── Caddyfile                    # TLS automático, cabeceras, /api → api:8000, fallback SPA
    (deploy/verificar-produccion.sh) # Verificación de cabeceras, redirección y puertos (SC-011)
tools/
└── brand/
    ├── procesar_logo.py             # Script PEP 723 (Pillow), reproducible
    └── fuente/logo-original.png

backend/
├── Dockerfile                       # Multietapa uv: targets dev y prod, usuario sin root
├── pyproject.toml                   # deps; [project.scripts] joyeria = "app.cli:app"; ruff y mypy estrictos
├── alembic.ini
├── alembic/
│   ├── env.py                       # Conecta como jb_owner
│   └── versions/                    # 0001 extensiones y roles; 0002 usuarios, sesiones y auditoría; 0003 provincias y clientes
├── app/
│   ├── main.py                      # Factoría de la app, middlewares y manejadores de problemas
│   ├── cli.py                       # crear-admin, restablecer-admin, cargar-datos-ejemplo, purgar-sesiones
│   ├── core/                        # config.py, db.py, security.py (hash, tokens), errors.py, logging.py, http.py (cabeceras, origen)
│   ├── domain/                      # identificacion.py, contrasenas.py, codigos_postales.py (puros, sin HTTP ni BD)
│   ├── models/                      # base.py, usuario.py, sesion.py, evento_auditoria.py, provincia.py, cliente.py
│   ├── repositories/                # usuarios.py, sesiones.py, auditoria.py, clientes.py, catalogos.py
│   ├── services/                    # auth.py, usuarios.py, auditoria.py, clientes.py, catalogos.py, documentos.py (puerto)
│   ├── schemas/                     # comunes.py (Problema, Pagina), sesion.py, usuario.py, cliente.py, auditoria.py, catalogos.py
│   ├── api/
│   │   ├── deps.py                  # get_db, get_current_session, require_admin, require_csrf
│   │   ├── salud.py
│   │   └── v1/                      # sesion.py, cuenta.py, usuarios.py, clientes.py, auditoria.py, catalogos.py
│   └── resources/                   # contrasenas_comunes.txt (NCSC top 100k + propias)
├── scripts/                         # medir_busqueda.py (SC-003)
└── tests/
    ├── conftest.py                  # BD de test, transacción/savepoint por test, cliente ASGI, factorías
    ├── unit/                        # domain/* y servicios con repos simulados
    └── integration/                 # API y BD: auth, CSRF, RBAC, clientes, auditoría, roles de BD

joyeriablanco_web/
├── package.json                     # scripts: dev, build, preview, lint, typecheck, test, gen:api, e2e
├── vite.config.ts                   # React + Compiler, TanStack Router, Tailwind, proxy /api → VITE_API_PROXY
├── tsconfig.json / tsconfig.app.json / tsconfig.node.json   # strict
├── eslint.config.js / .prettierrc
├── playwright.config.ts
├── index.html
├── public/                          # favicon.ico, favicon-32.png, apple-touch-icon.png, icon-192/512.png, manifest.webmanifest
├── scripts/                         # check-tokens.mjs (SC-009)
├── src/
│   ├── main.tsx / router.tsx / routeTree.gen.ts
│   ├── styles/                      # tokens.css (@theme desde DESIGN.md), base.css (tipografía, foco visible)
│   ├── assets/brand/logo.png
│   ├── api/                         # schema.gen.ts (openapi-typescript), client.ts (CSRF, 401 → acceso), queries/
│   ├── auth/                        # sesión (query), guardas de ruta
│   ├── components/
│   │   ├── ui/                      # Button, TextField, Select, ComboBox, Dialog/Drawer, Table, Chip, Card, Kpi, Pagination, EmptyState, Menu, Toast
│   │   └── layout/                  # AppShell, Sidebar, Header, UserMenu
│   ├── features/                    # acceso/, cuenta/, clientes/, usuarios/, auditoria/
│   ├── routes/                      # Rutas por fichero (ver contracts/ui-rutas.md)
│   └── lib/                         # fechas.ts, texto.ts, paises.ts (Intl.DisplayNames)
└── e2e/                             # global-setup.ts, helpers/db.ts, *.spec.ts
```

**Structure Decision**: aplicación web en monorepo, con `backend/` y `joyeriablanco_web/` (nombres ya
fijados en CLAUDE.md). La infraestructura compartida va en la raíz (`docker-compose*.yml`, `infra/`,
`deploy/`, `tools/`). `joyeriablanco_android/` no se toca.

## Enfoque de implementación (orden por dependencias)

1. **Infraestructura base**: `.env.example`, compose de desarrollo, roles de BD, Dockerfile del
   backend, esqueleto FastAPI (salud, configuración, logging, problemas), Alembic, esqueleto Vite y
   tokens de DESIGN.md.
2. **Dominio puro** (TDD): identificación (NIF, NIE, CIF y normalización), política de contraseñas y
   código postal a provincia, con los datos y algoritmos verificados en R-20.
3. **Seguridad**: modelos de usuarios, sesiones y auditoría, servicio de autenticación (login,
   bloqueo, límite por origen, CSRF y caducidad), dependencias de autorización y CLI `crear-admin`.
   Después, web: acceso, cambio obligatorio de contraseña, shell y guardas (US1).
4. **Clientes**: modelo, repositorio con búsqueda, servicio (unicidad, CP, concurrencia, ciclo de
   vida y puerto de documentos), API y web (US2, US3, US4).
5. **Usuarios, cuenta y auditoría**: API y web (US5, US6, FR-051).
6. **Datos de ejemplo** y E2E (US7).
7. **Logo e iconos**, **producción** (Caddy, compose de producción y verificación de cabeceras) y
   quickstart validado (US8).

## Complexity Tracking

Sin violaciones de la constitución que justificar.
