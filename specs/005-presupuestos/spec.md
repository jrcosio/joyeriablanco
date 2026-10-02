# Feature Specification: Presupuestos con conversión en factura

**Feature Branch**: `005-presupuestos`

**Created**: 2026-10-02

**Status**: Draft

**Input**: Descripción del responsable del proyecto (2026-10-02): "Nueva feature, la de presupuestos...
exactamente todas las funcionalidades de las facturas, es lo mismo; lo único, que al imprimir tiene
que poner PROFORMA / Presupuesto o algo así. Busca cuál es la forma más correcta."

**Referencias**:
- Constitución 2.3.0: principios II, III, IV, V, VI, VII y VIII y restricciones «Numeración»,
  «PDF» y «Sistema de diseño». La enmienda 2.3.0 (2026-10-02) fija el ciclo de vida del
  presupuesto y la serie `PRE`.
- Sistema de diseño normativo: [`docs/DESIGN.md`](../../docs/DESIGN.md), con su sección «Paper»,
  que ya prevé los presupuestos impresos («and, later, estimates»).
- Features previas:
  - [`specs/001-cimientos-clientes`](../001-cimientos-clientes/spec.md): clientes, roles,
    auditoría y datos de ejemplo.
  - [`specs/002-facturas`](../002-facturas/spec.md): borrador, emisión, numeración, listado,
    modal, correcciones e idempotencia. Esta feature replica su comportamiento.
  - [`specs/003-pdf-impresion`](../003-pdf-impresion/spec.md): PDF de factura, listado impreso,
    contacto y pie.
  - La 001 y la 002 dejaron para esta feature la entrada «Presupuestos» del menú y que los
    presupuestos cuenten como documentos del cliente (001, FR-037; 002, FR-041 y FR-042).
- La numeración 004 queda reservada para la remisión a la AEAT (002, «Fuera de alcance»).
- Sin mockup: la pantalla replica la de facturas, y el documento impreso, la sección «Paper».

## Clarifications

### Session 2026-10-02 (decisiones previas a la especificación)

- Q: ¿Qué denominación lleva el documento impreso: «Factura proforma» o «Presupuesto»? → A:
  **«PRESUPUESTO»**, con la leyenda «Documento sin validez fiscal. No es una factura.» y la fecha
  «Válido hasta».
  - El presupuesto es una oferta previa a la aceptación, con validez limitada. Es el documento de
    los encargos, las reparaciones y las piezas a medida de una joyería.
  - La proforma anticipa una factura de una operación ya pactada (anticipos, aduanas,
    financiación), y su nombre invita a confundirla con una factura.
  - Ni el ROF ni el RRSIF regulan uno ni otro (F-6). La AEAT trata la proforma y el borrador como
    documentos preparatorios sin QR tributario (F-13).
- Q: ¿Qué ciclo de vida sigue un presupuesto? → A: **El de la factura** (constitución 2.3.0,
  principio III):
  - Borrador sin número, editable y borrable.
  - Emisión con número definitivo, desde la que el presupuesto es inalterable.
  - «Modificar» crea un presupuesto nuevo que sustituye al anterior y lo conserva.
  - «Anular» lo cierra con un motivo.
  - «Convertir en factura» lleva su contenido a una factura ordinaria (Session clarify).
- Q: ¿Cómo se numeran? → A: Serie propia **`PRE-AAAA-NNNN`**, correlativa por año, sin huecos ni
  reutilización y con la misma asignación segura que las facturas, sin ajuste al alza
  (constitución 2.3.0, «Numeración»).
- Q: ¿El presupuesto lleva QR tributario, la mención VERI\*FACTU o registro de facturación? → A:
  **No**, nunca (F-13; constitución 2.3.0). Solo la factura que resulta de la conversión los lleva,
  como cualquier factura.

### Session 2026-10-02 (clarify)

- Q: ¿«Convertir en factura» emite la factura directamente o crea un borrador de factura? → A:
  **Crea un borrador de factura** vinculado al presupuesto y precargado con su cliente, sus líneas
  y su tratamiento del IVA. Se revisa, se puede editar y se emite con el flujo normal de la factura
  (002, FR-019 a FR-021). El presupuesto queda convertido al emitir esa factura (FR-018 a FR-020).
- Q: ¿Qué pasa con el presupuesto mientras existe ese borrador? → A: **Queda bloqueado**.
  - Se muestra «En facturación» y no se puede modificar, anular ni volver a convertir.
    «Convertir en factura» abre ese mismo borrador.
  - Pasa a «Convertido en FAC-…» al emitir la factura, en la misma operación.
  - Si el borrador se elimina, el presupuesto vuelve a estar pendiente (o caducado).
- Q: ¿Se puede convertir un presupuesto caducado? → A: **Sí**, con un aviso de que la validez ha
  vencido.
- Q: ¿Quién puede modificar, anular y convertir? → A: **Como en facturas**. Cualquier usuario
  crea, emite, imprime y convierte, porque convertir es preparar y emitir una factura, y los
  empleados ya emiten. Solo los administradores modifican y anulan.
- Q: ¿Cómo se fija la validez por defecto y qué pie lleva el presupuesto impreso? → A: **30 días**
  por defecto, configurables de 1 a 365 y editables en cada presupuesto. El presupuesto tiene un
  **pie propio** y opcional (condiciones, variación del precio del oro…). Si está vacío, lleva el
  pie de factura (FR-031).

### Session 2026-10-02 (plan)

Decisiones técnicas del plan que fijan detalles del comportamiento descrito (research R-5, R-6,
R-10 y R-12):

- Q: ¿Cómo se evita que «Convertir en factura» cree dos borradores? → A: un presupuesto admite un
  único borrador vinculado, y una conversión repetida devuelve el que ya existe (FR-018, FR-028).
  No hace falta clave de operación.
- Q: ¿Qué responde el sistema si se intenta modificar o anular un presupuesto cerrado o en
  facturación, o convertir uno cerrado? → A: un aviso único, «el presupuesto ya ha cambiado», con
  su estado actual y, si está en facturación, el acceso a su borrador (FR-017, FR-021). Convertir
  uno que ya está en facturación no es un error: abre su borrador (FR-018).
- Q: ¿Qué número muestran las marcas «SUSTITUIDO por» y «CONVERTIDO en»? → A: «SUSTITUIDO por»
  muestra el último presupuesto de la cadena de sustituciones, y «CONVERTIDO en», la factura que
  se emitió en la conversión. Si esa factura se corrigió después, la consulta enlaza además la
  vigente (FR-017, FR-029).
- Q: ¿Qué tono tiene cada marca en pantalla? → A:
  - Borrador y en facturación, ámbar.
  - Caducado, rojo.
  - Convertido, verde.
  - Sustituido y anulado, neutro.

  Se escribe en `docs/DESIGN.md` 1.3 junto con el aviso no fiscal y las marcas del papel
  («Conformidad con el sistema de diseño»).

### Session 2026-10-02 (analyze)

- Q: Al «Modificar», ¿qué cuenta como cambio para no rechazarlo con «no hay cambios»? → A:
  **Contenido y validez**. Cuentan los datos del cliente tal como se copiarían, las líneas, la
  casilla de oro de inversión, el tipo de IVA que se aplicaría y «Válido hasta». La fecha sola no
  cuenta, porque el modal propone la de hoy. Es la regla de las rectificativas de 002, con la
  validez añadida (FR-015).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Crear, emitir y consultar presupuestos (Priority: P1)

