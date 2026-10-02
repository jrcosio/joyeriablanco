# Research — 005 Presupuestos con conversión en factura

**Fecha**: 2026-10-02 · **Spec**: [spec.md](spec.md)

Cada decisión sigue el formato **Decisión** · **Razón** · **Alternativas descartadas**.

Esta feature no añade formatos fiscales: un presupuesto no genera registros (FR-005), y la factura
convertida es una emisión normal de 002. La única fuente nueva es F-13, que fija qué NO lleva el
presupuesto. Se mantiene la numeración de fuentes de 002 y 003:

| Id | Documento | Versión / fecha | Consulta |
|---|---|---|---|
| F-4 | AEAT, *Aclaraciones a dudas de los desarrolladores*, aclaración 6 | 1.3 (04/12/2025) | 002, research (SHA-256 allí) |
| F-6 | RD 1619/2012 (ROF), BOE-A-2012-14696 | texto consolidado | BOE, 2026-10-02: no regula presupuestos ni proformas; art. 14, duplicados |
| F-13 | AEAT, FAQ VERI\*FACTU, «Cuestiones generales: conceptos y definiciones», pregunta sobre «Pre-Facturación» | página actualizada el 22/07/2026 | 2026-10-02 (HTML, sin hash estable; citas literales en la spec) |

**Punto de partida verificado en el código** (rama `005-presupuestos`, sobre `main` con 003
fusionada):
- `services/borradores.emit_borrador` toma en este orden:
  1. El cerrojo de la cadena (`registros.lock_chain`).
  2. La idempotencia, con `EMITIR_BORRADOR` y el borrador como origen.
  3. El borrador, con `FOR UPDATE`.
  4. `emision.emit_factura(..., cadena_bloqueada=True)`.

  Después borra el borrador.
- `repositories/contadores.py` está tipado con `Serie` y su `CHECK` en la BD es literal
  (`serie IN ('FAC','REC')`, migración 0005).
- Las migraciones usan literales en sus `CHECK`, nunca `sql_in(Enum)`. Así, ampliar una
  enumeración no cambia las migraciones anteriores.

---

## R-1. Modelo de datos: tablas propias, no generalizar las de factura

**Decisión**: tablas propias, copiadas del patrón de facturas, sin mezclarlas con las fiscales:
- `borradores_presupuesto` y `lineas_borrador_presupuesto`: mutables.
- `presupuestos`, `lineas_presupuesto`, `desgloses_presupuesto` y `cierres_presupuesto`: de solo
  inserción.

Todo en la migración `0008_presupuestos` (data-model).

**Razón**:
- `facturas` y su desglose llevan columnas y `CHECK` que solo tienen sentido para Verifactu:
  `tipo_factura`, rectificativa, `clave_regimen`, calificación y modalidad. Meter ahí los
  presupuestos contaminaría el perímetro fiscal, la vista del listado de facturas y
  `verificar-cadena`.
- Las copias del emisor y del destinatario usan los mismos nombres de columna (`emisor_*` y
  `dest_*`). Así, la composición del PDF las trata igual (R-9).

**Alternativas descartadas**:
- Una tabla `documentos` con un discriminador: exigiría rehacer los `CHECK` y los triggers de 002,
  sobre tablas que no admiten reescritura.
- Reutilizar `borradores_factura` para los borradores de presupuesto: el borrador vinculado de la
  conversión (R-5) ya es un borrador de factura, y confundir los dos haría ambiguo el listado de
  facturas.

## R-2. Inalterabilidad del presupuesto emitido en la BD

**Decisión**: las cuatro tablas de solo inserción siguen el bucle de la 0005:
- `REVOKE UPDATE, DELETE, TRUNCATE` a `jb_app`.
- Triggers `<tabla>_sin_modificaciones` y `<tabla>_sin_truncate`, que paran también a `jb_owner`.
- Una función propia, `impedir_modificacion_presupuesto()`, con el mensaje «Los presupuestos
  emitidos son inalterables» y el mismo `ERRCODE` (`insufficient_privilege`).

**Razón**: lo exige la constitución 2.3.0 (principio III), que apoya en F-13 la conservación de
los documentos preparatorios «debidamente vinculada». Con una función propia, el mensaje no dice
«documentos de facturación» de algo que no lo es.

**Alternativas descartadas**: protegerlo solo en la aplicación, lo que contradice el principio III.

## R-3. Estado derivado y caducidad

