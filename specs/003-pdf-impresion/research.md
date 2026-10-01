# Research — 003 PDF de factura con QR de cotejo e impresión del listado

**Fecha**: 2026-10-01 · **Spec**: [spec.md](spec.md)

Cada decisión sigue el formato **Decisión** · **Razón** · **Alternativas descartadas**.

Por la constitución (principio IV), toda regla fiscal o de formato sale de una fuente oficial y se
cita con su versión. Esta feature mantiene la numeración de fuentes de 002 y añade F-12:

| Id | Documento | Versión / fecha | SHA-256 / consulta |
|---|---|---|---|
| F-6 | RD 1619/2012 (ROF), BOE-A-2012-14696, arts. 6.1, 6.2, 6.5, 14 y 15 | texto consolidado; art. 6.5 añadido por el RD 1007/2023 | API de datos abiertos del BOE, bloques `a6` y `a14`, consulta del 2026-10-01 (XML, sin hash estable) |
| F-10 | Orden HAC/1177/2024, BOE-A-2024-22138, arts. 20 y 21 | texto consolidado | API de datos abiertos del BOE, bloques `a2-2` y `a2-3`, consulta del 2026-10-01 |
| F-11 | Ley 37/1992 (LIVA), art. 140 bis.Uno.1.º | la de 002 | 002, research |
| F-12 | AEAT, *Detalle de las especificaciones técnicas del código «QR» de la factura y de la «URL» del servicio de cotejo o remisión de información por parte del receptor de la factura* (`DetalleEspecificacTecnCodigoQRfactura.pdf`) | 0.5.0 (10/12/2025) | `f86b3c260d8a4963dbc18c5007732b53199156c5d1db63242e68db71501b49eb`, descarga del 2026-10-01 |

F-12 es el documento que enlaza la página oficial «Características del QR y especificaciones del
servicio de cotejo o remisión de información por parte del receptor de la factura», dentro del
índice de información técnica de VERI\*FACTU. Su versión coincide con la que cita CLAUDE.md.

**Prueba técnica previa** (2026-10-01): en un contenedor desechable `python:3.13.15-slim-trixie`,
con WeasyPrint 70.0, segno 1.6.6, pypdf 6.19.0 y zxing-cpp 3.1.1, se generaron una factura con QR
y listados de 1.000 y 5.000 filas. Sus mediciones respaldan R-2, R-4 y R-7.

---

## R-1. Contenido y codificación del QR (F-12 §4 a §8; F-10, art. 21.2)

**Decisión**: una función pura, `app/domain/qr.py → build_cotejo_url(...)`, compone la dirección:

1. **Base** según la modalidad guardada en la factura y el entorno de la instalación (R-3). Son
   las cuatro de F-12 §5:

   | Modalidad | Pruebas | Producción |
   |---|---|---|
   | `verifactu` | `https://prewww2.aeat.es/wlpl/TIKE-CONT/ValidarQR` | `https://www2.agenciatributaria.gob.es/wlpl/TIKE-CONT/ValidarQR` |
   | `no_verifactu` | `https://prewww2.aeat.es/wlpl/TIKE-CONT/ValidarQRNoVerifactu` | `https://www2.agenciatributaria.gob.es/wlpl/TIKE-CONT/ValidarQRNoVerifactu` |

2. **Parámetros**: exactamente `nif`, `numserie`, `fecha` e `importe`, en ese orden (F-12 §6).
   Sus valores salen **del registro de alta** de la factura:
   - `nif`: `id_emisor`, el NIF de 9 caracteres.
   - `numserie`: `num_serie`, de 60 caracteres como máximo.
   - `fecha`: `fecha_expedicion`, que ya se guarda como `DD-MM-AAAA` (002, data-model).
   - `importe`: `importe_total`, con `format_amount` de `app/domain/huella.py`: punto decimal y
     dos decimales, p. ej. `1560.90`. Como máximo 12 cifras enteras.

   Son los mismos valores que cotejará la AEAT al recibir el registro (004).
3. **Codificación**: «URL encoding» en UTF-8 (F-12 §4), con
   `urllib.parse.urlencode(pares, quote_via=urllib.parse.quote)`. Así, `&` pasa a `%26` y un
   espacio a `%20`.
4. **Validaciones previas**, que lanzan `ValueError` (sería un fallo interno, nunca de usuario):
   - Cada valor solo contiene ASCII de 32 a 126 (F-12 §4).
   - `nif` tiene 9 caracteres.
   - `numserie` tiene 60 caracteres como máximo.
   - `fecha` cumple `DD-MM-AAAA`.
   - El importe tiene como máximo 12 cifras enteras.
5. **Sin parámetros opcionales**: no van `idioma` ni `formato`. `formato` está prohibido en el QR
   (F-12 §7), y F-12 §6 dice que la URL «deberá incorporar únicamente» los cuatro obligatorios.

**Vectores de prueba** (tests unitarios):
- F-12 §4: con `nif=89890001K` y `numserie=12345678&G33`, la cadena debe llevar
  `numserie=12345678%26G33`. Es el ejemplo de codificación correcta. El ejemplo erróneo de §4, con
  `&` sin codificar, nunca debe producirse.
- F-12 §8.1 a §8.4: las cuatro direcciones de ejemplo, con `nif=89890001K`, `numserie=12345678-G33`
  y `fecha=01-09-2024`, deben coincidir con lo generado salvo el importe.
  - Los ejemplos escriben `importe=241.4`, y el sistema genera `241.40`.
  - Ambas formas cumplen F-12 §6 («máximo […] 2 dígitos en la parte decimal»).
  - La de dos decimales es la del formato `NNNNNNNNN.DD` de §5 y la que devuelve el propio servicio
    en sus respuestas JSON de §9 (`"importe": "241.40"`).
  - Es también la representación canónica del registro (002, R-2).
