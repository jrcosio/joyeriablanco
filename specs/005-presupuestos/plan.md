# Implementation Plan: Presupuestos con conversión en factura

**Branch**: `005-presupuestos` | **Date**: 2026-10-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/005-presupuestos/spec.md`

## Summary

Presupuestos con el ciclo de la factura y sin ninguna pieza fiscal (constitución 2.3.0).

**Qué ve el usuario**:
- **Presupuestos** en el menú, con un listado y un modal iguales que los de facturas: borrador,
  emisión con número `PRE-AAAA-NNNN`, validez («Válido hasta»), consulta e historial.
- **Imprimir**: un PDF titulado «PRESUPUESTO», con la leyenda «Documento sin validez fiscal. No es
  una factura.» y la validez, **sin QR tributario** ni mención VERI\*FACTU.
- **Convertir en factura**: crea un borrador de factura vinculado y precargado. El presupuesto
  queda «En facturación» hasta que se emite la factura, y entonces pasa a «Convertido en FAC-…».
- **Administradores**: «Modificar», que emite uno nuevo que sustituye al anterior, y «Anular», con
  motivo.
- **Listado impreso** con totales por tipo de IVA, y validez y pie propios en Configuración.

**Qué hace el servidor**:
- **Tablas propias de solo inserción** para los presupuestos emitidos, sus líneas, sus desgloses y
  sus cierres, protegidas en la BD como las facturas (R-1, R-2).
- **Estado derivado** con `estado_presupuesto()`, más la caducidad calculada con la fecha de hoy
  (R-3).
- **Serie PRE** en el contador de 002, con el mismo cerrojo (R-4).
- **Conversión en dos pasos** (R-5):
  1. `POST /v1/presupuestos/{id}/conversion` crea un borrador vinculado, único gracias a una
     restricción `UNIQUE`.
  2. Al emitir ese borrador con la operación de 002, la misma transacción inserta el cierre de
     conversión.

  El camino fiscal de 002 (cadena, número FAC, registro e idempotencia) no cambia.
- **Concurrencia**: un cerrojo consultivo para los cierres, más `UNIQUE` y dos triggers como
  barreras en la BD (R-6).
- **PDF**: se reutiliza la infraestructura de 003, con macros comunes y un modelo de vista **sin
  campo QR** (R-8, R-10).

**Fuera de alcance**: proformas como documento aparte, conversiones múltiples o parciales entre
documentos, aceptación formal, duplicados, filtros por estado, envío por correo y remisión a la
AEAT (004).

Decisiones y fuentes (F-4, F-6 y F-13) en [research.md](research.md).

## Technical Context

**Language/Version**: las de 001 a 003. Python 3.13 en el backend; TypeScript 6.0.3 sobre Node.js
26 en la web.

**Primary Dependencies**: sin dependencias nuevas. Se usan las de 003 (WeasyPrint, Jinja2 y pypdf)
y, en la web, `lucide-react` (`ClipboardList` ya está en el menú).

**Storage**: PostgreSQL 18.6. Una migración nueva, `0008_presupuestos`:
- Seis tablas: dos mutables y cuatro de solo inserción.
- Una vista, una función de estado y dos triggers de validación.
- DDL sobre tablas de 002:
  - `borradores_factura.presupuesto_id`.
  - Los `CHECK` de `contadores_factura` y de `eventos_auditoria`.
  - Dos columnas en `configuracion_facturacion`.

  Ninguna tabla de solo inserción de 002 cambia (data-model).

**Testing**: pytest contra la BD de test, Vitest + MSW y Playwright, como en 002 y 003. Las
pruebas de concurrencia hacen commit real y se limpian con `limpiar_facturacion_confirmada`, que
se amplía con las tablas nuevas. La marca `lento` cubre SC-008.

**Target Platform**: la de 001 a 003.

**Project Type**: aplicación web (API + SPA) en monorepo.

**Performance Goals**:
- SC-008: con 20.000 presupuestos, el 95 % de las búsquedas en menos de 1 s, con los mismos
  índices que facturas.
- PDF del presupuesto como el de la factura, en menos de 3 s. Listado impreso como en 003.

**Constraints**:
- Sin `float` (constitución II).
- **Ningún presupuesto genera registro ni huella**, ni consume números FAC (FR-005).
- La emisión de facturas de 002 no cambia de comportamiento: sus suites deben seguir en verde
  antes y después de la fase fundacional.
- CSP: la excepción de PDF del Caddyfile se amplía solo a las rutas de PDF de presupuestos.

**Scale/Scope**:
- API: 14 operaciones nuevas y la ampliación de 4 esquemas de 002.
- Web: 5 rutas nuevas y 3 pantallas de 002 tocadas: el borrador de factura, la consulta de
  factura y Configuración.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio / restricción (v2.3.0) | Cómo se cumple | Estado |
|---|---|---|
| **I. SDD** | La 003 se cerró y se fusionó en `main` antes de abrir la 005. La rama se creó a mano. Enmienda 2.3.0, specify con 4 decisiones previas del responsable y clarify con 5 preguntas, cada fase con su commit. Siguen checklist, tasks, analyze e implement | ✅ |
| **II. Integridad monetaria** | Mismos tipos `NUMERIC` y `domain/importes.compute_totals`, la política única de redondeo, para presupuestos, borradores y la factura convertida. Importes como cadena en la API. Los totales del listado impreso son sumas `NUMERIC` | ✅ |
| **III. Inalterabilidad** | Presupuestos, líneas, desgloses y cierres de solo inserción, con REVOKE y triggers que paran también a `jb_owner` (R-2). El borrador se edita y se borra. «Modificar» es una sustitución trazable y «Anular» es un cierre. Como mucho un cierre, por `UNIQUE`. El presupuesto nunca lleva QR, registro ni huella | ✅ |
| **IV. Verifactu por diseño** | El presupuesto queda fuera del perímetro fiscal (F-13). La conversión emite la factura por el camino único de 002: número FAC, registro de alta, huella y QR, con la modalidad de la configuración. El vínculo inalterable con la factura cumple la conservación «debidamente vinculada» de F-13 | ✅ |
| **V. Capas** | Routers finos. La lógica, en `services/presupuestos.py`, `borradores_presupuesto.py`, `conversion.py` e `impresion_presupuestos.py`. Lo puro, en `domain/presupuestos.py` y `domain/numeracion.py`. Esquemas `*Entrada` y `*Salida`, nunca un ORM en la API | ✅ |
| **VI. Servidor como fuente de verdad** | La web previsualiza con `lib/dinero.ts` y nunca envía totales. El servidor calcula al guardar, al emitir y al convertir | ✅ |
| **VII. Tests obligatorios** | Los cuatro: numeración PRE bajo concurrencia, importes del presupuesto y de la factura convertida, encadenamiento con conversiones intercaladas, y conversión simultánea, idempotente y frente a la anulación (R-14) | ✅ |
| **VIII. Español en el dominio** | Tablas (`presupuestos`, `cierres_presupuesto`…), rutas (`/v1/presupuestos/{id}/conversion`), errores (`presupuesto-no-modificable`) y UI en español | ✅ |
| **IX. Calidad automatizada** | ruff y mypy estricto en el backend. ESLint, typecheck, Prettier y `check:tokens` en la web | ✅ |
| **Restricción «PDF»** | WeasyPrint con plantilla HTML + CSS, sobre la infraestructura de 003 | ✅ |
| **Sistema de diseño** | `docs/DESIGN.md` se enmienda a la 1.3, aprobada en el plan de la feature: aviso no fiscal, marcas de presupuesto y tono neutro de los chips, que ya se usaba sin documentar. Sin tokens nuevos ni desviaciones | ✅ |
| **Numeración** | Serie `PRE-AAAA-NNNN`, correlativa, sin huecos ni reutilización, con el contador bloqueado de 002 y sin ajuste al alza (constitución 2.3.0) | ✅ |

**Re-check tras el diseño** (research, data-model, contracts y quickstart): sin violaciones.
- **Generalización en la fase fundacional (R-8)**: toca código de 002 y 003 sin cambiar su
  comportamiento. Se justifica para no duplicar la lógica de líneas, del listado ni del PDF, y la
  vigilan sus suites.
- **DDL sobre `borradores_factura` (R-5)**: es una tabla mutable. La columna nueva no afecta a las
  facturas emitidas ni a sus registros.
- **Ampliación de los contratos de 002 (R-12)**: las operaciones siguen en un único contrato, con
  sus esquemas marcados «ampliado en 005».

## Project Structure

### Documentation (this feature)

```text
specs/005-presupuestos/
├── spec.md
├── plan.md              # este fichero
├── research.md          # R-1 a R-14, fuentes F-4, F-6 y F-13
├── data-model.md        # migración 0008, estados, vista y modelos
├── quickstart.md        # validación manual, pruebas y producción
├── contracts/
│   ├── openapi.yaml     # 14 operaciones nuevas + ampliación de esquemas de 002
│   ├── ui-rutas.md      # /presupuestos*, ampliaciones de facturas y Configuración
│   └── documentos-pdf.md# presupuesto y listado de presupuestos impresos
├── checklists/
│   └── requirements.md
└── tasks.md             # /speckit.tasks
```

### Source Code (repository root)

```text
backend/
├── alembic/versions/0008_presupuestos.py
├── app/
│   ├── api/v1/
│   │   ├── presupuestos.py                     # listado, parámetros, PDF, emitir, detalle, modificar, anular, convertir
│   │   ├── borradores_presupuesto.py           # CRUD + emisión
│   │   └── __init__.py                         # + routers
│   ├── core/
│   │   ├── errors.py                           # + PresupuestoNoModificable; traducción de UNIQUE y triggers de cierre
│   │   └── pdf/respuestas.py                   # _mensaje por tipo de documento
│   ├── domain/
│   │   ├── tipos.py                            # + Serie.PRESUPUESTO, EstadoPresupuesto, TipoCierrePresupuesto, TipoEvento
│   │   ├── numeracion.py                       # (FAC|REC|PRE), mensajes genéricos
│   │   └── presupuestos.py                     # validez por defecto y estado visible (nuevo)
│   ├── models/
│   │   ├── presupuesto.py, borrador_presupuesto.py, cierre_presupuesto.py   # nuevos
│   │   ├── borrador_factura.py                 # + presupuesto_id
│   │   └── configuracion_facturacion.py        # + validez_presupuesto_dias, pie_presupuesto
│   ├── repositories/
│   │   ├── listado.py                          # filtros, órdenes y consulta comunes (nuevo, R-8)
│   │   ├── facturas.py                         # usa listado.py
│   │   ├── presupuestos.py, borradores_presupuesto.py, cierres_presupuesto.py   # nuevos
│   │   └── borradores.py                       # + get_by_presupuesto
│   ├── schemas/
│   │   ├── presupuesto.py, borrador_presupuesto.py   # nuevos
│   │   ├── borrador.py, factura.py             # + presupuesto_origen
│   │   └── configuracion_facturacion.py        # + validez y pie de presupuesto
│   ├── services/
│   │   ├── contenido.py                        # líneas, previstos y copias de partes (nuevo, R-8)
│   │   ├── emision.py, borradores.py           # usan contenido.py; emit_borrador cierra la conversión
│   │   ├── presupuestos.py, borradores_presupuesto.py, conversion.py   # nuevos
│   │   ├── impresion_comun.py                  # piezas comunes de impresión (nuevo, R-8)
│   │   ├── impresion.py                        # usa impresion_comun.py
│   │   ├── impresion_presupuestos.py           # PresupuestoImpreso y listado (nuevo)
│   │   ├── facturas.py                         # presupuesto_origen en el detalle
│   │   ├── documentos.py                       # + presupuestos y sus borradores
│   │   ├── configuracion_facturacion.py        # + validez y pie, auditados
│   │   └── datos_ejemplo.py                    # + _cargar_presupuestos
│   └── resources/pdf/
│       ├── _documento.html                     # macros comunes (nuevo)
│       ├── factura.html                        # usa las macros (mismo resultado)
│       ├── presupuesto.html                    # sin QR (nuevo)
│       ├── listado.html                        # textos desde el modelo
│       └── papel.css                           # @page documento, .aviso-no-fiscal
└── tests/
    ├── unit/domain/test_presupuestos.py, test_numeracion.py (+PRE)
    └── integration/
        ├── facturacion_datos.py                # + datos de presupuesto y limpieza de las tablas nuevas
        ├── test_numeracion_presupuestos.py      # ⚖ obligatorio
        ├── test_conversion_presupuesto.py      # ⚖ obligatorio
        ├── test_presupuestos_borradores.py, test_presupuestos_emision.py,
        ├── test_presupuestos_cierres.py, test_presupuestos_inalterables.py,
        ├── test_listado_presupuestos.py, test_pdf_presupuesto.py,
        ├── test_pdf_listado_presupuestos.py, test_configuracion_presupuestos.py
        └── test_contrato_openapi.py            # + 005

