---
description: "Tareas de implementación de la feature 003"
---

# Tasks: PDF de factura con QR de cotejo e impresión del listado

**Input**: `specs/003-pdf-impresion/`:
- [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md) y [data-model.md](data-model.md).
- [contracts/openapi.yaml](contracts/openapi.yaml), [contracts/ui-rutas.md](contracts/ui-rutas.md)
  y [contracts/documentos-pdf.md](contracts/documentos-pdf.md).
- [quickstart.md](quickstart.md).

**Prerequisites**: spec con clarify, plan, research con F-6, F-10, F-11 y F-12, data-model,
contratos, DESIGN.md 1.2 y checklists con su refinamiento. Todo en la rama `003-pdf-impresion`.

**Tests**: SÍ, con TDD como en 001 y 002. En cada historia, los tests se escriben primero y deben
fallar. Esta feature no toca los cuatro tests obligatorios de la constitución VII. Sí comprueba que
el QR coincide con el registro de alta (SC-002) y que los totales impresos cuadran al céntimo
(SC-005). Esas tareas van marcadas con ⚖️.

**Organization**: por historias de usuario: US1 (factura en PDF, P1) → US2 (listado, P2) → US3
(contacto y pie, P3).
- La migración y el modelo del contacto van en Foundational, porque US1 ya los lee para imprimir.
- US3 añade la API, la validación y la pantalla.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: puede ir en paralelo (ficheros distintos y sin dependencias pendientes).
- **[Story]**: historia de la spec (US1–US3).
- Las rutas son relativas a la raíz del repositorio.

## Path Conventions

- **Backend**: `backend/app/…`, `backend/tests/…` y `backend/alembic/versions/…`.
- **Web**: `joyeriablanco_web/src/…` y `joyeriablanco_web/e2e/…`.
- **Reglas del QR y del contenido**: se toman **solo** de research R-1 a R-12 y de sus fuentes
  F-n. Nunca de memoria (constitución IV).
- **Diseño de los documentos**: solo tokens `paper*` y `print-*` de `docs/DESIGN.md` 1.2 (R-5).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: dependencias, imagen con Pango, recursos estáticos, ajuste del entorno de la AEAT y
test de contrato preparado para 003.

- [X] T001 Dependencias y entorno de desarrollo (research R-4):
  - `backend/pyproject.toml`:
    - Dependencias: `weasyprint>=70,<71`, `jinja2>=3.1,<3.2`, `segno>=1.6,<1.7` y `pypdf>=6.19,<7`.
    - En el grupo `dev`: `zxing-cpp>=3.1,<3.2` y `numpy`.
    - Marca de pytest `lento` («mediciones de rendimiento»), excluida por defecto con `-m "not lento"` en `addopts`.
    - `[[tool.mypy.overrides]]` con `ignore_missing_imports` para `weasyprint.*`, `segno.*` y `zxingcpp.*`, si no traen tipos.
  - `uv lock` y `uv sync`.
  - Comprobar `uv run python -c "import weasyprint"` en el Mac. Si falla por Pango, **parar y pedir al responsable** `! brew install pango` y, si hace falta, `export DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib` (quickstart, «Requisitos previos»).
- [X] T002 `backend/Dockerfile` (R-4):
  - En las etapas `base` y `prod`, con `apt-get install --no-install-recommends` y limpieza de listas: `libpango-1.0-0`, `libpangoft2-1.0-0`, `libharfbuzz-subset0` y `fonts-dejavu-core`.
  - `XDG_CACHE_HOME=/tmp/cache` en las dos etapas.
  - Comprobar `docker compose build api` y `docker compose exec api python -c "import weasyprint"`.
- [X] T003 [P] Recursos estáticos (R-4):
  - `backend/app/resources/fuentes/`: los WOFF2 de Fontsource 5.3.0, subconjuntos `latin` y `latin-ext`, de Manrope 400, 600 y 700 (`@fontsource/manrope`) y de Bodoni Moda 400 y 500 (`@fontsource/bodoni-moda`).
  - `OFL.txt` y un `README.md` con el origen, la versión y el SHA-256 de cada fichero.
  - `backend/app/resources/marca/logo.png`, copiado de `joyeriablanco_web/src/assets/brand/logo.png`, con su `README.md` (origen y SHA-256).
  - Actualizar `backend/app/resources/README.md`.
