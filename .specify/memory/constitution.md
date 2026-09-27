<!--
SYNC IMPACT REPORT
==================
Cambio de version: 1.0.0 -> 1.1.0
Motivo del bump: MINOR. Se anade una restriccion nueva (Sistema de diseno) y se amplia
materialmente la guia de revision de artefactos. No se elimina ni redefine ningun principio.

Principios modificados: ninguno (I-IX se mantienen sin cambios de fondo).

Secciones anadidas:
  - Restricciones tecnicas > "Sistema de diseno" (nueva restriccion). Hace normativo
    docs/DESIGN.md ("Haute Joaillerie Atelier") para toda interfaz de usuario, fija la
    precedencia DESIGN.md > mockups y exige justificar por escrito cualquier desviacion.

Secciones ampliadas:
  - Flujo de trabajo y puertas de calidad, punto 5: la revision de spec/plan/tasks
    comprueba tambien la conformidad con docs/DESIGN.md en las features con UI.
  - Governance > Cumplimiento: misma verificacion; docs/DESIGN.md queda como documento
    normativo subordinado a esta constitucion, con cambios sujetos a aprobacion explicita.

Secciones eliminadas: ninguna.

Artefactos dependientes:
  - docs/DESIGN.md                  actualizado: movido desde temporal/DESIGN.md y corregida su
                                    incoherencia interna (mandan los tokens del frontmatter, como
                                    el mockup; se anaden success/warning/danger). Aprobado por el
                                    responsable el 2026-09-27. Ver su Changelog 1.1.
  - CLAUDE.md                       actualizado: estructura del monorepo + seccion "Interfaz de usuario"
  - .specify/templates/*.md         sin cambios: leen la constitucion en tiempo de ejecucion

Historico: 1.0.0 (2026-09-12) adopcion inicial con los principios I-IX.

TODO pendientes (no bloquean la ratificacion, se resuelven en el clarify de su feature):
  - TODO(MODALIDAD_VERIFACTU): elegir entre VERI*FACTU y no VERI*FACTU. El principio IV
    exige que el diseno soporte ambas, por lo que la eleccion no altera esta constitucion.
  - TODO(DECLARACION_RESPONSABLE): determinar quien la suscribe (art. 13 RRSIF). Pendiente
    de confirmacion por la asesoria.
-->

# Constitución de Joyería Blanco

Sistema de gestión de Joyería Blanco. Fase 1: facturación y presupuestos.

## Core Principles

### I. Desarrollo dirigido por especificación (SDD) — NO NEGOCIABLE

Ninguna línea de código se escribe fuera de `/speckit.implement` sobre un `tasks.md` aprobado.

Cada feature DEBE recorrer el ciclo completo, sin saltarse pasos:
`specify → clarify → plan → checklist → tasks → analyze → implement`.

`clarify` y `analyze` NO son opcionales en este proyecto: la facturación tiene reglas fiscales y de
negocio con demasiada ambigüedad como para prescindir de esas puertas de calidad.

Entre fase y fase se PARA y se espera revisión humana. No se encadenan comandos sin que el artefacto
anterior haya sido aprobado.

Si durante `implement` aparece algo que contradice la spec, se DETIENE la implementación y se corrige
la spec primero, nunca al revés.

Cada feature vive en `specs/NNN-nombre-feature/` con su rama propia y se cierra con sus tests en
verde antes de abrir la siguiente. Spec Kit NO crea ramas: se crean a mano con
`git checkout -b NNN-nombre-feature` antes de invocar `/speckit.specify`.

**Razón**: el coste de un error fiscal en producción es incomparablemente mayor que el de una fase
de especificación lenta.

### II. Integridad monetaria

Todo importe es `Decimal` de extremo a extremo y `NUMERIC` en PostgreSQL. `float` está PROHIBIDO en
cualquier punto de la cadena, incluida la serialización JSON.

La política de redondeo se define UNA sola vez y se aplica de forma idéntica en todo el sistema.

El tipo de IVA se guarda a nivel de línea, para soportar facturas con tipos mixtos; la cabecera
almacena los totales agregados por tipo.

**Razón**: un céntimo de descuadre por aritmética binaria invalida una factura y es indefendible
ante una inspección.

### III. Inalterabilidad de los documentos emitidos — REQUISITO LEGAL

No es una preferencia de diseño: lo impone el reglamento.

Una factura emitida y su registro de facturación NO se editan ni se borran. La prohibición se
impone a nivel de BASE DE DATOS (triggers/reglas y privilegios), no solo en la capa de aplicación.

Las correcciones se realizan mediante factura rectificativa, registro de anulación o registro de
subsanación.

Los presupuestos SÍ son editables mientras estén en estado `borrador`.

**Razón**: una restricción que solo vive en el código de aplicación se salta con un `UPDATE` manual
en una consola de base de datos.

### IV. Cumplimiento Verifactu por diseño

Conforme a RD 1007/2023 (RRSIF), RD 254/2025, RD-ley 15/2025 y Orden HAC/1177/2024.

Cada factura emitida genera un registro de facturación de alta con huella SHA-256, encadenada con la
huella del registro anterior.

Los formatos, longitudes de campo, orden de concatenación del hash y parámetros del QR se toman
EXCLUSIVAMENTE de la documentación técnica oficial de la AEAT y se CITAN en la spec con su URL y la
versión del documento. Lo que no se pueda verificar en fuente oficial se marca como pregunta
abierta: NUNCA se deduce de memoria ni se copia de blogs, foros o notas de asesoría.

La modalidad (VERI\*FACTU / no VERI\*FACTU) es un campo del registro y una opción de configuración,
NO una bifurcación del modelo de datos. El diseño DEBE soportar ambas y permitir el cambio de una a
otra sin rehacer migraciones.

Nota normativa verificada en fuente oficial (BOE, 2026-09-12): en modalidad VERI\*FACTU el
art. 16.3 RRSIF exime de la firma electrónica de los registros, y el art. 3 de la Orden
HAC/1177/2024 exime de los arts. 6 y 8 y del registro de eventos del art. 9 de dicha Orden. En
modalidad no VERI\*FACTU esos requisitos SÍ aplican, incluida la firma XAdES Enveloped conforme a
ETSI EN 319 132 (art. 14 de la Orden).

**Razón**: el cumplimiento no se añade al final. Condiciona el esquema desde la primera migración,
sobre tablas que por definición no admiten reescritura.

### V. Arquitectura en capas

`routers → services → repositories/modelos`. CERO lógica de negocio en los routers.

Esquemas Pydantic separados para entrada y para salida. JAMÁS se expone un modelo ORM directamente
en la API.

**Razón**: la lógica fiscal debe ser testable sin levantar HTTP, y el contrato de la API no puede
quedar acoplado a la forma de las tablas.

### VI. El servidor es la fuente de verdad de los cálculos

El front NUNCA envía totales. Puede previsualizar importes para dar respuesta inmediata al usuario,
pero la fuente de verdad es la API: el servidor calcula y devuelve subtotales, cuotas y totales.

**Razón**: los importes que se registran y se remiten a la AEAT no pueden depender de aritmética
ejecutada en un navegador.

### VII. Cobertura de test obligatoria

Son de cobertura obligatoria, y ninguna feature que los afecte se cierra sin ellos:

- Numeración correlativa bajo concurrencia, sin huecos ni reutilización.
- Cálculo de importes y redondeos.
- Encadenamiento de huellas Verifactu.
- Conversión presupuesto → factura.

Una fase del plan no se da por cerrada sin sus tests en verde.

**Razón**: son exactamente los cuatro puntos donde un fallo es silencioso en desarrollo y grave en
producción.

### VIII. Español en el dominio

Nombres de tablas, columnas, rutas de la API, mensajes de error y UI, en español.

Nombres de variables y funciones en el código, en inglés, salvo términos de dominio
(`factura`, `presupuesto`, `huella`, `cliente`).

**Razón**: el dominio es fiscal español; traducir sus términos introduce ambigüedad al contrastar
con la norma.

### IX. Calidad automatizada

`ruff` para lint y formato; `mypy` en modo estricto. El backend NO se da por válido si no pasan
ambos.

Commits atómicos y descriptivos.

## Restricciones técnicas

**Backend**: Python 3.13 gestionado con `uv`, FastAPI, SQLAlchemy 2.0 (declarativo tipado),
Pydantic v2, Alembic para migraciones, `pytest` con base de datos de test aislada.

**Ejecución**: todo el backend (API + base de datos) corre en Docker. `docker-compose.yml` para
desarrollo con servicio `api`, servicio `db` (PostgreSQL con volumen persistente) y variables por
`.env`, con `.env.example` versionado.

**PDF**: WeasyPrint (plantilla HTML + CSS).

**Web**: React con TypeScript y Vite.

**Sistema de diseño**: toda interfaz de usuario del proyecto (la web ahora, y cualquier otra UI
cuando entre en alcance) DEBE cumplir el sistema de diseño "Haute Joaillerie Atelier" definido en
`docs/DESIGN.md`. Eso incluye:

- Tokens de color.
- Tipografías: Bodoni Moda para titulares y cifras destacadas, Manrope para texto operativo y datos.
- Escala de espaciado y rejilla.
- Esquinas a 0 px.
- Elevación por planos y filetes de 1 px, sin más sombras que las que el propio documento define.
- Especificación de componentes.

Esos valores se definen UNA sola vez como tokens centralizados y se consumen desde ahí; no se
repiten como literales dispersos por el código.

Los mockups y capturas de referencia son orientativos. Ante un conflicto, mandan `docs/DESIGN.md`
y las decisiones registradas en la spec de la feature, nunca el mockup. Ejemplo: en la feature 001
la navegación lateral va a la izquierda aunque el mockup de clientes la muestre a la derecha.

Cualquier desviación de `docs/DESIGN.md` se justifica por escrito en la spec de la feature. Si la
desviación pasa a ser general, o si se detecta una incoherencia interna en el propio documento, se
corrige `docs/DESIGN.md` con aprobación del responsable del proyecto. Nunca se resuelve sobre la
marcha en el código.

**Numeración**: correlativa por año natural y por serie, sin huecos y sin reutilización, segura
frente a concurrencia mediante secuencia de base de datos o bloqueo explícito sobre una tabla de
contadores. Queda PROHIBIDO `MAX(numero)+1` sin lock. La estrategia elegida se justifica en la spec
de la feature correspondiente.

**Precios**: las líneas se introducen sin IVA (base imponible); el servidor calcula cuota y total.

## Flujo de trabajo y puertas de calidad

1. El ciclo SDD del principio I es obligatorio y completo para cada feature.
2. Se PARA entre fase y fase a esperar revisión humana del artefacto generado.
3. Ninguna feature se cierra sin sus tests en verde.
4. Ante contradicción entre el código y la spec, MANDA LA SPEC: se detiene la implementación, se
   corrige la especificación y se reanuda desde ahí.
5. Toda revisión de `spec.md`, `plan.md` y `tasks.md` verifica el cumplimiento de esta constitución
   y, en las features con interfaz de usuario, la conformidad con `docs/DESIGN.md`.

## Governance

Esta constitución PREVALECE sobre cualquier otra práctica, convención o preferencia del proyecto.

**Enmiendas**: requieren documentación del cambio, aprobación explícita del responsable del proyecto
y versionado semántico:

- **MAJOR**: cambio incompatible, redefinición o eliminación de un principio.
- **MINOR**: nuevo principio o nueva sección, o ampliación material de la guía existente.
- **PATCH**: aclaraciones, redacción, correcciones sin cambio de fondo.

**Cumplimiento**: toda revisión de artefactos (`spec.md`, `plan.md`, `tasks.md`) debe verificar la
conformidad con esta constitución y, en las features con interfaz de usuario, con `docs/DESIGN.md`.
Cualquier desviación debe justificarse por escrito en el artefacto correspondiente.

`CLAUDE.md`, en la raíz del repositorio, es la guía operativa de desarrollo del día a día y está
subordinado a esta constitución.

`docs/DESIGN.md` es la especificación normativa del sistema de diseño y está subordinado a esta
constitución. Sus cambios materiales requieren aprobación explícita del responsable del proyecto.

**Version**: 1.1.0 | **Ratified**: 2026-09-12 | **Last Amended**: 2026-09-27