- La dirección decodificada del QR (R-2) es idéntica a la generada.

**Razón**: tomar los valores del registro de alta y no de la cabecera garantiza que el QR coincide
byte a byte con lo que se remitirá (SC-002). La función es pura y se prueba sin HTTP (constitución
V).

**Alternativas descartadas**:
- Componer la URL con los datos de la cabecera de `facturas`: son los mismos, pero el registro es
  la fuente que coteja la AEAT.
- Añadir `idioma=es`: no está entre los cuatro parámetros del QR, y el idioma por defecto ya es el
  castellano (F-12 §7.1).

---

## R-2. Presentación del QR (F-10, arts. 20 y 21.1; F-12 §2, §3 y anexo)

**Decisión**:
- **Generación**: `segno` 1.6 (Python puro, sin Pillow), con
  `segno.make(url, error="m", micro=False, boost_error=False)`.
  - `boost_error=False` es imprescindible: por defecto segno sube el nivel de corrección a Q o H si
    cabe en la misma versión, y F-10, art. 21.1, fija el nivel M.
  - La versión del símbolo la elige segno. Con una dirección de prueba de unos 120 caracteres salió
    la versión 7, de 45 × 45 módulos.
  - **Norma**: F-10, art. 21.1, cita «ISO/IEC 18004» sin edición, y F-12 §2 la transcribe como
    «ISO/IEC 18004:2015». Se aplica la de 2015, la vigente, que es la que implementa segno. No hay
    contradicción: F-12 concreta la referencia de la Orden.
- **Formato**: SVG vectorial en línea, generado con `svg_inline(border=0, omitsize=True)`. El
  color de los módulos es el token `paper-qr` (R-5).
- **Tamaño**: el símbolo mide **35 × 35 mm**, el centro del intervalo de 30 a 40 mm. Así sigue
  dentro aunque la impresora reduzca un 10 % al «ajustar a la página».
  - El margen en blanco, la llamada zona tranquila, es de **6 mm** por los cuatro lados, el valor
    recomendado. Se aplica como relleno en CSS, no como módulos.
  - Medido en la prueba previa con el árbol de cajas de WeasyPrint: caja de 35,0 × 35,0 mm con
    6,0 mm de relleno.
- **Posición**: en la cabecera de la primera página, arriba a la izquierda, como en el ejemplo j
  del anexo de F-12 (A4 vertical, QR a la izquierda y datos del emisor con el logotipo a la
  derecha). Solo una vez y antes de cualquier otro contenido de la factura.
- **Textos**:
  - «QR tributario:» encima del QR, centrado respecto a él.
  - Si la modalidad de la factura es `verifactu`, debajo y centrada, la frase larga «Factura
    verificable en la sede electrónica de la AEAT», partida en las líneas que hagan falta
    (Clarifications).
  - Ambos textos en `print-body-strong`, de 9 pt, el mismo tamaño que los datos de la factura y
    nunca menor (F-12 §3; SC-006).
- **Verificación automática**:
  - *Contenido*: en un test unitario, la matriz de segno se rasteriza con numpy y se lee con
    `zxing-cpp`. Debe dar exactamente la dirección de R-1 y nivel de corrección M. En la prueba
    previa se leyó el ejemplo de F-12 §4 con nivel M.
  - *Geometría*: un test de integración recorre el árbol de cajas del documento WeasyPrint de la
    factura (`document.pages[0]._page_box`). Localiza la caja `#qr` y comprueba:
    - que tiene un lado de 30 a 40 mm y un relleno de 2 mm o más;
    - que está en la primera página y no aparece en las siguientes.
  - Las dos verificaciones usan dependencias solo de desarrollo: `zxing-cpp` y `numpy`.

**Razón**: el SVG vectorial se imprime nítido a cualquier resolución («impresos con una resolución
apropiada», F-10, art. 20.1). segno no arrastra dependencias nativas. Las dos verificaciones
cubren SC-002 y SC-006 sin depender de rasterizar el PDF, para lo que haría falta poppler.

**Alternativas descartadas**:
- `qrcode` con Pillow: añade una dependencia nativa, y su salida por defecto es una imagen PNG.
- PNG incrustado como `data:`: pierde nitidez y no aporta nada.
- 40 × 40 mm: está en el límite superior, y una impresión «a tamaño real» que amplíe lo dejaría
  fuera.
- QR centrado arriba (ejemplo h): deja los datos del emisor debajo y alarga la cabecera.

---

## R-3. Entorno de la AEAT de la dirección de cotejo (FR-017)

**Decisión**: un ajuste nuevo de la instalación en `app/core/config.py`,
`aeat_entorno: EntornoAeat | None = None`, con los valores `pruebas` y `produccion`.
- Fuera de producción, un valor vacío equivale a `pruebas`. La propiedad `entorno_aeat` lo
  resuelve.
- Con `ENTORNO=produccion`, el validador de `Settings` exige que `AEAT_ENTORNO` esté fijado
  expresamente, igual que los datos del productor (002, R-5). Si falta, la API no arranca con el
  mensaje «En producción hay que fijar AEAT_ENTORNO (pruebas o produccion)».
- No se guarda en la factura. La modalidad sí (002, FR-030), porque condiciona el registro; el
  entorno es de la instalación y la feature 004 lo reutilizará para el endpoint de remisión.
- `.env.example` documenta la variable, y `docker-compose.prod.yml` la pasa desde `.env` sin valor
  por defecto.

