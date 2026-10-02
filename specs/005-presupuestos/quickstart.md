# Quickstart y validación — 005

Guía para comprobar de extremo a extremo los presupuestos y su conversión en factura. El entorno se
levanta como en [001](../001-cimientos-clientes/quickstart.md), [002](../002-facturas/quickstart.md)
y [003](../003-pdf-impresion/quickstart.md).

Referencias:
- Endpoints en [contracts/openapi.yaml](contracts/openapi.yaml).
- Interfaz en [contracts/ui-rutas.md](contracts/ui-rutas.md).
- Documentos impresos en [contracts/documentos-pdf.md](contracts/documentos-pdf.md).
- Modelo y estados en [data-model.md](data-model.md).
- Decisiones en [research.md](research.md).

## Requisitos previos

Los de 001 a 003, incluido Pango en el Mac para los tests de PDF. No hay variables de entorno
nuevas.

## 1. Puesta en marcha

```bash
docker compose up -d --build
docker compose exec api alembic upgrade head           # aplica 0008_presupuestos
docker compose exec api joyeria cargar-datos-ejemplo   # añade presupuestos en todos los estados (FR-036)
cd joyeriablanco_web && npm ci && npm run dev           # http://localhost:5173
```

## 2. Validaciones manuales clave

| # | Paso | Resultado esperado | Requisito |
|---|---|---|---|
| 1 | Entrar como empleado y mirar el menú lateral | «Presupuestos» activo, sin «Próximamente» | FR-032 |
| 2 | Presupuestos → «Nuevo presupuesto»: cliente, dos líneas (2 × 45,00 y 1 × 1.200,00) y «Guardar borrador» | Previsualiza 1.290,00 + 270,90 = 1.560,90 €. Aparece en el listado con «Borrador». «Válido hasta» propone hoy + 30 días | FR-007, FR-009, FR-012 |
| 3 | Abrir el borrador, cambiar la fecha sin tocar la validez, y emitir confirmando | La validez se recalcula. Recibe `PRE-AAAA-0001` (o el siguiente). Ya no es editable. El contador de facturas no cambia | FR-002, FR-003, FR-014 |
| 4 | «Imprimir» el presupuesto, con y sin «Incluir número de cuenta» | PDF A4 con «PRESUPUESTO», la leyenda «Documento sin validez fiscal. No es una factura.» en su recuadro, «Válido hasta», el emisor y el cliente, las líneas, los totales y el pie. **Sin QR ni frase VERI\*FACTU**. El IBAN solo con la casilla. «PRE-… · Página 1 de 1» | FR-029, SC-007 |
| 5 | «Convertir en factura» y confirmar | Se abre el borrador de factura con «Procede del presupuesto PRE-…», con el cliente, las líneas y la fecha de hoy. El presupuesto está «En facturación» y no ofrece Modificar ni Anular | FR-018, FR-021 |
| 6 | Volver a pulsar «Convertir en factura», o «Abrir borrador de factura», desde el presupuesto | Abre el mismo borrador. No se crea otro | FR-018, FR-028 |
| 7 | Poner en el borrador una fecha anterior a la del presupuesto e intentar emitir | Error en el campo de la fecha. No se emite | FR-019 |
| 8 | Emitir el borrador | «Factura FAC-… emitida. PRE-… queda convertido». La factura lleva su QR y su registro. El presupuesto, «Convertido en FAC-…» con enlace, y la factura, «Procede del presupuesto PRE-…» | FR-020, FR-022 |
| 9 | Convertir otro presupuesto y eliminar el borrador de factura | El presupuesto vuelve a pendiente y se puede convertir, modificar o anular | FR-020 |
| 10 | Como administrador: «Modificar» un presupuesto pendiente, cambiar una línea y guardar con motivo | Se emite el siguiente PRE. El original queda «Sustituido por PRE-…» y el nuevo, «Sustituye a PRE-…», con el historial en ambos. Guardar sin cambios da el aviso de que no hay cambios | FR-015, FR-017 |
| 11 | Como administrador: «Anular» con motivo «Rechazado por el cliente» | Marca «Anulado», el motivo en el historial y «ANULADO» en el PDF | FR-016, FR-029 |
| 12 | Como empleado: abrir un presupuesto pendiente | No ve Modificar ni Anular. Un `POST …/anulacion` responde 403 | FR-015 a FR-017 |
| 13 | Ver un presupuesto de ejemplo con la validez vencida | «Caducado» en el listado. Al convertirlo, el aviso de validez vencida | FR-001, FR-018 |
| 14 | Configuración → Facturación: validez de 15 días y un pie de presupuesto; imprimir | Se guardan y quedan en la auditoría. Los nuevos proponen +15 días y el PDF lleva el pie de presupuesto. Si el pie se vacía, lleva el de factura | FR-031 |
| 15 | Intentar borrar un cliente que solo tiene un borrador de presupuesto | Se rechaza con el motivo y se sugiere desactivarlo | FR-033 |
| 16 | Presupuestos: filtrar por mes e «Imprimir listado» | PDF apaisado con todas las filas, sus marcas y los totales de los pendientes, caducados, en facturación y convertidos. Debajo, «No se suman: …» | FR-030 |
| 17 | Listado y modal a 360 px, y a 768, 1024, 1280, 1440 y 1536 px | Sin desplazamiento horizontal y con las acciones visibles | SC-009 |

## 3. Pruebas automáticas

```bash
# Backend (desde backend/)
uv run pytest                     # incluye numeración PRE, conversión, inalterabilidad, PDF y contrato
uv run pytest -k presupuesto      # solo esta feature
uv run pytest -m lento            # listado con 20.000 presupuestos (SC-008) y PDF de 20 líneas
uv run ruff check . && uv run ruff format --check . && uv run mypy .
uv run joyeria verificar-cadena   # íntegra tras las conversiones (SC-005)

# Web (desde joyeriablanco_web/)
uv --directory ../backend run joyeria exportar-openapi && npm run gen:api
npm run lint && npm run typecheck && npm run test && npm run build && npm run check:tokens
npx playwright test               # incluye e2e/presupuestos*.spec.ts
```

Tests de cobertura obligatoria (constitución VII; research R-14):
- `tests/integration/test_numeracion_presupuestos.py`: numeración PRE bajo concurrencia.
- `tests/unit/domain/test_importes.py` y `tests/integration/test_presupuestos_emision.py`:
  importes.
- `tests/integration/test_conversion_presupuesto.py`: conversión, también simultánea, idempotente
  y frente a la anulación.
- El encadenamiento con conversiones, en el mismo fichero y en `test_integridad*`.

## 4. Producción

- **Caddyfile**: la excepción de la CSP de la SPA cubre ya `^/api/v1/(facturas|presupuestos)/(listado|[^/]+)/pdf$`.
- **`deploy/verificar-produccion.sh`**: comprueba también `GET /api/v1/presupuestos/listado/pdf`
  sin sesión, que debe dar 401 con la CSP de la API.

```bash
docker compose -f docker-compose.prod.yml --env-file .env up -d --build
docker compose -f docker-compose.prod.yml exec api alembic upgrade head
deploy/verificar-produccion.sh <dominio>
```