- [X] T004 [P] Entorno de la AEAT (research R-3, FR-017):
  - `backend/app/core/config.py`: `class EntornoAeat(StrEnum)` con `pruebas` y `produccion`, el campo `aeat_entorno: EntornoAeat | None = None` y la propiedad `entorno_aeat`, que vale `pruebas` si está vacío.
  - En el validador de producción: sin `aeat_entorno`, `ValueError("En producción hay que fijar AEAT_ENTORNO (pruebas o produccion)")`.
  - `.env.example`: la variable comentada y explicada.
  - `docker-compose.prod.yml`: `AEAT_ENTORNO: ${AEAT_ENTORNO:?Falta AEAT_ENTORNO}`.
  - Test `backend/tests/unit/test_config_aeat.py`: por defecto, `pruebas`; en producción sin la variable falla; con `produccion` arranca.
- [X] T005 Test de contrato para 003 (002 R-14) en `backend/tests/integration/test_contrato_openapi.py`:
  - Lista `PENDIENTES_003` con las dos operaciones de [contracts/openapi.yaml](contracts/openapi.yaml), excluidas solo del sentido «contrato → API».
  - `test_hay_un_contrato_por_feature` incluye `003-pdf-impresion`.
  - El test vuelve a verde tras añadir el contrato en el plan.
  - Las tareas T024 y T033 vacían la lista, y T033 la elimina.

**Checkpoint**: dependencias instaladas en el Mac y en la imagen, recursos copiados con su
procedencia, y el test de contrato en verde.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: formato en español, tokens e infraestructura de renderizado, y las columnas de
contacto que US1 ya imprime.

**⚠️ CRITICAL**: ninguna historia empieza antes de cerrar esta fase.

### Tests ⚠️ (escribir primero, deben fallar)

- [ ] T006 [P] Test `backend/tests/unit/domain/test_formato.py` (FR-006, R-6):
  - `format_euros`: «1.560,90 €», «0,00 €», «1.234.567,89 €», sin `float`, y `Decimal` con más de dos decimales → `ValueError`.
  - `format_unidades`: «2», «1,50» y «1.200».
  - `format_fecha`: «05/03/2026».
  - `format_iban`: «ES91 2100 0418 4502 0005 1332».
  - `format_porcentaje`: «21 %» y «10,5 %».
  - Etiquetas de identificación: `NIF` y L7 de `02` a `06`, con el país si no es `ES`, p. ej. «Pasaporte X1234567 (Francia)».
  - Las cadenas esperadas son las mismas que en `joyeriablanco_web/src/lib/dinero.test.ts` y `facturacion.test.ts`.
- [ ] T007 [P] Test `backend/tests/unit/test_tokens_papel.py` (R-5, FR-030):
  - Lee con `yaml` el frontmatter de `docs/DESIGN.md`.
  - Comprueba que `app/core/pdf/tokens.py` tiene exactamente los colores `paper*`, la tipografía `print-*` y `print-margin` / `print-gutter` del documento, con los mismos valores.
  - `app/resources/pdf/papel.css` no contiene `#`, `rgb(`, `hsl(` ni tamaños `pt`/`mm` fuera de declaraciones `var(--…)`. Se saltan los comentarios.
- [ ] T008 [P] Test `backend/tests/unit/test_pdf_render.py` (R-4):
  - Renderizar una plantilla mínima que extienda `base.html` produce un PDF.
  - pypdf lo abre, extrae el texto con tildes, eñes y «€», y encuentra incrustadas las fuentes `Manrope` y `Bodoni-Moda`, sin otras salvo DejaVu como último recurso.
  - `render` respeta el limitador: con capacidad 1, dos llamadas simultáneas se serializan.

### Implementación

- [ ] T009 [P] `backend/app/domain/formato.py` con las funciones de T006. Usa `Decimal` y separadores españoles, y ningún `locale` del sistema.
- [ ] T010 [P] `backend/app/core/pdf/tokens.py`: los tokens de R-5 como constantes tipadas y `css_variables() -> str`, que produce el bloque `:root { --paper-ink: …; --print-body-size: …; … }`.
- [ ] T011 Plantilla base y CSS de papel (R-5, contracts/documentos-pdf.md, «Comunes»):
  - `backend/app/resources/pdf/base.html`: `<html lang="es">`, `<title>`, `<meta name="author">`, `@font-face` relativos a `fuentes/` con `unicode-range` y los bloques `{% block %}`.
  - `backend/app/resources/pdf/papel.css`: solo `var(--…)`, filetes de `0.75pt`, esquinas a 0 y sin sombras, `@page` con `print-margin`, `font-variant-numeric: tabular-nums` en las cifras, y `thead { display: table-header-group }` y `tr { break-inside: avoid }`.