**Razón**: CLAUDE.md exige integrar primero contra preproducción y nunca directamente contra
producción. Con un valor por defecto de `produccion`, una instalación de pruebas imprimiría QR
reales; con uno de `pruebas` en producción, el cliente final no podría cotejar. Exigirlo
expresamente en producción evita ambos errores.

**Alternativas descartadas**:
- Deducirlo de `ENTORNO`: impediría la prueba de integración de la 004, que se hace con la
  instalación de producción apuntando a preproducción.
- Guardarlo en cada factura: no es un dato de la factura y obligaría a una migración sobre una
  tabla de solo inserción.

---

## R-4. Motor PDF y dependencias (constitución, restricción «PDF»)

**Decisión**:

| Pieza | Elección | Uso |
|---|---|---|
| Maquetación | **WeasyPrint 70** (`weasyprint>=70,<71`) | HTML + CSS a PDF, como exige la constitución |
| Plantillas | **Jinja2 3.1** (`jinja2>=3.1,<3.2`), `autoescape=True` | HTML de la factura, del listado y de la página de error |
| QR | **segno 1.6** (`segno>=1.6,<1.7`) | R-2 |
| Unión de PDF | **pypdf 6** (`pypdf>=6.19,<7`), en tiempo de ejecución | Listado por bloques (R-7). En los tests, además, para extraer el texto |
| Lectura de QR en tests | `zxing-cpp>=3.1,<3.2` y `numpy`, solo de desarrollo | R-2 |

- **Paquetes del sistema**: `libpango-1.0-0`, `libpangoft2-1.0-0` y `libharfbuzz-subset0`, más
  `fonts-dejavu-core` como último recurso para caracteres fuera de los subconjuntos latinos.
  - Se instalan en la etapa `base` y también en `prod` de `backend/Dockerfile`, porque `prod`
    parte otra vez de `python:3.13.15-slim-trixie`.
  - La prueba previa confirmó que con los tres primeros basta para generar el PDF en esa imagen.
- **Caché de fontconfig**: `XDG_CACHE_HOME=/tmp/cache` en las dos etapas.
  - En producción el contenedor es `read_only` y solo `/tmp` admite escritura.
  - En desarrollo, el usuario `app` tiene `/app` como «home», que es el volumen del código. Sin
    esta variable, la caché acabaría dentro del repositorio.
- **Fuentes**: los ficheros WOFF2 estáticos de Fontsource 5.3.0, la misma versión que usa la web.
  - Subconjuntos `latin` y `latin-ext`.
  - Manrope 400, 600 y 700: paquete `@fontsource/manrope`, estático.
  - Bodoni Moda 400 y 500: paquete `@fontsource/bodoni-moda`.
  - Se copian a `backend/app/resources/fuentes/` con su licencia OFL-1.1 y un `README.md` con el
    origen y el SHA-256 de cada fichero, como `contrasenas_comunes.txt`.
  - Se declaran con `@font-face` y `unicode-range`.
  - En la prueba previa, el PDF incrustó `Manrope` y `Bodoni-Moda` como subconjuntos, sin recurrir
    a fuentes del sistema.
- **Logotipo**: copia de `joyeriablanco_web/src/assets/brand/logo.png` (512 px, 001 R-18) en
  `backend/app/resources/marca/logo.png`, con su origen y SHA-256 en el README.
- **Desarrollo en macOS**: los tests se lanzan desde el Mac con `uv run pytest` (CLAUDE.md), y
  WeasyPrint necesita Pango.
  - Hay que instalarlo con `brew install pango`. A día de hoy no está instalado en el equipo del
    responsable: está cairo, pero no pango.
  - Si `cffi` no encuentra las librerías de Homebrew, basta con
    `export DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib`.
  - Se documenta en el quickstart.

**Razón**: WeasyPrint lo fija la constitución. Las piezas añadidas son las mínimas: Jinja2 para no
componer HTML a mano, segno para el QR y pypdf para acotar la memoria del listado (R-7). Las
fuentes de Fontsource garantizan la misma tipografía que la web y están en un formato que
WeasyPrint incrusta sin conversión.

**Alternativas descartadas**:
- TTF variables de `google/fonts`: no está comprobado cómo resuelve WeasyPrint los pesos de una
  fuente variable. Las estáticas no tienen esa duda.
- Fuentes instaladas en el sistema de la imagen: no estarían en el Mac de desarrollo, y los PDF
  de los tests diferirían de los de producción.
- ReportLab: contradice la constitución.

---

## R-5. Tokens de «Papel» y plantillas (FR-030; constitución, «Sistema de diseño»)

**Decisión**:
- **DESIGN.md 1.2** (enmienda aprobada por el responsable, Clarifications 2026-10-01):
  - Un grupo nuevo de colores de papel en el frontmatter, derivados de tokens existentes:

    | Token | Valor | Deriva de | Uso |
    |---|---|---|---|
    | `paper` | `#ffffff` | — | Fondo del papel |
    | `paper-ink` | `#2d3037` | `inverse-on-surface` | Texto principal |
    | `paper-ink-muted` | `#434750` | `secondary-container` | Etiquetas y texto secundario |
    | `paper-accent` | `#7c580a` | `inverse-primary` | Títulos de sección, total, acento dorado legible sobre blanco |
    | `paper-rule` | `#b48a3c` | `primary-container` | Filetes de 1 px y marco de los totales |
    | `paper-alert` | `#93000a` | `error-container` | Marcas «ANULADA», «RECTIFICADA» y «DUPLICADO» |
    | `paper-qr` | `#000000` | — | Módulos del QR: contraste máximo (F-12 §3) |

  - Una escala tipográfica de impresión en puntos:

    | Token | Fuente | Tamaño |
    |---|---|---|
    | `print-title` | Bodoni Moda 400 | 22 pt |
    | `print-total` | Bodoni Moda 500 | 15 pt |
    | `print-heading` | Manrope 700, mayúsculas, 0,12 em | 8 pt |
    | `print-body` | Manrope 400 | 9 pt / 12 pt |
    | `print-body-strong` | Manrope 600 | 9 pt / 12 pt |
    | `print-label` | Manrope 600, mayúsculas, 0,12 em | 7 pt |
    | `print-small` | Manrope 400 | 7,5 pt |
    | `print-table` | Manrope 400, cifras tabulares | 8,5 pt |

  - Márgenes `print-margin` de 15 mm y separación `print-gutter` de 6 mm.
  - Prosa nueva, «Paper (print and PDF)», en el idioma del documento (inglés): papel blanco, sin
    sombras, esquinas a 0, filetes de 1 px en `paper-rule` y caja de totales con marco
    `paper-rule`.
  - La fila de Changelog: «1.2 (2026-10-01): Paper tokens for printed documents (feature 003).
    Approved by the project owner».
