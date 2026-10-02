# Quickstart y validación — 003

Guía para comprobar de extremo a extremo la factura en PDF con su QR y el listado impreso. El
entorno se levanta como en [001](../001-cimientos-clientes/quickstart.md) y
[002](../002-facturas/quickstart.md).

Referencias:
- Endpoints en [contracts/openapi.yaml](contracts/openapi.yaml).
- Interfaz en [contracts/ui-rutas.md](contracts/ui-rutas.md).
- Disposición de los documentos en [contracts/documentos-pdf.md](contracts/documentos-pdf.md).
- Decisiones y fuentes oficiales en [research.md](research.md).

## Requisitos previos

- Los de 001 y 002.
- **Pango en el Mac**, para lanzar los tests del backend desde `backend/` (R-4):

  ```bash
  brew install pango
  # Si WeasyPrint no encuentra las librerías de Homebrew:
  export DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib
  uv run python -c "import weasyprint; print(weasyprint.__version__)"   # 70.x
  ```

- **`AEAT_ENTORNO`** (R-3):
  - En desarrollo, test y e2e puede quedar vacío, y equivale a `pruebas`.
  - En producción es obligatorio: `pruebas` mientras se valida la integración, y `produccion`
    cuando se facture de verdad.
  - La API no arranca en producción sin él.

## 1. Puesta en marcha

```bash
docker compose up -d --build                           # la imagen instala Pango (R-4)
docker compose exec api alembic upgrade head           # aplica 0007_contacto_pie_factura
docker compose exec api joyeria cargar-datos-ejemplo   # añade contacto y pie ficticios (FR-032)
cd joyeriablanco_web && npm ci && npm run dev           # http://localhost:5173
```

## 2. Validaciones manuales clave

| # | Paso | Resultado esperado | Requisito |
|---|---|---|---|
| 1 | Abrir una factura emitida y pulsar «Imprimir» | Se abre una pestaña con el PDF A4: QR arriba a la izquierda con «QR tributario:» encima, emisor con logotipo y contacto a la derecha, título, número, fechas, cliente, líneas, desglose, totales, pie de factura y «FAC-… · Página 1 de 1» | FR-001 a FR-006, FR-011, FR-013 |
| 2 | Escanear el QR del PDF, en pantalla o impreso, con el móvil | Abre `https://prewww2.aeat.es/wlpl/TIKE-CONT/ValidarQR?nif=…&numserie=FAC-…&fecha=DD-MM-AAAA&importe=…` con los datos de la factura. Antes de la 004 la AEAT responde que no consta: es lo esperado | FR-016, FR-017, SC-002 |
| 3 | Con la modalidad VERI\*FACTU, comprobar el texto bajo el QR. Repetir con una factura no VERI\*FACTU, en una BD de pruebas con esa modalidad | «Factura verificable en la sede electrónica de la AEAT» debajo, solo en VERI\*FACTU. La dirección usa `ValidarQRNoVerifactu` en la otra | FR-015, FR-016 |
| 4 | Medir el QR en el papel con una regla, impreso «a tamaño real» | Unos 35 × 35 mm, con margen en blanco alrededor | FR-014, SC-006 |
| 5 | Factura con IBAN: imprimir sin marcar la casilla y marcándola | Sin la casilla, sin bloque de pago. Con ella, «Pago por transferencia» con el IBAN agrupado | FR-010, SC-004 |
| 6 | Factura emitida sin IBAN | No aparece la casilla | FR-010 |
| 7 | Marcar «Duplicado» e imprimir. Abrir una anulada | «DUPLICADO» bajo el título. En la anulada no hay casilla de duplicado, y el PDF lleva «ANULADA» y, si se reemitió, «Sustituida por FAC-…» | FR-009, FR-033 |
| 8 | Imprimir la rectificativa `REC-…` y su original | La REC dice «Factura rectificativa», «Rectifica a FAC-… de …», la causa y el importe de la rectificación. La original lleva «RECTIFICADA por REC-…» | FR-008, FR-009 |
| 9 | Imprimir una factura de oro de inversión | «Base exenta», «IVA 0,00 €» y la mención del art. 140 bis | FR-007 |
| 10 | Factura con 60 líneas | Varias páginas, cabecera de la tabla repetida, QR solo en la primera y «Página n de m» | FR-011, FR-013 |
| 11 | Facturas: filtrar «2026», un mes y «Total mayor», y pulsar «Imprimir listado» | PDF apaisado con el filtro descrito en la cabecera, todas las filas del filtro y no solo las 25 de la página, en ese orden, y los totales por tipo y generales de las vigentes, con las excluidas contadas | FR-018 a FR-022 |
| 12 | Filtro sin resultados. Y con «Todos los años» si hay más de 5.000, o `GET /api/v1/facturas/listado/pdf?anio=todos` con el límite reducido en un entorno de pruebas | Botón desactivado con su motivo. El servidor responde 422 `listado-demasiado-grande` | FR-018, SC-007 |
| 13 | Cerrar la sesión en otra pestaña y pulsar «Imprimir» | La pestaña nueva muestra la página «Tu sesión ha caducado…» con «Volver a la aplicación», nunca JSON | FR-028, R-8 |
| 14 | Como admin: Configuración → Facturación, rellenar teléfono, correo, web y un pie de dos líneas; guardar; reimprimir una factura antigua | Se guardan y quedan en la auditoría. La factura antigua sale con el contacto y el pie nuevos y con su emisor fiscal de siempre | FR-024 a FR-026 |
| 15 | Teléfono `abc`, correo `x@`, y el mismo `PUT` como empleado | Errores en sus campos. 403 para el empleado | FR-024, FR-027 |
| 16 | Consulta y listado a 360 px | Casillas y botones apilados, sin desplazamiento horizontal | ui-rutas |

