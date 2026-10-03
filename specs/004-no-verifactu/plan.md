# Implementation Plan: Modalidad No VERI\*FACTU — registros firmados, registro de eventos y exportación

**Branch**: `004-no-verifactu` | **Date**: 2026-10-03 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/004-no-verifactu/spec.md`

## Summary

Joyería Blanco funciona en modalidad **No VERI\*FACTU** (constitución 2.4.0): no envía nada a la
AEAT y, a cambio, cumple los arts. 6 a 9, 14 y 15 de la Orden HAC/1177/2024.

- **Registros firmados**: cada registro de alta y de anulación se genera en XML (F-15), se valida
  contra el XSD y se firma con XAdES-EPES (F-14 y F-18, mediante `signxml`) **antes de insertarlo**,
  en la misma transacción.
- **Sin certificado no hay emisión**: no se emite ni se consume número.
- **Anomalía en la cadena**: ya no bloquea la emisión. Se anota y salta la alarma (F-4, p. 28).
- **Registro de eventos** (F-17): una cadena propia, inalterable y firmada, con inicio y fin por
  arranque, resumen cada 6 horas, detección de anomalías y exportaciones.
- **Comprobación de integridad** bajo demanda, con alarma visible para todos y navegación por la
  cadena (art. 7.h).
- **Exportación** en ZIP, con cada registro tal como se firmó.
- **Configuración**: modalidad fija, estado del certificado y «Acerca del sistema» con la
  declaración responsable de Joyería Blanco como productora.

Las decisiones están en [research.md](research.md), de R-1 a R-16.

## Technical Context

**Language/Version**: Python 3.13 (backend) y TypeScript 5 con React 19 (web), como en 001–005.

**Primary Dependencies**:
- Backend, lo existente: FastAPI, SQLAlchemy 2 (async, psycopg 3), Alembic, Pydantic 2,
  pydantic-settings, Typer y WeasyPrint.
- Backend, **dependencias nuevas**: `signxml` 5.1, que trae `lxml` y `cryptography`, para el
  XML, la validación XSD, PKCS#12 y XAdES.
- Web: Vite, TanStack Router y Query, React Aria, react-hook-form con zod, y openapi-fetch.

**Storage**:
- PostgreSQL 18. Migración `0009_no_verifactu.py`:
  - columnas de firma en `registros_facturacion`;
  - tablas `registros_evento` y `comprobaciones_integridad`, de solo inserción, con triggers y
    REVOKE.
- El certificado, fuera de la BD: un PKCS#12 montado como *secret* de Docker.

**Testing**:
- pytest contra PostgreSQL real, con certificados de prueba generados en los tests.
- Validación XSD con `lxml` y verificación de firmas con `XAdESVerifier`.
- Pruebas `lento` para los volúmenes de 20.000 registros.
- Vitest + MSW y Playwright.

**Target Platform**: servidor Linux con Docker (API con 2 *workers* uvicorn, BD y Caddy) y
navegadores de escritorio y móvil.

**Project Type**: aplicación web (monorepo `backend/` + `joyeriablanco_web/`).

**Performance Goals**:
- Emisión con firma: p95 por debajo de 1 s (SC-007).
- Exportación de 20.000 registros en menos de 1 minuto (SC-005).
- Comprobación completa de 20.000 en menos de 3 minutos (SC-006).

**Constraints**:
- Nada de UPDATE ni DELETE en registros y eventos: la firma va antes del INSERT.
- Formatos solo de fuentes oficiales, con su SHA-256.
- La contraseña y la clave privada nunca salen del proceso.
- Sin conexión a servicios externos: ni AEAT, ni OCSP, ni TSA.

**Scale/Scope**: 5 historias, unos 34 requisitos funcionales, 2 tablas nuevas, unas 8 rutas nuevas
de la API y 2 pantallas nuevas, más 3 pantallas de 002 ampliadas.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio / restricción (v2.4.0) | Cómo se cumple | Estado |
|---|---|---|
| **I. SDD** | La rama se creó a mano desde `main`. Enmienda 2.4.0, specify con 5 decisiones previas, una parada normativa (capacidad de remisión) resuelta por el responsable y clarify con 4 preguntas, cada fase con su commit. Siguen checklist, tasks, analyze e implement | ✅ |
| **II. Integridad monetaria** | Las sumas de cuotas e importes de los eventos 08 y 10 se calculan con `NUMERIC` en SQL y se formatean con `domain/huella.format_amount`. Ningún `float` | ✅ |
| **III. Inalterabilidad** | `registros_evento` y `comprobaciones_integridad`, de solo inserción, con REVOKE y triggers que paran también a `jb_owner`. En `registros_facturacion`, la firma va en el mismo INSERT (R-4): no hay UPDATE posible ni necesario | ✅ |
| **IV. Verifactu por diseño** | Formatos de F-14 a F-17, citados con su URL, versión y SHA-256. La firma XAdES-EPES va antes de insertar. Registro de eventos y requisitos de los arts. 6 a 9 de la Orden. La modalidad sigue siendo un campo y una opción de configuración. VERI\*FACTU no se puede elegir, sin cambiar el modelo | ✅ |
| **V. Capas** | XML y huella de los eventos, puros en `domain/`. Firma, certificado, eventos, integridad y exportación, en `services/`. Routers finos y esquemas separados | ✅ |
| **VI. Servidor como fuente de verdad** | Los recuentos y las sumas de los eventos y de la exportación los calcula el servidor. La web solo muestra | ✅ |
| **VII. Tests obligatorios** | Los de 002 y 005 en verde, más los de 2.4.0: firma de registros, cadena y firma de eventos (con concurrencia) y validación XSD | ✅ |
| **VIII. Español en el dominio** | Tablas (`registros_evento`, `comprobaciones_integridad`), rutas (`/v1/registro-fiscal/...`), errores (`sin-registros`) y UI en español. Los nombres de los nodos XML son los oficiales | ✅ |
| **IX. Calidad automatizada** | ruff y mypy estricto. `signxml` y `lxml` tipados o con *stubs*. ESLint, typecheck, Prettier y `check:tokens` | ✅ |
| **Restricción «PDF»** | La declaración responsable en PDF usa WeasyPrint y la sección «Paper» (003) | ✅ |
| **Sistema de diseño** | Solo componentes y tokens existentes. Alarma en `danger` y aviso en `warning`, siempre con texto. Sin enmienda de DESIGN.md | ✅ |
| **Numeración** | Sin cambios. Los eventos llevan su propia secuencia, que no es una serie de facturación | ✅ |

**Re-check tras el diseño** (research, data-model, contracts y quickstart): sin violaciones. Hay
cuatro decisiones que conviene vigilar:
- **Cambio de comportamiento de 002 (R-5)**: en No VERI\*FACTU, la comprobación previa ya no
  bloquea la emisión. Lo exige la FAQ oficial (F-4, p. 28) y lo cubren los tests de 002
  actualizados.
- **Riesgo normativo**: sin capacidad de remisión. Lo asume el responsable y está documentado en
  la spec.
- **Dependencias nuevas** (`signxml`, `lxml` y `cryptography`): hay que comprobar que la imagen de
  producción (*read-only*, no root) construye y funciona.
- **Ampliación de los contratos de 002**: los esquemas marcados «ampliado en 004».

## Project Structure

### Documentation (this feature)

```text
specs/004-no-verifactu/
├── plan.md              # Este fichero
├── research.md          # R-1 a R-16, fuentes F-2, F-4, F-8, F-10 y F-14 a F-20
├── data-model.md        # Migración 0009, tablas nuevas, enumeraciones y ajustes
├── quickstart.md        # Validación manual y producción
├── contracts/
│   ├── openapi.yaml     # Operaciones nuevas (alarmas, sistema, registro fiscal)
│   ├── exportacion.md   # Formato del ZIP
│   └── ui-rutas.md      # Pantallas y comportamientos
├── checklists/          # requirements.md (+ los de /speckit-checklist)
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── alembic/versions/0009_no_verifactu.py      # columnas de firma, registros_evento, comprobaciones_integridad
├── app/
│   ├── core/config.py                          # + CERTIFICADO_*, SIF_PRODUCTOR_DIRECCION, SIF_DECLARACION_*
│   ├── domain/
│   │   ├── tipos.py                            # + TipoEventoSif, TipoAnomalia, EstadoRemision.NO_APLICA
│   │   ├── huella.py                           # + CamposHuellaEvento (F-2 §3.c)
│   │   ├── xml_registro.py                     # nuevo: XML de alta, anulación y evento (R-1)
│   │   └── eventos.py                          # nuevo: contenido de cada tipo de evento
│   ├── models/registro_evento.py, comprobacion_integridad.py, registro_facturacion.py (+columnas)
│   ├── repositories/eventos.py, comprobaciones.py, registros.py (+consultas por rango)
│   ├── services/
│   │   ├── certificado.py                      # nuevo: carga del PKCS#12 y su estado (R-6)
│   │   ├── firma.py                            # nuevo: XSD y XAdES-EPES (R-2, R-3)
│   │   ├── cadena.py                           # + firma antes de insertar (R-4) y anomalía sin bloqueo (R-5)
│   │   ├── eventos_sif.py                      # nuevo: generación de eventos y líder (R-7, R-8)
│   │   ├── integridad.py                       # + firmas, eventos, rango y alarma (R-9 a R-11)
│   │   ├── exportacion.py                      # nuevo: ZIP (R-12)
│   │   ├── sistema.py                          # nuevo: declaración responsable (R-13)
│   │   ├── configuracion_facturacion.py        # + certificado, modalidad fija (R-14)
│   │   └── datos_ejemplo.py                    # no_verifactu y certificado de prueba
│   ├── api/v1/registro_fiscal.py, alarmas.py, sistema.py   # nuevos
│   ├── schemas/registro_fiscal.py, sistema.py  # nuevos; factura.py y configuracion (+ampliados)
│   ├── resources/aeat/xsd/                     # F-15, F-16, F-17, F-20 + README con SHA-256
│   ├── resources/pdf/declaracion.html          # declaración en «Paper»
│   ├── lifespan.py                             # + inicio, resumen periódico y fin (líder)
│   └── cli.py                                  # verificar-cadena ampliado, exportar-registros, generar-certificado-pruebas
└── tests/
    ├── unit/domain/test_xml_registro.py, test_huella_evento.py
    └── integration/test_firma_registros.py, test_eventos_sif.py, test_integridad_anomalias.py,
        test_exportacion.py, test_sistema.py, test_alarmas.py, test_no_verifactu_rendimiento.py (lento)