- **Fuente única en el backend**: `app/core/pdf/tokens.py` declara esos valores una sola vez. El
  CSS de papel los consume como propiedades personalizadas (`--paper-ink`…), generadas desde ese
  módulo al renderizar. El color del QR sale del mismo módulo.
- **Sincronía**: un test lee el frontmatter de `docs/DESIGN.md` (YAML) y comprueba que los tokens
  `paper*` y `print-*` del backend coinciden con los del documento. Si alguien cambia uno sin el
  otro, el test falla.
- **Plantillas**: `app/resources/pdf/` con `base.html`, `factura.html`, `listado.html`,
  `error.html` y `papel.css`.
  - Jinja2 con `autoescape=True`, `StrictUndefined` y un `FileSystemLoader` sobre
    `importlib.resources`.
  - `base_url` apunta a `app/resources` para resolver las fuentes y el logotipo con rutas
    relativas.
  - `papel.css` no contiene literales de color ni de tamaño, solo `var(--…)`. Un test lo comprueba
    buscando `#`, `rgb(` y tamaños en `pt` fuera de las variables, con el mismo criterio que
    `check:tokens`.

**Razón**: la constitución exige tokens definidos una vez y consumidos desde ahí. La web no imprime
y no necesita los tokens de papel, así que su `tokens.css` no cambia.

**Alternativas descartadas**:
- Leer `docs/DESIGN.md` en tiempo de ejecución: no está en el contexto de la imagen Docker del
  backend.
- Un `papel.css` con los valores literales y sin módulo Python: el color del QR, que va en el SVG,
  tendría que repetirse.
- Tema claro en la web con `@media print`: descartado con el responsable. Mandan el PDF y
  WeasyPrint.

---

## R-6. Contenido de la factura impresa (FR-003 a FR-012, FR-033)

**Decisión**: `app/services/impresion.py → build_factura_impresa(db, factura_id, *, iban,
duplicado)` reutiliza `services/facturas.get_factura` (002), que trae la factura, su estado
derivado, la factura que rectifica, la que la sustituye, la vigente actual y los registros. Con
eso forma un modelo de vista inmutable (data-model, «FacturaImpresa»). La plantilla solo pinta:
no calcula ni consulta nada.

| Bloque | Origen | Notas |
|---|---|---|
| QR | Registro de tipo `alta` de la factura | R-1 y R-2. Siempre existe en una factura emitida |
| Emisor fiscal | `facturas.emisor_*` | Copia al emitir (002, FR-016). La provincia es el texto copiado |
| Contacto y pie | `configuracion_facturacion` vigente | FR-005 y FR-025. Se omite lo vacío |
| Título | `tipo_factura` | `F1`: «Factura». `R1` y `R4`: «Factura rectificativa» |
| Número y fechas | `num_serie`, `fecha_expedicion` y `fecha_operacion` | La fecha de la operación solo si existe y es distinta (002, FR-018) |
| Destinatario | `facturas.dest_*` | La identificación lleva su etiqueta: «NIF», o para L7 «NIF-IVA», «Pasaporte», «Documento oficial de identificación», «Certificado de residencia» u «Otro documento probatorio», más el país si no es `ES` |
| Líneas | `lineas_factura` en su `orden` | Unidades, descripción, precio unitario sin IVA e importe |
| Desglose | `desgloses_factura` | Por tipo: «Base imponible al 21 %» e «IVA 21 %». La línea exenta: «Base exenta» e «IVA 0,00 €» |
| Totales | `base_total`, `cuota_total` e `importe_total` | El total en `print-total` |
| Mención de la exención | `mencion_exencion(clave_regimen)` de `app/domain/exenciones.py` | El texto único de 002 (FR-007) |
| Rectificación | `rectifica_a` (factura ORM), `causa_rectificacion`, `base_rectificada` y `cuota_rectificada` | «Rectifica a FAC-… de {fecha}», la causa con el texto de la consulta y el importe de la rectificación (FR-008) |
| Marca de estado | Estado derivado y `vigente_actual` | `anulada`: «ANULADA», y «Sustituida por X» si hay una vigente que la sustituye. `rectificada`: «RECTIFICADA por X» |
| Duplicado | Parámetro `duplicado` | «DUPLICADO». Una factura anulada responde 409 `duplicado-no-disponible` |
| Pago | Parámetro `iban` y `emisor_iban` | Solo si los dos: «Pago por transferencia · IBAN ES91 2100 …». Si se pide sin IBAN, se ignora (FR-010) |
| Pie de página | — | «FAC-2026-0005 · Página n de m» con `counter(page)` y `counter(pages)` en `@page @bottom-right` |