## 3. Pruebas automáticas

```bash
# Backend (desde backend/)
uv run pytest                               # incluye unitarias de QR y formato, integración de PDF y contrato
uv run pytest -m lento                      # SC-001 y SC-005: factura de 20 líneas y listados de 1.000 y 5.000 filas
uv run ruff check . && uv run ruff format --check . && uv run mypy .

# Web (desde joyeriablanco_web/)
uv --directory ../backend run joyeria exportar-openapi && npm run gen:api
npm run lint && npm run typecheck && npm run test && npm run build && npm run check:tokens
npx playwright test                          # incluye e2e/impresion.spec.ts
```

Resultados esperados de `-m lento`:
- La factura, en menos de 3 s.
- El listado de 1.000 filas, en menos de 15 s.
- El de 5.000, en menos de 60 s.
- Ninguno supera unos 300 MB de memoria residente por generación. La prueba previa dio 11,6 s y
  250 MB con 5.000 filas (R-7).

## Resultado de la validación (2026-10-02)

**Rendimiento** (`uv run pytest -m lento`; SC-001 y SC-005), en el contenedor de la API, que es
Linux como el servidor:

| Medida | Resultado | Objetivo |
|---|---|---|
| Factura de 20 líneas (20 generaciones) | p95 0,21 s, mediana 0,15 s | p95 < 3 s |
| Listado de 1.000 filas | 3,7 s, 240 MB de pico, PDF de 0,32 MB | < 15 s |
| Listado de 5.000 filas | 19,2 s, 265 MB de pico, PDF de 0,98 MB | < 60 s y unos 300 MB |

En el Mac, los tiempos son parecidos (0,25 s, 3,6 s y 18,2 s) y la memoria algo mayor (294 MB con
5.000 filas), por el asignador de macOS.

**Validaciones de §2**:

