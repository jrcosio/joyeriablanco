# Implementation Plan: Facturación con registro Verifactu

**Branch**: `002-facturas` | **Date**: 2026-09-28 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-facturas/spec.md`

## Summary

Se añade la facturación sobre la base de 001.

**Qué ve el usuario**:
- Un **listado** con la misma lógica que clientes, sin indicadores ni estado de cobro.
- Un **modal** sobre el listado para crear, editar borradores, consultar y modificar.
- **Configuración → Facturación**: IVA por defecto (21 %), clave de régimen, modalidad pendiente de
  la asesoría, datos del emisor y ajuste al alza del contador.

**Qué hace el servidor**:
- Al emitir, en una sola transacción: asigna el número `FAC-AAAA-NNNN` bajo cerrojo, calcula los
  importes con `Decimal`, copia emisor y destinatario, y genera el **registro de alta** con la
  huella SHA-256 oficial encadenada.
- Facturas y registros son **inalterables en la BD**.
- «Modificar» (solo administradores) es siempre una corrección trazable:
  - **Factura que no debió emitirse o no se entregó**: anulación y reemisión con el siguiente
    número.
  - **Factura entregada**: rectificativa por sustitución `REC-AAAA-NNNN`, R1 o R4 según la causa,
    incluidas las devoluciones parciales y totales.
  - **Anular** está disponible sin reemisión.
- Una comprobación de integridad, lanzada desde la CLI, recalcula la cadena completa.

**Fuera de alcance**: el PDF con QR (003), la remisión a la AEAT y la firma (004) y los
presupuestos (005).

Las decisiones y las fuentes oficiales citadas (F-1 a F-10) están en [research.md](research.md).

## Technical Context

**Language/Version**: las de 001. Python 3.13 en el backend; TypeScript 6.0.3 sobre Node.js 26 en
la web.

**Primary Dependencies**: **sin dependencias nuevas**.
- Backend: FastAPI 0.141, SQLAlchemy 2.1, Alembic 1.20, Pydantic 2.13 y Typer 0.27. La huella usa
  `hashlib` y los importes `decimal`, ambos de la biblioteca estándar.
- Web: React 19.3, TanStack Router 1.170 y Query 5.104, React Hook Form 7.89 + Zod 4.6 y React Aria
  Components 1.21. La previsualización de importes usa `BigInt` nativo (R-11).

**Storage**: PostgreSQL 18.6. Una migración nueva, `0005_facturacion`, crea:
- Las tablas de solo inserción con `REVOKE` y triggers.
- Los triggers de encadenamiento y de contador solo al alza.
- La vista `v_listado_facturas`.
- La ampliación del `CHECK` de auditoría.

**Testing**: pytest contra la BD de test, Vitest + MSW y Playwright, como en 001. Los tests
obligatorios de la constitución VII se detallan en R-2, R-7 y R-10.

**Target Platform**: la misma que en 001, un VPS con Docker Compose y navegadores actuales.

**Project Type**: aplicación web (API + SPA) en monorepo.

**Performance Goals**:
- SC-007: el 95 % de las búsquedas y los filtros, en menos de 1 s con 20.000 facturas.
- La emisión, con un p95 inferior a 1 s con 20.000 facturas. Serializa la cadena, lo que es
  aceptable con menos de 10 usuarios. Se mide junto con SC-007.
- SC-002: 200 emisiones concurrentes sin huecos.

**Constraints**:
- Sin `float` en ningún punto: `NUMERIC` en la BD, `Decimal` en Python, cadenas en JSON y `BigInt`
  en la web.
- Registro simultáneo a la expedición, en la misma transacción (F-8, art. 9).
- Hora con desfase de Madrid y margen de un minuto (F-10, art. 7).
- Formatos exactos de F-1 y F-2.
- Constitución 2.2.0: número nunca a mano y ajuste solo al alza.

**Scale/Scope**:
- Volumen: menos de 10 usuarios y del orden de cientos a miles de facturas al año (hasta 20.000
  para las pruebas).
- Web: 5 pantallas o modales nuevos.
- API: 14 operaciones nuevas y 1 comando de CLI.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio / restricción (v2.2.0) | Cómo se cumple | Estado |
|---|---|---|
| **I. SDD** | Rama `002-facturas` creada a mano. Specify con 3 marcadores resueltos, clarify con 4 preguntas y plan con 2 preguntas de dominio, cada fase con su commit. Siguen checklist, tasks, analyze e implement | ✅ |
| **II. Integridad monetaria** | `NUMERIC(12,2)` y `Decimal` en todo el backend, con una única política de redondeo en `domain/importes.py` (R-10). También los totales previstos de los borradores se calculan ahí al guardarlos: la vista no redondea (R-9, R-12). JSON con cadenas: la entrada rechaza números (R-10). La web previsualiza con `BigInt` (R-11). IVA por línea (`lineas_factura.tipo_iva`) y totales por tipo en `desgloses_factura` | ✅ |
| **III. Inalterabilidad** | Tablas 🔒 con `REVOKE` y triggers también para `jb_owner` (R-8). Estado derivado de `correcciones_factura`, sin `UPDATE`. Borradores mutables porque no son facturas expedidas. «Modificar» es una corrección trazable: anulación y reemisión o rectificativa por sustitución (R-4). El límite heredado de `DISABLE TRIGGER` por el dueño se cubre con la comprobación de integridad (FR-031) | ✅ |
| **IV. Verifactu por diseño** | Formatos tomados de F-1, F-2 y F-3 con versión y SHA-256. Vectores oficiales de huella en los tests. Encadenamiento según F-10, art. 7, con cerrojo y trigger (R-6). Modalidad como columna de configuración y de cada registro: el cambio no exige migraciones. Lo no verificable queda en R-17 | ✅ |
| **V. Capas** | Routers finos: `routers → services → repositories/modelos`. Huella, importes, numeración y contenido del registro son funciones puras en `app/domain/` y se prueban sin HTTP. Esquemas `*Entrada`/`*Salida`; nunca se devuelve un ORM | ✅ |
| **VI. Servidor como fuente de verdad** | Las entradas no admiten totales (`additionalProperties: false`). El servidor calcula y devuelve líneas, desglose y totales. La web solo previsualiza | ✅ |
| **VII. Tests obligatorios** | Aplican tres: numeración bajo concurrencia (R-7), importes y redondeos (R-10) y encadenamiento de huellas (R-2, R-6). Además se prueba la inalterabilidad. La conversión presupuesto → factura llega en la 005 | ✅ |
| **VIII. Español en el dominio** | Tablas (`facturas`, `registros_facturacion`…), rutas (`/v1/facturas`, `/v1/borradores-factura`…), errores y UI en español. Los campos oficiales conservan su nombre de F-1 dentro de `contenido` | ✅ |
| **IX. Calidad automatizada** | ruff y mypy estricto obligatorios. ESLint, typecheck, Prettier y `check:tokens` en la web | ✅ |
| **Numeración (2.2.0)** | `FAC` y `REC` por año con `SELECT … FOR UPDATE` sobre `contadores_factura`. Nunca `MAX+1`. Sin número manual. Ajuste solo al alza, con motivo, aviso previo y trigger que impide bajar (R-7) | ✅ |
| **Precios sin IVA** | Las líneas llevan el precio unitario sin IVA. La cuota la calcula el servidor | ✅ |
| **Sistema de diseño** | `ModalDocumento`, `CampoDecimal` y los totales usan los tokens de DESIGN.md: nivel 2, radio 0 y «Monetary Inputs» / «Totals Section» (contracts/ui-rutas.md). Las desviaciones del mockup están justificadas en la spec. No hay desviaciones de DESIGN.md | ✅ |
| **Restricciones técnicas** | Mismo stack. WeasyPrint no se usa hasta la 003 | ✅ |

**Re-check tras las checklists** (2026-09-29): sin violaciones nuevas.
- **Fecha editable hacia atrás**: es una decisión del responsable, con el riesgo frente a F-8, art.
  9, documentado como Q-9 para la asesoría (principio IV: lo no verificado queda como pregunta
  abierta).
- **Anular una rectificativa**: la original vuelve a estar vigente por derivación, sin ningún
  `UPDATE` (principio III).
- **Idempotencia**: evita emisiones duplicadas que después exigirían una anulación.

**Re-check post-diseño**, tras data-model, contracts y quickstart: sin violaciones.
- **Borradores mutables**: los permite expresamente el principio III (2.1.0).
- **`contadores_factura` mutable**: la numeración necesita una tabla de contadores y la
  constitución la prevé. Se protege con el trigger que impide bajar.
- **El dueño puede desactivar triggers**: no es una violación, es el mismo límite que 001 R-10,
  compensado por FR-031. Queda documentado en R-8.

## Project Structure

### Documentation (this feature)

```text
specs/002-facturas/
├── spec.md              # Especificación (Clarifications: previas, specify, clarify y plan)
├── plan.md              # Este fichero
├── research.md          # Fase 0: fuentes oficiales F-1 a F-10 y decisiones R-1 a R-19
├── data-model.md        # Fase 1: tablas, restricciones, estado derivado y transiciones
├── quickstart.md        # Fase 1: validación de extremo a extremo
├── contracts/
│   ├── openapi.yaml     # 14 operaciones nuevas (OpenAPI 3.1, validado), con referencias al de 001
│   └── ui-rutas.md      # Rutas nuevas y aplicación de DESIGN.md
├── checklists/          # requirements.md (+ los de /speckit.checklist)
├── assets/              # mockup-facturas.png y mockup-nueva-factura.png (orientativos)
└── tasks.md             # Fase 2 (/speckit.tasks)
```

### Source Code (repository root)

```text
.env.example                          # + SIF_* ficticios (R-5)
backend/
├── alembic/versions/0005_facturacion.py
├── app/
│   ├── core/config.py                # + SIF_* con validación en producción (R-5)
│   ├── domain/
│   │   ├── importes.py               # redondeo, línea, desglose, totales y TIPOS_IVA_S1 (R-10)
│   │   ├── huella.py                 # cadenas de alta y anulación, SHA-256 (R-2)
│   │   ├── numeracion.py             # formato FAC/REC y año de la fecha (R-7)
│   │   ├── registro.py               # contenido del registro de alta y de anulación según F-1 (R-3, R-4)
│   │   └── tipos.py                  # + Serie, TipoFactura, Modalidad, MotivoModificacion, CausaRectificacion, TipoCorreccion y TipoEvento ampliado
│   ├── models/                       # configuracion_facturacion, contador_factura, borrador_factura, factura (+ línea y desglose), correccion_factura y registro_facturacion
│   ├── repositories/                 # facturas.py (listado sobre la vista), borradores.py, correcciones.py, registros.py (cadena), contadores.py y configuracion_facturacion.py
│   ├── services/
│   │   ├── configuracion_facturacion.py
│   │   ├── borradores.py
│   │   ├── emision.py                # emitir, anular y modificar: cerrojos, idempotencia, contador y auditoría (R-6, R-7, R-9, R-18)
│   │   ├── cadena.py                 # único generador de registros (comprobación previa, contenido y huella). Solo lo llama emision.py (R-6)
│   │   ├── facturas.py               # listado y detalle con estado derivado e historial
│   │   ├── integridad.py             # comprobación de la cadena (FR-031)
│   │   ├── documentos.py             # implementación real de ClienteDocumentosChecker (FR-042)
│   │   └── datos_ejemplo.py          # + facturas demo mediante los servicios (R-16)
│   ├── schemas/                      # factura.py, borrador.py, configuracion_facturacion.py e importes.py (tipos Importe y Cantidad, R-10)
│   ├── api/v1/                       # facturas.py, borradores.py y configuracion.py
│   └── cli.py                        # + verificar-cadena
├── scripts/medir_busqueda_facturas.py
└── tests/
    ├── unit/                         # domain/test_importes, domain/test_huella (vectores F-2), domain/test_numeracion, domain/test_registro y schemas/test_importes
    └── integration/                  # test_emision, test_numeracion_concurrencia, test_cadena_registros, test_facturacion_inalterable, test_correcciones, test_borradores, test_configuracion_facturacion, test_listado_facturas, test_verificar_cadena, test_contrato_openapi (generalizado)

