# Research — 001 Cimientos, seguridad y clientes

**Fecha**: 2026-09-27 · **Spec**: [spec.md](spec.md)

Formato de cada decisión: **Decisión** · **Razón** · **Alternativas descartadas**.

Las versiones se han consultado hoy en los registros oficiales: npm (`npm view`), PyPI (API JSON),
Docker Hub (tags) y el calendario de versiones de Node.js.

---

## R-1. Versiones de la plataforma

| Pieza | Versión fijada | Notas |
|---|---|---|
| Python | **3.13** (imagen `python:3.13.15-slim-trixie`) | Lo exige la constitución. 3.14 queda fuera por ese motivo. |
| uv | **0.12.x** (imagen `ghcr.io/astral-sh/uv:0.12`) | Última versión 0.12.19. |
| PostgreSQL | **18.6** (imagen `postgres:18.6-trixie`) | Aporta `uuidv7()` nativo. |
| Node.js (build y desarrollo) | **26.x** (imagen `node:26-trixie-slim`) | Pasa a LTS el 2026-10-28, en un mes, y tiene soporte hasta 2029-04-30. Node 24 entra en mantenimiento el 2026-10-20. |
| Caddy | **2.11.x** (imagen `caddy:2.11-alpine`) | HTTPS automático (ACME) y HTTP/3. |

**Alternativas**: Node 24 LTS (descartado: entra en mantenimiento dentro de tres semanas). Alpine
para Python (descartado: musl complica ruedas binarias como argon2 o psycopg).

## R-2. Backend: dependencias

| Paquete | Versión | Uso |
|---|---|---|
| fastapi | 0.141.x | API REST y OpenAPI 3.1 |
| uvicorn | 0.54.x | Servidor ASGI. En producción usa `--workers` y `--proxy-headers` |
| sqlalchemy | **2.1.x** | ORM con declarativo tipado (`Mapped[]`) y modo asíncrono |
| psycopg[binary] | 3.3.x | Un solo driver para la app (async) y para Alembic (sync) |
| alembic | 1.20.x | Migraciones |
| pydantic / pydantic-settings | 2.13.x / 2.15.x | Esquemas de entrada y salida y configuración por entorno |
| email-validator | 2.3.x | `EmailStr` |
| argon2-cffi | 25.1.x | Hash Argon2id |
| pycountry | 26.2.x | Catálogo ISO 3166-1 alfa-2 |
| typer | 0.27.x | CLI de operación (`crear-admin`, `restablecer-admin`, `cargar-datos-ejemplo`) |
| python-json-logger | 4.2.x | Logs JSON a stdout |
| **dev**: pytest 9.1, pytest-asyncio 1.4, httpx 0.28, asgi-lifespan 2.1, pytest-cov 7.1, ruff 0.16, mypy 2.3, faker 40 | | Pruebas, lint, tipos y datos de ejemplo |

**Nota de constitución**: la constitución cita "SQLAlchemy 2.0 (declarativo tipado)". SQLAlchemy 2.1
pertenece a la misma serie 2.x y mantiene exactamente la API declarativa tipada introducida en 2.0.
No es una desviación de fondo: se interpreta como "API estilo 2.0".

**Alternativas**:
- asyncpg: más rápido, pero obliga a un segundo driver para Alembic. Descartado.
- gunicorn: uvicorn ya gestiona workers. Descartado.
- structlog: el logging estándar con formato JSON basta para esta escala. Descartado.

## R-3. Web: dependencias