joyeriablanco_web/src/
├── features/registro-fiscal/                   # nuevo: eventos, cadena, comprobar, exportar
├── features/sistema/AcercaPage.tsx             # nuevo
├── components/layout/BandaAlarma.tsx           # nuevo
├── features/configuracion/FacturacionPage.tsx  # + certificado, modalidad fija
├── features/facturas/HistorialFactura.tsx      # + firmado
├── routes/_app/registro-fiscal.tsx, acerca.tsx
└── api/queries/registroFiscal.ts, sistema.ts, alarmas.ts
joyeriablanco_web/e2e/registro-fiscal.spec.ts, acerca.spec.ts

deploy/  docker-compose.prod.yml (secret del certificado), verificar-produccion.sh (+certificado)
docs/declaraciones/                              # PDF de la declaración de cada versión (RRSIF 13.3)
```

**Structure Decision**: el monorepo existente. Lo nuevo sigue la arquitectura en capas de 002 y
005, y se amplía lo de 002 (cadena, integridad, configuración y consulta de factura) sin duplicarlo.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Proceso líder con cerrojo consultivo de sesión para los eventos de inicio, fin y resumen | Hay 2 *workers* en producción, y los eventos del art. 9.1.a y b y del 9.2 no pueden duplicarse | Generarlos en cada *worker* duplica eventos. Un servicio aparte de planificación añade otro contenedor que vigilar |
| Eventos en su propia transacción | Un evento de anomalía o de exportación no debe perderse si se deshace la operación que lo originó | Hacerlo en la misma transacción: la anomalía detectada antes de una emisión fallida desaparecería |