Un empleado abre Presupuestos en el menú lateral y pulsa «Nuevo presupuesto». Se abre un modal
igual que el de la factura: elige al cliente, añade las líneas con las unidades, la descripción y
el precio sin IVA, y ve la base, el IVA y el total. Revisa la fecha de validez que propone el
sistema. Puede guardarlo como borrador o emitirlo. Al emitirlo recibe su número `PRE-AAAA-NNNN` y
aparece en el listado, donde se busca y se filtra igual que una factura.

**Why this priority**: sin presupuestos emitidos no hay nada que imprimir ni que convertir. Es la
base de la feature.

**Independent Test**: con el emisor configurado y un cliente activo, se crea un presupuesto de
varias líneas, se guarda como borrador, se edita y se emite. Hay que comprobar el número asignado,
los importes calculados por el servidor, que no se ha generado ningún registro de facturación y que
el presupuesto emitido ya no se puede editar.

**Acceptance Scenarios**:

1. **Given** el listado de presupuestos, **When** se pulsa «Nuevo presupuesto», **Then** se abre
   un modal sobre el listado con tres secciones:
   - Datos del presupuesto: número en solo lectura («Se asigna al emitir»), fecha, «Válido hasta»
     y cliente.
   - Detalle: las líneas.
   - Totales.

   La fecha propuesta es la de hoy y «Válido hasta» propone la fecha de hoy más la validez por
   defecto.
2. **Given** una línea con 2 unidades a 45,00 € y otra con 1 unidad a 1.200,00 €, **When** se
   rellenan, **Then** el modal previsualiza una base imponible de 1.290,00 €, un IVA (21 %) de
   270,90 € y un total de 1.560,90 €, igual que en una factura.
3. **Given** un presupuesto completo, **When** se pulsa «Emitir presupuesto» y se confirma el aviso
   de que después no se podrá editar, **Then** recibe el siguiente número de la serie del año de su
   fecha (p. ej. `PRE-2026-0001` si es el primero del año) y aparece en el listado. No se genera
   ningún registro de facturación, y el contador de facturas no cambia.
4. **Given** dos usuarios que emiten presupuestos a la vez, **When** ambas emisiones terminan,
   **Then** tienen números consecutivos distintos, sin huecos ni duplicados.
5. **Given** un presupuesto a medias, **When** se pulsa «Guardar borrador», **Then** se guarda sin
   número y aparece en el listado con la marca «Borrador». Se puede abrir, cambiar, volver a guardar,
   emitir o eliminar, y eliminarlo no consume ningún número.
6. **Given** un presupuesto emitido, **When** se abre desde el listado, **Then** el modal lo muestra
   en modo consulta, con sus datos, su fecha de validez y su historial. No hay ningún campo
   editable.
7. **Given** presupuestos de varios años, **When** se abre Presupuestos, **Then** aparecen los del
   año en curso, primero los más recientes, con las columnas del listado de facturas. Se busca por
   número, cliente o identificación, y se filtra por año y mes.
8. **Given** un presupuesto emitido cuya fecha de validez ya ha pasado, **When** aparece en el
   listado o se consulta, **Then** lleva la marca «Caducado».
9. **Given** un cliente que todavía no está en la cartera, **When** se pulsa «Nuevo cliente» junto
   al selector, **Then** se da de alta sin salir del modal y vuelve elegido, como en la factura.
10. **Given** una línea «Lingote de oro 100 g» y la casilla «Sin IVA (oro de inversión)» marcada,
    **When** se emite, **Then** el presupuesto lleva la base exenta, un IVA de 0,00 € y la mención
    de la exención, igual que una factura de oro de inversión.

---

### User Story 2 - Imprimir un presupuesto (Priority: P1)

Desde la consulta de un presupuesto emitido, el empleado pulsa «Imprimir» y, si quiere, marca
«Incluir número de cuenta». En una pestaña nueva se abre el presupuesto en PDF, con el aspecto de
una factura de la joyería pero titulado «PRESUPUESTO». Lleva la leyenda de que no tiene validez
fiscal y la fecha hasta la que es válido. No lleva QR tributario.

**Why this priority**: el presupuesto impreso es lo que recibe el cliente. Además, es lo que pidió
expresamente el responsable: que no se confunda con una factura.

**Independent Test**: se emite un presupuesto de varias líneas y se imprime. Hay que comprobar que
el PDF lleva el título, la leyenda, la validez y todo el contenido, y que no lleva QR, la frase
VERI\*FACTU ni la dirección de cotejo.

**Acceptance Scenarios**:

1. **Given** la consulta de `PRE-2026-0003`, emitido a «María López García», **When** se pulsa
   «Imprimir», **Then** se abre en una pestaña nueva un PDF A4 con:
   - el título «PRESUPUESTO»;
   - la leyenda «Documento sin validez fiscal. No es una factura.»;
   - el número, la fecha y «Válido hasta: dd/mm/aaaa»;
   - los datos de la joyería, con el logotipo y el contacto, y los del cliente;
   - las líneas, el desglose por tipo de IVA y los totales;
   - el pie configurado, si lo hay.
2. **Given** ese PDF, **When** se revisa, **Then** no contiene ningún código QR, ni «QR tributario»,
   ni la frase «Factura verificable en la sede electrónica de la AEAT», ni «VERI\*FACTU», ni ninguna
   dirección de la AEAT.
3. **Given** un presupuesto con IBAN, **When** se marca «Incluir número de cuenta» y se imprime,
   **Then** el PDF lleva el bloque de pago con el IBAN. Sin marcarla, no lo lleva.
4. **Given** un presupuesto anulado, sustituido o convertido, **When** se imprime, **Then** lleva la
   marca «ANULADO», «SUSTITUIDO por PRE-…» o «CONVERTIDO en FAC-…» en la primera página.
5. **Given** un borrador de presupuesto, **When** se consulta, **Then** no ofrece «Imprimir».

---

### User Story 3 - Convertir un presupuesto en factura (Priority: P1)

El cliente acepta el presupuesto `PRE-2026-0003`. El empleado lo abre y pulsa «Convertir en
factura». Se crea un borrador de factura con el cliente, las líneas y el tratamiento del IVA del
presupuesto, y se abre en el modal de la factura con la indicación «Procede del presupuesto
PRE-2026-0003». El empleado lo revisa, cambia lo que haga falta y lo emite como cualquier factura:
`FAC-2026-0012`, con su registro de alta, su huella y su QR. En esa misma operación, el presupuesto
queda «Convertido en FAC-2026-0012», y la factura sigue indicando que procede de él.

**Why this priority**: es la razón de ser del presupuesto en el sistema y uno de los cuatro tests
de cobertura obligatoria de la constitución (principio VII).

**Independent Test**: se convierte un presupuesto y se emite el borrador resultante. Hay que
comprobar lo siguiente:
- La factura tiene su contenido, el siguiente número FAC y su registro de alta encadenado.
- El presupuesto queda convertido, y los dos documentos se enlazan en ambos sentidos.
- Convertir dos veces, o a la vez desde dos sesiones, produce un solo borrador.
- Emitir ese borrador dos veces, o a la vez, produce una sola factura.