**Decisión**:
- `public.estado_presupuesto(uuid)` es una función SQL `STABLE` y la ÚNICA implementación del
  estado guardado. Devuelve, por orden:
  1. El tipo del cierre, si lo hay: `anulado`, `sustituido` o `convertido`.
  2. `en_facturacion`, si existe un `borradores_factura` con ese `presupuesto_id`.
  3. `pendiente` en otro caso.
- **«Caducado» no va en SQL.** Lo calcula `domain/presupuestos.estado_visible(estado, valido_hasta,
  hoy)` con `hoy()` en `settings.zona_horaria`: un `pendiente` con `valido_hasta < hoy` se muestra
  `caducado`. En los filtros y el orden del listado no interviene, así que no hace falta en SQL.
  - En el listado y en los totales del listado impreso, el repositorio pasa `hoy` como parámetro
    para contar o marcar los caducados.
  - `en_facturacion` prevalece sobre la caducidad (FR-001).

**Razón**:
- Es el patrón de `estado_factura()` (002, R-8): sin columnas mutables y con una sola
  implementación.
- La caducidad depende del día. Calculada en la BD con `now()` usaría el huso del servidor de la
  BD, no el de la aplicación.

**Alternativas descartadas**:
- Una columna `estado`: el presupuesto es de solo inserción.
- Un trabajo nocturno que marque los caducados: genera escrituras y auditoría de algo que no es
  una operación (spec, casos límite).

## R-4. Numeración PRE

**Decisión**:
- Se amplía `ck_contadores_factura_serie` a `('FAC', 'REC', 'PRE')`. Se añade
  `Serie.PRESUPUESTO = "PRE"` y `_FORMATO = (FAC|REC|PRE)-…` en `domain/numeracion.py`. Los
  mensajes de error pasan a decir «documento».
- `repositories/contadores.assign_numero` se usa **sin cambios**: inserta la fila (serie, año),
  la bloquea con `SELECT … FOR UPDATE` y la avanza en la misma transacción que el presupuesto. Si
  algo falla, el rollback deshace el avance.
- El año es el de la fecha del presupuesto. Respeta `ck_contadores_factura_anio` (≥ 2024), porque
  la fecha mínima es el 28/10/2024 (FR-008).
- **Sin ajuste**: `adjust_counter` sigue fijado a `Serie.ORDINARIA` y su esquema de salida a
  `Literal["FAC"]`.
- `presupuestos` lleva `ck_presupuestos_serie CHECK (serie = 'PRE')` y el mismo `CHECK` de formato
  de `num_serie` que facturas, restringido a `PRE`.

**Razón**:
- Mismas garantías que FAC (constitución 2.3.0) con el mecanismo ya probado bajo concurrencia
  (002, `test_numeracion_concurrencia.py`).
- El trigger `contador_solo_al_alza` y la prohibición de borrar el contador ya protegen la fila PRE.
- El nombre `contadores_factura` se queda como está: renombrarla tocaría la 0005. El data-model
  documenta que guarda también la serie PRE.

**Alternativas descartadas**:
- Una tabla `contadores_presupuesto`: duplica el repositorio, los triggers y los tests.
- Una secuencia de BD: deja huecos si se deshace la transacción, y la constitución exige que no
  los haya.

## R-5. Conversión mediante un borrador de factura vinculado (Clarifications, clarify)

**Decisión**: en dos pasos, y cada uno en una transacción.

**1. `POST /v1/presupuestos/{id}/conversion`** (`services/conversion.create_borrador_conversion`):
1. Toma `presupuestos.lock_presupuestos(db)`, un `pg_advisory_xact_lock` con clave constante (R-6).
2. Lee el presupuesto y su estado. Si tiene un cierre, responde 409 `presupuesto-no-modificable`.
3. Si ya está en facturación, devuelve **200** con su borrador. Una repetición o un doble clic no
   crean otro.
4. Si no, crea un `BorradorFactura` con:
   - `presupuesto_id`, y el cliente, las líneas y `oro_inversion` del presupuesto;
   - la fecha de hoy y el IVA vigente como previsto, como cualquier borrador.

   Lo audita como `borrador_factura_creado`, con el presupuesto de origen en el detalle, y
   devuelve **201** con `BorradorSalida`.

   El borrador se crea **directamente** con el `cliente_id` del presupuesto, sin pasar por
   `_check_cliente` de `services/borradores.py`, aunque el cliente se haya desactivado después.
   La emisión lo rechazará con `cliente-no-facturable` hasta que se cambie o se reactive (US3-8).

   No exige la configuración emisible ni un cliente facturable: un borrador se guarda incompleto
   (002, FR-019), y eso se comprueba al emitir.