- **Formatos** (FR-006): `app/domain/formato.py` reúne funciones puras con sus tests:
  - `format_euros`: «1.560,90 €», con `Decimal` y sin `float`.
  - `format_unidades`: «2» o «1,50».
  - `format_fecha`: `DD/MM/AAAA`.
  - `format_iban`: grupos de cuatro.
  - `format_porcentaje`: «21 %».

  Son el equivalente en el servidor de `lib/dinero.ts` y `lib/facturacion.ts` de la web, y los
  tests comparan sus salidas con las mismas cadenas que los tests de la web.
- **Textos de la causa**: `app/domain/tipos.py` añade `TEXTO_CAUSA_RECTIFICACION`, con los mismos
  literales que `joyeriablanco_web/src/lib/facturacion.ts` (líneas 68-70):
  - «Devolución, descuento o cambio de precio posterior a la venta, o IVA mal aplicado».
  - «Error en datos o importes de la factura».
- **Borrador**: su identificador no está en `facturas`, así que la ruta responde 404
  `no-encontrado`, «La factura no existe.», como la consulta (FR-001). No hace falta un tipo de
  error propio.
- **Multipágina** (FR-011):
  - `thead { display: table-header-group }` repite la cabecera de la tabla de líneas.
  - `tr { break-inside: avoid }` impide partir una fila.
  - La caja de totales lleva `break-inside: avoid`.
  - El QR está en la cabecera del flujo, así que solo aparece en la primera página.
- **Metadatos del PDF**: `<title>` «Factura FAC-2026-0005», `<html lang="es">` y autor el nombre
  del emisor. El texto es real: se puede seleccionar y copiar (FR-030).

**Razón**: reutilizar `get_factura` garantiza que el PDF y la consulta cuentan lo mismo, porque
comparten el estado derivado y los enlaces. El modelo de vista separa los datos de la presentación
y se prueba sin renderizar.

**Alternativas descartadas**:
- Generar el PDF a partir de `FacturaSalida`, el esquema de la API: no tiene la fecha de la factura
  rectificada ni el registro completo, y acoplaría el PDF al contrato JSON.
- Un 422 propio para los borradores: la API ya los distingue porque no existen como factura.

---

## R-7. Listado impreso (FR-018 a FR-023; Clarifications)

**Decisión**:
- **Datos**: `repositories/facturas.py` añade dos funciones:
  - `list_facturas_impresion(...)` reutiliza `_filtros` y `_ORDENES` y la vista
    `v_listado_facturas`, sin `OFFSET`/`LIMIT`. Devuelve las mismas filas, en el mismo orden y con
    el mismo desempate que la pantalla (002, FR-035).
  - `totales_vigentes(...)`, con los mismos filtros, devuelve tres cosas:
    - El desglose por tipo: `JOIN desgloses_factura` sobre las filas con
      `tipo_documento = 'factura' AND estado = 'vigente'`, agrupado por `tipo_iva`, con `NULL` (la
      exenta) al final.
    - Las sumas de base, cuota y total de esas filas.
    - El recuento de filas fuera de la suma por clase: borradores, anuladas y rectificadas.
- **Límite**: antes de leer las filas se cuentan con el `count(*)` del listado. Si pasan de 5.000,
  la respuesta es 422 `listado-demasiado-grande`, con `limite` y `total`. La web ya conoce el total
  por el listado paginado y desactiva el botón antes (FR-018).
- **Cuadre** (FR-021): un test comprueba que la suma de las líneas por tipo es igual a la suma de
  `base`, `cuota` y `total` de las filas vigentes del propio listado.
- **Formato**: A4 **apaisado**, márgenes de 15 mm y tipografía `print-table`, de 8,5 pt.
  - En apaisado caben las siete columnas sin recortar el nombre del cliente, que se parte en
    líneas si es largo.
  - Anchos fijos: número 13 %, fecha 9 %, cliente 36 %, identificación 12 %, base 10 %, IVA 9 % y
    total 11 %, con `table-layout: fixed`.
- **Generación por bloques**, para acotar la memoria:
  - *Problema*: en la prueba previa, un único documento de 5.000 filas alcanzó unos 750 MB de
    memoria residente, frente a 330 MB con 2.000. CPython no devuelve después esa memoria al
    sistema.
  - *Proceso*:
    1. Las filas se maquetan en bloques de 1.000 con `HTML(...).render()`. El primer bloque lleva
       la cabecera del listado y el último, los totales.
    2. De cada bloque que no es el último se escriben solo sus páginas completas
       (`document.copy(pages[:-1]).write_pdf()`).
    3. Las filas de su última página, que es incompleta, se cuentan en el árbol de cajas y pasan al
       bloque siguiente. Así ninguna página queda a medias.
    4. Los PDF parciales se unen con `pypdf.PdfWriter`.
  - *Pie*: «Página n de m» no se puede calcular hasta tener todas las páginas. Por eso, al final se
    maqueta un documento ligero de `m` páginas que solo contiene el pie, y se superpone a cada
    página con `merge_page`. Después se comprimen los flujos (`compress_content_streams`).
  - *Resultado de la prueba previa* (5.000 filas, el 20 % con el nombre en dos líneas):
    - 194 páginas, con las 5.000 filas una sola vez cada una.
    - Pie correcto de «Página 1 de 194» a «Página 194 de 194».
    - **11,6 s**, **250 MB** de pico y 0,73 MB de PDF.
    - Sin comprimir los flujos, el PDF pesaba 8,2 MB.
- **Concurrencia**: el renderizado es síncrono y usa mucha CPU.
  - Corre en un hilo con `anyio.to_thread.run_sync`, para no bloquear el bucle de eventos.
  - Lo limita un `anyio.CapacityLimiter` por proceso: 1 para los listados y 4 para las facturas.
  - Con los 2 *workers* de producción, el peor caso son 2 listados simultáneos, unos 500 MB.