- [ ] T012 `backend/app/core/pdf/plantillas.py` y `backend/app/core/pdf/render.py` (R-4, R-7):
  - Entorno Jinja2 sobre `importlib.resources.files("app.resources") / "pdf"`, con `autoescape=True`, `StrictUndefined` y los filtros de `domain/formato.py`.
  - `base_url` hacia `app/resources`.
  - `render_html_pdf(plantilla, contexto) -> bytes` con `FontConfiguration` por llamada.
  - Ejecución en hilo con `anyio.to_thread.run_sync` bajo un `anyio.CapacityLimiter`: `LIMITE_FACTURAS = 4` y `LIMITE_LISTADOS = 1`.
  - `backend/app/core/pdf/__init__.py` exporta la API pública.
- [ ] T013 Migración `backend/alembic/versions/0007_contacto_pie_factura.py` y modelo (data-model):
  - Las cuatro columnas y `ck_config_contacto_sin_vacios`, con `downgrade`.
  - `backend/app/models/configuracion_facturacion.py`: `emisor_telefono`, `emisor_correo`, `emisor_web` y `pie_factura`.
  - Comprobar `alembic upgrade head` y `downgrade -1` en la BD de desarrollo, y que la suite de 002 sigue en verde.

**Checkpoint**: formato y tokens probados, plantillas renderizables con las fuentes de la marca,
y las columnas de contacto disponibles.

---

## Phase 3: User Story 1 - Imprimir una factura con su QR (Priority: P1) 🎯 MVP

**Goal**: desde la consulta de una factura emitida, «Imprimir» abre en una pestaña nueva el PDF A4
con todo el contenido obligatorio y el QR tributario. Incluye las casillas «Incluir número de
cuenta» y «Duplicado».

**Independent Test**:
1. Se emite una factura y se pide su PDF: contiene FR-003, su QR se lee con la URL de R-1 y nivel
   M, y mide de 30 a 40 mm.
2. El IBAN y «DUPLICADO» solo salen si se piden.
3. Una anulada lleva «ANULADA» y rechaza el duplicado.

### Tests for User Story 1 ⚠️

- [ ] T014 [P] [US1] ⚖️ Test `backend/tests/unit/domain/test_qr.py` (R-1, R-2; SC-002):
  - Vectores de F-12:
    - §4: `numserie=12345678&G33` → `numserie=12345678%26G33`.
    - §8.1 a §8.4: las cuatro URL, con `nif=89890001K`, `numserie=12345678-G33` y `fecha=01-09-2024`, salvo `importe=241.40` frente a `241.4` (research R-1).
  - Orden exacto de los parámetros y ningún parámetro más (`idioma` y `formato` nunca).
  - Validaciones: ASCII de 32 a 126, `nif` de 9, `numserie` de hasta 60, fecha `DD-MM-AAAA` y 12 cifras enteras. Un incumplimiento → `ValueError`.
  - Base según `Modalidad` × `EntornoAeat`.
  - `qr_svg(url)`: la matriz de segno, rasterizada con numpy y leída con `zxingcpp.read_barcodes`, devuelve exactamente la URL con `ec_level == "M"`. Un `boost_error` accidental haría fallar este caso.