**2. Emisión del borrador**, con `POST /v1/borradores-factura/{id}/emision` (002). En
`services/borradores.emit_borrador`, si el borrador tiene `presupuesto_id`:
1. **Antes de emitir**, comprueba que la fecha de expedición no es anterior a la del presupuesto.
   Si lo es, responde 422 `fecha-expedicion` en el campo, como el resto de límites (FR-019).
2. Emite con `emision.emit_factura` sin cambios: el número FAC, la copia, el registro y la huella
   son los de siempre.
3. En la misma transacción, `conversion.close_conversion` inserta el cierre `conversion` con la
   factura y audita `presupuesto_convertido`.
4. Borra el borrador.

- **Idempotencia**: la de `emit_borrador`, que ya existe (`EMITIR_BORRADOR`, con el borrador como
  origen). Una repetición devuelve la misma factura, aunque el borrador ya no exista. No hace falta
  ningún valor nuevo en `ck_facturas_operacion_idempotencia`.
- **El aviso del IVA cambiado** es el del borrador (`tipo_iva_previsto` frente al vigente, 002,
  casos límite). El modal lo muestra sin código nuevo.

**Razón**:
- Es lo que eligió el responsable: revisar antes de emitir.
- Reutiliza **íntegro** el camino fiscal de 002 (validaciones, cerrojos e idempotencia), y la
  única pieza nueva en la transacción de emisión es una inserción.
- El vínculo inalterable se crea al emitir la factura, que es cuando existe el documento al que
  vincularse (F-13).

**Alternativas descartadas**:
- Crear el cierre al crear el borrador: el borrador se puede borrar, y quedaría un presupuesto
  «convertido» sin factura.
- Exigir `Idempotency-Key` en la conversión: la unicidad del borrador vinculado ya hace que la
  operación sea idempotente por sí misma.

## R-6. Concurrencia y cerrojos

**Decisión**:
- **Por qué un cerrojo consultivo**: `jb_app` no tiene UPDATE sobre `presupuestos`, y PostgreSQL
  lo exige para `SELECT … FOR UPDATE`. Toda operación que emite o cierra un presupuesto toma
  **primero** `lock_presupuestos`, un `pg_advisory_xact_lock` con una clave constante («JBPRES»):
  emitir, emitir un borrador, modificar, anular y convertir. Con el volumen de la joyería, un
  cerrojo global no compite.
- **El cerrojo va antes de buscar la clave de idempotencia**, igual que `lock_chain` en 002. Si no,
  dos peticiones simultáneas con la misma clave pasarían las dos la búsqueda: en la emisión directa
  chocarían con `uq_presupuestos_clave_idempotencia` y, desde un borrador, la segunda recibiría un
  404.
- **Orden fijo de cerrojos**, sin ciclos posibles:

  | Operación | Cerrojos, en orden |
  |---|---|
  | Emitir un presupuesto | `lock_presupuestos` → clave → contador PRE |
  | Emitir un borrador de presupuesto | `lock_presupuestos` → clave → borrador de presupuesto `FOR UPDATE` → contador PRE |
  | Modificar | `lock_presupuestos` → clave → estado → contador PRE |
  | Anular | `lock_presupuestos` → clave → estado |
  | Convertir (crear el borrador) | `lock_presupuestos` → estado |
  | Emitir el borrador vinculado (002) | cadena → clave → borrador de factura `FOR UPDATE` → contador FAC |

  La emisión del borrador vinculado no toma `lock_presupuestos`: no puede competir con una
  anulación ni con una modificación, porque estas se rechazan mientras el borrador exista. Las
  barreras siguientes lo garantizan en la BD.
- **Barreras en la BD**, que valen aunque la aplicación fallara:
  - `cierres_presupuesto.presupuesto_id` es `UNIQUE`: como mucho, un cierre.
  - `borradores_factura.presupuesto_id` es `UNIQUE`: como mucho, un borrador vinculado.
  - Trigger `validar_cierre_presupuesto` (BEFORE INSERT en `cierres_presupuesto`): rechaza una
    anulación o una sustitución si existe un borrador vinculado (FR-021).
  - Trigger `validar_vinculo_presupuesto` (BEFORE INSERT o UPDATE de `presupuesto_id` en
    `borradores_factura`): rechaza el vínculo con un presupuesto que ya tiene cierre.
  - Los dos triggers lanzan `check_violation` con `USING CONSTRAINT = 'tg_cierres_presupuesto_en_facturacion'`
    y `'tg_borradores_factura_presupuesto_cerrado'`. Así, `core/errors.py` traduce por el nombre
    de la restricción, igual que las unicidades, y no por el texto del mensaje.