- **Cabecera** (FR-020): título, logotipo, nombre del emisor actual y descripción del filtro en
  palabras:
  - «Búsqueda: “maria lopez”» o «Sin búsqueda».
  - El año, o «Todos los años».
  - El mes en letra, o «Todos los meses».
  - El orden con el texto del selector de la web: «Más recientes», «Más antiguas», «Total mayor» y
    «Total menor».
  - El número de filas, y la fecha y la hora de generación en hora de Madrid.
  - **Emisor**: un listado no es una factura, así que lleva el nombre del emisor de la
    configuración actual. Si no está configurado, solo «Joyería Blanco» del logotipo.
- **Marcas por fila**: «Borrador» en lugar del número, y «Anulada» y «Rectificada» junto al número,
  como la web (002, FR-033). La exenta muestra «Exenta» en el IVA.

**Razón**: la generación por bloques respeta el límite de 5.000 filas que eligió el responsable sin
recortar datos y con la memoria acotada a un bloque. La prueba previa confirmó el número de filas,
la numeración y el tamaño. El A4 apaisado evita recortar los nombres de los clientes.

**Alternativas descartadas**:
- **Un solo documento**: hasta 750 MB por listado, que en un VPS modesto, con PostgreSQL y dos
  *workers*, arriesga quedarse sin memoria.
- **Paginación determinista con filas de alto fijo**: probada con 49 filas por página, 9,6 s y
  266 MB. Obliga a recortar con «…» los nombres largos.
- **Bajar el límite a 2.000 filas**: contradice la decisión del responsable.
- **Generarlo en un proceso aparte**: libera la memoria al terminar, pero no rebaja el pico.

**Corrección respecto a la pregunta de clarify**: la pregunta estimaba «unas 110 páginas» para
5.000 filas. En A4 apaisado, con nombres de dos líneas, salen unas 190, y en vertical, de 100 a
230 según el interlineado. La decisión de 5.000 filas no cambia: el tiempo y la memoria medidos
están dentro de SC-005.

---

## R-8. Entrega al navegador (FR-002, FR-018, FR-023, FR-028)

**Decisión**:
- **Enlace directo**: «Imprimir» e «Imprimir listado» son enlaces `<a href target="_blank"
  rel="noopener">` a la URL de la API, con las opciones en la consulta, p. ej.
  `/api/v1/facturas/{id}/pdf?iban=true&duplicado=false`.
  - Un clic en un enlace no lo bloquea ningún bloqueador de ventanas emergentes.
  - La pestaña nueva hace un `GET` del mismo sitio, así que la cookie de sesión
    (`SameSite=Strict`, 001) se envía.
  - Un `GET` no exige CSRF ni `Origin` (001, R-6).
- **Respuesta**:
  - `200 application/pdf` con `Content-Disposition: inline; filename="FAC-2026-0005.pdf"`. El
    listado se llama `facturas-2026.pdf`, `facturas-2026-03.pdf` o `facturas-todos.pdf`.
  - El middleware ya pone `Cache-Control: no-store` en `/api/v1` (001).
- **Errores en una navegación**: si la petición es una navegación de documento, se responde con
  una página HTML breve en español, con los tokens de papel, el mismo código de estado y sin datos
  técnicos.
  - Se reconoce por `Sec-Fetch-Dest: document`, o, si falta, por un `Accept` que incluye
    `text/html`.
  - Solo afecta a las dos rutas de PDF. El resto de la API sigue respondiendo con
    `application/problem+json`.
  - Mensajes:
    - 401: «Tu sesión ha caducado. Vuelve a la aplicación e inicia sesión de nuevo», con un enlace a
      `/`.
    - 404: «La factura no existe».
    - 409 `duplicado-no-disponible`.
    - 422 `listado-demasiado-grande`: «El listado tiene {total} facturas y el máximo para imprimir
      es 5.000. Acota el filtro, por ejemplo por año».
    - 500: «No se ha podido generar el PDF. Vuelve a intentarlo».
  - Se implementa en `register_error_handlers` (`app/core/errors.py`) con una comprobación de ruta y
    de navegación, y renderiza `error.html` con Jinja2.
- **Doble clic**: la web ignora un segundo clic sobre el mismo enlace durante 2 s
  (`preventDefault`). El botón muestra «Preparando…» ese tiempo y luego vuelve a su estado. Un
  listado grande tarda más, y la pestaña nueva muestra la carga del navegador.