**Acceptance Scenarios**:

1. **Given** el presupuesto pendiente `PRE-2026-0003`, **When** se pulsa «Convertir en factura» y
   se confirma, **Then**:
   - Se crea un borrador de factura con el cliente, las líneas (unidades, descripción y precio) y la
     casilla «Sin IVA (oro de inversión)» del presupuesto.
   - El borrador propone la fecha de hoy y el IVA vigente, como cualquier borrador.
   - Se abre en el modal de la factura con «Procede del presupuesto PRE-2026-0003».
   - No se consume ningún número y no se genera ningún registro.
2. **Given** ese borrador, **When** se emite tras confirmar, **Then**:
   - Recibe el siguiente número `FAC` del año de su fecha de expedición.
   - Se genera su registro de alta con la huella encadenada.
   - En la misma operación, `PRE-2026-0003` queda «Convertido en FAC-2026-0012».
   - El aviso es «Factura FAC-2026-0012 emitida. PRE-2026-0003 queda convertido».
3. **Given** la factura convertida, **When** se consulta, **Then** indica «Procede del presupuesto
   PRE-2026-0003», con acceso directo. El presupuesto indica «Convertido en FAC-2026-0012», con
   acceso directo a la factura.
4. **Given** un presupuesto con su borrador de factura en curso, **When** se consulta o aparece en
   el listado, **Then** lleva la marca «En facturación». No ofrece «Modificar» ni «Anular», y
   «Convertir en factura» pasa a «Abrir borrador de factura», que abre ese mismo borrador.
5. **Given** dos usuarios que pulsan «Convertir en factura» sobre el mismo presupuesto a la vez, o
   un doble clic, **When** terminan, **Then** existe un solo borrador vinculado y los dos acaban en
   él.
6. **Given** el borrador de factura de un presupuesto, **When** se elimina, **Then** el presupuesto
   vuelve a estar pendiente (o caducado) y se puede convertir, modificar o anular de nuevo.
7. **Given** un presupuesto anulado, sustituido o ya convertido, **When** se consulta, **Then** no
   ofrece «Convertir en factura», y el servidor rechaza cualquier intento de convertirlo.
8. **Given** un borrador de factura vinculado cuyo cliente se ha desactivado o no tiene el
   domicilio completo, o la configuración sin modalidad, **When** se intenta emitir, **Then** no se
   emite nada, se indica qué falta y el presupuesto sigue en facturación, igual que con cualquier
   borrador (002, FR-004 y FR-017).
9. **Given** un presupuesto emitido al 21 % y el IVA por defecto cambiado después al 22 %, **When**
   se convierte, **Then** el borrador avisa de que la factura llevará el tipo vigente, con la misma
   base y el total recalculado, como cualquier borrador (002, casos límite).
10. **Given** un presupuesto caducado, **When** se pulsa «Convertir en factura», **Then** la
    confirmación avisa de que la validez ha vencido y permite continuar.

---

### User Story 4 - Modificar o anular un presupuesto emitido (Priority: P2)

El cliente pide un cambio sobre un presupuesto ya entregado: otra pieza, otro precio o más plazo.
Un administrador pulsa «Modificar», cambia lo necesario en el mismo modal e indica el motivo. Se
emite un presupuesto nuevo con el siguiente número, que sustituye al anterior. El original se
conserva marcado como sustituido, con el enlace al nuevo. Si el cliente rechaza el presupuesto, el
administrador lo «Anula» indicando el motivo.

**Why this priority**: los presupuestos se negocian, y el sistema tiene que reflejarlo sin
sobrescribir lo que se entregó al cliente. Se puede trabajar sin ello: basta con emitir uno nuevo.

**Independent Test**: sobre un presupuesto emitido se hace una modificación y una anulación, y se
comprueba lo siguiente:
- El original sigue intacto.
- El nuevo tiene el siguiente número.
- Los dos se enlazan en el historial.
- Ningún número se ha reutilizado.

**Acceptance Scenarios**:

1. **Given** `PRE-2026-0003` pendiente, **When** un administrador pulsa «Modificar», **Then** el
   modal se abre con sus datos precargados y editables:
   - cliente, líneas, «Válido hasta» y la casilla «Sin IVA (oro de inversión)»;
   - la fecha, que propone la de hoy.

   El número no es editable.
2. **Given** esa modificación con una línea cambiada, **When** se guarda indicando el motivo,
   **Then** se emite `PRE-2026-0008` (el siguiente de la serie) con los datos nuevos.
   - `PRE-2026-0003` queda marcado «Sustituido por PRE-2026-0008».
   - `PRE-2026-0008` indica «Sustituye a PRE-2026-0003».
   - Ambos lo muestran en su historial, con el motivo, el autor y la fecha.
3. **Given** una modificación sin ningún cambio en el contenido ni en «Válido hasta», aunque la
   fecha propuesta sea la de hoy, **When** se intenta guardar, **Then** se rechaza con el aviso de
   que no hay cambios.
4. **Given** un presupuesto que el cliente rechaza, **When** un administrador pulsa «Anular» e
   indica el motivo, **Then** queda marcado «Anulado», con el motivo en su historial, y su número no
   vuelve a usarse.
5. **Given** un presupuesto sustituido, anulado o convertido, **When** se consulta, **Then** no
   ofrece «Modificar», «Anular» ni «Convertir en factura».
6. **Given** un empleado, **When** consulta un presupuesto emitido, **Then** no ve «Modificar» ni
   «Anular», y el servidor rechaza cualquier intento suyo de hacerlo.
7. **Given** un presupuesto caducado, **When** un administrador lo modifica ampliando «Válido hasta»,
   **Then** se emite el sustituto con la validez nueva, y el caducado queda sustituido.

---

### User Story 5 - Listado impreso y datos de ejemplo (Priority: P3)

En Presupuestos, un empleado filtra por un mes y pulsa «Imprimir listado». En una pestaña nueva se
abre un PDF con todos los presupuestos de ese filtro y los totales por tipo de IVA, igual que el
listado de facturas. En el entorno de desarrollo, los datos de ejemplo incluyen presupuestos en
todos los estados.

**Why this priority**: es útil para revisar la actividad comercial en papel, pero no forma parte
del flujo diario del presupuesto.

**Independent Test**: con más de 100 presupuestos que cumplen un filtro, se imprime el listado y se
comprueba que salen todos, en el orden elegido, y que los totales cuadran al céntimo con los de los
presupuestos que suman.

**Acceptance Scenarios**:

1. **Given** 130 presupuestos de marzo de 2026 y el filtro «2026, marzo», **When** se pulsa
   «Imprimir listado», **Then** el PDF contiene las 130 filas, en el orden de la pantalla y con la
   descripción del filtro en la cabecera.
2. **Given** un filtro con presupuestos en todos los estados, **When** se imprime, **Then** cada fila
   lleva su marca igual que en pantalla. Los totales por tipo de IVA y generales suman solo los que
   cuentan (FR-030) e indican cuántas filas quedan fuera y por qué.
3. **Given** un filtro sin resultados o con más de 5.000, **When** se mira el listado, **Then**
   «Imprimir listado» está desactivado con su motivo, igual que en facturas.