- **Orden de lectura** en anular y modificar: primero se mira si hay borrador vinculado y después
  si hay cierre. En `READ COMMITTED`, si la emisión del borrador termina entre las dos lecturas, la
  segunda ve su cierre.
- **El perdedor de una carrera** recibe 409 `presupuesto-no-modificable`, traducido desde la
  violación de unicidad o desde el trigger, y su transacción se deshace entera: sin números
  consumidos.

**Razón**: así se cumplen FR-020, FR-021, FR-028 y el SC-003 sin depender del orden de llegada.

**Alternativas descartadas**:
- Dar UPDATE a `jb_app` para poder usar `FOR UPDATE`: debilita la inalterabilidad.
- Un cerrojo por presupuesto (`hashtext(id)`): es más complejo y no aporta nada con este volumen.

## R-7. Emisión, modificación y anulación del presupuesto

**Decisión**: `services/presupuestos.py`, con la forma de `services/emision.py`.

- **Idempotencia, común a todas las operaciones**: `find_previous_presupuesto(db, clave, operacion,
  origen)`.
  - Busca la clave en `presupuestos.clave_idempotencia` (`emitir`, `emitir_borrador` y
    `modificar`) y en `cierres_presupuesto.clave_idempotencia` (`anular`).
  - Si la encuentra con la misma operación y el mismo origen, devuelve el resultado previo. Si
    la encuentra con otra operación o con otro origen, responde 409 `idempotencia-conflicto`.
  - El ámbito es el de los presupuestos. Las claves de facturas y correcciones las sigue
    comprobando `emision.find_previous`. Cada modal genera su propia clave UUID, así que no se
    cruzan.
- **`emit_presupuesto`**:
  1. `lock_presupuestos` (R-6).
  2. Idempotencia: `find_previous_presupuesto`, con la operación `emitir`, `emitir_borrador` o
     `modificar` y su origen.
  3. Comprobaciones:
     - los datos del emisor completos, con un nuevo `missing_for_presupuesto` que no pide la
       modalidad (FR-011); si faltan, 409 `emision-no-disponible` con `faltan`;
     - el cliente activo; si no, 422 `cliente-no-facturable` con `faltan: ["activo"]`;
     - al menos una línea y un total mayor que cero;
     - la fecha entre el 28/10/2024 y hoy, y la validez no anterior a la fecha (422 `validacion`
       en el campo).
  4. Cálculo con `domain/importes.compute_totals` y el IVA vigente.
  5. Número PRE.
  6. Copia de las partes (R-8).
  7. Inserción de la cabecera, las líneas y el desglose.
  8. Evento `presupuesto_emitido`.

  `emit_presupuesto` recibe un parámetro `bloqueado=True` cuando el cerrojo ya lo tomó quien lo
  llama, igual que `cadena_bloqueada` en 002.
- **`modify_presupuesto`** (solo `AdminSession`):
  1. `lock_presupuestos`.
  2. `find_previous_presupuesto` con la operación `modificar` y el original como origen. Si hay
     una petición previa, se devuelve el presupuesto nuevo que creó, **antes de mirar el estado**:
     tras la primera, el original ya está sustituido.
  3. Estado `pendiente` o `caducado`, sin borrador vinculado (R-6, orden de lectura).
  4. **«Sin cambios»** (Clarifications, analyze): se responde 422 `sin-cambios` si coinciden:
     - el cliente, tal como quedaría copiado, comparado con la copia del original;
     - las líneas (unidades, descripción y precio, en su orden);
     - la casilla de oro de inversión;
     - el tipo de IVA que se aplicaría;
     - «Válido hasta».

     **La fecha no cuenta**, porque el modal propone la de hoy. Es la regla de `_sin_cambios` de
     002 con la validez añadida.
  5. Emisión del nuevo con `emit_presupuesto(…, operacion=modificar, origen=original,
     bloqueado=True)`.
  6. Cierre `sustitucion` con `motivo_texto` y el presupuesto nuevo.
  7. Evento `presupuesto_modificado`.
- **`annul_presupuesto`** (solo `AdminSession`):
  1. `lock_presupuestos`.
  2. `find_previous_presupuesto` con `anular` y el presupuesto como origen. Si hay una petición
     previa, se devuelve el presupuesto ya anulado.
  3. Estado `pendiente` o `caducado`, sin borrador vinculado.
  4. Cierre `anulacion` con su motivo y su clave.
  5. Evento `presupuesto_anulado`.
