# CLAUDE.md — Joyería Blanco

Guía operativa de desarrollo. Está **subordinada a la constitución del proyecto**, en
`.specify/memory/constitution.md`. Ante cualquier conflicto, manda la constitución.

## El proyecto

Sistema de gestión para Joyería Blanco, desarrollado por fases.

**Fase 1 (actual): facturación y presupuestos.** Cubre clientes, facturas con cumplimiento
Verifactu, generación de PDF con código QR de cotejo de la AEAT, y presupuestos con conversión a
factura.

## Cómo se trabaja aquí — LEE ESTO PRIMERO

**Todo el desarrollo pasa por Spec Kit (SDD). No se escribe código fuera de `/speckit.implement`,
y el `tasks.md` que se implementa tiene que haber superado `/speckit.analyze`.**

Ciclo obligatorio por feature, sin saltarse pasos:

```
/speckit.specify → /speckit.clarify → /speckit.plan → /speckit.checklist
                 → /speckit.tasks   → /speckit.analyze → /speckit.implement
```

Reglas:

- `/speckit.clarify` y `/speckit.analyze` **no son opcionales**.
- **Las fases se encadenan sin pedir aprobación entre ellas.** Solo se para para preguntar las
  dudas que requieren decisión humana: las preguntas de `clarify` y las ambigüedades de dominio o
  normativas. Después se continúa.
- Cada fase se cierra con un **commit atómico** en la rama de la feature. No se hace push sin
  pedirlo.
- Si durante `implement` algo contradice la spec, **se detiene y se corrige la spec primero**,
  nunca al revés.
- Cada feature vive en `specs/NNN-nombre-feature/` y se cierra con sus tests en verde antes de
  abrir la siguiente.

**Spec Kit no crea ramas.** `create-new-feature.sh` solo crea el directorio y exporta
`SPECIFY_FEATURE`. Hay que crear la rama a mano antes de empezar:

```bash
git checkout -b 002-nombre-feature
```

## Estructura del monorepo

```
/                          Repositorio único (git init en la raíz)
├── backend/               API REST: FastAPI + PostgreSQL, gestionado con uv
├── joyeriablanco_web/     Aplicación web de gestión: React + TypeScript + Vite
├── joyeriablanco_android/ App móvil — FUERA DE ALCANCE, NO TOCAR
├── docs/                  Documentación normativa transversal (DESIGN.md)
├── specs/                 Una carpeta por feature (NNN-nombre-feature/)
└── .specify/              Spec Kit: constitución, plantillas y scripts
```

## Comandos de desarrollo

Todo el backend (API + base de datos) corre en Docker. La guía completa está en
`specs/001-cimientos-clientes/quickstart.md`.

```bash
# Entorno de desarrollo (raíz del repo)
cp .env.example .env                          # y cambiar las contraseñas
docker compose up -d --build                  # db (PostgreSQL 18) + api (FastAPI con recarga)
docker compose exec api alembic upgrade head  # migraciones como jb_owner
docker compose exec api joyeria crear-admin --usuario admin --nombre "Administrador"
docker compose exec api joyeria cargar-datos-ejemplo   # clientes y usuarios *.demo ficticios
docker compose logs -f api
docker compose down                           # -v para borrar también los datos

# Backend (dentro de backend/; los tests usan la BD joyeriablanco_test del servicio db)
uv sync
uv run pytest                     # tests contra PostgreSQL real
uv run pytest -k clientes         # un subconjunto
uv run ruff check . && uv run ruff format --check . && uv run mypy .   # calidad (obligatoria)
uv run alembic revision -m "descripcion"   # nueva migración (escrita a mano y revisada)
uv run joyeria --help             # CLI: crear-admin, restablecer-admin, purgar-sesiones,
                                  # cargar-datos-ejemplo, reiniciar-bd-e2e, exportar-openapi

# Web (dentro de joyeriablanco_web/)
npm ci
npm run dev                       # http://localhost:5173, proxy de /api a la API
npm run lint && npm run typecheck && npm run test && npm run build && npm run check:tokens
uv --directory ../backend run joyeria exportar-openapi && npm run gen:api  # regenerar tipos
npx playwright test               # E2E: levanta api-e2e con BD propia y Vite en :5174

# Producción (ver quickstart §4 y §5)
docker compose -f docker-compose.prod.yml --env-file .env up -d --build
deploy/verificar-produccion.sh <dominio>
```

## Convenciones de código

### Idioma

- **Español**: nombres de tablas, columnas, rutas de la API, mensajes de error y UI.
- **Inglés**: nombres de variables y funciones, salvo términos de dominio (`factura`,
  `presupuesto`, `huella`, `cliente`).

### Arquitectura

```
routers → services → repositories/modelos
```

- **Cero lógica de negocio en los routers.** Los routers validan, delegan y serializan.
- Esquemas Pydantic **separados para entrada y salida**. Nunca se expone un modelo ORM.
- La lógica fiscal debe poder testearse sin levantar HTTP.