4. **Given** el entorno de desarrollo recién preparado, **When** se cargan los datos de ejemplo,
   **Then** hay presupuestos ficticios de varios meses: borradores, pendientes, caducados, en
   facturación (con su borrador de factura), convertidos (con su factura), sustituidos y anulados.

---

### Edge Cases

- **Cambio de año**: el primer presupuesto fechado el 1 de enero de 2027 recibe `PRE-2027-0001`.
  El año del número es siempre el de la fecha del presupuesto.
- **Series independientes**: emitir presupuestos no consume números de factura, y emitir facturas
  no consume números de presupuesto. Una conversión consume un número `FAC` y ninguno `PRE`.
- **Fallo durante la emisión, la modificación o la conversión**: la operación se deshace entera. No
  queda ningún número consumido (ni `PRE` ni `FAC`), ningún registro a medias ni ningún cambio de
  estado. El borrador o el presupuesto siguen como estaban.
- **Conversión frente a modificación o anulación simultáneas**: si un administrador anula o
  modifica un presupuesto mientras otro usuario pulsa «Convertir en factura», solo una de las dos
  operaciones tiene efecto. La otra se rechaza con el aviso de que el presupuesto ya ha cambiado.
- **Borrador de factura vinculado**:
  - Se edita como cualquier borrador, incluidos el cliente, las líneas, la fecha y la casilla de oro
    de inversión. La factura puede acabar distinta del presupuesto: eso es lo que permite revisar
    antes de emitir.
  - Su fecha de expedición no puede ser anterior a la fecha del presupuesto. Se indica en el propio
    campo, como el resto de límites de fecha (002, FR-018).
  - Si otro usuario lo emite o lo elimina a la vez, se aplican las reglas de los borradores de
    factura (002, casos límite).
- **Factura convertida que después se corrige**: la factura se anula o se rectifica como cualquier
  otra (002, FR-023 a FR-027). El presupuesto sigue convertido. Su acceso directo lleva a la
  factura que se emitió en la conversión y, si esta se corrigió, también a la vigente que la
  sustituye. Un presupuesto no se convierte dos veces.
- **Caducidad**: un presupuesto pendiente pasa a mostrarse «Caducado» el día siguiente a su fecha
  de validez, en hora de España peninsular. La caducidad no es una operación: no genera auditoría
  ni cambia el presupuesto, que se puede seguir consultando, imprimiendo, modificando, anulando y
  convirtiendo.
- **IVA cambiado entre el presupuesto y la conversión**: la factura lleva el tipo de Configuración
  vigente al emitirla (002, FR-013), con la misma base. El borrador lo avisa, como cualquier
  borrador. El presupuesto conserva el tipo con el que se emitió.
- **Presupuesto de oro de inversión**: la factura convertida también lo es, exenta (002, FR-052),
  y el cambio del IVA por defecto no le afecta.
- **Cambios en el cliente después de emitir el presupuesto**: el presupuesto conserva los datos del
  cliente tal como estaban al emitirlo. La factura convertida copia los datos de la ficha **al
  emitirse**, como cualquier factura (002, FR-016).
- **Cliente con presupuestos**: no se puede borrar, tampoco si solo tiene borradores. Se ofrece
  desactivarlo (001, FR-037).
- **Borrador de presupuesto incompleto**: puede guardarse sin cliente o sin líneas. Todo se exige al
  emitir.
- **Borrador ya emitido**: si otro usuario emite el mismo borrador, el segundo intento no emite nada
  y se informa de que ya se ha emitido.
- **Edición simultánea de un borrador**: el segundo en guardar recibe el aviso de que el borrador ha
  cambiado, como en facturas (002, FR-020).
- **Doble envío**: un doble clic o un reintento de red en «Emitir», «Modificar», «Anular» o
  «Convertir en factura» nunca genera dos documentos ni dos borradores (FR-028).
- **Usuario eliminado**: los presupuestos que emitió siguen mostrando su nombre con la marca
  «(eliminado)» (001, FR-061).
- **Validez anterior a la fecha**: «Válido hasta» no puede ser anterior a la fecha del presupuesto.
  Se indica en el propio campo.
- **Sesión caducada con el modal abierto**: igual que en facturas (002, casos límite).

## Requirements *(mandatory)*

### Functional Requirements

#### Ciclo de vida y numeración

- **FR-001**: Los presupuestos DEBEN seguir el ciclo de la factura (constitución 2.3.0,
  principio III):
  - **Borrador**: sin número, editable y borrable.
  - **Emitido**: número definitivo e inalterable.
  - **Cierre**: como mucho uno, por sustitución, anulación o conversión.

  Estado visible de un presupuesto emitido:
  - **Pendiente**: sin cierre y dentro de su validez. No lleva marca.
  - **Caducado**: sin cierre y con la fecha de validez vencida.
  - **En facturación**: pendiente o caducado, con un borrador de factura vinculado en curso
    (FR-018). Lleva esta marca en lugar de la de caducado.
  - **Convertido**: convertido en una factura.
  - **Sustituido**: sustituido por otro presupuesto.
  - **Anulado**: anulado con motivo.

  El estado se deriva de los cierres, del borrador vinculado y de la fecha, y no se guarda en el
  propio presupuesto.
- **FR-002**: La serie de presupuestos DEBE numerarse `PRE-AAAA-NNNN`:
  - `AAAA` es el año de la fecha del presupuesto.
  - `NNNN` es un correlativo de cuatro dígitos que empieza en `0001` cada año natural y crece en
    cifras si se superan los 9.999.
  - Se aplican las mismas reglas que a las facturas: asignación al emitir y dentro de la misma
    operación, segura frente a emisiones simultáneas, sin huecos ni duplicados (002, FR-006 y
    FR-007).
- **FR-003**: Un número `PRE` ya usado NO DEBE volver a usarse nunca, ni siquiera el de un
  presupuesto anulado o sustituido. El número nunca se introduce a mano: en el modal se muestra en
  solo lectura, «Se asigna al emitir» en un borrador. La serie no admite ajuste al alza.
- **FR-004**: Un presupuesto emitido y sus líneas y cierres NO DEBEN poder modificarse ni borrarse
  por ningún medio. La protección DEBE estar en el propio almacenamiento y resistir también un
  intento directo con las credenciales del servicio y con las del propietario de los datos, igual
  que las facturas (002, FR-022; constitución 2.3.0).
- **FR-005**: Un presupuesto NUNCA DEBE generar un registro de facturación ni una huella, ni
  consumir números de factura (F-13). Emitir, modificar o anular presupuestos no altera la cadena de
  registros.

#### Contenido e importes

- **FR-006**: Cada presupuesto emitido DEBE tener:
  - Fecha.
  - Fecha de validez («Válido hasta»).
  - Cliente destinatario, elegido entre los clientes activos.
  - Al menos una línea y un total mayor que cero.
  - Autor y fecha de emisión.

  Un borrador puede guardarse incompleto. Los requisitos se comprueban al emitir.