- **Borradores de presupuesto** (`services/borradores_presupuesto.py`): copia de
  `services/borradores.py` con `valido_hasta`, con versión optimista, conflicto y borrado
  auditado. La emisión sigue el orden `lock_presupuestos` → clave (`emitir_borrador`) → borrador
  `FOR UPDATE` → `emit_presupuesto(…, bloqueado=True)` → borrado del borrador.

**Razón**:
- Es el ciclo de 002 sin la parte fiscal. Las mismas respuestas de error permiten reutilizar en la
  web el tratamiento de errores del modal.
- Buscar la clave antes de mirar el estado es lo que hace que una repetición devuelva el mismo
  resultado (FR-028) en vez de un 409.

**Alternativas descartadas**:
- Abstraer la emisión de factura y de presupuesto en un servicio genérico: el camino fiscal (cadena,
  registro y huella) quedaría detrás de una abstracción y sería más difícil de auditar.

## R-8. Lo que se generaliza antes de empezar (fase fundacional)

**Decisión**: se extrae, **sin cambiar el comportamiento**, lo que comparten los dos documentos.
Las suites de 002 y 003 deben pasar antes y después:

1. **`app/services/contenido.py`** (nuevo), con lo que hoy está en `emision.py` y `borradores.py`:
   - `DatosLinea` y `check_lineas`.
   - `normalize_lineas`, el antiguo `_normalizar`.
   - `previstos`, que calcula los totales con su error de rango.
   - `copia_emisor(config)` y `copia_destinatario(cliente)`, que devuelven los valores de las
     columnas `emisor_*` y `dest_*`.

   `emision.py` reexporta `DatosLinea` para no tocar sus llamadas.
2. **`app/repositories/listado.py`** (nuevo): `filtros(v, …)`, `ordenes(v)` y `consulta_filas(v,
   columnas, …)`, parametrizados con la vista (`table()`). `repositories/facturas.py` los usa con
   `v_listado_facturas`, y `repositories/presupuestos.py`, con `v_listado_presupuestos`, que tiene
   las mismas columnas más `valido_hasta`.
3. **Impresión**:
   - **`app/services/impresion_comun.py`**, con las piezas genéricas de `services/impresion.py`:
     - `DocumentoPdf`, `ParteImpresa`, `ContactoImpreso`, `LineaImpresa` y `DesgloseImpreso`.
     - `domicilio`, `contacto` y `desglose_impreso`.
     - `emisor` y `destinatario`, tipados con un `Protocol` `CopiaPartes` que cumplen `Factura` y
       `Presupuesto`. Sus miembros son `@property` de solo lectura, y los de domicilio son
       `str | None`: así mypy estricto acepta los dos, aunque la factura tenga el domicilio
       obligatorio y el presupuesto no (invarianza de los atributos mutables).
   - **`resources/pdf/_documento.html`**, con las macros de la cabecera del emisor, el cliente, la
     tabla de líneas, los totales, el pago y el pie. `factura.html` las usa y conserva su QR.
   - **`papel.css`**:
     - `@page factura` pasa a `@page documento` y `.numero-factura` a `.numero-documento`.
     - `body.doc-factura` y `body.doc-presupuesto` usan esa página.
     - Se añade `.aviso-no-fiscal` (R-10).
   - **`listado.html`**: sus textos fijos («Listado de facturas», «No hay facturas con este
     filtro», «Totales de las facturas vigentes», el texto de las filas excluidas y el pie) pasan
     al modelo `l.textos`.
4. **`core/pdf/respuestas._mensaje`**: el texto de «no existe» y el enlace de vuelta dependen de
   la ruta. Con `/api/v1/presupuestos/…` dice «El presupuesto no existe.» y enlaza a
   `/presupuestos`.

**Razón**: así no se duplica la lógica de líneas, del listado ni del PDF. Se hace en una fase
propia, con su commit, para que una regresión en facturas se vea aislada (riesgo principal del
plan).

**Alternativas descartadas**:
- Copiar los módulos enteros: dos implementaciones del redondeo previsto, del filtro y del
  formato impreso que acabarían divergiendo.

## R-9. Copia de las partes y datos que se imprimen

**Decisión**:
- Al emitir, el presupuesto guarda `emisor_*` (IBAN incluido) y `dest_*` con las mismas columnas y
  la misma función de copia que la factura (`contenido.copia_*`, FR-010).