joyeriablanco_web/
├── src/features/documentos/                    # movido de facturas/ sin cambio de comportamiento (R-13)
├── src/features/presupuestos/                  # páginas, modal, consulta, diálogos e impresión (nuevo)
├── src/features/facturas/                      # «Procede del presupuesto» en el borrador y la consulta
├── src/features/configuracion/FacturacionPage.tsx   # + validez y pie de presupuesto
├── src/features/auditoria/tipos-evento.ts      # + eventos
├── src/routes/_app/presupuestos.tsx, presupuestos/**   # rutas nuevas
├── src/api/queries/presupuestos.ts, borradoresPresupuesto.ts   # nuevas; borradores.ts invalida presupuestos
├── src/components/layout/Sidebar.tsx (+ test)  # Presupuestos activo
├── src/lib/impresion.ts                        # base por tipo de documento
├── src/test/presupuestos.ts                    # datos de prueba (nuevo)
├── src/api/openapi.json, schema.gen.ts         # regenerados
└── e2e/presupuestos.spec.ts, presupuestos-listado.spec.ts, helpers/presupuestos.ts
    (+ acceso, acciones-visibles, responsive, teclado y facturas-listado ajustados)

deploy/caddy/Caddyfile                          # excepción de CSP también para los PDF de presupuestos
deploy/verificar-produccion.sh                  # + comprobación del listado de presupuestos
docs/DESIGN.md                                  # 1.3 (hecho en esta fase)
specs/002-facturas/contracts/openapi.yaml       # esquemas ampliados en 005 (hecho en esta fase)
```

**Structure Decision**: el monorepo de 001 a 003.
- **Módulos nuevos**: los presupuestos tienen sus propios modelos, repositorios, servicios y
  routers, en paralelo a los de facturas.
- **Módulos comunes**: lo que comparten los dos documentos se extrae a `services/contenido.py`,
  `repositories/listado.py`, `services/impresion_comun.py`, `resources/pdf/_documento.html` y
  `features/documentos/`.
- **Vínculo con 002**: la conversión toca 002 en un solo punto, el cierre al final de
  `emit_borrador`.

## Complexity Tracking

Sin violaciones de la constitución que justificar.