| Paquete | Versión | Uso |
|---|---|---|
| react / react-dom | 19.3.x | UI |
| **React Compiler** (`babel-plugin-react-compiler`) | 1.0.x | Memoización automática (estable). Se integra con `@vitejs/plugin-react` 6 |
| vite | **8.3.x** | Build (Rolldown) y servidor de desarrollo con proxy `/api` |
| @vitejs/plugin-react | 6.1.x | |
| typescript | **6.0.3** | Ver R-4 |
| @tanstack/react-router + router-plugin | 1.170.x / 1.168.x | Rutas tipadas por fichero, con guardas de autenticación en `beforeLoad` |
| @tanstack/react-query | 5.104.x | Caché de servidor e invalidaciones |
| react-hook-form + @hookform/resolvers + zod | 7.89.x / 5.9.x / 4.6.x | Formularios con validación de forma (la validación de negocio la hace el servidor) |
| tailwindcss + @tailwindcss/vite | 4.3.x | Tokens de DESIGN.md en `@theme` |
| react-aria-components | 1.21.x | Primitivas accesibles sin estilos (teclado y foco, FR-052) |
| lucide-react | 1.48.x | Iconos de línea fina como los del mockup |
| @fontsource/bodoni-moda, @fontsource-variable/manrope | 5.3.x | Tipografías autoalojadas (CSP y RGPD) |
| openapi-typescript + openapi-fetch | 7.13.x / 0.17.x | Tipos generados desde el OpenAPI de FastAPI y cliente tipado |
| **dev**: vitest 5.0, @testing-library/react 16.3, user-event 14.6, jest-dom 7.0, jsdom 30, msw 2.15, @playwright/test 1.63, eslint 10.11, typescript-eslint 8.70, eslint-plugin-react-hooks 7.1, prettier 3.9 | | Pruebas, lint y formato |

**Alternativas**:
- React Router 7: su tipado de rutas es menos estricto que el de TanStack Router. Descartado.
- Radix/shadcn: sus estilos por defecto son redondeados y hay que deshacerlos. React Aria da
  primitivas sin estilo y un manejo de teclado más completo. Descartado.
- Google Fonts por CDN: rompe la CSP `'self'` y cede datos a terceros (RGPD). Descartado.

## R-4. TypeScript 6.0 y no 7.0

**Decisión**: TypeScript **6.0.3**.
**Razón**: `typescript@latest` es la 7.0.2, el compilador nativo, pero `typescript-eslint` 8.70
declara `typescript >=4.8.4 <6.1.0`. La 6.0 es la última compatible con el lint tipado. Además,
`openapi-typescript` declara `typescript ^5.x`. Se resuelve con un `overrides` de npm que le deja
usar la 6.0, que mantiene la API del compilador de la serie 5.
**Alternativas**:
- TS 7.0: no hay lint tipado todavía.
- TS 5.9: más antigua sin ninguna ventaja.
- `@hey-api/openapi-ts` 0.99, que sí admite TS 6: queda como recambio si falla el `overrides`. Por
  ahora se descarta porque sigue en 0.x con cambios incompatibles frecuentes.

## R-5. Autenticación: sesiones de servidor

**Decisión**:
- **Token**: 32 bytes aleatorios (`secrets.token_urlsafe`). En la tabla `sesiones` solo se guarda
  su **SHA-256**.
- **Cookie de producción**: `__Host-jb_sesion`, con `HttpOnly`, `Secure`, `SameSite=Strict` y
  `Path=/`.
- **Cookie de desarrollo**: el entorno local va por `http://localhost`, así que la variable
  `SESION_COOKIE_SEGURA=false` usa el nombre `jb_sesion` sin `Secure`.
- **Caducidad**: 30 minutos de inactividad y 10 horas absolutas, configurables.
- **Actividad**: se guarda la marca de última actividad, a lo sumo una vez por minuto, para no
  escribir en cada petición.
- **Rotación**: el login siempre crea una sesión nueva; no se reutilizan identificadores.
- **Revocación**: se marca `revocada_en` en todas las sesiones del usuario al desactivarlo o
  restablecer su contraseña. Al cambiar la propia contraseña se revocan todas salvo la actual.

**Razón**: la web y la API comparten origen, así que la cookie `HttpOnly` evita exponer el token a
JavaScript. Además, la revocación es inmediata (FR-005 y FR-016), algo que un JWT sin estado no da.
**Alternativas**:
- JWT de acceso con refresh: la revocación no es inmediata y añade complejidad de rotación.
  Descartado.
- IdP externo (Keycloak): desproporcionado para menos de 10 usuarios. Descartado.

## R-6. CSRF y origen

**Decisión**: defensa en tres capas.
1. `SameSite=Strict`.
2. **Token sincronizador**: cada sesión tiene un `csrf_token` aleatorio. Se entrega en la respuesta
   de login y en `GET /api/v1/sesion`. La web lo envía en la cabecera `X-CSRF-Token` en todo
   POST, PUT, PATCH o DELETE, y el servidor lo compara en tiempo constante.