- [ ] T015 [P] [US1] Test `backend/tests/integration/test_pdf_factura.py`. Las facturas se emiten con los servicios reales (`facturacion_datos.py`) y el texto se extrae con pypdf:
  - **Contenido** (SC-003): en una ordinaria, una exenta, una REC R4, una REC de devolución total («Devolución total de la factura …»), una anulada con y sin reemisión y una rectificada:
    - cada dato de FR-003 y FR-008;
    - la mención exacta de `MENCION_EXENCION_ORO_INVERSION`;
    - las marcas de FR-009, con el número de la vigente actual.
  - **Fuente de los datos**: tras cambiar la configuración del emisor y la ficha del cliente, el PDF conserva los datos copiados al emitir (FR-004). El contacto y el pie, si están en la configuración (columnas de T013), salen; si no, no hay etiquetas vacías.
  - **IBAN** (FR-010, SC-004): con `iban=true`, sale «IBAN ES91 2100 …». Sin el parámetro, no. En una factura sin IBAN, `iban=true` no añade nada.
  - **Duplicado** (FR-033, SC-007): `duplicado=true` en vigente y rectificada → «DUPLICADO». En una anulada → 409 `duplicado-no-disponible`.
  - **QR**:
    - En el árbol de cajas del documento, la caja `#qr` está en la primera página, mide de 30 a 40 mm y tiene al menos 2 mm de relleno (SC-006).
    - «QR tributario:» y, solo en `verifactu`, la frase larga. Con una factura emitida en `no_verifactu`, en una BD de pruebas, la URL usa `ValidarQRNoVerifactu` y no hay frase.
    - El tamaño de letra de los textos del QR es mayor o igual que el de los datos, comparando las cajas.
  - **Varias páginas**: 100 líneas largas → más de una página, el QR solo en la primera y «FAC-… · Página n de m».
  - **Respuesta**: `application/pdf`, `Content-Disposition: inline; filename="FAC-AAAA-NNNN.pdf"`, `Cache-Control: no-store` y la CSP de PDF de R-8.
  - **Errores**: sin sesión → 401. El id de un borrador → 404. Con `Sec-Fetch-Dest: document`, los errores son `text/html` con el mensaje de R-8, la CSP con el *hash* del estilo y sin `type` ni trazas (FR-028).
  - **Logs** (FR-029): `caplog` no contiene el nombre, el NIF ni los importes del cliente.
- [ ] T016 [P] [US1] Tests web (Vitest + MSW):
  - `joyeriablanco_web/src/lib/impresion.test.ts`: `urlPdfFactura`, con y sin opciones.
  - `joyeriablanco_web/src/features/facturas/ImprimirFactura.test.tsx`:
    - El enlace tiene `target="_blank"`, `rel="noopener"` y el nombre «Imprimir factura FAC-…».
    - La casilla del IBAN aparece solo con `emisor.iban`, y la de duplicado, salvo en una anulada.
    - Las dos empiezan desmarcadas y cambian el `href` al marcarlas.
    - El doble clic dentro de los 2 s se ignora, y «Preparando…» se anuncia con `aria-live`.
  - Ampliar `FacturaModal.consulta.test.tsx`: «Imprimir» para empleado y administrador, y en una anulada, sin la casilla de duplicado.

### Implementation for User Story 1

- [ ] T017 [P] [US1] `backend/app/domain/qr.py`: `build_cotejo_url(modalidad, entorno, *, nif, num_serie, fecha_expedicion, importe_total)` y `qr_svg(url, *, color)`, según R-1 y R-2. Usan `format_amount` de `domain/huella.py`, `urlencode(..., quote_via=quote)` y `segno.make(url, error="m", micro=False, boost_error=False).svg_inline(border=0, omitsize=True, …)`.
- [ ] T018 [P] [US1] `backend/app/domain/tipos.py`: `TEXTO_CAUSA_RECTIFICACION` con los literales de `joyeriablanco_web/src/lib/facturacion.ts` (R-6), y las etiquetas de los tipos de identificación de L7 si no están ya.
- [ ] T019 [US1] `backend/app/core/errors.py`:
  - `DuplicadoNoDisponible` (409, `duplicado-no-disponible`) y `ListadoDemasiadoGrande` (422, con `limite` y `total`).
  - En `register_error_handlers`: si la ruta es de PDF (`…/pdf`) y la petición es una navegación (`Sec-Fetch-Dest: document`, o `Accept` con `text/html` si falta), responder con `error.html` renderizado (`HTMLResponse`), el mismo estado y la CSP con el *hash* del estilo (R-8).
  - `backend/app/resources/pdf/error.html` según contracts/documentos-pdf.md.
- [ ] T020 [US1] `backend/app/services/impresion.py` → `build_factura_impresa(db, factura_id, *, iban, duplicado) -> FacturaImpresa`, con los modelos de vista de data-model:
  - Reutiliza `services/facturas.get_factura`, el registro `alta`, `Settings.entorno_aeat` y la configuración vigente para el contacto y el pie.
  - Lanza `DuplicadoNoDisponible` en una anulada.
  - `factura_pdf(db, …) -> DocumentoPdf(nombre, contenido)`.
  - Registra en `app.impresion` el tipo, el número y la duración, sin datos personales.