- El contacto (teléfono, correo y web) y el pie no se copian. Al imprimir se leen de la
  configuración vigente, como en 003.
- **Pie**: `pie_presupuesto` si lo hay; si no, `pie_factura` (FR-031).

**Razón**: un presupuesto entregado debe poder reimprimirse tal como se entregó, igual que una
factura.

**Alternativas descartadas**: leer la ficha del cliente al imprimir, lo que alteraría lo entregado.

## R-10. PDF del presupuesto

**Decisión**:
- **Composición**: `services/impresion_presupuestos.py → build_presupuesto_impreso(db, id, *,
  iban)` compone un `PresupuestoImpreso`:
  - `titulo = "PRESUPUESTO"` y `aviso_no_fiscal = "Documento sin validez fiscal. No es una
    factura."`.
  - Número, fecha, `valido_hasta`, emisor y destinatario de la copia, contacto, líneas, desglose,
    totales, mención de exención, IBAN opcional y pie.
  - Marcas: «ANULADO», «SUSTITUIDO por {PRE vigente}» o «CONVERTIDO en {FAC}». Para
    «CONVERTIDO» se usa la factura del cierre, no su vigente: el presupuesto se convirtió en esa.
  - **No tiene campo `qr`**, así que mypy impide pintarlo.
- **Plantilla**: `resources/pdf/presupuesto.html` extiende `base.html` y usa las macros de
  `_documento.html`. No incluye el bloque del QR ni ninguna frase VERI\*FACTU.
  - La leyenda va en `.aviso-no-fiscal`, justo bajo el título: `print-body-strong` en `paper-ink`,
    dentro de un marco de 1 px en `paper-rule` (DESIGN.md 1.3).
  - Las marcas, en `paper-alert`, como en la factura.
- **Rutas**:
  - `GET /v1/presupuestos/{id}/pdf?iban=` devuelve `PRE-AAAA-NNNN.pdf`. Un borrador responde 404,
    igual que en 003.
  - `GET /v1/presupuestos/listado/pdf`, declarada antes de `/{id}`, devuelve
    `presupuestos-{anio}[-{mes}].pdf` o `presupuestos-todos.pdf`.
- **Generación**: con los limitadores de 003, que se reutilizan sin renombrar: `LIMITE_FACTURAS`
  para el documento y `LIMITE_LISTADOS` para el listado.

**Razón**: cumple FR-029 y SC-007. Que el modelo no tenga `qr` garantiza en el tipo que el
presupuesto nunca lleve QR (F-13).

**Alternativas descartadas**:
- Reutilizar `FacturaImpresa` con `qr=None`: dejaría la posibilidad en el tipo y en la plantilla.
- Una marca de agua «PRESUPUESTO»: DESIGN.md prohíbe las marcas de agua.

## R-11. Listado en pantalla y listado impreso

**Decisión**:
- **Vista `v_listado_presupuestos`** (`UNION ALL` de borradores y presupuestos). Tiene las columnas
  de `v_listado_facturas` más `valido_hasta`:
  - En los borradores, `tipo_documento = 'borrador'`, `estado = 'borrador'` y el cliente de la
    ficha.
  - En los emitidos, `estado = estado_presupuesto(id)` y el cliente de la copia.
- **Filtros, órdenes y paginación**: los de `repositories/listado.py` (R-8). En el listado, el
  servicio aplica `estado_visible` con `hoy` para marcar los caducados.
- **Totales del listado impreso** (FR-030): suman los de estado guardado `pendiente`,
  `en_facturacion` o `convertido`. Los caducados son pendientes, así que entran. Se cuentan aparte
  los borradores, los sustituidos y los anulados. El desglose por tipo de IVA se agrupa sobre
  `desgloses_presupuesto`, con la misma SQL que `totales_vigentes`.
- **Límite**: el mismo de 003, 5.000 filas (`ListadoDemasiadoGrande`).
- **Rendimiento** (SC-008): índices como los de facturas:
  - `ix_presupuestos_fecha`.
  - Un índice trigram GIN sobre `texto_busqueda`, generado con la misma expresión que facturas.
  - `ix_presupuestos_cliente`.
  - `ix_borradores_presupuesto_cliente`.

  Se mide con 20.000 presupuestos sintéticos en el test lento.

**Razón**: el responsable pidió las mismas funcionalidades, y compartir el repositorio garantiza
la misma búsqueda.

**Alternativas descartadas**: un filtro por estado, fuera de alcance (spec).

## R-12. API, permisos y errores