- **FR-007**: Las líneas, el IVA, los importes y el redondeo DEBEN ser exactamente los de la factura
  (002, FR-012 a FR-015 y FR-052):
  - Unidades mayores que cero, descripción obligatoria de hasta 500 caracteres y precio unitario
    sin IVA mayor o igual que cero.
  - El tipo de IVA de Configuración vigente al emitir, guardado en cada línea, o «Sin IVA (oro de
    inversión)» para todo el presupuesto.
  - El servidor calcula el importe de cada línea, la base y la cuota de cada tipo y los totales. La
    web solo previsualiza, y una petición con importes calculados se rechaza (constitución VI).
  - La misma política de redondeo única.
- **FR-008**: **Fecha**: propone la de hoy, en hora de España peninsular, y se puede cambiar.
  - **Superior**: no puede ser posterior a hoy.
  - **Inferior**: no puede ser anterior al 28/10/2024, el mismo límite que la factura (Assumptions).
  - **Error**: se indica en el propio campo y el servidor lo rechaza con un error de validación en
    ese campo, al guardar el borrador, al emitir y al modificar.
- **FR-009**: **Validez**:
  - «Válido hasta» propone la fecha del presupuesto más la validez por defecto de Configuración
    (FR-031) y se puede cambiar en cada presupuesto.
  - No puede ser anterior a la fecha del presupuesto. El error se indica en el propio campo, como el
    de la fecha (FR-008).
  - Si se cambia la fecha del presupuesto y «Válido hasta» no se ha tocado, se recalcula.
- **FR-010**: Al emitir, el presupuesto DEBE guardar una copia de los datos del emisor, IBAN
  incluido si lo hay, y del destinatario, tal como están en ese momento, igual que la factura (002,
  FR-016). Los cambios posteriores no alteran el presupuesto emitido.
- **FR-011**: Para emitir un presupuesto DEBEN estar completos los datos del emisor de
  Configuración (002, FR-001). La modalidad VERI\*FACTU no se exige, porque el presupuesto no genera
  registros. El cliente DEBE estar activo. Su domicilio no se exige: si le falta, el resumen del
  cliente avisa de que la factura convertida no se podrá emitir hasta completarlo (FR-019).

#### Borrador y emisión

- **FR-012**: Un borrador de presupuesto DEBE poder crearse, editarse y borrarse por cualquier
  usuario autenticado. No tiene número. El borrado es definitivo y queda en la auditoría.
- **FR-013**: La edición concurrente de un borrador DEBE detectarse igual que en la factura (002,
  FR-020).
- **FR-014**: Emitir DEBE pedir una confirmación que explique que el presupuesto no podrá editarse y
  que los cambios posteriores se harán con «Modificar». La emisión es atómica: el número y el
  presupuesto se guardan juntos o no se guarda nada.

#### Modificar y anular (sustitución trazable)

- **FR-015**: Solo un administrador DEBE poder «Modificar» un presupuesto pendiente o caducado que
  no esté en facturación:
  - El modal se abre con sus datos precargados.
  - Son editables el cliente, las líneas, la fecha (que propone la de hoy), «Válido hasta» y la
    casilla «Sin IVA (oro de inversión)».
  - «Válido hasta» se precarga con el del original. Si es anterior a la fecha propuesta, propone esa
    fecha más la validez por defecto.
  - Al guardar se pide un motivo de texto libre, obligatorio.
  - Se emite un presupuesto nuevo con el siguiente número `PRE`, y el original queda sustituido por
    él.
  - Si no hay ningún cambio respecto al original, se rechaza (Clarifications, analyze). Se
    comparan:
    - los datos del cliente tal como se copiarían;
    - las líneas;
    - la casilla de oro de inversión;
    - el tipo de IVA que se aplicaría;
    - «Válido hasta».

    La fecha sola no cuenta como cambio.
- **FR-016**: Solo un administrador DEBE poder «Anular» un presupuesto pendiente o caducado que no
  esté en facturación, con un motivo de texto libre obligatorio, p. ej. «Rechazado por el cliente».
  La anulación no emite nada.
- **FR-017**: El original y su cierre DEBEN conservarse intactos y enlazados en ambos sentidos:
  - El historial de cada presupuesto muestra su cierre, con el tipo, la fecha, el autor, el motivo
    si lo hay y el documento que lo materializa.
  - Un presupuesto sustituido o convertido ofrece acceso directo al documento que lo sustituye o en
    el que se convirtió.
  - Un presupuesto que sustituye a otro muestra «Sustituye a PRE-…».

  El servidor DEBE rechazar cualquier modificación o anulación que pida un empleado, cualquier
  operación sobre un presupuesto que ya tenga un cierre y la modificación o anulación de uno en
  facturación.

#### Conversión en factura

- **FR-018**: Un presupuesto pendiente o caducado DEBE ofrecer «Convertir en factura» a cualquier
  usuario autenticado. Tras una confirmación, que avisa si el presupuesto está caducado, crea un
  **borrador de factura vinculado** al presupuesto (Clarifications, clarify):
  - Precargado con el cliente, las líneas (unidades, descripción y precio) y la casilla «Sin IVA
    (oro de inversión)» del presupuesto.
  - La fecha y el IVA previsto son los de cualquier borrador nuevo: hoy y el tipo vigente.
  - No consume ningún número ni genera ningún registro.
  - Se abre en el modal de la factura, que indica «Procede del presupuesto {número}» con acceso
    directo.

  Un presupuesto tiene como mucho un borrador de factura vinculado. Si ya lo tiene, «Convertir en
  factura» pasa a «Abrir borrador de factura» y abre ese borrador. Una petición de conversión
  repetida o simultánea no crea otro.
- **FR-019**: El borrador vinculado DEBE comportarse como cualquier borrador de factura (002, FR-019
  a FR-021): se edita, se guarda, se elimina y se emite con las mismas validaciones, incluidas la
  configuración emisible y el cliente facturable (002, FR-004 y FR-017). Además, su fecha de
  expedición no puede ser anterior a la fecha del presupuesto.
- **FR-020**: La conversión DEBE quedar completa al **emitir** el borrador vinculado, de forma
  atómica y única:
  - La factura, su registro de alta y el cierre de conversión del presupuesto se guardan juntos o no
    se guarda nada.
  - Un presupuesto se convierte como mucho una vez. Si al emitir ya tiene un cierre, la emisión se
    rechaza y no se consume ningún número.
  - La emisión del borrador es idempotente y segura frente a emisiones simultáneas, como la de
    cualquier borrador (002, FR-047).
  - La conversión no altera el encadenamiento de huellas. El registro de la factura convertida es
    como el de cualquier factura emitida.
  - Si el borrador vinculado se elimina, el presupuesto vuelve a estar pendiente (o caducado), y el
    borrado queda en la auditoría.
- **FR-021**: Mientras un presupuesto está **en facturación** no se puede modificar, anular ni
  volver a convertir (FR-015 a FR-017). Una conversión simultánea a una modificación o una anulación
  del mismo presupuesto: solo una de las dos tiene efecto, y la otra se rechaza con el aviso de que
  el presupuesto ya ha cambiado.
- **FR-022**: La consulta de una factura que procede de una conversión DEBE indicar «Procede del
  presupuesto {número}», con acceso directo. El borrador vinculado lo indica también. Tras emitirlo,
  el aviso es «Factura {número} emitida. {presupuesto} queda convertido». Las correcciones
  posteriores de esa factura siguen las reglas de 002 y no cambian el presupuesto.

#### Listado y búsqueda

