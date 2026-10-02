# Implementation Plan: PDF de factura con QR de cotejo e impresión del listado

**Branch**: `003-pdf-impresion` | **Date**: 2026-10-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-pdf-impresion/spec.md`

## Summary

Se añade la salida en papel sobre la facturación de 002.

**Qué ve el usuario**:
- En la consulta de una factura emitida: **«Imprimir»**, con las casillas «Incluir número de
  cuenta» (solo si la factura tiene IBAN) y «Duplicado» (salvo si está anulada). Se abre en una
  pestaña nueva el PDF A4 con todo el contenido obligatorio y el **QR tributario** arriba.
- En el listado: **«Imprimir listado»**, que abre un PDF A4 apaisado con todas las filas del filtro
  actual, de todas las páginas, y los totales de las vigentes desglosados por tipo de IVA. Admite
  hasta 5.000 filas.
- En Configuración → Facturación: **teléfono, correo, web y pie de factura**, que se imprimen en
  todas las facturas.

**Qué hace el servidor**:
- Genera los PDF con **WeasyPrint** a partir de plantillas Jinja2 y de los tokens «Paper» de
  `docs/DESIGN.md`, enmendado a la 1.2 (R-4, R-5).
- **QR**: dirección de cotejo de F-12 según la modalidad de la factura y el entorno de la
  instalación (`AEAT_ENTORNO`), con los cuatro valores de su registro de alta. Nivel M, 35 mm y
  6 mm de margen (R-1 a R-3).
- **Factura**: se compone desde la copia guardada al emitir. Se reutiliza `get_factura` de 002:
  estado, enlaces y registro (R-6).
- **Listado**: se genera **por bloques** de 500 filas, con arrastre de la última página y el pie
  «Página n de m» pintado en cada bloque en una segunda pasada. Medido en el contenedor: 5.000 filas
  en 19,2 s con 265 MB de pico, frente a los 750 MB de un documento único (R-7).
- Los errores en una navegación se devuelven como una página HTML en español. Las rutas de PDF
  llevan su propia CSP, que permite el visor del navegador (R-8).

**Fuera de alcance**: envío por correo, factura electrónica estructurada, exportación de datos,
remisión a la AEAT (004) y PDF de presupuestos (005).

Decisiones y fuentes oficiales (F-6, F-10, F-11 y F-12, esta con SHA-256) en
[research.md](research.md).

## Technical Context

**Language/Version**: las de 001 y 002. Python 3.13 en el backend; TypeScript 6.0.3 sobre Node.js
26 en la web.

**Primary Dependencies**:
- **Backend, nuevas en ejecución**: `weasyprint>=70,<71`, `jinja2>=3.1,<3.2`, `segno>=1.6,<1.7` y
  `pypdf>=6.19,<7`.
- **Backend, nuevas de desarrollo**: `zxing-cpp>=3.1,<3.2` y `numpy`.
- **Sistema**, en la imagen: `libpango-1.0-0`, `libpangoft2-1.0-0`, `libharfbuzz-subset0` y
  `fonts-dejavu-core`.
- **Sistema**, en el Mac de desarrollo: `brew install pango` (R-4).
- **Web**: sin dependencias nuevas. Se usa el icono `Printer` de `lucide-react`, que ya está
  instalado.

**Storage**: PostgreSQL 18.6. Una migración nueva, `0007_contacto_pie_factura`, con solo DDL sobre
la fila mutable `configuracion_facturacion`: cuatro columnas opcionales y un `CHECK`. Ninguna
tabla de solo inserción cambia (data-model).

**Testing**: pytest contra la BD de test, Vitest + MSW y Playwright, como en 002.
- Texto de los PDF extraído con pypdf.
- QR leído con zxing-cpp.
- Geometría comprobada en el árbol de cajas de WeasyPrint.
- Marca `lento` para las mediciones de SC-001 y SC-005 (R-11).

**Target Platform**: la misma de 001 y 002: un VPS con Docker Compose y navegadores actuales con
visor de PDF integrado.

**Project Type**: aplicación web (API + SPA) en monorepo.

**Performance Goals**:
- SC-001: factura de 20 líneas en menos de 3 s. En la prueba previa, menos de 0,1 s de render.
- SC-005: listado de 1.000 filas en menos de 15 s, y de 5.000 en menos de 60 s. Medido en el
  contenedor: 3,7 s y 19,2 s.

**Constraints**:
- Sin `float`: los importes se formatean desde `Decimal` (constitución II).
- QR conforme a F-10, arts. 20 y 21, y a F-12.
- Memoria acotada a unos 250-300 MB por listado.
- Renderizado en hilos, con un limitador por proceso: 1 listado y 4 facturas (R-7).
- CSP de producción sin relajar para la SPA (R-8).
- Contenedor `read_only`: la caché de fontconfig va a `/tmp` (R-4).

**Scale/Scope**:
- Volumen: el de 002, cientos a pocos miles de facturas al año, y listados de hasta 5.000 filas.
- API: 2 operaciones nuevas y la ampliación del esquema de configuración.
- Web: 3 pantallas tocadas y ninguna ruta nueva.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio / restricción (v2.2.0) | Cómo se cumple | Estado |
|---|---|---|
| **I. SDD** | Rama `003-pdf-impresion` creada a mano. Specify con 7 decisiones previas del responsable, clarify con 5 preguntas y plan con 2 decisiones técnicas registradas en la spec. Cada fase con su commit. Siguen checklist, tasks, analyze e implement | ✅ |
| **II. Integridad monetaria** | El PDF no calcula nada. Imprime los importes guardados, formateados desde `Decimal` (`domain/formato.py`). Los totales del listado son sumas `NUMERIC` en la BD, y un test comprueba que cuadran al céntimo con las filas (R-7) | ✅ |
| **III. Inalterabilidad** | Solo lectura de facturas, registros y correcciones. La 0007 solo amplía la fila mutable de configuración. Los datos fiscales del PDF salen de la copia guardada al emitir. El contacto y el pie, no fiscales, no se copian | ✅ |
| **IV. Verifactu por diseño** | URL, parámetros, codificación, tamaño, nivel M, posición y textos del QR tomados de F-12 v0.5.0 (SHA-256) y de F-10, arts. 20 y 21, con los vectores oficiales en los tests (R-1, R-2). La modalidad de cada factura decide la URL y la frase: no hay bifurcación del modelo. El entorno de la AEAT es configuración, y por defecto apunta a pruebas (R-3) | ✅ |
| **V. Capas** | Routers finos con dos `GET`. `services/impresion.py` compone los modelos de vista. `domain/qr.py`, `domain/formato.py` y `domain/contacto.py` son puros y se prueban sin HTTP. El renderizado vive en `core/pdf/`. Esquemas `*Entrada`/`*Salida` para la configuración, y nunca un ORM en la API | ✅ |
| **VI. Servidor como fuente de verdad** | Los PDF los genera el servidor con los importes registrados. La web solo construye la URL con los filtros | ✅ |
| **VII. Tests obligatorios** | No toca numeración, cálculos, encadenamiento ni conversión de presupuestos. Comprueba que el QR coincide con el registro de alta y que los totales impresos cuadran al céntimo (R-11) | ✅ |
| **VIII. Español en el dominio** | Rutas (`/v1/facturas/{id}/pdf`, `/v1/facturas/listado/pdf`), columnas, errores (`duplicado-no-disponible`, `listado-demasiado-grande`), documentos y UI en español | ✅ |
| **IX. Calidad automatizada** | ruff y mypy estricto en el backend. ESLint, typecheck, Prettier y `check:tokens` en la web | ✅ |
| **Restricción «PDF»** | WeasyPrint con plantilla HTML + CSS, como fija la constitución | ✅ |
| **Sistema de diseño** | `docs/DESIGN.md` se enmienda a la 1.2 con tokens y prosa «Paper», con la aprobación del responsable (Clarifications). Los tokens se declaran una vez en `core/pdf/tokens.py`, y un test los compara con el frontmatter. Las plantillas solo usan variables, y otro test busca literales (R-5). En la web, botones y casillas ya definidos. No hay desviaciones | ✅ |
| **Numeración** | Sin cambios. El número impreso es el asignado al emitir | ✅ |

**Re-check tras el diseño** (research, data-model, contracts y quickstart): sin violaciones.
- **Generación por bloques del listado (R-7)**: añade complejidad dentro de `core/pdf/`, pero es
  la única forma de mantener el límite de 5.000 filas que eligió el responsable sin recortar datos
  ni arriesgar la memoria del servidor. No contradice ningún principio.
- **CSP propia de las rutas de PDF (R-8)**: solo afecta a dos rutas de solo lectura. La SPA
  conserva su CSP estricta.
- **Ampliación del contrato de 002 (R-9)**: la operación sigue en un único contrato. Sus esquemas
  se marcan «ampliado en 003».

## Project Structure

### Documentation (this feature)

```text
specs/003-pdf-impresion/
├── spec.md
├── plan.md              # este fichero
├── research.md          # R-1 a R-12, fuentes F-6, F-10, F-11 y F-12
├── data-model.md        # migración 0007, lecturas y modelos de vista
├── quickstart.md        # validación manual, pruebas y producción
├── contracts/
│   ├── openapi.yaml     # 2 operaciones nuevas + ampliación de esquemas de 002
│   ├── ui-rutas.md      # cambios en /facturas, la consulta y Configuración
│   └── documentos-pdf.md# disposición de la factura, el listado y la página de error
├── checklists/
│   └── requirements.md
└── tasks.md             # /speckit.tasks
```

### Source Code (repository root)

```text
backend/
├── Dockerfile                                # + apt Pango/HarfBuzz/DejaVu en base y prod; XDG_CACHE_HOME
├── pyproject.toml                            # + weasyprint, jinja2, segno, pypdf; dev: zxing-cpp, numpy; marca «lento»
├── alembic/versions/0007_contacto_pie_factura.py
├── app/
│   ├── api/v1/facturas.py                    # + GET /listado/pdf (antes de /{id}) y GET /{id}/pdf
│   ├── core/
│   │   ├── config.py                         # + EntornoAeat y aeat_entorno (R-3)
│   │   ├── errors.py                         # + DuplicadoNoDisponible, ListadoDemasiadoGrande; página HTML en navegaciones
│   │   └── pdf/                              # infraestructura de impresión (nuevo)
│   │       ├── __init__.py
│   │       ├── tokens.py                     # tokens «Paper» (fuente única en el backend)
│   │       ├── plantillas.py                 # entorno Jinja2, CSS de tokens, hash del estilo de error
│   │       └── render.py                     # WeasyPrint: factura, listado por bloques + pie, limitadores
│   ├── domain/
│   │   ├── qr.py                             # URL de cotejo (F-12) y SVG del QR (segno, nivel M)
│   │   ├── formato.py                        # euros, unidades, fechas, IBAN, porcentajes
│   │   ├── contacto.py                       # teléfono (sale de services/clientes.py)
│   │   └── tipos.py                          # + TEXTO_CAUSA_RECTIFICACION
│   ├── models/configuracion_facturacion.py   # + 4 columnas
│   ├── repositories/facturas.py              # + list_facturas_impresion, count, totales_vigentes
│   ├── schemas/configuracion_facturacion.py  # + ContactoEntrada/Salida, pie_factura
│   ├── services/
│   │   ├── impresion.py                      # FacturaImpresa, ListadoImpreso y su composición (nuevo)
│   │   ├── configuracion_facturacion.py      # + contacto y pie, normalización y auditoría
│   │   ├── clientes.py                       # usa domain/contacto.validate_telefono
│   │   └── datos_ejemplo.py                  # + contacto y pie ficticios
│   └── resources/
│       ├── pdf/{base,factura,listado,error}.html, papel.css
│       ├── fuentes/*.woff2, OFL.txt, README.md
│       └── marca/logo.png, README.md
└── tests/
    ├── unit/domain/test_qr.py, test_formato.py, test_contacto.py
    ├── unit/test_tokens_papel.py
    └── integration/test_pdf_factura.py, test_pdf_listado.py, test_pdf_rendimiento.py (lento),
        test_configuracion_contacto.py

joyeriablanco_web/
├── src/lib/impresion.ts (+ .test.ts)         # urlPdfFactura, urlPdfListado
├── src/features/facturas/
│   ├── ImprimirFactura.tsx                   # enlace + casillas (consulta)
│   ├── ImprimirListado.tsx                   # enlace / botón deshabilitado con motivo
│   ├── FacturaConsulta.tsx                   # monta ImprimirFactura en el pie
│   └── FacturasPage.tsx                      # monta ImprimirListado en la cabecera
├── src/features/configuracion/FacturacionPage.tsx   # + contacto y pie
├── src/api/openapi.json, schema.gen.ts       # regenerados
└── e2e/impresion.spec.ts

deploy/
├── caddy/Caddyfile                           # CSP global solo fuera de las rutas de PDF
└── verificar-produccion.sh                   # + comprobaciones de CSP de PDF
docker-compose.prod.yml, .env.example         # + AEAT_ENTORNO
docs/DESIGN.md                                # 1.2: tokens y sección «Paper» (hecho en esta fase)
specs/002-facturas/contracts/openapi.yaml     # esquemas de configuración ampliados (hecho en esta fase)
```

**Structure Decision**: el monorepo de 001 y 002. La infraestructura de impresión vive en
`backend/app/core/pdf/`, junto a `db` y `http`, porque es transversal y la reutilizarán los
presupuestos (005). La lógica pura está en `domain/` y la composición, en `services/impresion.py`.
Los recursos estáticos (plantillas, fuentes y logotipo) están en `app/resources/`, que ya se
empaqueta en la imagen de producción.

## Complexity Tracking

Sin violaciones de la constitución que justificar.