- **CSP propia de las rutas de PDF**:
  - La CSP global de Caddy incluye `object-src 'none'`. Eso puede impedir que el visor de PDF
    integrado muestre el documento: Chrome, por ejemplo, aplica `object-src` a su visor basado en
    *plugin*.
  - Por eso **la API fija la CSP de sus dos rutas de PDF**, tanto en el PDF como en la página de
    error, y Caddy no les añade la global. Se usan dos *matchers* excluyentes, `@pdf` y su
    negación, para que el resultado no dependa del orden de los `header` (`deploy/caddy/Caddyfile`).
  - Con el PDF: `default-src 'none'; object-src 'self'; frame-ancestors 'none'; base-uri 'none';
    form-action 'none'`.
  - Con la página de error: `default-src 'none'; style-src 'sha256-…'; frame-ancestors 'none';
    base-uri 'none'; form-action 'none'`.
    - El *hash* es el del `<style>` en línea de `error.html`. Lo calcula la API al cargar la
      plantilla.
    - Ni `unsafe-inline` ni scripts.
  - Así la cabecera es la misma en desarrollo (proxy de Vite), en las pruebas y en producción, y
    se prueba con pytest.
  - Caddy sigue añadiendo a esas rutas `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
    `Referrer-Policy` y el resto de cabeceras globales. La API mantiene `Cache-Control: no-store`.
  - `deploy/verificar-produccion.sh` comprueba con `curl -D -` dos cosas:
    - Que una ruta de PDF sin sesión trae la CSP de la API, con `object-src 'self'`, y no la global.
    - Que `/` sigue con la global.
  - El quickstart incluye la verificación manual del visor en Chrome, Firefox y Safari.

**Razón**: es la única vía que cumple a la vez cuatro condiciones:
- abre el PDF en una pestaña nueva;
- no la bloquea ningún navegador;
- no relaja la CSP de la aplicación;
- no obliga a componer el PDF en el navegador.

Los errores siguen siendo comprensibles (FR-028), aunque se muestren en la pestaña nueva y no
dentro de la aplicación.

**Alternativas descartadas**:
- **`fetch` + `Blob` + `window.open`**:
  - Un documento `blob:` hereda la CSP de la SPA, con `object-src 'none'`, y el visor podría
    quedar bloqueado igualmente. Para evitarlo habría que relajar la CSP de toda la aplicación.
  - Además, `window.open` después de un `await` lo bloquea Safari.
- **`iframe` dentro de un modal**: choca con `frame-ancestors 'none'` y `X-Frame-Options DENY` en
  todo el sitio.
- **Abrir una ventana en blanco al hacer clic y navegarla tras comprobar la sesión**: añade una
  petición y un estado intermedio sin ventajas frente a la página de error.

**Ajuste de la spec**: los casos límite «Sesión caducada al imprimir», «Error al generar el PDF»,
«Bloqueador de ventanas emergentes» y «Doble clic», y los requisitos FR-023 y FR-028, se reescriben
según esta decisión (Clarifications, sesión «plan»).

---

## R-9. Contacto y pie de factura en Configuración (FR-024 a FR-026, FR-032)

**Decisión**:
- **Migración `0007_contacto_pie_factura`**, solo DDL sobre la fila única y mutable de
  `configuracion_facturacion`:
  - `emisor_telefono VARCHAR(30)`, `emisor_correo VARCHAR(254)`, `emisor_web VARCHAR(200)` y
    `pie_factura VARCHAR(600)`, todos `NULL` por defecto.
  - `CHECK` de que, si no son nulos, no están vacíos ni empiezan o acaban en espacio.
  - No toca `facturas`.
- **Esquemas**: `ConfiguracionFacturacionEntrada` y `…Salida` añaden dos campos:
  - `contacto: {telefono, correo, web}`.
  - `pie_factura`.

  Son campos opcionales: un cliente de la API que no los envíe sigue funcionando, porque se tratan
  como «sin cambios» y no como vaciado (ver «Compatibilidad»).
- **No van en `DatosEmisor`**: ese esquema es también la copia del emisor dentro de
  `FacturaSalida`, que es fiscal, y estos datos no se copian en la factura (FR-025).
- **Validación**:
  - El teléfono usa la misma regla que el de los clientes (001, FR-055): `[0-9 +()\-]+` con al
    menos 6 dígitos. La regla pasa de `services/clientes.py` a una función pura,
    `app/domain/contacto.py → validate_telefono`, que reutilizan los dos servicios sin cambiar el
    comportamiento de clientes. Sus tests siguen pasando.
  - El correo usa `email-validator`, como en clientes, y se guarda en minúsculas.
  - La web admite un dominio, p. ej. `joyeriablanco.es`, o una URL `http(s)://`. Se guarda tal
    cual, recortada, y al imprimir se quita `https://`, `http://` y la barra final.
  - El pie admite texto de varias líneas: se normalizan los saltos a `\n` y se recortan los espacios
    de los extremos.
- **Auditoría**: los cuatro campos se añaden a `CAMPOS_AUDITADOS` del servicio. El evento
  `configuracion_facturacion_cambiada` y la concurrencia optimista por `version` no cambian.
- **Compatibilidad**: si `contacto` o `pie_factura` no vienen en el `PUT`, se conservan los valores
  actuales. La web siempre los envía.
- **Contrato**: la operación `PUT /v1/configuracion/facturacion` es de 002. Su ampliación se
  documenta en dos sitios:
  - En los esquemas de `specs/002-facturas/contracts/openapi.yaml`, marcada «(ampliado en 003,
    FR-024)».
  - En la descripción del contrato de 003, que no repite la operación. El test de contrato exige
    que cada operación esté en un único contrato.
- **Datos de ejemplo** (FR-032): `cargar-datos-ejemplo` rellena:
  - teléfono `+34 900 000 000`;
  - correo `info@joyeriablanco.demo`;
  - web `joyeriablanco.demo`;
  - un pie ficticio de protección de datos, con el aviso «Texto de ejemplo».

**Razón**: son datos no fiscales y opcionales, que se leen al imprimir. La fila de configuración
es mutable y ya tiene auditoría y concurrencia, así que no hace falta nada nuevo.

**Alternativas descartadas**:
- Copiarlos en la factura al emitir: contradice la decisión del responsable (Clarifications).
- Una tabla aparte de «datos de la empresa»: duplica la concurrencia y la auditoría para cuatro
  campos.

---

## R-10. API: rutas y permisos (FR-001, FR-018, FR-027)

**Decisión**:

| Ruta | Operación | Permiso | Éxito | Errores |
|---|---|---|---|---|
| `/v1/facturas/listado/pdf` | `GET ?q&anio&mes&orden` | Sesión | 200 `application/pdf` | 401, 422 `validacion` o `listado-demasiado-grande` |
| `/v1/facturas/{factura_id}/pdf` | `GET ?iban=false&duplicado=false` | Sesión | 200 `application/pdf` | 401, 404, 409 `duplicado-no-disponible` |