- **FR-023**: El listado de presupuestos DEBE comportarse igual que el de facturas (002, FR-032 a
  FR-036 y FR-049):
  - Paginación en el servidor (25 por página por defecto y 100 como máximo).
  - Búsqueda, filtros, orden y página reflejados en la dirección.
  - Acciones siempre visibles.
  - Los mismos estados de pantalla:
    - «Todavía no hay presupuestos», que invita a crear el primero.
    - «No hay presupuestos en {año}», con «Ver todos los años».
    - «No hay resultados», con «Limpiar filtros».
- **FR-024**: **Columnas**: las del listado de facturas, con los mismos anchos según la pantalla:
  número, fecha, cliente, identificación fiscal, base imponible, IVA, total y acciones.
  - No hay columna de estado.
  - Un borrador muestra «Borrador» en lugar del número.
  - Un presupuesto caducado, en facturación, convertido, sustituido o anulado lleva su marca junto
    al número. La marca es siempre un texto, no solo un color.
  - Uno de oro de inversión muestra «Exenta» en el IVA.
- **FR-025**: **Búsqueda, filtros y orden**, iguales que en facturas:
  - Búsqueda parcial por número, cliente e identificación, sin distinguir mayúsculas ni tildes.
  - Año, con el año en curso por defecto o todos, y mes.
  - Orden: más recientes, más antiguos, total mayor y total menor, con desempate estable.

#### Modal de presupuesto

- **FR-026**: Crear, consultar, editar y modificar un presupuesto DEBE hacerse en un modal por encima
  del listado, con las mismas secciones, comportamiento, accesibilidad y adaptación a móvil que el
  de la factura (002, FR-037, FR-039, FR-040, FR-046 y FR-049).
  - **Nombres accesibles**:
    - «Imprimir presupuesto {número}».
    - «Convertir en factura {número}».
    - «Abrir borrador de factura de {número}».
    - «Ver presupuesto {número}».
    - «Abrir borrador de {cliente}».
    - «Imprimir listado».
  - **Imprimir**: el estado «Preparando…» se anuncia a los lectores de pantalla (003, FR-031).
- **FR-027**: Botones del modal según el caso:
  - **Nuevo**: «Cancelar», «Guardar borrador» y «Emitir presupuesto».
  - **Borrador**: además, «Eliminar borrador».
  - **Pendiente o caducado**:
    - Todos: «Cerrar», «Imprimir» (con la casilla del número de cuenta si lo tiene) y «Convertir
      en factura».
    - Solo administradores: además, «Anular» y «Modificar».
  - **En facturación**: «Cerrar», «Imprimir» y «Abrir borrador de factura».
  - **Convertido, sustituido o anulado**: «Cerrar» e «Imprimir».

#### Operaciones seguras

- **FR-028**: Emitir, modificar y anular un presupuesto DEBEN ser **idempotentes** frente a un doble
  envío, igual que en facturas (002, FR-047):
  - La misma clave de operación devuelve el resultado de la primera petición.
  - Una clave usada en otra operación o sobre otro documento se rechaza.

  «Convertir en factura» repetido devuelve el borrador vinculado que ya existe (FR-018), y la
  emisión de ese borrador es idempotente como la de cualquier borrador (FR-020).

#### Impresión

- **FR-029**: **PDF del presupuesto**: la consulta de todo presupuesto emitido DEBE ofrecer
  «Imprimir» a cualquier usuario autenticado. Los borradores no lo ofrecen, y el servidor rechaza su
  PDF. «Imprimir» abre en una pestaña nueva un PDF en A4 vertical, cuyo nombre propuesto es el
  número, p. ej. `PRE-2026-0003.pdf`. El PDF lleva:
  - **Título**: «PRESUPUESTO», en mayúsculas. A diferencia del título «Factura», así se distingue a
    primera vista de una factura (Clarifications).
  - **Leyenda**: «Documento sin validez fiscal. No es una factura.», justo bajo el título, visible y
    sin tapar ningún dato.
  - **Datos**: el número, la fecha y «Válido hasta: dd/mm/aaaa».
  - **Emisor y cliente**: los datos fiscales de la copia guardada al emitir, el logotipo y el
    contacto vigente al imprimir (003, FR-004 y FR-005).
  - **Contenido**: las líneas, el desglose por tipo de IVA y los totales, con la mención de la
    exención si es de oro de inversión (003, FR-006 y FR-007).
  - **Número de cuenta**: la casilla «Incluir número de cuenta» funciona igual que en la factura
    (003, FR-010).
  - **Marcas** en la primera página: «ANULADO», «SUSTITUIDO por {número}» o «CONVERTIDO en
    {número}». Un pendiente, un caducado o uno en facturación no llevan marca, porque la fecha de
    validez ya se ve y el borrador de factura todavía no es una factura.
  - **Pie**: el pie de Configuración (FR-031).
  - **Páginas**: como la factura (003, FR-011). Si ocupa varias, cada página lleva el número del
    presupuesto y «Página n de m», la cabecera de la tabla de líneas se repite y una línea nunca se
    parte. El aviso no fiscal y las marcas van en la primera página.
  - **Lo que NO lleva** (F-13; constitución 2.3.0): código QR, «QR tributario», la frase
    VERI\*FACTU, dirección de cotejo de la AEAT ni la expresión «DUPLICADO».
  - **Generación**: bajo demanda y sin almacenarse, igual que la factura (003, FR-012).
- **FR-030**: **Listado impreso**: el listado de presupuestos DEBE ofrecer «Imprimir listado», igual
  que el de facturas (003, FR-018 a FR-023):
  - Todas las filas del filtro, hasta 5.000, en A4 apaisado.
  - Las columnas de FR-024.
  - Cabecera con el título «Listado de presupuestos» y el filtro.
  - **Totales por tipo de IVA y generales**: solo de los presupuestos que **cuentan**, que son los
    pendientes, los caducados, los que están en facturación y los convertidos. Los sustituidos no
    cuentan, porque su sustituto ya
    está en la suma. Los anulados y los borradores tampoco. Se indica cuántas filas quedan fuera y
    por qué.

#### Configuración

- **FR-031**: Configuración → Facturación DEBE añadir, solo para administradores, dos campos que se
  auditan como el resto de la configuración (002, FR-003):
  - **Validez de los presupuestos**: número de días, de 1 a 365, con 30 por defecto.
  - **Pie de presupuesto**: texto libre opcional de hasta 600 caracteres, con las mismas normas que
    el pie de factura (003, FR-024), p. ej. las condiciones del encargo o la variación del precio del
    oro. Si está vacío, el presupuesto impreso lleva el pie de factura, si lo hay.

  No se copian al emitir: cada impresión usa el pie vigente.

#### Integración con el resto del sistema

- **FR-032**: El menú lateral DEBE activar la entrada «Presupuestos». Desaparece la marca
  «Próximamente».
- **FR-033**: Un cliente con cualquier presupuesto, sea borrador o emitido, NO DEBE poder borrarse
  (001, FR-037). El sistema responde con el motivo y sugiere desactivarlo.