### Interfaz de usuario

Toda la UI cumple **`docs/DESIGN.md`**, el sistema de diseño "Haute Joaillerie Atelier"
(normativo desde la constitución 1.1.0).

- **Tokens definidos una sola vez.** Colores, tipografías (Bodoni Moda y Manrope), espaciado y
  elevación se declaran una vez y se consumen desde ahí. No se repiten como literales.
- **Esquinas a 0 px** y filetes de 1 px. Sin sombras difusas fuera de las definidas en el documento.
- **Los mockups son orientativos.** Mandan `docs/DESIGN.md` y la spec. Por ejemplo, la navegación
  lateral va a la **izquierda**.
- **Desviaciones.** Toda desviación se justifica en la spec de la feature. Las incoherencias del
  propio DESIGN.md se corrigen en el documento, con aprobación, nunca sobre la marcha en el código.

### Dinero

- `Decimal` de extremo a extremo, `NUMERIC` en PostgreSQL.
- **`float` está prohibido**, incluida la serialización JSON.
- El tipo de IVA se guarda **por línea**; la cabecera almacena los totales agregados por tipo.
- Las líneas se introducen **sin IVA** (base imponible); el servidor calcula cuota y total.
- **El front nunca envía totales.** Puede previsualizar; la fuente de verdad es la API.

### Numeración

Correlativa por año natural y por serie, **sin huecos y sin reutilización**, segura frente a
concurrencia (secuencia de BD o bloqueo explícito sobre tabla de contadores).

**`MAX(numero)+1` sin lock está prohibido.**

## Reglas innegociables de Verifactu

- **Nada de `UPDATE` ni `DELETE`** sobre facturas ni sobre registros de facturación. La restricción
  va **en la base de datos** (triggers/reglas y privilegios), no solo en la aplicación.
- Las correcciones son factura rectificativa, registro de anulación o registro de subsanación.
- Cada factura emitida genera un **registro de alta con huella SHA-256 encadenada** con la del
  registro anterior.
- **Los formatos se toman de la documentación oficial de la AEAT y se citan en la spec** (URL +
  versión del documento). Lo que no se pueda verificar en fuente oficial se marca como pregunta
  abierta. **Nunca se deduce de memoria ni se copia de blogs.**
- La **modalidad** (VERI\*FACTU / no VERI\*FACTU) es configuración y un campo del registro, no una
  bifurcación del modelo de datos.

### Marco normativo

RD 1007/2023 (RRSIF), RD 254/2025, RD-ley 15/2025 y Orden HAC/1177/2024.

Plazos de adaptación vigentes (verificados en BOE el 2026-09-12, disposición final cuarta del
RD 1007/2023 en su redacción por el RD-ley 15/2025):

- Contribuyentes del Impuesto sobre Sociedades: **antes del 1 de enero de 2027**.
- Resto de obligados del art. 3.1 (autónomos incluidos): **antes del 1 de julio de 2027**.

### Documentación técnica oficial (fuente única de verdad para formatos)

| Documento | URL | Versión |
|---|---|---|
| Diseños de registro | `agenciatributaria.es/static_files/AEAT_Desarrolladores/EEDD/IVA/VERI-FACTU/DsRegistroVeriFactu.xlsx` | 1.0 |
| Huella / hash | `.../Veri-Factu_especificaciones_huella_hash_registros.pdf` | 0.1.2 (27/08/2024) |
| Código QR | `.../DetalleEspecificacTecnCodigoQRfactura.pdf` | 0.5.0 (10/12/2025) |
| Firma electrónica (no VERI\*FACTU) | `.../Espec-Tecnicas/EspecTecGenerFirmaElectRfact.pdf` | 0.1.5 (06/03/2025) |
| Validaciones y errores | `.../Validaciones_Errores_Veri-Factu.pdf` | 1.2.2 (08/04/2026) |
| Descripción de servicios web | `.../Veri-Factu_Descripcion_SWeb.pdf` | 1.0.3 (28/07/2025) |

Índice oficial:
`https://sede.agenciatributaria.gob.es/Sede/iva/sistemas-informaticos-facturacion-verifactu/informacion-tecnica.html`

**Entorno de pruebas**: `https://preportal.aeat.es`. La integración se hace **primero contra
preproducción**, nunca directamente contra producción.

## Tests de cobertura obligatoria

Ninguna feature que los afecte se cierra sin ellos:

1. Numeración correlativa bajo concurrencia (sin huecos ni reutilización).
2. Cálculo de importes y redondeos.
3. Encadenamiento de huellas Verifactu.
4. Conversión presupuesto → factura.

## Git

- Commits **atómicos y descriptivos**.
- Una rama por feature: `NNN-nombre-feature`.
- Una fase no se da por cerrada sin sus tests en verde.