joyeriablanco_web/src/
├── lib/dinero.ts (+ test)            # BigInt: parsear, calcular y formatear (R-11)
├── lib/idempotencia.ts (+ test)      # clave de operación por modal (R-18)
├── components/ui/                    # ModalDocumento, CampoDecimal y CampoFecha (extraído de AuditoriaPage)
├── components/layout/Sidebar.tsx     # Facturas activa
├── api/queries/                      # facturas.ts, borradores.ts y configuracionFacturacion.ts; tipos.ts ampliado
├── features/facturas/                # FacturasPage, FiltrosFacturas, TablaFacturas, FacturaModal, FacturaForm, LineasFactura, TotalesFactura, ResumenCliente, HistorialFactura, MotivoModificacionDialog, AnularFacturaDialog, ConfirmarEmisionDialog y factura-valores.ts (+ tests)
├── features/clientes/ClienteAltaPanel.tsx   # extraído de ClientePanel para usarlo desde el modal (FR-046)
├── features/configuracion/FacturacionPage.tsx + AjusteContadorDialog.tsx
└── routes/_app/                      # facturas.tsx, facturas/{nueva, borradores/$borradorId, $facturaId, $facturaId/modificar}.tsx y configuracion/facturacion.tsx
joyeriablanco_web/e2e/                # facturas.spec.ts; acciones-visibles, teclado y responsive ampliados
```

**Structure Decision**: el mismo monorepo y la misma organización por capas de 001. La lógica
fiscal pura va en `app/domain/`. La transaccional está concentrada en `services/emision.py`. Los
registros solo los genera `services/cadena.py`, al que solo llama `emision.py`.

## Enfoque de implementación (orden por dependencias)

1. **Dominio puro** (TDD, sin BD), empezando por los tests obligatorios:
   - `importes.py` con la tabla de casos de R-10.
   - `huella.py` con los tres vectores de F-2.
   - `numeracion.py`.
   - `registro.py`, que genera el contenido F-1 para F1, R1/R4-S y anulación.
2. **Migración 0005 y modelos**: tablas, `REVOKE`, triggers de inalterabilidad, encadenamiento y
   contador, vista y auditoría. Los tests de inalterabilidad y de linealidad de la cadena van
   contra la BD.
3. **Configuración de facturación** (US1): servicio, API, `/v1/facturas/parametros`, pestaña web y
   ajuste del contador.
4. **Emisión** (US2): `services/emision.py` (cerrojos, contador, cálculo, copias, registro,
   auditoría e idempotencia por `Idempotency-Key`, R-18), `POST /v1/facturas`, el modal «Nueva factura», `ModalDocumento`, `CampoDecimal`,
   `lib/dinero.ts` y el alta de cliente desde el modal. El test de concurrencia de 200 emisiones va
   aquí.
5. **Listado** (US3): vista, repositorio, API, página, filtros y tabla con acciones fijas, además de
   la entrada del menú.
6. **Borradores** (US4): CRUD, emisión desde borrador y concurrencia optimista.
7. **Correcciones** (US5): anulación, reemisión y rectificativa R1/R4 por sustitución, incluida la
   devolución total.
   - Anulación de una rectificativa con reactivación de la original (FR-048, R-8), incluido el
     trigger `validar_correccion`.
   - Rechazo `sin-cambios`.
   - Diálogos de motivo y de anulación, historial y permisos de administrador.
   - Implementación real de `ClienteDocumentosChecker`.
8. **Integridad** (US6): `services/integridad.py`, `joyeria verificar-cadena` y el test de
   alteración con `DISABLE TRIGGER`.
9. **Cierre**:
   - Datos de ejemplo y reinicio e2e.
   - Contrato generalizado.
   - Regeneración de tipos.
   - E2E: `facturas.spec.ts`, acciones visibles, teclado y responsive.
   - Medición de SC-007.
   - Actualización del README (estado de los módulos) y validación del quickstart.

## Complexity Tracking

Sin violaciones de la constitución que justificar.