3. **Comprobación de `Origin`** contra `ORIGEN_PERMITIDO` en toda petición que modifica datos,
   incluido el login, para evitar la falsificación de login.

**Alternativas**: *double-submit cookie* (descartado: el sincronizador ligado a la sesión es más
fuerte y ya tenemos estado).

## R-7. Contraseñas

**Decisión**:
- **Hash**: Argon2id con los parámetros por defecto de argon2-cffi (perfil RFC 9106 *low-memory*:
  t=3, m=64 MiB, p=4) y *rehash* transparente si cambian los parámetros.
- **Política** (FR-008): entre 12 y 128 caracteres, rechazo si coincide (sin distinguir
  mayúsculas) con la lista de contraseñas comunes o si contiene el nombre de usuario.
- **Lista de contraseñas comunes**: la top 100.000 de contraseñas filtradas publicada por el NCSC
  británico (`PwnedPasswordsTop100k`, Open Government Licence v3), más una lista propia pequeña
  (`joyeria`, `blanco`, `joyeriablanco`, `contraseña`…). Se versiona en `backend/app/resources/`.
  En `implement` se registran la URL y la huella SHA-256 del fichero descargado.
- **Contraseña temporal**: 16 caracteres de un alfabeto sin ambigüedades, agrupados de 4 en 4. Se
  muestra una sola vez.
- **Tiempo constante**: si el usuario no existe, se verifica igualmente contra un hash ficticio, de
  modo que el tiempo de respuesta no delate qué usuarios existen (FR-007).

**Alternativas**:
- bcrypt: límite de 72 bytes y peor resistencia a GPU. Descartado.
- Consultar la API de HIBP: dependencia externa en cada alta. Descartado.

## R-8. Fuerza bruta

**Decisión**:
- **Por cuenta**: contador `intentos_fallidos` y `bloqueado_hasta` en `usuarios`. El quinto fallo
  consecutivo bloquea 15 minutos, y un acceso correcto reinicia el contador.
- **Por origen**: se cuentan los eventos `acceso_fallido` de la auditoría desde la misma IP en los
  últimos 10 minutos (índice por `origen_ip, tipo, ocurrido_en`). Si llegan a 20, se rechaza sin
  evaluar la contraseña: se responde 429 con un mensaje propio y se registra `acceso_limitado`, que
  no suma al límite.
- **IP real detrás de Caddy**: `uvicorn --proxy-headers --forwarded-allow-ips=<red interna>`.

**Razón**: no hace falta infraestructura adicional (Redis) y el estado sobrevive a reinicios y a
varios workers.

## R-9. Autorización

**Decisión**:
- **Dependencias de FastAPI**: `get_current_session` exige una sesión válida y aplica la regla de
  contraseña temporal (solo se permiten cambiar la contraseña, `GET /sesion` y `DELETE /sesion`).
  `require_admin` comprueba el rol. Por defecto se deniega: todo router de `/api/v1` salvo
  `POST /sesion` monta `get_current_session`.
- **Regla del último administrador** (FR-017): se comprueba en el servicio con un bloqueo
  `SELECT … FOR UPDATE` sobre los administradores activos, para que dos degradaciones simultáneas
  no dejen el sistema sin administrador.

## R-10. Auditoría inalterable

**Decisión**:
- **Tabla**: `eventos_auditoria`, de solo inserción.
- **Doble cierre en la BD** (FR-022):
  1. `REVOKE UPDATE, DELETE, TRUNCATE` al rol de aplicación.
  2. Trigger `BEFORE UPDATE OR DELETE` que lanza una excepción, incluso para el propietario.
- **Campo `detalle`** (JSONB): lleva los campos cambiados (`{campo: [antes, después]}`), sin
  contraseñas.
- **Borrado de un cliente**: se guarda una instantánea de nombre e identificación. `cliente_id` no
  tiene FK, para que el borrado físico no rompa la auditoría.

**Razón**: se aplica ahora la misma técnica que exigirá el principio III para las facturas, así que
queda probada desde la feature 001.

