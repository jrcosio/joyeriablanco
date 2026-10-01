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