| # | Cómo se ha validado |
|---|---|
| 1 | `test_pdf_factura.py` (contenido completo, pie «Página n de m») y revisión visual de PDF generados con los datos de desarrollo: ordinaria, rectificativa, rectificada y anulada |
| 2 | `test_qr.py` (vectores de F-12 §4 y §8, lectura con zxing-cpp y nivel M) y `test_pdf_factura.py` (valores del registro de alta). Además, el QR **pintado por Chromium** a partir de la plantilla real se capturó y se leyó con zxing-cpp: misma URL que el modelo y nivel M. **Pendiente del responsable**: escanearlo con un móvil |
| 3 | `test_pdf_factura.py` (frase solo en VERI\*FACTU y `ValidarQRNoVerifactu` en no VERI\*FACTU) |
| 4 | `test_pdf_factura.py` (árbol de cajas: 35 × 35 mm y 6 mm de margen en la primera página). **Pendiente del responsable**: medirlo en papel |
| 5 y 6 | `test_pdf_factura.py`, `ImprimirFactura.test.tsx` y E2E `impresion.spec.ts` |
| 7 | `test_pdf_factura.py` (DUPLICADO y 409 en una anulada, «Sustituida por» la vigente actual) y `ImprimirFactura.test.tsx` |
| 8 y 9 | `test_pdf_factura.py` (rectificativa, devolución total, rectificada y exenta) |
| 10 | `test_pdf_factura.py` (100 líneas: varias páginas, QR solo en la primera, pie en todas) |
| 11 | `test_pdf_listado.py` (105 filas en los cuatro órdenes, filtros, totales por tipo cuadrados con el detalle de cada vigente, excluidas, generación por bloques) y E2E `impresion.spec.ts` |
| 12 | `ImprimirListado.test.tsx` (desactivado con su motivo) y `test_pdf_listado.py` (422 `listado-demasiado-grande`, también en HTML) |
| 13 | `test_pdf_factura.py` (página HTML con «Tu sesión ha caducado», sin JSON ni datos técnicos) y, contra Caddy, la misma página |
| 14 y 15 | `test_configuracion_contacto.py` (validación, auditoría, conservación, versión, 403 y reimpresión con el contacto nuevo), `FacturacionPage.test.tsx` y E2E `configuracion-facturacion.spec.ts` |
| 16 | Vitest de los componentes en móvil; la revisión visual a 360 px queda **pendiente del responsable** |

**Producción**:
- La imagen `prod` genera un PDF con el contenedor `read_only`, `cap_drop: ALL`, `/tmp` en tmpfs y
  el usuario `app`: fuentes y logotipo empaquetados, y la caché de fontconfig en `/tmp/cache`.
- Las cuatro comprobaciones nuevas de `verificar-produccion.sh` se ejecutaron contra Caddy con el
  `Caddyfile` de producción, delante de la API de desarrollo, y pasaron:
  - el PDF sin sesión responde 401;
  - la respuesta lleva la CSP de la API con `object-src 'self'`;
  - no lleva la CSP de la SPA;
  - la SPA conserva `object-src 'none'`.
- **Pendiente del responsable**:
  - La simulación completa de producción, que necesita el `.env` de producción con
    `AEAT_ENTORNO`.
  - La comprobación del visor de PDF en Chrome, Firefox y Safari (§4).

## 4. Producción

```bash
# .env de producción: AEAT_ENTORNO=pruebas (validación) o produccion (facturación real)
docker compose -f docker-compose.prod.yml --env-file .env up -d --build
deploy/verificar-produccion.sh <dominio>
```

`verificar-produccion.sh` comprueba además (R-8):
- Que `GET /api/v1/facturas/listado/pdf` sin sesión responde 401 con la CSP de la API, con
  `object-src 'self'`, y sin la CSP global.
- Que `/` mantiene la CSP global, con `object-src 'none'`.

**Verificación manual del visor**: con sesión, abrir el PDF de una factura y el del listado en
Chrome, Firefox y Safari de escritorio, y en Safari de iOS. Deben mostrarse en el visor integrado
y poder imprimirse.

Antes de facturar de verdad hay que cumplir lo de 002 (quickstart, «Antes de producción») y, además,
fijar `AEAT_ENTORNO=produccion`.