## R-11. Roles de PostgreSQL

**Decisión**: tres roles.
- **Superusuario de arranque** (`POSTGRES_USER`): solo lo usa el script de inicialización.
- **`jb_owner`**: dueño del esquema; ejecuta Alembic.
- **`jb_app`**: solo DML, sin DDL.

Las migraciones fijan `ALTER DEFAULT PRIVILEGES FOR ROLE jb_owner … GRANT SELECT, INSERT, UPDATE,
DELETE ON TABLES TO jb_app` y los `REVOKE` específicos (auditoría). El script
`infra/db/init/01-roles.sh` crea roles y bases (`joyeriablanco`, `joyeriablanco_test`,
`joyeriablanco_e2e`).

**Razón**: FR-047 y los cimientos del principio III.

## R-12. Identificadores, concurrencia y búsqueda

**Decisión**:
- **Claves primarias**: UUID v7 generados por PostgreSQL (`uuidv7()`), ordenables por tiempo y sin
  filtrar volúmenes.
- **Concurrencia optimista** (FR-030): columna `version` con `version_id_col` de SQLAlchemy. La
  edición envía la `version` leída y, si no coincide, se responde 409 con el mensaje "El cliente ha
  cambiado desde que lo abriste".
- **Búsqueda** (FR-032):
  - Extensiones `unaccent` y `pg_trgm`.
  - Función `inmutable_unaccent(text)`, declarada IMMUTABLE para poder indexarla.
  - Columna generada `texto_busqueda = inmutable_unaccent(lower(nombre || ' ' ||
    identificacion_numero || ' ' || coalesce(localidad,'')))` con índice GIN trigram.
  - La consulta usa `ILIKE '%término%'` sobre el término normalizado igual.
- **Paginación**: por *offset* con total (`pagina`, `tamano` hasta 100, 25 por defecto). A esta
  escala, con 10.000 clientes, basta.

## R-13. Errores de la API

**Decisión**: RFC 9457 `application/problem+json`, con los campos `type`, `title`, `status` y
`detail` (en español) y `errores: [{campo, mensaje}]` para la validación. Un manejador global
convierte `RequestValidationError` y las excepciones de dominio. Nunca se exponen trazas (FR-049).

## R-14. Seguridad del transporte y cabeceras

**Decisión**:
- **Caddy** en producción:
  - Certificado ACME automático para `{$DOMINIO}` y redirección de HTTP a HTTPS.
  - HSTS `max-age=31536000; includeSubDomains`.
  - CSP `default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:;
    font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self';
    form-action 'self'; object-src 'none'`.
  - `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer` y `Permissions-Policy`
    restrictiva.
- **API**: añade `Cache-Control: no-store` a toda respuesta autenticada.
- **Desarrollo**: sin CSP, porque el HMR de Vite necesita scripts en línea. La CSP de producción
  se verifica en el entorno local de producción con `tls internal` (SC-011).

**Razón**: React aplica los estilos en línea por CSSOM, que la CSP no bloquea. Tailwind genera un
fichero CSS estático. Nada exige `unsafe-inline`.

## R-15. Entornos Docker

**Decisión**:
- **`docker-compose.yml`** (desarrollo):
  - `db`: volumen persistente y puerto enlazado solo a `127.0.0.1`.
  - `api`: *target* `dev`, recarga en caliente, código montado y puerto `127.0.0.1:8000`.
  - `api-e2e`: perfil `e2e`, puerto 8001, BD `joyeriablanco_e2e`.
  - La web corre en el host con `npm run dev`, y Vite hace de proxy de `/api` a `VITE_API_PROXY`
    (8000 por defecto).
- **`docker-compose.prod.yml`**:
  - `db`: sin puertos publicados.
  - `migrate`: servicio de un solo uso que ejecuta Alembic como `jb_owner`.
  - `api`: *target* `prod`, usuario sin privilegios y healthcheck.
  - `caddy`: construye la SPA en una etapa Node y la sirve desde `/srv`.
- **Secretos**: en `.env` (ignorado). Solo se versiona `.env.example`.

**Alternativas**: servir la SPA desde FastAPI (descartado: mezcla responsabilidades y complica la
CSP y la caché de estáticos).

