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
docker compose exec api joyeria cargar-datos-ejemplo  # configuración de facturación demo, unas 50 facturas con algunas correcciones y 5 borradores
                                                      # (sobre una BD con los datos de 001, añade solo la facturación)
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
| 3 bis | Emitir una factura con una fecha anterior a la última emitida (p. ej. de hace tres días) y probar una fecha futura y el 27/10/2024 | Se emite con la fecha elegida y el siguiente número de la serie del año de esa fecha. La futura y la anterior al 28/10/2024 se rechazan en el campo de la fecha | FR-018 |
| 4 | Emitir y confirmar | Aviso «FAC-2026-000N emitida». Aparece en el listado. En el detalle, el historial muestra el registro de alta con su huella | FR-007, FR-021, FR-028 |
| 5 | «Nuevo cliente» desde el modal, guardar y volver | El cliente nuevo queda elegido y las líneas siguen escritas | FR-046 |
| 6 | Guardar como borrador, cerrar y reabrir desde el listado | Marca «Borrador» sin número. Se puede editar y eliminar, y eliminarlo no consume ningún número | FR-019 |
| 7 | Emitir un borrador cuyo cliente no tiene dirección | 422 `cliente-no-facturable` con enlace a la ficha del cliente | FR-017 |
| 8 | Como admin: «Modificar» una factura con «no debió emitirse» | La original queda anulada y se emite una FAC nueva con el siguiente número. El historial enlaza las dos | FR-024 |
| 9 | Como admin: «Modificar» con «ya entregada» y causa «error en datos», cambiando la fecha a un día anterior a hoy | Se emite `REC-2026-000N` (R4, S) con la fecha elegida y base y cuota rectificadas. La original queda rectificada. El campo no admite una fecha anterior a la de la operación de la original | FR-018, FR-024, R-4 |
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

Las 20.000 facturas se generan con los servicios, así que quedan encadenadas como las reales:

```bash
docker compose --profile e2e up -d --build api-e2e
docker compose --profile e2e exec -T api-e2e joyeria reiniciar-bd-e2e
docker compose --profile e2e exec -T api-e2e joyeria cargar-datos-ejemplo \
    --clientes 500 --facturas 20000 --contrasena-demo '<contraseña>'
cd backend && uv run python scripts/medir_busqueda_facturas.py --contrasena '<contraseña>'
docker compose --profile e2e exec -T api-e2e joyeria verificar-cadena
```

Medición del 2026-09-29, en el equipo de desarrollo con la pila de E2E en Docker:

| Medida | Resultado | Objetivo |
|---|---|---|
| Generación de 20.000 facturas, con correcciones y borradores, por los servicios | 1 min 31 s | — |
| Búsquedas y cambios de filtro (100 variadas, sobre 20.009 documentos) | mediana 26 ms, p95 50 ms, máximo 66 ms | p95 < 1000 ms |
| Emisión de una factura (100 por la API) | mediana 7 ms, p95 9 ms, máximo 27 ms | p95 < 1000 ms (plan) |
| `verificar-cadena` sobre 20.107 registros | íntegra, 12,6 s | — |

## Resultado de la validación (2026-09-29)

Las 17 validaciones de §2 se cubren con pruebas automáticas que pasan en verde; algunas se
repitieron además a mano sobre la pila de desarrollo.

| # | Cómo se ha validado |
|---|---|
| 1 | `FacturacionPage.test.tsx` y `test_configuracion_facturacion.py` (BD sin configurar: aviso con lo que falta) |
| 2 | E2E `configuracion-facturacion.spec.ts` (acceso denegado) y `test_configuracion_facturacion.py` (403) |
| 3 | `FacturaModal.test.tsx` (1.290,00 / 270,90 / 1.560,90) y E2E `facturas.spec.ts` |
| 3 bis | E2E `facturas.spec.ts` («fecha libre») y `test_emision.py` (anterior a la última de la serie, de otro año, futura y anterior al 28/10/2024) |
| 4 | E2E `facturas.spec.ts`: aviso, listado y detalle con el registro de alta y su huella |
| 5 | `ClienteAltaPanel.test.tsx` y E2E `facturas.spec.ts` |
| 6 | E2E `facturas.spec.ts` (guardar, reabrir, editar y emitir; eliminar sin consumir número) y `test_borradores.py` |
| 7 | `test_borradores.py` y `test_emision.py` (`cliente-no-facturable`); aviso con enlace en `ResumenCliente` |
| 8 | E2E `facturas.spec.ts` (reemisión) y `test_correcciones.py` |
| 9 | E2E `facturas.spec.ts` (REC R4 y rectificativa con fecha anterior a hoy), `test_correcciones.py` (contenido del registro según R-4 y fecha no anterior a la operación) y `FacturaModal.consulta.test.tsx` |
| 10 | `test_correcciones.py` (R1 sin líneas, total 0 y desglose a cero) |
| 11 | E2E `facturas.spec.ts` y `test_correcciones.py` |
| 12 | E2E `facturas.spec.ts` (empleado sin acciones) y `test_correcciones.py` (403 en ambas rutas) |
| 13 | E2E `configuracion-facturacion.spec.ts` y `test_configuracion_facturacion.py` |
| 14 | `test_configuracion_facturacion.py` (`contador-no-ajustable`) |
| 15 | `test_emision.py` y `test_borradores.py` (`cliente-con-documentos`, con factura o con borrador) |
| 16 | A mano en desarrollo: tras la migración 0005 y los datos de ejemplo, «Cadena íntegra (57 registros).», código 0. Automatizado en `test_verificar_cadena.py` |
| 17 | E2E `acciones-visibles.spec.ts` (360 a 1536 px, página completa) y `responsive.spec.ts` (modal a pantalla completa en móvil) |

**Inalterabilidad (SC-005)**, a mano en desarrollo: el `UPDATE` como `jb_app` da «permission
denied for table facturas» y el `DELETE` como `jb_owner`, «Los documentos de facturación emitidos
son inalterables». Después, `verificar-cadena` sigue dando la cadena por íntegra.

**SC-001** (emitir una factura de tres líneas en menos de 2 minutos): el recorrido automático de
`facturas.spec.ts`, que además da de alta al cliente desde el modal, tarda unos 3,5 s. El
cronometraje con una persona de la tienda queda pendiente del responsable.

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