- [ ] T021 [US1] `backend/app/resources/pdf/factura.html`, más los estilos propios en `papel.css`, según contracts/documentos-pdf.md, «Factura»:
  - Cabecera con el QR a la izquierda y el emisor a la derecha.
  - Identificación con las marcas, rectificación, cliente, detalle con la variante de devolución total, totales con la mención y el importe rectificado, pago y pie.
  - `@page` con «{número} · Página n de m».
  - `render_factura(modelo) -> bytes` en `core/pdf/render.py`, bajo `LIMITE_FACTURAS`.
- [ ] T022 [US1] Ruta `GET /v1/facturas/{factura_id}/pdf` en `backend/app/api/v1/facturas.py`:
  - Parámetros `iban: bool = False` y `duplicado: bool = False`.
  - `Response(media_type="application/pdf")` con `Content-Disposition` y la CSP de PDF de R-8.
  - `responses={200: {"content": {"application/pdf": {}}}}`.
  - Se quita de `PENDIENTES_003`.
- [ ] T023 [US1] Web:
  - Regenerar los tipos (`exportar-openapi` + `gen:api`).
  - `joyeriablanco_web/src/lib/impresion.ts` → `urlPdfFactura`.
  - `joyeriablanco_web/src/features/facturas/ImprimirFactura.tsx`: enlace con `claseBotonSecundario` e icono `Printer`, casillas `Casilla` en un `role="group"` «Opciones de impresión», y la ventana de 2 s con «Preparando…».
  - Montarlo en el pie de `FacturaConsultaModal` (`FacturaConsulta.tsx`), después de «Cerrar», en toda factura emitida.
  - En móvil, apilado (contracts/ui-rutas.md).
- [ ] T024 [US1] E2E `joyeriablanco_web/e2e/impresion.spec.ts` (SC-009):
  - Abrir una factura de los datos de ejemplo y leer el `href` de «Imprimir».
  - Con `page.request.get(href)`, comprobar `application/pdf` y que empieza por `%PDF`.
  - Con «Incluir número de cuenta» y «Duplicado» marcadas, el `href` lleva `iban=true&duplicado=true` y el PDF también se descarga.
  - Como empleado, el botón también está.
- [ ] T025 [US1] Producción (R-8):
  - `deploy/caddy/Caddyfile`: *matchers* `@pdf path_regexp ^/api/v1/facturas/(listado|[^/]+)/pdf$` y `@nopdf not path_regexp …`. La CSP global se aplica solo con `@nopdf`, y el resto de cabeceras, a todo.
  - `deploy/verificar-produccion.sh`: una ruta de PDF sin sesión responde 401 con `object-src 'self'` y sin la CSP global, y `/` conserva `object-src 'none'`.

**Checkpoint**: MVP. Toda factura emitida se imprime con su QR conforme a F-12, con las opciones de
IBAN y duplicado.

---

## Phase 4: User Story 2 - Imprimir el listado filtrado (Priority: P2)

**Goal**: «Imprimir listado» abre un PDF A4 apaisado con todas las filas del filtro (hasta 5.000),
en el mismo orden, con los totales de las vigentes desglosados por tipo de IVA.

**Independent Test**: con más de 100 facturas que cumplen un filtro, el PDF contiene todas, en el
orden elegido. Los totales cuadran al céntimo con las vigentes, y con más de 5.000 filas se
rechaza.

### Tests for User Story 2 ⚠️

- [ ] T026 [P] [US2] ⚖️ Test `backend/tests/integration/test_pdf_listado.py`. Las facturas se emiten con los servicios reales:
  - **Todas las filas**: más de 100 facturas del filtro, todas en el PDF y una sola vez, en el orden de cada `orden` (los cuatro) y con el mismo desempate que `GET /v1/facturas`.
  - **Filtros**: `q` (nombre, NIF y número, sin tildes), `anio` (número y `todos`) y `mes`. El valor por defecto es el año en curso.
  - **Marcas**: «Borrador» en lugar del número, «Anulada», «Rectificada» y «Exenta».
  - **Totales** (FR-021, SC-005):
    - Desglose por tipo en orden descendente, con la exenta al final.
    - Total general y recuento de excluidas.
    - Cuadre al céntimo: la suma por tipo es igual al total general, y es igual a la suma de las vigentes calculada en el test.
    - Una REC vigente cuenta y su original rectificada no.
  - **Cabecera**: el filtro en palabras, el número de filas, la fecha de generación y el nombre del emisor actual, o solo el logotipo si falta.
  - **Vacío**: con un filtro sin resultados por la API → PDF con «No hay facturas con este filtro» y totales a 0.
  - **Límite**: con `monkeypatch` de `LIMITE_LISTADO_IMPRESO` a 3 → 422 `listado-demasiado-grande` con `limite` y `total`, y HTML en una navegación.
  - **Bloques** (R-7): con `monkeypatch` del tamaño de bloque a 7 y unas 40 filas, sale cada número una vez, ninguna página intermedia está a medias y el pie va de «Página 1 de m» a «Página m de m».
  - **Respuesta**: `application/pdf` y `filename` según el filtro.
  - **Errores**: 401 sin sesión, y 422 `validacion` con `mes=13`.
  - **Logs**: no contienen el texto de `q`.