## R-16. Pruebas

**Decisión**:
- **Backend**:
  - `pytest` contra PostgreSQL real, en la base `joyeriablanco_test` (constitución: "base de datos
    de test aislada").
  - Cada test corre en una transacción con *savepoint* que se revierte.
  - Las pruebas de dominio puras (NIF, contraseñas, código postal) no tocan la BD ni HTTP
    (principio V).
  - Las de API usan `httpx.AsyncClient` con `ASGITransport`.
- **Web**: Vitest con Testing Library y MSW para los componentes y formularios.
- **E2E**: Playwright.
  - Levanta Vite con `VITE_API_PROXY=http://localhost:8001`.
  - `globalSetup` reinicia y siembra `joyeriablanco_e2e` con la CLI dentro de `api-e2e`.
  - La prueba de sesión caducada envejece la sesión directamente en la BD con `psql` desde el
    helper de prueba. No hay ningún endpoint de pruebas en la API.

## R-17. Convenciones de nombres

**Decisión**: tablas, columnas, rutas y mensajes en español (principio VIII). Las **entidades de
dominio** se nombran en español también en el código: `Cliente`, `Usuario`, `Sesion`,
`EventoAuditoria` y `Provincia`, igual que los esquemas `ClienteEntrada` y `ClienteSalida`.
Funciones y variables van en inglés salvo términos de dominio (`create_cliente`, `validate_nif`,
`revoke_sessions`).

## R-18. Logo

**Decisión**: script reproducible `tools/brand/procesar_logo.py`, con metadatos PEP 723
(`pillow`), que se ejecuta con `uv run tools/brand/procesar_logo.py`.

1. Aísla el disco negro por luminancia, estima centro y radio por momentos y ajusta el radio por el
   borde.
2. Genera una máscara circular antialiasada con supermuestreo ×4.
3. Neutraliza el degradado gris del bisel del borde: los píxeles grises de la corona exterior que no
   son del monograma pasan a negro.
4. Recorta al contenido y exporta:
   - `joyeriablanco_web/src/assets/brand/logo.png` (512 px).
   - `public/favicon.ico` (16, 32 y 48 px), `favicon-32.png`, `apple-touch-icon.png` (180 px),
     `icon-192.png`, `icon-512.png` y `manifest.webmanifest`.

El original se conserva en `tools/brand/fuente/logo-original.png`.

## R-19. Datos de ejemplo

**Decisión**: comando `cargar-datos-ejemplo`, que se niega si `ENTORNO=produccion`.
- Crea unos 40 clientes ficticios con Faker `es_ES`, con NIF generados válidos (dígito de control
  correcto) y marca `(EJEMPLO)` en observaciones.
- Crea usuarios `admin.demo` y `empleado.demo`.
- Es idempotente: primero comprueba si existe un marcador de carga.

## R-20. Fuentes oficiales: identificación, provincias y código postal

Verificación hecha el 2026-09-27 en fuentes oficiales (BOE, AEAT, INE y web de la Administración
General del Estado). Cada fila indica su veredicto.

### R-20.1 Validaciones AEAT del destinatario

**Fuente (F-3)**: AEAT, *Sistemas Informáticos de Facturación y Sistemas VERI\*FACTU — Validaciones
y errores*, **v1.2.2 (08/04/2026)**.
- URL:
  `https://www.agenciatributaria.es/static_files/AEAT_Desarrolladores/EEDD/IVA/VERI-FACTU/Validaciones_Errores_Veri-Factu.pdf`.
- SHA-256: `426eb926fc098a36a163f66ca5f40d9e0847ca23300bbe5008979832d3513440`.

Apartado 3.1.3, punto 13 (`Destinatarios/IDDestinatario`, p. 10), **VERIFICADO**, literal:
- «Si se cumplimenta NIF, no deberá existir la agrupación IDOtro y viceversa, pero es obligatorio
  que se cumplimente uno de los dos.»
- «Si el campo IDType = "02" (NIF-IVA), no será exigible el campo CodigoPais.»
- «Si el campo IDType = "07" (No censado), el campo CodigoPais debe ser "ES".»
- «… e IDType sea "02", se validará que el campo identificador se ajuste a la estructura de NIF-IVA
  de alguno de los Estados Miembros y debe estar identificado. Ver nota (1).»
- «… IDOtro y CodigoPais sea "ES", se validará que el campo IDType sea "03" o "07".»

Nota (1) (pp. 17–18), tabla **"Estructura NIF-IVA"**, **VERIFICADO**:

| País | Prefijo | Número |
|---|---|---|
| Alemania | DE | 9 numéricos |
| Austria | AT | 9 alfanuméricos |
| Bélgica | BE | 10 numéricos |
| Bulgaria | BG | 9 o 10 numéricos |
| Chipre | CY | 9 alfanuméricos |
| Croacia | HR | 11 numéricos |
| Dinamarca | DK | 8 numéricos |
| Eslovaquia | SK | 10 numéricos |
| Eslovenia | SI | 8 numéricos |
| Estonia | EE | 9 numéricos |
| Finlandia | FI | 8 numéricos |
| Francia | FR | 11 alfanuméricos |
| Grecia | **EL** (ISO: GR) | 9 numéricos |
| Hungría | HU | 8 numéricos |
| Irlanda | IE | 8 o 9 alfanuméricos |
| Irlanda del Norte | **XI** (GB antes de 01/02/2021; ISO: GB) | 5, 9 o 12 alfanuméricos |
| Italia | IT | 11 numéricos |
| Letonia | LV | 11 numéricos |
| Lituania | LT | 9 o 12 numéricos |
| Luxemburgo | LU | 8 numéricos |
| Malta | MT | 8 numéricos |
| Países Bajos | NL | 12 alfanuméricos |
| Polonia | PL | 10 numéricos |
| Portugal | PT | 9 numéricos |
| República Checa | CZ | 8, 9 o 10 numéricos |
| Rumanía | RO | 2 a 10 numéricos, sin ceros a la izquierda |
| Suecia | SE | 12 numéricos |

Notas de la tabla:
- España no figura.
- «Sólo se admiten mayúsculas.»

**Decisiones derivadas**:
- **Combinaciones de país y tipo admitidas en la ficha de cliente** (FR-024, FR-025):

  | País de identificación | Tipos admitidos |
  |---|---|
  | ES | `NIF` o `03` (pasaporte) |
  | Estado de la tabla NIF-IVA (distinto de ES) | `02`, `03`, `04`, `05` o `06` |
  | Resto de países | `03`, `04`, `05` o `06` |

- **Tipo 02**:
  - Se valida la estructura de la tabla oficial.
  - Forma canónica almacenada: **prefijo NIF-IVA + número** (p. ej. `FR12345678901`, `EL123456789`,
    `XI123456789`). Si el usuario lo teclea sin prefijo, se añade el del país elegido.
  - El país de identificación se guarda siempre, aunque la AEAT no lo exija con 02, porque la ficha
    lo necesita para saber qué estructura aplicar.
- **Tipo 07 "No censado"**: no es un documento distinto. Es un NIF correcto de persona física que no
  figura en el censo (apartado 4.3.1, p. 21; error 1131 de `errores.properties`: «El valor del
  campo ID ha de ser el NIF de una persona física cuando el campo IDType tiene valor No Censado
  (07)»). En la ficha, ese cliente se guarda con tipo `NIF`. La decisión de declararlo como 07 es
  de la **generación del registro de facturación** (feature de facturas).

### R-20.2 Composición y carácter de control del NIF

| Tipo | Composición | Carácter de control | Fuente | Veredicto |
|---|---|---|---|---|
| DNI (españoles) | 8 dígitos + letra | Número mod 23 → `TRWAGMYFPDXBNJZSQVHLCKE` (ej.: 12345678 → Z) | RD 1065/2007 (BOE-A-2007-15984), art. 19.1; RD 255/2025 (BOE-A-2025-6601), art. 12. Algoritmo: Ministerio del Interior, «Cálculo del dígito de control del NIF/NIE» (interior.gob.es; acceso automático bloqueado, texto confirmado por extracto) y DGOJ, `https://www.ordenacionjuego.es/en/node/2988` | **VERIFICADO** en web oficial (no en BOE) |
| NIE | X/Y/Z + 7 dígitos + letra | Se sustituye X→0, Y→1, Z→2 y se aplica el mismo algoritmo | Orden INT/2058/2008 (BOE-A-2008-12050): «letra inicial… siete dígitos… carácter de verificación alfabético»; sustitución: DGOJ (web oficial) | **VERIFICADO** en web oficial |
| Personas jurídicas y entidades | Letra (A, B, C, D, E, F, G, H, J, P, Q, R, S, U, V; N extranjeras; W establecimientos permanentes) + 7 dígitos + carácter de control | **Algoritmo no publicado** | RD 1065/2007, art. 22.1; Orden EHA/451/2008 (BOE-A-2008-3580), arts. 2–5, redacción de la Orden HAP/5/2016 (BOE-A-2016-358) | Composición **VERIFICADA**; algoritmo **NO VERIFICADO** |
| K, L (españoles sin DNI) y M (extranjeros sin NIE) | Letra + 7 alfanuméricos + letra de verificación | **Algoritmo no publicado** | RD 1065/2007, arts. 19.2 y 20.2 | Composición **VERIFICADA**; algoritmo **NO VERIFICADO** |

**Decisión** (consultada con el responsable el 2026-09-27): DNI y NIE se validan con su letra. El
NIF de entidades y el de K, L y M se validan **solo por estructura**, con estos patrones:
- Entidades: `^[ABCDEFGHJNPQRSUVW][0-9]{7}[0-9A-Z]$`.
- K, L y M: `^[KLM][0-9A-Z]{7}[A-Z]$`.

Así lo exige la constitución (principio IV: no se deduce de fuentes no oficiales). Una errata en un
NIF de entidad la detectará la consulta al censo de la AEAT en una feature posterior.

### R-20.3 Provincias y código postal

- **Provincias (F-6)**: INE, «Relación de provincias con sus códigos», **a 1 de enero de 2026**
  (publicada el 04/02/2026). **VERIFICADO**.
  - URL: `https://www.ine.es/daco/daco42/codmun/cod_provincia.htm`.
  - Contrastada con `diccionario26.xlsx`: 52 códigos del 01 al 52.
  - Se cargan los 52 literales INE tal cual (p. ej. `Araba/Álava`, `Coruña, A`, `Balears, Illes`,
    `Palmas, Las`, `Rioja, La`, `Valencia/València`).
  - Para ordenar y mostrar, el literal con coma se presenta en orden natural ("A Coruña"). Es una
    decisión de presentación; el literal oficial se conserva en la BD.
- **Código postal (F-7)**:
  - Orden de 23 de enero de 1984 (BOE-A-1984-3487), art. 2: «Los dos primeros identifican la
    provincia según el código geográfico nacional».
  - Orden de 27 de septiembre de 1995 (BOE-A-1995-21835): «En los casos de las ciudades de Ceuta y
    Melilla, los dos primeros dígitos serán el 51 y 52, respectivamente».
  - **VERIFICADO**.
  - La equivalencia entre "código geográfico nacional" y codificación provincial del INE no está
    escrita literalmente. Se infiere de la coincidencia de Ceuta (51) y Melilla (52) con la tabla
    INE. Registrado como **interpretación**.
  - Riesgo: si existiera una excepción, un código postal válido sería rechazado. Mitigación: la
    tabla de correspondencia es un dato versionado que se corrige sin tocar código.

### R-20.4 Preguntas abiertas (para features posteriores; no bloquean la 001)

1. **"FormatoNIF"**: no está definido más allá de 9 caracteres (diseño de registro y XSD
   `NIFType length 9`). La 001 aplica los patrones de R-20.2.
2. **NIF de destinatario no censado**: el error 1193 (rechazo) y el 2001 (aceptado con errores) de
   `errores.properties` se contradicen. Se resolverá en la feature de facturas.
3. **Tipo 02 en el registro**: queda por confirmar si `IDOtro/ID` lleva el prefijo NIF-IVA. La ficha
   guarda la forma canónica con prefijo y puede derivar ambas.
4. **Algoritmo del carácter de control** de entidades y K, L y M: no publicado. Si la AEAT lo
   publicara, se añadiría.