- **FR-034**: DEBEN quedar en la auditoría:
  - La creación, la modificación y el borrado de borradores de presupuesto.
  - La emisión, la modificación y la anulación.
  - La conversión: la creación del borrador vinculado, con el presupuesto de origen, y la emisión
    de la factura con el cierre de conversión.
  - Los cambios de la configuración de FR-031.

  Los importes se guardan como texto decimal exacto (constitución II).
- **FR-035**: Los registros de actividad del servidor NO DEBEN contener datos personales ni importes
  (002, FR-051). Solo pueden registrar identificadores internos, números de presupuesto y de
  factura y el tipo de operación.
- **FR-036**: Los datos de ejemplo del entorno de desarrollo DEBEN incluir presupuestos ficticios de
  varios meses en todos los estados: borradores, pendientes, caducados, en facturación con su
  borrador de factura, convertidos con su factura, sustituidos y anulados. Su carga sigue prohibida en producción (001, FR-045).
- **FR-037**: Las pantallas, el modal y el documento impreso DEBEN cumplir `docs/DESIGN.md`, también
  su sección «Paper». La leyenda y las marcas del presupuesto impreso y las marcas del listado se
  añaden a `docs/DESIGN.md` antes de implementarlas («Conformidad con el sistema de diseño»).

### Key Entities *(include if feature involves data)*

- **Borrador de presupuesto**: presupuesto en preparación.
  - Fecha, validez, cliente, líneas, si es de oro de inversión, autor y versión para detectar la
    edición concurrente.
  - Sin número. Se puede editar y borrar.
- **Presupuesto emitido**: documento comercial inalterable y sin validez fiscal.
  - Número `PRE`, fecha y validez.
  - Copia de los datos del emisor (IBAN incluido) y del destinatario.
  - Líneas con su tipo de IVA, desglose por tipo y totales.
  - Autor y fecha de emisión.
  - No tiene registro de facturación ni huella.
- **Línea de presupuesto**: unidades, descripción, precio unitario sin IVA, tipo de IVA e importe,
  como la de factura.
- **Cierre de presupuesto**: el desenlace de un presupuesto emitido. Hay como mucho uno por
  presupuesto, y es inalterable. Tiene tres tipos:
  - **Sustitución**: enlaza con el presupuesto nuevo y lleva motivo.
  - **Anulación**: lleva motivo.
  - **Conversión**: enlaza con la factura emitida. Se crea al emitir el borrador vinculado.

  Además guarda el autor y la fecha. Es lo que alimenta el historial y el estado.
- **Serie y contador** (de 002): se añade la serie `PRE`, con un contador por año que serializa las
  asignaciones simultáneas. No admite ajuste.
- **Borrador de factura** (de 002): puede estar vinculado a un presupuesto, como mucho uno por
  presupuesto. Mientras existe, el presupuesto está en facturación.
- **Factura** (de 002): la que procede de una conversión queda enlazada con su presupuesto a través
  del cierre de conversión. La factura en sí no cambia.
- **Configuración de facturación** (de 002 y 003): se amplía con la validez por defecto y el pie de
  presupuesto.
- **Cliente** (de 001): destinatario. Si tiene presupuestos, no se puede borrar.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un empleado crea y emite un presupuesto de tres líneas para un cliente de la cartera en
  menos de 2 minutos desde que pulsa «Nuevo presupuesto». Lo convierte y emite la factura sin
  cambios en menos de 1 minuto desde su consulta.
- **SC-002**: En 200 emisiones de presupuestos repartidas entre 10 usuarios simultáneos, los números
  `PRE` resultantes son consecutivos, sin ningún hueco ni duplicado. Si a la vez se emiten facturas,
  ninguna serie se ve afectada por la otra.
- **SC-003**: En 20 intentos simultáneos de convertir el mismo presupuesto se crea exactamente un
  borrador vinculado. En 20 emisiones simultáneas de ese borrador se emite exactamente una factura,
  el contador `FAC` avanza en uno, la cadena de registros crece en uno y el presupuesto queda
  convertido una sola vez. Una conversión que coincide con la anulación del presupuesto deja solo
  uno de los dos resultados.
- **SC-004**: En un juego de casos de cálculo con medios céntimos, cantidades con decimales e
  importes grandes, el 100 % de las bases, cuotas y totales de presupuestos coincide al céntimo con
  la referencia. Con el mismo tipo de IVA, la factura convertida coincide al céntimo con su
  presupuesto.
- **SC-005**: Tras intercalar conversiones con emisiones, anulaciones y rectificativas de facturas,
  la comprobación de integridad de 002 (FR-031) da la cadena por íntegra en el 100 % de los casos.
- **SC-006**: Ningún intento de modificar o borrar un presupuesto emitido, sus líneas o sus cierres
  prospera, incluidos los intentos directos sobre el almacenamiento con las credenciales del servicio
  y con las del propietario de los datos. El servidor rechaza el 100 % de los intentos de un
  empleado de modificar o anular un presupuesto, y el 100 % de las operaciones sobre un presupuesto
  ya cerrado.
- **SC-007**: El 100 % de los presupuestos impresos de un juego de pruebas (pendiente, caducado, de
  oro de inversión, con y sin número de cuenta, convertido, sustituido y anulado) lleva el título,
  la leyenda literal, la validez y su marca. Ninguno lleva código QR, «QR tributario», la frase
  VERI\*FACTU ni una dirección de la AEAT.
- **SC-008**: Con 20.000 presupuestos, el 95 % de las búsquedas y cambios de filtro muestran
  resultados en menos de 1 segundo, en el entorno local de pruebas de extremo a extremo.
- **SC-009**: El listado y el modal no provocan desplazamiento horizontal de la página a 360, 768 y
  1440 px. El 100 % de las filas de una página completa muestran sus acciones a 768, 1024, 1280,
  1440 y 1536 px.
- **SC-010**: En pruebas de doble envío de «Emitir», «Modificar», «Anular» y «Convertir en factura»,
  tanto simultáneos como repetidos, cada operación genera exactamente un documento: 0 duplicados.
- **SC-011**: Los totales del listado impreso coinciden al céntimo con la suma de los desgloses de
  los presupuestos que cuentan, calculada aparte. El número de filas coincide con el total de la
  pantalla.
- **SC-012**: Todas las pantallas y el documento impreso superan la revisión de conformidad con
  `docs/DESIGN.md`, sección «Paper» incluida. Las pruebas de extremo a extremo cubren las historias
  P1 y P2 y pasan en su totalidad antes de cerrar la feature.

## Conformidad con el sistema de diseño

- **Web**: el listado, el modal, los diálogos y las marcas reutilizan los componentes de facturas
  (002, «Conformidad con el sistema de diseño»): botones, tablas, chips de marca de 1 px con
  esquinas a 0 y estados de pantalla.
  - La marca «Borrador» usa el mismo tono que en facturas.
  - El tono de cada marca nueva (caducado, en facturación, convertido, sustituido y anulado) se
    fija en el plan con los tonos de estado de `docs/DESIGN.md`. El documento ya asocia el ámbar a
    los presupuestos abiertos («Open estimates»).