- [ ] T027 [P] [US2] Tests web:
  - `joyeriablanco_web/src/lib/impresion.test.ts`: `urlPdfListado` con `q`, `anio`, `mes` y `orden` de la URL, sin `pagina` y sin vacíos.
  - `joyeriablanco_web/src/features/facturas/ImprimirListado.test.tsx`:
    - Habilitado con resultados.
    - Deshabilitado mientras carga, con 0 resultados y con más de 5.000, con el motivo enlazado por `aria-describedby`.
    - Doble clic ignorado durante 2 s.
  - Ampliar `FacturasPage.test.tsx`: el botón en la cabecera junto a «Nueva factura».

### Implementation for User Story 2

- [ ] T028 [US2] `backend/app/repositories/facturas.py` (data-model, «Lecturas nuevas»):
  - `count_listado(...)`.
  - `list_facturas_impresion(...)`: reutiliza `_filtros` y `_ORDENES`, sin `OFFSET`/`LIMIT`.
  - `totales_vigentes(...)`: el desglose con `JOIN desgloses_factura` agrupado por `tipo_iva` (`NULLS LAST`) y los totales y recuentos con `FILTER`, con `coalesce` a 0.
- [ ] T029 [US2] `backend/app/services/impresion.py` → `build_listado_impreso(db, filtros) -> ListadoImpreso`:
  - Año por defecto como `services/facturas.list_facturas`.
  - Límite `LIMITE_LISTADO_IMPRESO = 5000`, comprobado antes de leer las filas → `ListadoDemasiadoGrande`.
  - Descripción del filtro en palabras: meses en español, y los textos del orden iguales a los del selector de la web.
  - Emisor de la configuración vigente y fecha y hora de Madrid.
  - `listado_pdf(...) -> DocumentoPdf`, con el nombre según el filtro, y el log sin `q`.
- [ ] T030 [US2] `backend/app/resources/pdf/listado.html`, según contracts/documentos-pdf.md, «Listado» (A4 apaisado, columnas y marcas, vacío y totales), más `render_listado(modelo) -> bytes` en `core/pdf/render.py` (R-7):
  - Bloques de `TAMANO_BLOQUE_LISTADO = 1000` filas con `HTML(...).render()`.
  - Escritura de `document.copy(pages[:-1])` y arrastre de las filas de la última página, contadas en el árbol de cajas.
  - El último bloque, con los totales.
  - Unión con `PdfWriter` y pie «Listado de facturas · Página n de m» superpuesto con `merge_page`.
  - `compress_content_streams()`, todo bajo `LIMITE_LISTADOS`.
- [ ] T031 [US2] Ruta `GET /v1/facturas/listado/pdf` en `backend/app/api/v1/facturas.py`, declarada **antes** de `/{factura_id}`:
  - Filtros con el mismo tipo y validación que `GET /v1/facturas`, mediante `FiltrosListado` compartido.
  - Respuesta PDF como en T022.
  - Se quita de `PENDIENTES_003`.
- [ ] T032 [US2] Web:
  - Regenerar los tipos.
  - `urlPdfListado` en `joyeriablanco_web/src/lib/impresion.ts`.
  - `joyeriablanco_web/src/features/facturas/ImprimirListado.tsx`: enlace o botón deshabilitado con su motivo, según `lista.data.total` y `isPending`.
  - Montarlo en las `actions` de `PageHeader` de `FacturasPage.tsx`, con los filtros de `src/routes/_app/facturas.tsx`.
  - En móvil, debajo de «Nueva factura».
- [ ] T033 [US2] Cierre del contrato y E2E:
  - Eliminar `PENDIENTES_003` de `test_contrato_openapi.py`, que pasa a comprobar la igualdad estricta.
  - Ampliar `joyeriablanco_web/e2e/impresion.spec.ts`: filtrar por año y mes, leer el `href` de «Imprimir listado» (con `anio`, `mes` y `orden`, sin `pagina`) y descargarlo con `page.request` (`application/pdf`, `%PDF`).