**Decisión**:
- **Rutas**: las del contrato [`contracts/openapi.yaml`](contracts/openapi.yaml). Hay dos routers
  nuevos, `api/v1/presupuestos.py` y `api/v1/borradores_presupuesto.py`, finos y sin lógica
  (constitución V).
- **Permisos**:
  - `CurrentSession`: listar, consultar, crear y editar borradores, emitir, imprimir y convertir.
  - `AdminSession`: `…/modificacion` y `…/anulacion`.
  - La configuración sigue en su router de administración.
- **Idempotencia**: `Idempotency-Key` en las operaciones que emiten o cierran (emitir, emitir el
  borrador, modificar y anular). La conversión no la necesita (R-5).
- **Errores nuevos**: solo `presupuesto-no-modificable` (409). Lleva `estado`, el estado visible,
  y, si está en facturación, `borrador_factura_id`.
- **Errores que se reutilizan**: `emision-no-disponible`, `cliente-no-facturable`, `sin-cambios`,
  `conflicto-version`, `idempotencia-conflicto`, `listado-demasiado-grande`, `validacion`,
  `no-encontrado` y `fecha-expedicion`. Este último solo en la emisión del borrador vinculado.
- **Ampliaciones de 002**, que siguen en su contrato con la marca «ampliado en 005»:
  - `BorradorSalida.presupuesto_origen` y `FacturaSalida.presupuesto_origen`, de tipo
    `PresupuestoReferencia | null`.
  - `ConfiguracionFacturacionEntrada` y `ConfiguracionFacturacionSalida` ganan
    `validez_presupuesto_dias` y `pie_presupuesto`. En la entrada son opcionales: si faltan, se
    conservan, como en 003, R-9.
- **Contrato**: `test_contrato_openapi.py` compara la API con la unión de contratos. Se amplía
  `test_hay_un_contrato_por_feature` con `005-presupuestos`.

**Razón**: es el patrón de 002 y 003. Con un solo error nuevo, la web trata los demás como ya lo
hace.

## R-13. Web

**Decisión**:
- **`src/features/documentos/`** (nuevo): recibe de `features/facturas/` lo que es del documento
  y no de la factura:
  - `LineasDocumento` (antes `LineasFactura`, tipado con `Control<{ lineas: ValorLinea[] }>`).
  - `TotalesDocumento`, `SelectorCliente`, `ResumenCliente` (con el texto del aviso por props),
    `CargandoModal`, `AvisoCambioIva` y `EnlaceImprimir`.
  - `documento-valores.ts`: `ValorLinea`, el esquema zod de línea, `lineasCuerpo`,
    `lineasCalculo`, `campoDelServidor` y `etiquetaCliente`.
  - `FiltrosDocumentos`, con `placeholder` y `aria-label` por props, y el esquema zod de búsqueda
    (`q`, `anio`, `mes`, `orden` y `pagina`), que hoy es una constante local de
    `routes/_app/facturas.tsx`. Pasa a `src/lib/filtros-documentos.ts`.
  - `ImprimirListado`, con el documento, los textos y la URL por props.
  - `TablaDocumentos`, con las celdas de número y acción por props y los mismos anchos medidos.

  Es un movimiento sin cambio de comportamiento, en la fase fundacional, con los tests de facturas
  en verde.
- **`CamposFactura`**: sigue siendo de facturas. El presupuesto tiene su `CamposPresupuesto`, con
  «Válido hasta». Los dos usan `CamposDocumento`, una sección de datos con hueco para campos
  extra.
- **Ciclo de vida**: se copia `FormularioFactura` a `FormularioPresupuesto`, sin abstraerlo en un
  hook genérico (R-7).
- **`features/presupuestos/`** (nuevo):
  - `PresupuestosPage`, `PresupuestoModal` (nuevo y borrador) y `PresupuestoConsulta`, con su
    historial.
  - `ConvertirPresupuestoDialog`, `ModificarPresupuestoModal` y `AnularPresupuestoDialog`.
  - `ImprimirPresupuesto` (casilla IBAN) y `MarcaPresupuesto` (chip). El listado impreso usa el
    `ImprimirListado` de `features/documentos/`.
- **Rutas** (`routes/_app/presupuestos*`): las de [`contracts/ui-rutas.md`](contracts/ui-rutas.md).
  Tras convertir, se navega a `/facturas/borradores/$borradorId` con el aviso.
