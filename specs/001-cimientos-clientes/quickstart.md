# Quickstart y validación — 001

Guía para levantar el sistema y comprobar que la feature funciona de extremo a extremo (SC-010).
Detalle de endpoints en [contracts/openapi.yaml](contracts/openapi.yaml), de rutas en
[contracts/ui-rutas.md](contracts/ui-rutas.md) y de tablas en [data-model.md](data-model.md).

## Requisitos previos

- Docker con Compose v2.
- `uv` 0.12 o superior (Python 3.13 lo instala uv).
- Node.js 26.
- Puertos libres en `127.0.0.1`: 5432, 8000, 8001 y 5173.

## 1. Entorno de desarrollo

```bash
cp .env.example .env                  # revisar y cambiar las contraseñas de ejemplo
docker compose up -d --build          # db + api (el entorno virtual está en el PATH del contenedor)
docker compose exec api alembic upgrade head          # migraciones como jb_owner (idempotente)
docker compose exec api joyeria crear-admin --usuario admin --nombre "Administrador"
#   → muestra una contraseña temporal UNA vez
docker compose exec api joyeria cargar-datos-ejemplo  # 40 clientes y usuarios *.demo (temporales)
cd joyeriablanco_web && npm ci && npm run dev          # http://localhost:5173
```

**Medición SC-010** (2026-09-27, desde volúmenes vacíos y con las imágenes ya descargadas):
- El backend queda listo en 11 s, con migraciones, administrador y datos de ejemplo.
- `npm ci` tarda unos 30 s.
- La primera vez se suma la descarga de las imágenes base: unos minutos, según la conexión.

**Resultado esperado**:
1. Al entrar como `admin`, pide cambiar la contraseña temporal.
2. Después aparece la pantalla Clientes, con el menú a la izquierda, los indicadores y unos 40
   clientes de ejemplo.

## 2. Validaciones manuales clave

| # | Paso | Resultado esperado | Requisito |
|---|---|---|---|
| 1 | Usuario inexistente y, después, contraseña errónea | Mismo mensaje genérico en ambos casos | FR-007 |
| 2 | 5 fallos seguidos con `empleado.demo` y luego la contraseña correcta | Rechazado durante 15 minutos | FR-006 |
| 3 | Buscar "maria lopez" | Aparece "María López García" (ejemplo) | FR-032 |
| 4 | Alta con NIF `12345678A` | Error de carácter de control en el campo | FR-024 |
| 5 | Alta con CP `29001` y país España | Provincia "Málaga" asignada | FR-028 |
| 6 | Editar un cliente en dos pestañas y guardar en ambas | La segunda recibe el aviso de conflicto | FR-030 |
| 7 | Como admin, desactivar `empleado.demo` mientras tiene sesión abierta en otra ventana | Su siguiente acción lleva al inicio de sesión | FR-016 |
| 8 | Configuración → Auditoría y filtrar por tipo `acceso_fallido` | Aparecen los intentos de los pasos 1 y 2 con IP y fecha | FR-051 |
| 9 | Como empleado, abrir `/configuracion/usuarios` | Pantalla de acceso denegado | FR-013 |
| 10 | Ventana a 360 px | Cajón de menú y sin desplazamiento horizontal | FR-040, SC-008 |

## 3. Pruebas automáticas

```bash
# Backend (dentro de backend/; usa la BD joyeriablanco_test del servicio db)
uv run ruff check . && uv run ruff format --check . && uv run mypy . && uv run pytest

# Web (dentro de joyeriablanco_web/)
npm run lint && npm run typecheck && npm run test && npm run build

# E2E: globalSetup levanta api-e2e, reconstruye su BD y carga datos con contraseña conocida.
# Vite se arranca solo en el puerto 5174, con proxy a la API de E2E en el 8001.
npx playwright install chromium    # solo la primera vez
npx playwright test
```

**Resultado esperado**: todo en verde. La inalterabilidad de la auditoría se prueba con `UPDATE` y
`DELETE` directos como `jb_app` y como `jb_owner`: ambos fallan (FR-022).

## 4. Producción en local (simulación)

```bash
DOMINIO=localhost TLS_MODO=internal docker compose -f docker-compose.prod.yml --env-file .env up -d --build
curl -sI http://localhost      | head -3   # → 308 hacia https://
curl -skI https://localhost    | grep -iE 'strict-transport|content-security|x-content-type|referrer-policy'
docker compose -f docker-compose.prod.yml port db 5432 || echo "BD sin puertos publicados ✔"
```

**Resultado esperado**:
- La redirección a HTTPS funciona.
- Aparecen las cuatro cabeceras de seguridad.
- La base de datos no tiene puertos publicados.
- La aplicación funciona igual que en desarrollo (FR-046 a FR-048).

**En el servidor real**, con `DOMINIO=<dominio>` y los puertos 80 y 443 abiertos, Caddy obtiene el
certificado solo. SC-011 se valida con un análisis público de la configuración TLS.