**Checkpoint**: US1 y US2 completas. Se imprime cualquier factura y cualquier filtro del listado.

---

## Phase 5: User Story 3 - Datos de contacto y pie de factura (Priority: P3)

**Goal**: el administrador guarda teléfono, correo, web y pie en Configuración → Facturación, y
toda factura impresa los lleva.

**Independent Test**: un administrador guarda los cuatro campos y una factura antigua se reimprime
con ellos y con su emisor fiscal original. Un empleado recibe 403.

### Tests for User Story 3 ⚠️

- [ ] T034 [P] [US3] Test `backend/tests/unit/domain/test_contacto.py`:
  - `validate_telefono`: los casos de clientes de 001 FR-055.
  - `normalize_web` y `display_web`: dominio, `https://…/` → `joyeriablanco.es`, y un esquema distinto de `http(s)` rechazado.
  - Normalización del pie: `\r\n` → `\n` y espacios de los extremos recortados.
- [ ] T035 [P] [US3] Test `backend/tests/integration/test_configuracion_contacto.py`:
  - `PUT` con `contacto` y `pie_factura`, y `GET` que los devuelve.
  - Errores 422 en `contacto.telefono`, `contacto.correo`, `contacto.web` y `pie_factura` (más de 600 caracteres).
  - El correo, en minúsculas.
  - Un `PUT` sin los campos los conserva, y `null` los borra.
  - Auditoría con el antes y el después de cada campo.
  - Conflicto de versión → 409. Empleado → 403.
  - Integración con US1: tras cambiar el teléfono, reimprimir una factura antigua muestra el nuevo con el emisor fiscal copiado (US3-5).
  - Los tests de clientes siguen en verde, porque la regla del teléfono no cambia.
- [ ] T036 [P] [US3] Test web en `joyeriablanco_web/src/features/configuracion/FacturacionPage.test.tsx`:
  - Los cuatro campos en «Datos del emisor», sin la marca de necesarios.
  - La ayuda de FR-025 y el contador «n / 600».
  - Envío con `contacto` y `pie_factura`, también `null`.
  - Errores de la API en su campo.

### Implementation for User Story 3

- [ ] T037 [P] [US3] `backend/app/domain/contacto.py`:
  - `validate_telefono`, que se mueve de `services/clientes.py` sin cambiar la regla.
  - `normalize_web`, `display_web` y `normalize_pie`.
  - `backend/app/services/clientes.py` pasa a usar `validate_telefono`.
- [ ] T038 [US3] Esquemas y servicio (R-9):
  - `backend/app/schemas/configuracion_facturacion.py`: `ContactoEntrada`, `ContactoSalida` y `pie_factura`, opcionales en la entrada y presentes en la salida.
  - `backend/app/services/configuracion_facturacion.py`: normalizar y validar con `domain/contacto.py` y `email-validator`, conservar lo que no venga en la petición (`model_fields_set`) y añadir los campos a `CAMPOS_AUDITADOS`.
  - `backend/app/api/v1/configuracion.py → _salida`: los devuelve.
- [ ] T039 [US3] `backend/app/services/datos_ejemplo.py`:
  - Teléfono `+34 900 000 000`, correo `info@joyeriablanco.demo`, web `joyeriablanco.demo` y un pie ficticio de protección de datos marcado «Texto de ejemplo» (FR-032).
  - Ampliar `backend/tests/integration/test_datos_ejemplo.py`.
- [ ] T040 [US3] Web:
  - Regenerar los tipos.
  - `joyeriablanco_web/src/features/configuracion/FacturacionPage.tsx`: los campos en el esquema Zod y el formulario, con `TextField` (`tel` y `email`) y un área de texto de 4 filas con contador, con el mismo marco que `TextField`.
  - Mapear los errores en su campo y la ayuda de FR-025.
  - Ampliar `joyeriablanco_web/e2e/configuracion-facturacion.spec.ts`: guardar el contacto y el pie, y comprobar que el PDF de una factura (con `page.request`) responde 200.