- **Queries**: `api/queries/presupuestos.ts` y `borradoresPresupuesto.ts`.
  - La conversión invalida presupuestos, facturas y clientes, y siembra el borrador en la caché.
  - La emisión de un borrador de factura invalida también `PRESUPUESTOS_KEY`, porque puede cerrar
    un presupuesto.
  - Eliminar un borrador de factura también la invalida, porque puede devolver un presupuesto a
    pendiente.
- **Facturas**: el borrador y la consulta de una factura muestran «Procede del presupuesto
  PRE-…» con un enlace (`EnlacePresupuesto`).
- **`lib/impresion.ts`**: la base por tipo de documento.
- **Otros**:
  - `Sidebar.tsx`: «Presupuestos» con `to: '/presupuestos'`. Desaparece la rama «Próximamente» si
    queda sin uso.
  - `features/auditoria/tipos-evento.ts`: los eventos nuevos.
  - `FacturacionPage`: «Validez de los presupuestos (días)» y «Pie de presupuesto».

**Razón**: se reutiliza lo que es igual y se copia lo que difiere en textos, mutaciones y reglas.
Las suites de facturas vigilan que el movimiento no cambie nada.

## R-14. Estrategia de pruebas (constitución VII)

**Decisión**:
- **Obligatorias**:
  - **Numeración PRE bajo concurrencia** (`test_numeracion_presupuestos.py`, con commit real como
    en 002):
    - 10 sesiones × 20 emisiones dan los números 1 a 200 sin huecos.
    - Con emisiones FAC en paralelo, las dos series son independientes.
    - Una emisión que falla no consume número.
    - La misma clave en paralelo da un solo presupuesto.
    - Modificar consume el siguiente número.
    - El cambio de año reinicia el correlativo.
  - **Importes**:
    - Los totales del presupuesto y del borrador cuadran con `compute_totals`, también con oro de
      inversión y en los límites.
    - Con el mismo IVA, la factura convertida coincide al céntimo con su presupuesto.
    - Con el IVA cambiado, la misma base y la cuota recalculada.
  - **Conversión** (`test_conversion_presupuesto.py`):
    - El borrador sale precargado.
    - 20 conversiones simultáneas dan un solo borrador.
    - 20 emisiones simultáneas de ese borrador dan una sola factura, y el contador FAC y la cadena
      crecen en uno.
    - En una carrera entre conversión y anulación gana una sola, y el trigger y la unicidad
      responden también sin la aplicación.
    - Al borrar el borrador, el presupuesto vuelve a pendiente.
    - Una fecha anterior a la del presupuesto da 422.
    - Un cliente no facturable o sin modalidad no consume número.
    - La factura muestra su origen.
  - **Encadenamiento**: con conversiones intercaladas entre emisiones, anulaciones y rectificativas,
    `services/integridad` informa de una cadena íntegra.
- **Otras**:
  - Inalterabilidad: 42501 para `jb_app` y el trigger para `jb_owner` en las cuatro tablas.
  - Estado y caducidad con `hoy` simulado.
  - Borradores: versión y borrado.
  - Modificar y anular: permisos, `sin-cambios` y estados.
  - Listado y búsqueda.
  - PDF con pypdf:
    - Lleva «PRESUPUESTO», la leyenda literal, «Válido hasta», las marcas, el IBAN opcional y el
      pie propio o el de factura.
    - No lleva `<svg`, «QR tributario», `FRASE_VERIFACTU` ni ninguna dirección `aeat.es` o
      `agenciatributaria`.
  - Listado impreso con sus totales.
  - Configuración: validación, auditoría y conservación.
  - Un cliente con presupuestos no se borra.
  - Logs sin datos personales.
  - Datos de ejemplo.
  - Ida y vuelta de la migración.
  - Contrato.
- **Web**: Vitest + MSW para el ciclo del modal, las acciones según el estado y el rol, la
  conversión y sus invalidaciones, la marca «Procede del presupuesto», el Sidebar y
  `lib/impresion`.
- **E2E**:
  - `presupuestos.spec.ts`: crear, emitir, imprimir, convertir, emitir la factura, comprobar los
    enlaces, y modificar y anular como administrador.
  - `presupuestos-listado.spec.ts`.
  - Se actualizan `acceso.spec.ts` (sin «Próximamente»), `acciones-visibles`, `responsive` y
    `teclado`.
- **Rendimiento** (marca `lento`): el listado con 20.000 presupuestos (SC-008) y el PDF de un
  presupuesto de 20 líneas.

**Razón**: cubre los cuatro tests obligatorios (la spec, Assumptions) y SC-001 a SC-012.
