# Quickstart y validación — 002

Esta guía sirve para comprobar de extremo a extremo que la facturación funciona. El entorno se
levanta igual que en [001](../001-cimientos-clientes/quickstart.md) (§1).

Referencias: endpoints en [contracts/openapi.yaml](contracts/openapi.yaml), rutas en
[contracts/ui-rutas.md](contracts/ui-rutas.md), tablas en [data-model.md](data-model.md) y fuentes
oficiales en [research.md](research.md).

## Requisitos previos

- Los de 001: Docker con Compose v2, `uv` 0.12 o superior y Node.js 26.
- Variables `SIF_*` del sistema informático (R-5):
  - En desarrollo, test y e2e se usan los valores ficticios de `.env.example`.
  - En producción son obligatorias. La API no arranca sin ellas.

## 1. Puesta en marcha

```bash
docker compose up -d --build
docker compose exec api alembic upgrade head          # aplica 0005_facturacion
docker compose exec api joyeria cargar-datos-ejemplo  # añade la configuración de facturación demo, unas 50 facturas con algunas correcciones y 5 borradores
cd joyeriablanco_web && npm ci && npm run dev          # http://localhost:5173
```

**Resultado esperado**: el menú muestra Facturas activa. Facturas lista las del año en curso, sin
indicadores ni columna de estado, con los borradores marcados.

## 2. Validaciones manuales clave

| # | Paso | Resultado esperado | Requisito |
|---|---|---|---|
| 1 | Como admin: Configuración → Facturación en una BD recién migrada (sin datos de ejemplo) | IVA al 21 %, clave 01, modalidad y emisor vacíos, y el aviso «no se puede emitir» con lo que falta | FR-001, FR-004 |
| 2 | Como empleado, abrir `/configuracion/facturacion` | Acceso denegado. El `PUT` directo responde 403 | FR-001, SC-005 |
| 3 | «Nueva factura», elegir un cliente, añadir 1 × 1.200,00 y 2 × 45,00 | Previsualización: base 1.290,00, IVA (21 %) 270,90 y total 1.560,90 | FR-013 a FR-015 |
| 4 | Emitir y confirmar | Aviso «FAC-2026-000N emitida». Aparece en el listado. En el detalle, el historial muestra el registro de alta con su huella | FR-007, FR-021, FR-028 |
| 5 | «Nuevo cliente» desde el modal, guardar y volver | El cliente nuevo queda elegido y las líneas siguen escritas | FR-046 |
| 6 | Guardar como borrador, cerrar y reabrir desde el listado | Marca «Borrador» sin número. Se puede editar y eliminar, y eliminarlo no consume ningún número | FR-019 |
| 7 | Emitir un borrador cuyo cliente no tiene dirección | 422 `cliente-no-facturable` con enlace a la ficha del cliente | FR-017 |
| 8 | Como admin: «Modificar» una factura con «no debió emitirse» | La original queda anulada y se emite una FAC nueva con el siguiente número. El historial enlaza las dos | FR-024 |
| 9 | Como admin: «Modificar» con «ya entregada» y causa «error en datos» | Se emite `REC-2026-000N` (R4, S) con base y cuota rectificadas. La original queda rectificada | FR-024, R-4 |
| 10 | Como admin: «Modificar» quitando todas las líneas con la causa «devolución…» | Se emite una rectificativa R1 con total 0,00 € | Clarifications (plan) |
| 11 | Como admin: «Anular» una factura duplicada | Registro de anulación sin factura nueva. El número queda como anulado | FR-025 |
| 12 | Como empleado, consultar una emitida | No aparecen «Anular» ni «Modificar». El `POST …/anulacion` responde 403 | FR-023, FR-025 |
| 13 | Configuración → «Ajustar» el próximo número a 143 con un motivo | El aviso previo indica cuántos números quedarán sin usar. La siguiente factura es `FAC-2026-0143` y el ajuste queda en la auditoría | FR-010 |
| 14 | Ajustar a un número ya usado | 409 `contador-no-ajustable` | FR-010 |
| 15 | Intentar borrar (admin) un cliente con facturas | 409 `cliente-con-documentos` y se sugiere desactivarlo | FR-042 |
| 16 | `docker compose exec api joyeria verificar-cadena` | «Cadena íntegra (N registros)», código de salida 0 | FR-031 |
| 17 | Tabla de facturas a 768, 1024, 1280, 1440 y 1536 px; modal a 360 px | Acciones visibles sin desplazar. Modal a pantalla completa y sin desplazamiento horizontal | SC-008 |

### Inalterabilidad (SC-005)

```bash
docker compose exec db psql -U jb_app -d joyeriablanco \
  -c "UPDATE facturas SET importe_total = 0"            # → ERROR: permission denied (42501)
docker compose exec db psql -U jb_owner -d joyeriablanco \
  -c "DELETE FROM registros_facturacion"                # → ERROR: Los documentos de facturación emitidos son inalterables
```

La misma comprobación está automatizada en `tests/integration/test_facturacion_inalterable.py`.

## 3. Pruebas automáticas

```bash
# Backend (dentro de backend/)
uv run ruff check . && uv run ruff format --check . && uv run mypy . && uv run pytest

# Solo los tests obligatorios de la constitución VII para esta feature
uv run pytest tests/unit/domain/test_importes.py tests/unit/domain/test_huella.py \
  tests/integration/test_numeracion_concurrencia.py tests/integration/test_cadena_registros.py

# Web (dentro de joyeriablanco_web/)
uv --directory ../backend run joyeria exportar-openapi && npm run gen:api
npm run lint && npm run typecheck && npm run test && npm run build && npm run check:tokens
npx playwright test          # incluye facturas.spec.ts, acciones-visibles y teclado ampliados
```

### Rendimiento (SC-007)

```bash
docker compose --profile e2e up -d api-e2e
docker compose exec api-e2e python scripts/medir_busqueda_facturas.py --facturas 20000
#   → p95 de 100 búsquedas y cambios de filtro < 1 s
```

El resultado de la medición se anota aquí al cerrar la feature.

## 4. Producción

Antes de emitir facturas reales:

- [ ] La asesoría confirma la modalidad (TODO(MODALIDAD_VERIFACTU)) y queda fijada en Configuración.
- [ ] La declaración responsable define el productor (TODO(DECLARACION_RESPONSABLE)) y `SIF_*` está
      en `.env`.
- [ ] La asesoría confirma la clave de régimen 01.
- [ ] El reloj del servidor está sincronizado por NTP (`timedatectl`), porque el margen es de un
      minuto (F-10, art. 7.f).
- [ ] Las copias de seguridad están configuradas (README), por la obligación legal de conservación.
- [ ] Las features 003 (PDF con QR) y 004 (remisión o firma) están desplegadas, o el responsable
      asume por escrito usar el sistema sin ellas (spec, Assumptions).