**Checkpoint**: todas las historias completas.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T041 [P] Test lento `backend/tests/integration/test_pdf_rendimiento.py` (`@pytest.mark.lento`; SC-001, SC-005):
  - Factura de 20 líneas: 20 generaciones seguidas, con el percentil 95 por debajo de 3 s.
  - Listados de 1.000 y 5.000 filas sintéticas en menos de 15 s y 60 s.
  - Memoria de la generación de 5.000 filas medida en un subproceso (`resource.getrusage`) por debajo de 300 MB.
  - Ejecutarlo con `uv run pytest -m lento` y anotar los resultados en el quickstart.
- [ ] T042 [P] Documentación:
  - `CLAUDE.md`: `AEAT_ENTORNO` en los comandos de producción.
  - `backend/app/resources/README.md`.
  - [quickstart.md](quickstart.md): la sección «Resultado de la validación» con las mediciones de T041.
  - Comprobar que la constitución no necesita enmienda: la restricción «PDF» ya fija WeasyPrint.
- [ ] T043 Validación manual del [quickstart](quickstart.md) §2 (pasos 1 a 16):
  - Escaneo real del QR con un móvil, medición en papel y visor en Chrome, Firefox y Safari.
  - Simulación de producción (`DOMINIO=localhost TLS_MODO=internal`) con `deploy/verificar-produccion.sh`.
  - Los resultados se anotan en el quickstart.
- [ ] T044 Puertas de calidad completas antes de cerrar:
  - **Backend**: `uv run pytest`, `uv run ruff check . && uv run ruff format --check . && uv run mypy .`
  - **Web**: `npm run lint && npm run typecheck && npm run test && npm run build && npm run check:tokens` y `npx playwright test`.
  - Revisar la conformidad con `docs/DESIGN.md` y con la sección «Paper» (SC-008).
  - Marcar todas las tareas en este fichero.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (F1)**: sin dependencias. T001 debe confirmar que WeasyPrint importa en el Mac antes de
  seguir. T005 deja el contrato en verde desde el principio.
- **Foundational (F2)**: depende de F1 y bloquea las historias. T012 depende de T010 y T011, y T011
  de T003.
- **US1 (F3)**: depende de F2. Es el **MVP**.
- **US2 (F4)**: depende de F2 y reutiliza de US1 el manejo de errores en navegación (T019), la
  plantilla base y la ruta de PDF. Puede empezar con US1 en marcha si T019 está hecho.
- **US3 (F5)**: depende de F2 (columnas, T013). Su test de integración con la impresión (T035)
  necesita US1.
- **Polish (F6)**: depende de todas.

### Within Each User Story

- Los tests se escriben primero y deben fallar.
- El orden es: dominio → repositorio → servicio → plantilla y renderizado → ruta → tipos
  generados → web → E2E.
- Cada ruta nueva vacía su entrada de `PENDIENTES_003`. T033 elimina la lista.
- Se hace un commit atómico al cerrar cada grupo lógico de tareas. **Una fase no se cierra sin sus
  tests en verde.**

### Parallel Opportunities

- **F1**: T003 y T004 en paralelo, después de T001.
- **F2**: tests T006, T007 y T008 en paralelo; T009 y T010 en paralelo; T013 en paralelo con
  T009–T012.
- **US1**: T014, T015 y T016 en paralelo; T017 y T018 en paralelo; T025 en paralelo con T023.
- **US2**: T026 y T027 en paralelo; T032 en paralelo con T030 y T031, una vez fijada la URL.
- **US3**: T034, T035 y T036 en paralelo; T037 antes de T038.
- **Polish**: T041 y T042 en paralelo.

---

## Parallel Example: User Story 1

```bash
# Tests (en paralelo):
Task: "T014 ⚖️ test_qr.py (vectores F-12 y lectura con zxing-cpp)"
Task: "T015 test_pdf_factura.py (contenido, IBAN, duplicado, QR, errores)"
Task: "T016 impresion.test.ts + ImprimirFactura.test.tsx"

# Dominio (en paralelo):
Task: "T017 domain/qr.py"
Task: "T018 domain/tipos.py (textos de la causa)"
```

---

## Implementation Strategy

### MVP First

1. F1 Setup → F2 Foundational (formato, tokens, renderizado y columnas).
2. F3 US1 → **validar**: una factura impresa con su QR que se lee y lleva a la URL de pruebas de la
   AEAT con los datos del registro.

### Incremental Delivery

1. F1 + F2: infraestructura de impresión probada con las fuentes de la marca.
2. US1: la factura en PDF (MVP), desplegable con su CSP de producción.
3. US2: el listado filtrado con totales.
4. US3: contacto y pie configurables.
5. Polish: mediciones, validación manual y puertas de calidad.