- **Orden de declaración**: `/listado/pdf` se declara **antes** de `/{factura_id}` en
  `app/api/v1/facturas.py`, como ya se hizo con `/parametros`.
- **Parámetros del listado**: los valida el mismo código que `GET /v1/facturas`, mediante un tipo
  `FiltrosListado` compartido en el router.
- **Respuesta**: los routers devuelven `Response(content=…, media_type="application/pdf")`, con
  `responses={200: {"content": {"application/pdf": {}}}}` para que el OpenAPI lo documente.
- **Capas**: toda la lógica está en `services/impresion.py`. El renderizado está en
  `app/core/pdf/` (infraestructura) y los formatos, en `app/domain/` (constitución V).
- **Registros de actividad** (FR-029): `app.impresion` registra el tipo de documento, el número de
  factura o el número de filas, y la duración. Nunca el texto de búsqueda, nombres ni importes. El
  log de acceso ya omite la consulta de la URL (001).

**Razón**: son dos recursos de solo lectura, colgados de los existentes y con los mismos permisos
que su consulta.

**Alternativas descartadas**:
- Un `POST` que devuelva el PDF: obligaría a CSRF y a `fetch`, el camino descartado en R-8.
- Negociar `Accept: application/pdf` en `GET /v1/facturas/{id}`: un enlace no puede fijar
  `Accept`.

---

## R-11. Estrategia de pruebas (constitución VII; SC-001 a SC-009)

**Decisión**:
- **Unitarias del dominio**, sin HTTP:
  - `qr.py`: los vectores de R-1, las validaciones y la decodificación con zxing-cpp y nivel M.
  - `formato.py`: euros, unidades, fechas, IBAN y porcentajes, con las mismas cadenas que la web.
  - `contacto.py`: el teléfono, con los casos de clientes.
  - `tokens.py`: la sincronía con el frontmatter de `docs/DESIGN.md`.
- **Integración del PDF de la factura** (pytest contra PostgreSQL, emitiendo con los servicios
  reales):
  - El texto se extrae con pypdf y se comprueba, por tipo (ordinaria, exenta, rectificativa R4,
    rectificativa de devolución total, anulada con y sin reemisión, rectificada), que contiene cada
    dato de FR-003 y FR-008 (SC-003).
  - Casillas: IBAN con `iban=true` y sin él, y factura sin IBAN; `DUPLICADO` con `duplicado=true`,
    y 409 en una anulada (SC-004, SC-007).
  - Geometría del QR en el árbol de cajas (SC-006), y la frase solo en `verifactu`.
  - Varias páginas: 100 líneas largas, con el QR solo en la primera y el pie «Página n de m».
  - Fuentes incrustadas: `Manrope` y `Bodoni-Moda`.
  - Errores: 401 sin sesión, 404 con el id de un borrador, y la página HTML de error en una
    navegación (`Sec-Fetch-Dest: document`).
- **Integración del PDF del listado**:
  - Más de 100 filas, es decir, más de una página de pantalla: están todas y en el orden de cada
    `orden`.
  - Los filtros `q`, `anio` y `mes`.
  - Las marcas y «Exenta».
  - Los totales por tipo y generales, cuadrados al céntimo con las filas (SC-005).
  - El recuento de excluidas.
  - 422 con más de 5.000 filas: el límite se prueba con un `monkeypatch` que lo baja a 3, para no
    insertar 5.001 facturas.
  - La generación por bloques se prueba con el tamaño de bloque reducido, de 1.000 a 7, sobre
    unas 40 filas. Debe salir cada número una sola vez, sin páginas a medias salvo la última, y con
    el pie correcto.
- **Rendimiento** (SC-001 y SC-005): un test marcado `lento`, fuera de la ejecución por defecto,
  mide la factura de 20 líneas y el listado de 1.000 y 5.000 filas con datos sintéticos. Se ejecuta
  en la verificación de cierre (quickstart).
- **Configuración**: guardar contacto y pie, la validación de cada campo, la auditoría con el
  antes y el después, 403 para un empleado, y la compatibilidad de un `PUT` sin los campos nuevos.
- **Contrato**: `test_contrato_openapi.py` incluye el contrato de 003.
- **Web (Vitest + MSW)**:
  - «Imprimir» con el `href` correcto.
  - Las casillas: la del IBAN solo con IBAN, la de duplicado salvo en una anulada, y la URL cambia
    con cada una.
  - «Imprimir listado» con los filtros de la URL y sin `pagina`, desactivado con 0 o más de 5.000
    resultados y con el motivo accesible.
  - Los campos nuevos de Configuración.
- **E2E (Playwright)**:
  - Se comprueba el `href` del enlace y se descarga con `page.request.get(href)` usando la sesión
    del contexto. El tipo debe ser `application/pdf` y el cuerpo empezar por `%PDF`, para la
    factura con y sin IBAN y para el listado filtrado (SC-009).
  - No se depende del visor de PDF de Chromium en modo *headless*.

**Razón**: cubre cada criterio de éxito con una prueba automática, salvo el escaneo real del QR con
un móvil y el visor en cada navegador, que van al quickstart como verificación manual.

---

## R-12. Preguntas abiertas

- **Ninguna nueva de fuente oficial.** F-12 resuelve todo lo del QR. Siguen abiertas, sin
  bloquear esta feature:
  - Las de la asesoría en 002 (research R-17).
  - El TODO(MODALIDAD_VERIFACTU) de la constitución: cada factura guarda su modalidad, y el QR y la
    frase dependen de ella.
- **Para la asesoría** (no bloquea): el texto del pie de factura, como la cláusula de protección de
  datos, lo aporta la joyería. El sistema solo lo imprime.