- **Paper**: el presupuesto impreso sigue la sección «Paper» de `docs/DESIGN.md`. Dos elementos no
  tienen todavía definición en el documento:
  - La leyenda de documento sin validez fiscal. `paper-alert` está reservado a las marcas de estado
    y prohíbe las marcas de agua.
  - Las marcas ANULADO, SUSTITUIDO y CONVERTIDO.

  Por eso se añaden a `docs/DESIGN.md` en el plan, con la aprobación del responsable, antes de
  implementarlos, como hizo la 003 con la sección «Paper». Quedan escritos en `docs/DESIGN.md` 1.3
  (2026-10-02), junto con el tono neutro de los chips, que la 002 ya usaba sin documentar.

Desviaciones de `docs/DESIGN.md`: **ninguna**. Las ampliaciones son enmiendas aprobadas, no
desviaciones.

## Fuentes normativas citadas

Se mantiene la numeración de las fuentes de 002 y 003 (F-1 a F-12). Esta feature cita F-4 y F-6 y
añade F-13.

- **F-13**: AEAT, preguntas frecuentes VERI\*FACTU, página «Cuestiones generales: conceptos y
  definiciones».
  - URL:
    `https://sede.agenciatributaria.gob.es/Sede/iva/sistemas-informaticos-facturacion-verifactu/preguntas-frecuentes/cuestiones-generales-conceptos-definiciones.html`.
  - Página actualizada el 22/07/2026; preguntas «actualizadas a 21 de julio de 2026». Consulta:
    2026-10-02.
  - Pregunta «¿Se puede implementar un sistema de «Pre-Facturación» («facturas proforma») o
    Borrador antes de expedir –y registrar– una factura?»:
    - «La introducción y edición temporal de datos, visualización previa, etc. de facturas no está
      prohibida ni por el reglamento que establece los requisitos de los sistemas informáticos de
      facturación ni por el reglamento de obligaciones de facturación».
    - «hasta no estar terminada la factura, esta no podrá ser expedida con su correspondiente
      código «QR» tributario. Por ello tanto los borradores de factura como las facturas proforma
      no llevan ningún código «QR» tributario».
    - Las proformas se permiten «siempre y cuando se sustituyan finalmente por la factura o factura
      simplificada oficial expedida y esta se entregue al cliente».
    - El sistema de prefacturas debe estar «vinculado indefectiblemente al sistema de emisión de
      facturas formando una unidad». «Conviene, a efectos de control interno, que se conserve
      registro de las prefacturas o facturas proforma elaboradas».
    - No sería legal un sistema que genere documentos preparatorios «sin que el sistema
      informático mismo disponga de elementos de control para la conservación de tales documentos
      preparatorios de forma debidamente vinculada a las facturas o a los registros de facturación
      que finalmente se emitan o, en defecto de factura, de forma que queden registrados y
      conservados en el sistema».
  - Pregunta sobre los documentos mercantiles a los que afecta el reglamento: los documentos que no
    son facturas no están sujetos a sus requisitos.
  - **Interpretación**: la FAQ habla de proformas y borradores, no de presupuestos. Aplicar su
    criterio a los presupuestos es una interpretación prudente del proyecto (constitución 2.3.0):
    sin QR, sin registro, conservados y vinculados a la factura de conversión (FR-005, FR-017 y
    FR-020).
- **F-4**: AEAT, *Aclaraciones a dudas de los desarrolladores*, versión 1.3 (002, F-4),
  aclaración 6: «los borradores y las prefacturas son una operación ordinaria» y, hasta validar la
  factura, cualquier alteración previa al registro es lícita.
- **F-6**: Reglamento por el que se regulan las obligaciones de facturación, RD 1619/2012
  (BOE-A-2012-14696, texto consolidado), consultado el 2026-10-02:
  - No regula los presupuestos ni las facturas proforma. Solo contempla facturas completas,
    simplificadas, rectificativas y duplicados.
  - **Art. 14**: el duplicado es de la factura y lleva la expresión «duplicado». Por eso el
    presupuesto impreso no ofrece «Duplicado» (FR-029).
- **Preguntas abiertas**: ninguna nueva de fuente oficial. Siguen abiertas las de 002 (research
  R-17) y el TODO(MODALIDAD_VERIFACTU) de la constitución. Esta feature solo depende de ellas a
  través de la conversión, que es una emisión normal de factura.

## Fuera de alcance

- **Otras features**: la remisión de los registros a la AEAT (004), que incluirá las facturas
  convertidas como cualquier otra.
- **Facturas proforma** como documento distinto del presupuesto (Clarifications).
- **Conversiones múltiples**: varias facturas desde un presupuesto o una factura desde varios
  presupuestos. Facturar solo parte de las líneas se consigue editando el borrador vinculado, y el
  presupuesto queda convertido igualmente.
- **Conversiones repetidas**: volver a convertir un presupuesto cuya factura se anuló. Para
  facturar de nuevo se emite un presupuesto o una factura nuevos.
- **Aceptación formal**: estados «enviado», «aceptado» o «rechazado», firma del cliente y
  recordatorios de caducidad. El rechazo se registra con «Anular» y su motivo.
- **Duplicados** del presupuesto impreso (F-6, art. 14).
- **Filtros nuevos**: estado o caducidad. Las marcas los distinguen, igual que en facturas (002,
  «Conformidad con el sistema de diseño»).
- **Mención del presupuesto en el PDF de la factura**: el vínculo está en el sistema y en la
  consulta (FR-022). La factura impresa no cambia.
- **Otros**: envío por correo, exportación, anticipos o pagos a cuenta, plantillas personalizadas y
  la aplicación Android.

## Assumptions

- **Permisos**, iguales que en facturas (002, Assumptions):
  - Empleados y administradores crean, editan y borran borradores, emiten, imprimen y convierten.
  - Solo los administradores modifican y anulan presupuestos emitidos y cambian la configuración.
- **Conversión mediante borrador** (Clarifications, clarify): el borrador vinculado se puede editar
  libremente, incluido el cliente. El vínculo con el presupuesto se mantiene, porque la factura
  nace de él (F-13).
- **Validez por defecto de 30 días**: es la práctica habitual en presupuestos de encargo. Se puede
  cambiar en Configuración y en cada presupuesto.
- **Límite inferior de la fecha**: el 28/10/2024, el mismo que el de la factura. Así el filtro de
  años del listado, que empieza en 2024, sirve para ambos documentos. Un presupuesto no tiene
  límites de la AEAT.
- **Caducidad sin marca en el PDF**: la fecha «Válido hasta» ya lo indica, y reimprimir un
  presupuesto caducado sirve, por ejemplo, para el archivo.
- **Totales del listado impreso**: suman lo presupuestado neto: pendientes, caducados, en
  facturación y convertidos.
  Los sustituidos quedan fuera para no contar dos veces una oferta renegociada.
- **Volumen**: del orden de las facturas o algo mayor. Los objetivos de rendimiento se fijan con
  20.000 presupuestos.
- **Hora de referencia**: hora de España peninsular para la fecha, la validez y la caducidad, como en
  el resto del sistema.
- **Tests obligatorios** (constitución VII): esta feature toca los cuatro.
  - Numeración `PRE` bajo concurrencia.
  - Importes y redondeos del presupuesto y de la factura convertida.
  - Encadenamiento de huellas con conversiones (SC-005).
  - Conversión presupuesto → factura con concurrencia e idempotencia, tanto al crear el borrador
    vinculado como al emitirlo (SC-003).

  Además se prueba la inalterabilidad del presupuesto en el almacenamiento (SC-006).
