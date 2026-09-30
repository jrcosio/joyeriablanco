# Feature Specification: Facturación con registro Verifactu

**Feature Branch**: `002-facturas`

**Created**: 2026-09-28

**Status**: Draft

**Input**: Descripción del responsable del proyecto (2026-09-28): "Siguiente feature, las facturas.
Tienes en `temporal` dos ejemplos de cómo quiero que sean las facturas. No quiero los indicadores
de KPI ni nada de eso: quiero que salga en el listado las facturas y arriba lo de buscar, la misma
lógica que los clientes. Lo que pasa es que para crear, editar, etc. quiero que sea como la
captura, es decir, un modal por encima, lógicamente con el estilo que tenemos en la web. En
configurar estaría bien poder poner el IVA por defecto al 21 %, pero que se pueda cambiar por si
en un futuro cambia. Lo de estado de la factura que sale en el ejemplo sobra, y la numeración de
las facturas es el año más un número incremental (FAC-2026-0002). Aunque sea un campo único,
estaría bien que también se pudiera editar, ya que si hay errores se puedan subsanar, pero
lógicamente con control para evitar duplicidad. En el ejemplo el menú está a la derecha y es a la
izquierda."

**Ajustes de cierre** (2026-09-30), pedidos por el responsable tras probar la facturación: "si
mañana le suben al 22 o le bajan al 20 […] no puedo ponerlo y eso es un fallo ya que esa era la
finalidad" (FR-001). "Lo de Clave de Régimen del IVA eso no lo quiero […] la joyería siempre es
régimen general" (FR-001). "Falta el número de cuenta bancaria IBAN para que salga en las
facturas" (FR-001, FR-016, FR-053). Y "si se vende un lingote de oro de inversión es sin IVA, por lo
tanto quiero desactivarlo para que no tenga IVA y ya está" (FR-052).

**Referencias**:
- Mockups orientativos:
  - [`assets/mockup-facturas.png`](assets/mockup-facturas.png) (listado).
  - [`assets/mockup-nueva-factura.png`](assets/mockup-nueva-factura.png) (modal «Nueva factura»).
- Sistema de diseño normativo: [`docs/DESIGN.md`](../../docs/DESIGN.md).
- Constitución 2.2.0: principios II, III, IV, VI y VII y restricción "Numeración".
- Feature previa: [`specs/001-cimientos-clientes`](../001-cimientos-clientes/spec.md).

## Clarifications

### Session 2026-09-28 (decisiones previas a la especificación)

- Q: ¿Qué entra en esta feature? → A: Facturas, con su registro de facturación de alta y la huella
  encadenada, inalterables en el almacenamiento. Quedan para features posteriores:
  - El PDF con el código QR (003).
  - La remisión a la AEAT (004).
  - Los presupuestos (005).
- Q: ¿Se pueden editar las facturas? → A: Sí, y cambia según la factura esté en borrador o emitida:
  - **Borrador**: se edita y se borra libremente.
  - **Emitida**: se puede «Modificar», incluido su número, pero solo mediante una **corrección
    trazable**. El original se conserva y la corrección queda en un historial visible.
  - El responsable pidió cambiar la constitución para permitirlo, y se enmendó a la 2.1.0
    (principio III). La sobrescritura no es posible porque la inalterabilidad la impone la
    normativa, no la constitución (LGT art. 201 bis.1.d, F-7).
- Q: ¿Se usan borradores? → A: Sí, con los botones «Guardar borrador» y «Emitir factura», como en la
  captura.
- Q: ¿Cómo se elige el IVA en la factura? → A: Siempre es el tipo por defecto de Configuración. En la
  factura no hay selector. *Desde el ajuste de cierre, una factura de oro de inversión va sin IVA:
  ver la sesión del 2026-09-30.*
- Q: ¿Indicadores y estado de cobro? → A: Ninguno de los dos. El listado no tiene KPI ni columna de
  estado (Cobrada, Pendiente o Vencida).

### Session 2026-09-28 (specify)

- Q: ¿Modalidad VERI\*FACTU o no VERI\*FACTU? → A: Pendiente de la asesoría.
  - Es una opción de Configuración sin valor inicial.
  - Hay que fijarla antes de la feature 004.
  - El TODO(MODALIDAD_VERIFACTU) de la constitución sigue abierto (FR-001, FR-004).
- Q: ¿Qué tipos de factura emite esta feature? → A: Solo completas (F1), siempre con un cliente
  identificado de la cartera. Las simplificadas quedan fuera de alcance (FR-005).
- Q: ¿Cómo decide «Modificar» qué corrección genera? → A: Pregunta el motivo (FR-024).
  - **«La factura no debió emitirse o no llegó a entregarse»**: anulación, y después una factura
    nueva con el siguiente número.
  - **«Hay que corregir una factura ya entregada»**: factura rectificativa por sustitución en su
    propia serie.
  - **Consulta intermedia**: el responsable eligió primero «siempre anular y reemitir». Se le
    advirtió de que, para una venta real ya entregada, el ROF art. 15 obliga a la rectificativa,
    y de que la AEAT reserva la anulación a las facturas que no debieron emitirse (F-4,
    aclaración 17). Tras eso eligió preguntar el motivo.
- Q: ¿Cómo se corrige el número? → A: Nunca a mano en la factura.
  - Toda factura nueva recibe el siguiente número de su serie, incluidas la que sustituye a una
    anulada y la rectificativa.
  - El administrador puede ajustar al alza el próximo número de la serie del año **en cualquier
    momento**, siempre por encima del último usado y con un motivo obligatorio, que queda en la
    auditoría (FR-010).
  - El responsable eligió esa opción sabiendo que deja huecos dentro del sistema, que habrá que
    poder justificar.

### Session 2026-09-28 (clarify)

- Q: ¿En qué régimen de IVA factura la joyería sus ventas? → A: Todas en régimen general, clave
  01 de la lista L8A (F-1), al tipo de Configuración. La clave queda en Configuración para que la
  asesoría la confirme o la cambie antes de producción (FR-001). *En el ajuste de cierre la clave
  sale de Configuración y la fija el sistema: ver la sesión del 2026-09-30.*
- Q: ¿Quién puede anular o modificar una factura ya emitida? → A: Solo los administradores. Los
  empleados crean borradores y emiten (FR-023, FR-025).
- Q: ¿Cómo se rellena la descripción del objeto de la factura que exige el registro? → A: Se
  forma automáticamente con las descripciones de las líneas y se recorta a 500 caracteres. El
  modal no tiene campos nuevos (FR-045).
- Q: ¿Se puede dar de alta un cliente nuevo desde el modal de la factura? → A: Sí. «Nuevo cliente»
  abre por encima el formulario de cliente de 001. Al guardarlo, se vuelve a la factura con ese
  cliente elegido y sin perder lo escrito (FR-046).

### Session 2026-09-28 (plan)

Preguntas surgidas del research del plan, que se basa en las fuentes oficiales F-9 y F-3.

- Q: Al rectificar una factura ya entregada, ¿cómo se elige la causa que exige la AEAT? → A: El
  modal la pregunta con dos opciones (FR-024):
  - **«Devolución, descuento o cambio de precio posterior a la venta, o IVA mal aplicado»**:
    código R1.
  - **«Error en datos o importes de la factura»**: código R4.
- Q: ¿Entran las devoluciones en esta feature? → A: Sí, parciales y totales, como rectificativas
  R1 por sustitución.
  - **Devolución parcial**: la rectificativa lleva menos líneas o unidades.
  - **Devolución total**: la rectificativa no lleva líneas y su total es 0 €.
  - **Límite**: una rectificativa nunca puede dar un total negativo (FR-012, casos límite).

### Session 2026-09-29 (checklist)

Estas preguntas salen de revisar las checklists de calidad de requisitos.

- Q: ¿Se puede poner a una factura una fecha de expedición anterior al día en que se emite? → A: Sí,
  hacia atrás, nunca antes de la última factura emitida de la serie en ese año ni en el futuro
  (FR-018). *Los límites propios se retiraron después: ver la sesión «cambio tras la
  implementación».*
  - Se advirtió al responsable de que F-8, art. 9, exige generar el registro «de forma simultánea o
    inmediatamente anterior a la expedición». Se le propuso usar la fecha de la operación para una
    venta de otro día.
  - Mantuvo la fecha editable. Queda como pregunta abierta para la asesoría (research R-17, Q-9).
- Q: ¿Se puede anular una factura rectificativa? → A: Sí. Al anularla, la factura que rectificaba
  vuelve a estar vigente y se puede corregir de nuevo (FR-025, FR-048).

### Session 2026-09-29 (cambio tras la implementación)

El responsable pide poder poner a cualquier factura la fecha que corresponda, porque las facturas
se emiten a final de semana o de mes.

- Q: ¿Qué límites tiene la fecha de expedición? → A: Solo los que valida la AEAT: no posterior a
  hoy (F-3 §3.1.3.1, error 1112) y no anterior al 28/10/2024 (F-3 §3.1.3.1, error 1152). Se
  retiran los dos límites propios: no ser anterior a la última factura de la serie y ser del año
  en curso o del anterior (FR-018).
  - Una factura puede llevar un número posterior y una fecha anterior a la de la factura
    precedente de su serie.
  - El número sale siempre de la serie del año de su fecha: una factura de diciembre de 2025
    emitida en enero de 2026 lleva `FAC-2025-NNNN` (constitución, «Numeración»).
  - Sigue abierta para la asesoría la pregunta Q-9 (research R-17), ahora también con este
    desorden posible entre número y fecha.
- Q: ¿Se elige también la fecha al corregir una factura emitida? → A: Sí. La factura nueva tras una
  anulación y la rectificativa tienen la fecha de expedición editable, con los mismos límites y
  uno más de la AEAT: no puede ser anterior a su fecha de la operación, que es la heredada de la
  original (F-3 §3.1.3.1, error 1146).

### Session 2026-09-30 (ajuste de cierre)

El responsable pide cuatro cambios tras probar la facturación (cabecera, «Ajustes de cierre»).
Antes de responder se le informó de lo que dicen las fuentes oficiales:
- La AEAT solo admite hoy los tipos 0, 4, 10 y 21 en una operación sujeta y no exenta (F-3 §15.1).
- La entrega de oro de inversión está exenta (F-11, art. 140 bis) y pertenece al «Régimen especial
  del oro de inversión» (F-11, capítulo V del título IX). El registro la identifica con la clave
  de régimen `04` de la lista L8A y con la causa de exención `E6`, «Exenta por otros», de la lista
  L10 (F-1; F-3 §15.6.3).

- Q: El IVA por defecto va a admitir cualquier tipo. ¿Cómo se evita un error de tecleo (12 en vez
  de 21)? → A: Se admite cualquier tipo de 0 a 99,99 %. Si no es uno de los que la AEAT admite en
  la fecha actual, se avisa y se pide confirmación antes de guardar. Emitir nunca se bloquea por el
  tipo (FR-001).
- Q: ¿Qué pasa con la clave de régimen de Configuración? → A: Se retira. La joyería factura en
  régimen general, y la clave del registro la fija el sistema: `01` en toda factura, salvo `04` en
  las de oro de inversión (FR-001, FR-052).
- Q: ¿Dónde se quita el IVA en «Nueva factura»? → A: Con un único interruptor para toda la factura,
  «Sin IVA (oro de inversión)», junto al IVA. No hay selector por línea. Una venta mixta, como un
  lingote y una joya, se documenta en dos facturas (FR-052).
- Q: ¿El «sin IVA» sirve para otras exenciones? → A: No, solo para el oro de inversión. El sistema
  pone solo en el registro la clave `04` y la exención `E6`, y en la factura la mención legal de la
  exención (F-6, art. 6.1.j). La asesoría confirma las claves y la mención antes de producción
  (research R-17, Q-10).
- Q: ¿El IBAN es obligatorio? → A: No, es opcional y no impide emitir. Si está, se valida su
  dígito de control, se copia en cada factura al emitirla y sale en ella: hoy en la consulta y,
  cuando exista, en el PDF de la feature 003 (FR-001, FR-016, FR-053).
- Q: ¿Quién puede marcar «Sin IVA (oro de inversión)»? → A: Todos los que facturan, empleados y
  administradores, igual que para emitir. La factura guarda quién la emitió y la emisión queda en
  la auditoría (FR-052).
- Q: ¿La joyería fabrica oro de inversión o transforma oro en oro de inversión? → A: No, solo lo
  vende. Toda venta de oro de inversión es exenta, y la renuncia a la exención (F-11, art. 140 ter)
  queda fuera de alcance (Assumptions).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Configurar la facturación (Priority: P1)

Antes de facturar, el administrador abre Configuración → Facturación. Allí fija el tipo de IVA por
defecto, que viene al 21 %, y los datos de la joyería como emisora de las facturas, incluido el
IBAN en el que cobra. Si un día cambia el tipo general, escribe el nuevo en esa misma pantalla.

**Why this priority**: sin los datos del emisor no se puede expedir una factura válida (F-6,
art. 6.1), y el IVA por defecto es lo que se aplica en cada línea.

**Independent Test**: un administrador guarda el IVA y los datos del emisor, y luego se comprueba
dos cosas: que una factura nueva usa ese tipo y que un empleado no puede entrar en la sección.

**Acceptance Scenarios**:

1. **Given** una instalación nueva, **When** el administrador abre Configuración → Facturación,
   **Then** el IVA por defecto aparece al 21 % y los datos del emisor, vacíos, marcados como
   necesarios para emitir, salvo el IBAN, que es opcional. No hay ningún campo de clave de régimen.
2. **Given** el IVA por defecto al 21 %, **When** el administrador lo cambia a 10 y guarda,
   **Then** los borradores nuevos y los que se emitan a partir de ese momento usan el tipo nuevo, y
   las facturas ya emitidas conservan el suyo.
3. **Given** un empleado, **When** intenta abrir o guardar la configuración de facturación,
   **Then** el sistema se lo impide.
4. **Given** datos del emisor incompletos o la modalidad sin elegir, **When** alguien intenta emitir
   una factura, **Then** no se emite y un aviso indica qué falta y que lo debe completar un
   administrador.
5. **Given** la serie de 2026 con la última factura `FAC-2026-0005`, **When** el administrador fija
   el próximo número en 143 e indica el motivo (p. ej. "continuación de la numeración del programa
   anterior"), **Then** la siguiente factura emitida es `FAC-2026-0143` y el cambio queda en la
   auditoría con su motivo.
6. **Given** la misma serie, **When** el administrador intenta fijar el próximo número en 5 o menos,
   **Then** el sistema lo rechaza, porque ese número ya se ha usado.
7. **Given** el IVA por defecto al 21 %, **When** el administrador escribe 22 y guarda, **Then** un
   aviso le indica que 22 no está entre los tipos que la AEAT admite hoy (0, 4, 10 y 21) y le pide
   confirmarlo. Si confirma, se guarda y se aplica igual que cualquier otro tipo. Si no, nada
   cambia.
8. **Given** el formulario de datos del emisor, **When** el administrador escribe un IBAN con el
   dígito de control erróneo y guarda, **Then** el sistema lo rechaza con el error en el propio
   campo. Con un IBAN válido, lo guarda y lo muestra agrupado de cuatro en cuatro.

---

### User Story 2 - Crear y emitir una factura en el modal (Priority: P1)

Desde el listado, un empleado pulsa «Nueva factura» y se abre un modal por encima del listado.
Elige al cliente, que se muestra con sus datos fiscales, y añade las líneas con las unidades, la
descripción y el precio unitario sin IVA. El modal va mostrando la base imponible, el IVA y el
total. Puede guardarlo como borrador o emitirlo directamente. Al emitir, la factura recibe su
número definitivo `FAC-AAAA-NNNN` y queda registrada con su huella.

**Why this priority**: facturar es el objetivo de la fase 1 del proyecto.

**Independent Test**: con el emisor configurado y un cliente activo, se crea una factura de varias
líneas y se emite. Hay que comprobar el número asignado, los importes calculados por el servidor,
el registro de alta y su huella encadenada con la del registro anterior.

**Acceptance Scenarios**:

1. **Given** el listado de facturas, **When** se pulsa «Nueva factura», **Then** se abre un modal
   sobre el listado con tres secciones: datos de emisión (número, fecha y cliente), detalle (líneas)
   y totales. La fecha propuesta es la de hoy.
2. **Given** el modal abierto, **When** se elige un cliente, **Then** se muestra su nombre o razón
   social, su identificación fiscal y su domicilio. Los clientes inactivos no se pueden elegir.
3. **Given** una línea con 2 unidades a 45,00 € y otra con 1 unidad a 1.200,00 €, **When** se
   rellenan, **Then** el modal previsualiza unos importes de 90,00 € y 1.200,00 €, una base
   imponible de 1.290,00 €, un IVA (21 %) de 270,90 € y un total de 1.560,90 €.
4. **Given** una factura completa, **When** se pulsa «Emitir factura» y se confirma el aviso de
   que después no se podrá editar, **Then** se asigna el siguiente número de la serie del año de
   la fecha de expedición (p. ej. `FAC-2026-0001` si es la primera del año). Además se genera el
   registro de alta con su huella encadenada y la factura aparece en el listado.
5. **Given** dos usuarios que emiten facturas a la vez, **When** ambas emisiones terminan, **Then**
   tienen números consecutivos distintos, sin huecos ni duplicados, y sus registros quedan
   encadenados en el orden en que se emitieron.
6. **Given** una factura a medias, **When** se pulsa «Guardar borrador», **Then** se guarda sin
   número definitivo ni registro, y aparece en el listado con la marca «Borrador».
7. **Given** un cliente al que le falta un dato obligatorio para la factura, como el domicilio,
   **When** se intenta emitir, **Then** no se emite y se indica el dato que falta, con acceso a
   la ficha del cliente para completarlo.
8. **Given** el modal con cambios, **When** se pulsa «Cancelar» o se cierra, **Then** se pide
   confirmación antes de descartarlos.
9. **Given** un cliente que todavía no está en la cartera, **When** se pulsa «Nuevo cliente» junto
   al selector, se rellena su ficha y se guarda, **Then** el modal de la factura vuelve con ese
   cliente elegido y conserva las líneas ya escritas.
10. **Given** una factura con una línea «Lingote de oro 100 g» de 1 unidad a 7.450,00 €, **When** se
    marca «Sin IVA (oro de inversión)», **Then** el modal previsualiza una base exenta de 7.450,00 €,
    un IVA de 0,00 € y un total de 7.450,00 €, con la mención de la exención. Al emitirla, su
    registro de alta identifica la operación como exenta de oro de inversión (FR-052).

---

### User Story 3 - Consultar y buscar facturas (Priority: P1)

Un empleado abre Facturas y ve el listado paginado, con la búsqueda arriba, igual que en clientes.
Busca por número, cliente o identificación fiscal, filtra por año y mes, y ordena el resultado.

**Why this priority**: localizar una factura es la operación diaria más frecuente, y es la puerta a
consultarla, modificarla y, más adelante, imprimirla.

**Independent Test**: con facturas de ejemplo cargadas se prueban la búsqueda, cada filtro, el
orden y la paginación, y se comprueba que no hay indicadores ni columna de estado.

**Acceptance Scenarios**:

1. **Given** facturas emitidas y borradores de varios años, **When** se abre Facturas, **Then**
   aparecen las del año en curso, primero las más recientes, con estas columnas: número, fecha,
   cliente, identificación, base imponible, IVA, total y acciones. No hay indicadores ni columna
   de estado.
2. **Given** una factura de "María López García", **When** se busca "maria lopez", su NIF o
   "2026-0005", **Then** la factura aparece en los resultados.
3. **Given** los filtros de año y mes, **When** se combinan con una búsqueda, **Then** el resultado
   cumple todas las condiciones a la vez.
4. **Given** un borrador, una factura anulada o una rectificada, **When** aparecen en el listado,
   **Then** cada una se distingue con una marca discreta en la columna del número, sin columna de
   estado.
5. **Given** una página completa de facturas, **When** se mira a 768, 1024, 1280, 1440 o 1536 px de
   ancho, **Then** cada fila muestra sus acciones sin desplazar nada.
6. **Given** una búsqueda sin resultados, **When** se ejecuta, **Then** aparece un estado vacío con
   la opción de limpiar los filtros. Si todavía no hay ninguna factura, el estado vacío invita a
   crear la primera.

---

### User Story 4 - Editar y borrar borradores (Priority: P2)

Un empleado retoma un borrador desde el listado. Lo abre en el mismo modal, lo cambia y lo vuelve a
guardar o lo emite. Si ya no lo necesita, lo borra.

**Why this priority**: permite preparar facturas con calma y corregir errores antes de emitir. Es
el momento en que corregir no tiene ningún coste fiscal (F-4, aclaración 17, caso 1).

**Independent Test**: se crea un borrador, se modifica, se borra y se comprueba que no ha dejado
registro de facturación ni ha consumido ningún número.

**Acceptance Scenarios**:

1. **Given** un borrador, **When** se abre desde el listado, **Then** el modal muestra sus datos
   editables y los botones «Cancelar», «Eliminar borrador», «Guardar borrador» y «Emitir factura».
2. **Given** un borrador abierto por dos usuarios, **When** ambos guardan, **Then** el segundo
   recibe un aviso de que el borrador ha cambiado desde que lo abrió, y nada se sobrescribe sin
   que lo sepa.
3. **Given** un borrador, **When** se borra con confirmación, **Then** desaparece del listado sin
   dejar número consumido ni registro de facturación.
4. **Given** un borrador cuyo cliente se ha desactivado, **When** se intenta emitir, **Then** no se
   emite hasta que se elija otro cliente o se reactive el cliente.

---

### User Story 5 - Modificar o anular una factura emitida (Priority: P2)

Un administrador detecta un error en una factura ya emitida, como un dato del cliente, un importe
o una descripción. Pulsa «Modificar» y el mismo modal se abre con los datos de la factura. Hace los
cambios y, al guardar, indica qué ha pasado.

- **Si la factura no debió emitirse o no llegó a entregarse al cliente**: se anula y se emite una
  factura nueva, con el siguiente número.
- **Si ya se entregó**: se emite una factura rectificativa que sustituye a la original.

Si la factura sobraba del todo, por ejemplo por estar duplicada, se «Anula» sin emitir otra. En
ningún caso se sobrescribe nada: se conserva la original y queda constancia en su historial.

**Why this priority**: los errores en facturas emitidas existen, y el responsable necesita
subsanarlos sin salir de la aplicación. La obligación legal hace que la forma de hacerlo sea
crítica.

**Independent Test**: sobre una factura emitida se hace una modificación y se comprueban cuatro
cosas:
- La factura original y su registro siguen intactos.
- Existe la corrección, con su registro encadenado.
- El historial la muestra.
- Ningún número se ha reutilizado.

**Acceptance Scenarios**:

1. **Given** una factura emitida, **When** se abre desde el listado, **Then** el modal la muestra en
   modo consulta, con las acciones «Anular» y «Modificar» y su historial de correcciones.
2. **Given** `FAC-2026-0007`, que no llegó a entregarse, **When** se modifica el cliente y se guarda
   indicando «La factura no debió emitirse o no llegó a entregarse», **Then** se genera el registro
   de anulación de `FAC-2026-0007` y se emite una factura nueva con los datos corregidos y el
   siguiente número, p. ej. `FAC-2026-0012`. `FAC-2026-0007` sigue constando en la serie, marcada
   como anulada.
3. **Given** `FAC-2026-0007`, ya entregada, **When** se corrige una unidad y se guarda indicando «Hay
   que corregir una factura ya entregada» con la causa «Error en datos o importes», **Then** se emite la rectificativa por sustitución, p.
   ej. `REC-2026-0001`, con los datos corregidos. La rectificativa identifica la factura original
   y el importe de la rectificación (F-6, art. 15.4 y 15.5), y la original queda marcada como
   rectificada.
4. **Given** `FAC-2026-0009`, ya entregada, cuyo cliente devuelve todas las piezas, **When** se
   modifica quitando todas las líneas y se indica la causa «Devolución, descuento o cambio de
   precio posterior», **Then** se emite una rectificativa R1 por sustitución con total 0 €. Además,
   `FAC-2026-0009` queda rectificada y su importe consta como importe rectificado.
5. **Given** una factura duplicada por error, **When** se pulsa «Anular», se declara que no debió
   emitirse y se indica el motivo, **Then** se genera su registro de anulación sin emitir otra
   factura, y su número no vuelve a usarse.
6. **Given** una factura rectificada o anulada, **When** se consulta, **Then** se ve con claridad
   su situación, con acceso directo a la factura vigente que la sustituye, si la hay. Además, no
   ofrece «Modificar» ni «Anular».
7. **Given** `REC-2026-0001`, que rectifica `FAC-2026-0007` y no debió emitirse, **When** un
   administrador la anula, **Then** se genera el registro de anulación de la rectificativa y
   `FAC-2026-0007` vuelve a estar vigente. Su historial muestra la rectificación anulada, y se
   puede corregir de nuevo.
8. **Given** un empleado, **When** consulta una factura emitida, **Then** no ve «Anular» ni
   «Modificar», y el servidor rechaza cualquier intento suyo de anular o modificar.
9. **Given** `FAC-2026-0010`, ya entregada, en la que se vendió un lingote de oro de inversión con
   IVA por error, **When** se modifica marcando «Sin IVA (oro de inversión)» y la causa
   «Devolución, descuento o cambio de precio posterior a la venta, o IVA mal aplicado», **Then** se
   emite una rectificativa R1 por sustitución, exenta, y `FAC-2026-0010` queda rectificada.

---

### User Story 6 - Integridad comprobable del registro de facturación (Priority: P3)

El responsable técnico, o un inspector ante un requerimiento, necesita comprobar que la cadena de
registros de facturación no se ha alterado. El sistema recalcula todas las huellas en orden e
informa de si la cadena está íntegra o de cuál es el primer registro que no cuadra.

**Why this priority**: la integridad y la trazabilidad son requisitos del sistema de facturación
(F-8). Poder comprobarlas cierra el círculo de la inalterabilidad, aunque no sea una operación
diaria.

**Independent Test**: se emiten y corrigen varias facturas y se lanza la comprobación, que debe
salir íntegra. Luego, en una base de pruebas y saltándose las protecciones con privilegios de
superusuario, se altera un registro y se repite: debe señalar ese registro.

**Acceptance Scenarios**:

1. **Given** una cadena de registros sin alterar, **When** se lanza la comprobación, **Then** informa
   de que la cadena es íntegra, con el número de registros revisados.
2. **Given** un registro alterado por fuera del sistema, **When** se lanza la comprobación, **Then**
   identifica el primer registro cuya huella no coincide.

---

### Edge Cases

- **Cambio de año**: la primera factura con fecha de expedición del 1 de enero de 2027 recibe
  `FAC-2027-0001`, aunque la serie de 2026 no haya terminado. El año del número es siempre el de
  la fecha de expedición.
- **Emisiones simultáneas**: dos o más emisiones al mismo tiempo nunca obtienen el mismo número ni
  dejan huecos, y sus registros se encadenan sin bifurcaciones.
- **Fallo durante la emisión**: si algo falla al asignar el número, generar el registro o calcular
  la huella, la emisión se deshace entera. No queda número consumido ni registro a medias, y el
  borrador sigue intacto.
- **Fecha de expedición**: cualquiera entre el 28/10/2024 y hoy, en cualquier orden respecto a las
  demás facturas de la serie (FR-018). El número se toma de la serie del año de esa fecha.
- **Cambio del IVA por defecto con un borrador abierto**: al emitirse, el borrador usa el tipo
  vigente en ese momento y el modal avisa si ha cambiado desde que se guardó.
- **IVA de una rectificativa o una reemisión**: se aplica el tipo de Configuración vigente al
  emitirla, igual que en cualquier factura (FR-013). Si no coincide con el de la factura original,
  el modal lo avisa antes de guardar (research R-4).
- **Tipo de IVA fuera de la lista de la AEAT**: tras confirmarlo en Configuración (FR-001), las
  facturas se emiten con él sin más avisos. Si la AEAT aún no lo admite, rechazará el registro
  cuando se remita (feature 004; research R-17, Q-11).
- **Factura de oro de inversión** (FR-052):
  - **Venta mixta**: un lingote y una joya en la misma venta se documentan en dos facturas, una sin
    IVA y otra con IVA. Una factura nunca mezcla líneas exentas y sujetas.
  - **Borrador**: guarda si está marcado «Sin IVA». Un cambio del IVA por defecto no le afecta ni
    provoca el aviso de cambio de tipo.
  - **Corrección**: «Modificar» parte del valor de la factura original y deja cambiarlo. Cambiarlo
    cuenta como un cambio: la modificación no se considera «sin cambios».
  - **Rectificar una factura exenta a sujeta, o al revés**: la rectificativa lleva el tratamiento
    que se marque, y su importe de rectificación se calcula igual que en cualquier rectificativa.
  - **Total**: como en cualquier factura ordinaria, no se admite un total de cero (Casos límite,
    «Importes límite»).
- **Cambio del IBAN**: las facturas ya emitidas conservan el IBAN que tenían al emitirse. Las
  emitidas antes del ajuste de cierre, o cuando el IBAN estaba vacío, no llevan ninguno.
- **Cambios en el cliente después de emitir**: la factura emitida conserva los datos del cliente y
  del emisor tal como estaban al emitirla. Editar después la ficha del cliente no la altera.
- **Cliente con facturas**: no se puede borrar. Se ofrece desactivarlo, y el borrado lo rechaza el
  sistema con el motivo (001, FR-037). Los borradores también cuentan como documentos.
- **Usuario eliminado**: las facturas que emitió siguen mostrando su nombre con la marca
  "(eliminado)" (001, FR-061).
- **Importes límite**: los importes admiten dos decimales, y ninguna línea puede tener unidades a
  cero o negativas ni un precio negativo.
  - **Factura ordinaria**: no se admite sin líneas ni con un total de cero.
  - **Rectificativa**: puede quedarse sin líneas y con total 0 € en una devolución total, pero
    nunca con un total negativo (Clarifications).
  - **Borrador**: puede guardarse incompleto, sin cliente o sin líneas. Todo se exige al emitir.
- **Redondeo**: las cifras con medio céntimo se redondean siempre igual (FR-015). La suma de las
  líneas que se muestra coincide al céntimo con la base imponible registrada.
- **Ajuste del próximo número**: se rechaza cualquier valor igual o inferior al último número usado
  de la serie y año, aunque ese número corresponda a una factura anulada. También se rechaza si
  falta el motivo. Dos ajustes simultáneos no pueden dejar el contador por debajo de un número ya
  asignado.
- **Modificar una factura ya corregida**: solo se puede modificar o anular la factura vigente. La
  original queda como consulta.
- **Fechas de la factura que sustituye**: la factura nueva tras una anulación y la rectificativa
  proponen la fecha de hoy, que se puede cambiar (FR-018). Como fecha de la operación conservan la
  de la factura original (F-6, art. 6.1.i; F-9), y la de expedición no puede ser anterior a ella
  (F-3 §3.1.3.1).
- **Rectificar una rectificativa**: una rectificativa vigente se corrige con «Modificar» y la causa
  correspondiente, que genera una rectificativa nueva de la rectificativa (F-9, ejemplos 4–6).
- **Anular una rectificativa**: con «Anular» deja de tener efecto y la factura que rectificaba
  vuelve a estar vigente, con su historial completo (FR-048). En una rectificativa no se ofrece
  «Modificar → no debió emitirse»: el mismo resultado se consigue anulándola y modificando después
  la original.
- **Modificar sin cambios**:
  - Se admite solo con el motivo «no debió emitirse o no llegó a entregarse». Es la forma de
    corregir una factura cuyo único error es el número (FR-010): se anula y se reemite igual, con el
    siguiente número.
  - Una rectificativa sin ningún cambio se rechaza.
- **Doble envío**: un doble clic o un reintento de red en «Emitir», «Modificar» o «Anular» nunca
  genera dos facturas ni dos correcciones (FR-047).
- **Borrador ya emitido**: si otro usuario emite el mismo borrador, el segundo intento no emite nada
  y se informa de que el borrador ya se ha emitido.
- **Borrador con fecha no válida**: si al emitir su fecha no cumple FR-018, se indica el motivo en
  el campo de la fecha para corregirla.
- **Sesión caducada con el modal abierto**: igual que en 001 (contracts/ui-rutas.md, 401 durante el
  uso). Por seguridad, lo tecleado **no se conserva**: se avisa de que la sesión ha caducado y, tras
  volver a entrar, hay que repetir la acción. Ante un error de red o de servidor sí se conserva lo
  escrito (FR-036).

## Requirements *(mandatory)*

### Functional Requirements

#### Configuración de facturación

- **FR-001**: Configuración DEBE tener una sección «Facturación», solo para administradores, con:
  - **IVA por defecto**: vale 21 al instalar y se escribe libremente, porque el tipo puede cambiar
    por ley (Clarifications, ajuste de cierre):
    - Admite cualquier porcentaje de 0 a 99,99, con hasta dos decimales.
    - **Aviso**: si el tipo no está entre los que las validaciones oficiales permiten en la fecha
      actual para una operación sujeta y no exenta (F-3 §15.1; hoy 0, 4, 10 y 21), el sistema lo
      avisa y NO DEBE guardarlo sin una confirmación expresa del administrador. La exigencia de
      confirmación la aplica el servidor, no solo la pantalla.
    - Emitir nunca se bloquea por el tipo (FR-013).
  - **Datos del emisor**: razón social o nombre y apellidos, NIF y domicilio completo (dirección,
    código postal, localidad y provincia), exigidos por F-6, art. 6.1.c, d y e.
    - **IBAN** de la cuenta en la que cobra la joyería: opcional, y no forma parte de lo necesario
      para emitir (FR-004). Si se rellena, DEBE tener la estructura de ISO 13616 (código de país,
      dos dígitos de control y hasta 34 caracteres en total), 24 caracteres si la cuenta es
      española, y el dígito de control correcto (research R-22). Se guarda sin espacios y en
      mayúsculas, y se muestra agrupado de cuatro en cuatro.
  - **Modalidad del sistema de facturación**: VERI\*FACTU o no VERI\*FACTU. Empieza sin valor
    («Sin decidir»), porque la elección está pendiente de la asesoría (Clarifications). La elige el
    administrador y DEBE fijarse antes de la feature 004. Una vez generado el primer registro, queda
    bloqueada (FR-050).
  - **Sin clave de régimen**: la clave de régimen del IVA NO se configura. El sistema la fija en
    cada registro: `01`, «Operación de régimen general», en toda factura, y `04`, «Régimen especial
    del oro de inversión», en las de oro de inversión (lista L8A de F-1; FR-052). La asesoría las
    confirma antes de producción.
  - **Próximo número de la serie ordinaria del año en curso**: solo informativo, salvo el ajuste
    de FR-010.
- **FR-002**: El NIF del emisor DEBE validarse con las mismas reglas que el de los clientes (001,
  FR-024 y FR-026).
- **FR-003**: Todo cambio en la configuración de facturación DEBE quedar en la auditoría con el
  valor anterior y el nuevo. Un cambio nunca altera facturas emitidas ni sus registros.
- **FR-004**: Mientras falte algún dato obligatorio del emisor o la modalidad, NO DEBE poder
  emitirse ninguna factura. Sí se pueden guardar borradores.

#### Tipos de factura y numeración

- **FR-005**: Esta feature emite solo **facturas completas**, siempre con un cliente identificado de
  la cartera: ordinarias y, como corrección, rectificativas. Las facturas simplificadas quedan
  fuera de alcance (Clarifications).
- **FR-006**: La serie ordinaria DEBE numerarse `FAC-AAAA-NNNN`:
  - `AAAA` es el año de la fecha de expedición.
  - `NNNN` es un correlativo de cuatro dígitos que empieza en `0001` cada año natural.
  - Si en un año se superan las 9.999 facturas, el correlativo pasa a tener más cifras sin cambiar
    el resto del formato.
- **FR-007**: El número definitivo DEBE asignarse en el momento de emitir, dentro de la misma
  operación que genera el registro de alta. La asignación debe ser segura cuando hay emisiones
  simultáneas: sin huecos, sin duplicados y sin reutilizar números (constitución, "Numeración").
- **FR-008**: Un número ya usado NO DEBE volver a usarse nunca, ni siquiera el de una factura
  anulada, que sigue constando en su serie (F-4, aclaración 6; F-5).
- **FR-009**: Las facturas rectificativas DEBEN numerarse en una serie propia, distinta de la
  ordinaria (F-6, art. 6.1.a, 2.º). Su formato es `REC-AAAA-NNNN`, con las mismas reglas de FR-006
  y la misma asignación segura de FR-007.
- **FR-010**: El número de una factura NUNCA se introduce a mano. En el modal se muestra como dato
  de solo lectura: «Se asigna al emitir» en un borrador, y el número definitivo en una factura
  emitida. Corregir la numeración solo es posible de dos formas:
  - **Una factura concreta con número erróneo**: se anula y se reemite con el siguiente número
    (FR-024).
  - **El contador de la serie ordinaria del año en curso**: un administrador puede ajustar al alza
    el próximo número en cualquier momento. Las condiciones son:
    - El valor debe ser mayor que el que ya correspondería (último número usado + 1, incluidos
      los anulados). Así el ajuste siempre salta al menos un número.
    - El motivo es obligatorio y queda en la auditoría.
    - Antes de guardar, se avisa de cuántos números quedarán sin usar.
    - El ajuste es seguro frente a emisiones simultáneas: nunca provoca un duplicado.

#### Contenido e importes de la factura

- **FR-011**: Cada factura emitida DEBE tener:
  - Fecha de expedición.
  - Cliente destinatario, elegido entre los clientes activos.
  - Al menos una línea. En una rectificativa puede no haber ninguna (devolución total).
  - Autor y fechas de creación y emisión.

  Un borrador puede guardarse incompleto, sin cliente o sin líneas. Los requisitos se comprueban
  al emitir.
- **FR-012**: Cada línea DEBE tener:
  - **Unidades**: mayor que cero, con hasta dos decimales.
  - **Descripción**: obligatoria, de hasta 500 caracteres.
  - **Precio unitario sin IVA**: cero o mayor, con dos decimales.

  El importe de la línea lo calcula el servidor.
- **FR-013**: El tipo de IVA de cada línea DEBE ser el de la configuración vigente al emitir, y se
  guarda en la propia línea (constitución II). En el modal no hay selector de tipo. La etiqueta de
  los totales muestra el tipo aplicado, p. ej. «IVA (21 %)». Al emitir no se vuelve a comprobar el
  tipo contra la lista de la AEAT: el aviso se da al configurarlo (FR-001). La única excepción es
  la factura de oro de inversión, cuyas líneas van sin tipo ni cuota (FR-052).
- **FR-014**: El servidor DEBE calcular y devolver:
  - El importe de cada línea.
  - La base imponible y la cuota de cada tipo de IVA.
  - La base total, la cuota total y el total de la factura.

  La web solo previsualiza y nunca envía importes calculados. Si una petición los incluyera, el
  servidor la rechazaría con un error de validación (constitución VI).
- **FR-015**: Una única política de redondeo para todo el sistema:
  - El importe de cada línea se redondea al céntimo.
  - La base de cada tipo es la suma de los importes de sus líneas.
  - La cuota de cada tipo se calcula sobre su base y se redondea al céntimo.
  - El medio céntimo siempre se redondea alejándose de cero.

  La política DEBE contrastarse con las tolerancias oficiales de validación (F-3) antes de la
  implementación (constitución II).
- **FR-016**: Al emitir, la factura DEBE guardar una copia de los datos del emisor, IBAN incluido
  si lo hay, y del destinatario, tal como están en ese momento. Los cambios posteriores en la
  configuración o en la ficha del cliente no alteran la factura emitida.
- **FR-017**: Para emitir una factura completa, el destinatario DEBE tener su identificación
  fiscal y su domicilio: dirección, código postal y localidad (F-6, art. 6.1.c, d y e). Si falta
  algo, el sistema lo indica y ofrece abrir la ficha del cliente.
- **FR-018**: La fecha de expedición es editable en toda factura: nueva, borrador, la nueva tras
  una anulación y la rectificativa (Clarifications, «cambio tras la implementación»). Va en hora de
  España peninsular y propone la de hoy. Solo tiene los límites que valida la AEAT:
  - **Superior**: NO DEBE ser posterior al día actual (F-3 §3.1.3.1, error 1112).
  - **Inferior**: NO DEBE ser anterior al 28/10/2024 (F-3 §3.1.3.1, error 1152).
  - **Correcciones**: NO DEBE ser anterior a la fecha de la operación (F-3 §3.1.3.1, error 1146:
    solo se admite con las claves de régimen 14 y 15, que no se usan).
  - **Sin límites propios**: puede ser anterior a la de otras facturas ya emitidas de su serie y de
    cualquier año. El número se toma siempre de la serie del año de esa fecha.
  - **Pendiente**: que la fecha pueda ser anterior al día de emisión está por validar con la
    asesoría (research R-17, Q-9).

  La fecha de la operación solo se indica si es distinta de la de expedición (F-6, art. 6.1.i).
  No se pide al crear una factura. La factura nueva tras una anulación y la rectificativa heredan
  como fecha de la operación la de la original, o su fecha de expedición si no tenía ninguna (F-9:
  «la fecha de realización de la operación correspondiente a la factura original»). Se muestra en
  solo lectura.
- **FR-045**: La descripción del objeto de la factura, obligatoria en el registro con un máximo de
  500 caracteres (F-1), DEBE formarse automáticamente al emitir:
  - Se unen las descripciones de las líneas, en su orden y separadas por «; ».
  - Si el resultado supera los 500 caracteres, se recorta a 500, terminando en «…».
  - En una rectificativa sin líneas, la descripción es «Devolución total de la factura
    <número rectificado>».
  - No se pide ningún dato adicional en el modal.
- **FR-052**: Factura de **oro de inversión** sin IVA (Clarifications, ajuste de cierre):
  - **Interruptor**: el modal DEBE ofrecer, junto al IVA de los totales, la casilla «Sin IVA (oro
    de inversión)», desmarcada por defecto. Afecta a toda la factura: no hay elección por línea.
    Está en la factura nueva, en el borrador, que la guarda, y en «Modificar». La pueden marcar
    todos los que crean y emiten facturas, empleados incluidos (Clarifications). Marcarla en
    «Modificar» sigue exigiendo ser administrador, igual que modificar (FR-023).
  - **Importes**: con la casilla marcada, las líneas van sin tipo ni cuota, y toda la base es
    exenta. La cuota total es 0 y el total de la factura es igual a su base. La previsualización y
    los totales muestran «Base exenta», «IVA 0,00 €» y el total.
  - **Mención obligatoria** (F-6, art. 6.1.j): la factura DEBE llevar «Operación exenta de IVA
    (art. 140 bis.Uno.1.º de la Ley 37/1992)». Se ve en el modal y en la consulta, y la llevará el
    PDF de la feature 003.
  - **Registro de alta** (F-1; F-3 §15.5 y §15.6.3): el desglose de la factura lleva la clave de
    régimen `04`, la causa de exención `E6` y la base en `BaseImponibleOimporteNoSujeto`, sin
    `CalificacionOperacion`, `TipoImpositivo` ni `CuotaRepercutida`. La codificación completa de
    los campos está en research.
  - **Qué es oro de inversión**: lo decide quien factura, según F-11, art. 140. Por ejemplo,
    lingotes o láminas de ley igual o superior a 995 milésimas, o las monedas que cumplen sus
    requisitos. El sistema no lo comprueba.
- **FR-053**: El IBAN copiado en una factura emitida (FR-016) DEBE mostrarse en su consulta, en el
  bloque de pago. Si la factura no tiene IBAN, ese bloque no aparece. La consulta DEBE mostrar
  también la mención de FR-052 en las facturas de oro de inversión.

#### Ciclo de vida: borrador y emisión

- **FR-019**: Un borrador DEBE poder crearse, editarse y borrarse por cualquier usuario autenticado,
  sin número definitivo ni registro de facturación (constitución III; F-4, aclaración 6). El
  borrado es definitivo y queda en la auditoría.
- **FR-020**: La edición concurrente de un borrador DEBE detectarse igual que la de un cliente
  (001, FR-030): nunca se sobrescriben cambios ajenos sin aviso.
- **FR-021**: Emitir DEBE pedir una confirmación que explique que la factura no podrá editarse y
  que los cambios posteriores se harán mediante corrección. La emisión es atómica: número,
  factura, registro de alta y huella se guardan juntos o no se guarda nada.
- **FR-022**: Una factura emitida y su registro NO DEBEN poder modificarse ni borrarse por ningún
  medio. La protección DEBE estar en el propio almacenamiento y resistir también un intento directo
  con las credenciales del servicio y con las del propietario de los datos (constitución III).
  Técnicamente se sigue el patrón de la auditoría de 001.

#### Modificar una factura emitida (corrección trazable)

- **FR-023**: Solo un administrador DEBE poder «Modificar» la factura vigente de una serie,
  sea ordinaria o rectificativa. El modal se abre con los datos precargados, y son editables el
  cliente, las líneas, la fecha de expedición y la casilla «Sin IVA (oro de inversión)» (FR-052).
  El número no es editable (FR-010), y la fecha de la operación se hereda (FR-018).
- **FR-024**: Al guardar una modificación, el modal DEBE pedir el motivo, que es obligatorio y se
  elige entre dos opciones, con un texto libre adicional. Según el motivo, el sistema genera la
  corrección que prescribe la normativa (F-4, aclaración 17; F-5; F-6, art. 15):
  - **«La factura no debió emitirse o no llegó a entregarse al cliente»**, casos 1 y 2.d:
    1. Registro de anulación de la original.
    2. Emisión de una factura ordinaria nueva con los datos corregidos y el siguiente número de la
       serie `FAC`.
  - **«Hay que corregir una factura ya entregada»**, caso 2.a: emisión de una factura
    rectificativa **por sustitución** en la serie `REC`, con los datos corregidos. Debe:
    - Identificar la factura rectificada.
    - Expresar el importe de la rectificación junto a los datos tal como quedan (F-6, art. 15.4
      y 15.5; F-9, opción 1).

    El modal pide además la causa (F-9):
    - **«Devolución, descuento o cambio de precio posterior a la venta, o IVA mal aplicado»**:
      tipo R1.
    - **«Error en datos o importes de la factura»**: tipo R4.

  La codificación completa de los campos del registro está en research R-4.
  La declaración del motivo y su texto quedan guardados con la corrección.

  El servidor DEBE rechazar cualquier modificación o anulación que pida un empleado. Los empleados
  no ven esas acciones en el modal.
- **FR-025**: La factura emitida vigente DEBE ofrecer también «Anular», solo a los administradores,
  para el caso 2.d sin factura nueva, por ejemplo una factura duplicada por error:
  - Exige declarar que la factura no debió emitirse e indicar un motivo.
  - Genera solo el registro de anulación.
  - No se ofrece sobre una factura ya anulada ni sobre una rectificada. Sí se ofrece sobre una
    rectificativa vigente (FR-048).
- **FR-026**: La factura original y sus registros DEBEN conservarse intactos:
  - La original y su corrección quedan enlazadas en ambos sentidos.
  - El historial de la factura DEBE mostrar cada corrección con su tipo, fecha, autor, motivo y
    la factura o registro que la materializa.
  - Las facturas anuladas o rectificadas quedan en modo consulta, con una marca visible y acceso
    directo a la vigente que las sustituye, si la hay.
  - Una factura puede acumular varias correcciones a lo largo del tiempo: por ejemplo, una
    rectificación que después se anula (FR-048). En cada momento tiene como mucho una corrección
    en vigor.
- **FR-027**: Toda corrección DEBE generar sus registros de facturación, encadenados según FR-029:
  - **Anulación**: registro de anulación de la original y, si se reemite, registro de alta de la
    factura nueva.
  - **Rectificativa**: su registro de alta.

  El registro de alta de subsanación (caso 2.b, datos internos del registro) no se ofrece en esta
  feature, porque aquí esos datos se derivan de la configuración y no los edita el usuario. Llega
  con la remisión a la AEAT (feature 004), que es donde surgen los rechazos que lo requieren.

#### Registro de facturación y huella

- **FR-028**: Cada emisión, rectificativa incluida, y cada anulación DEBE generar su registro de
  facturación de alta o de anulación. El contenido, los formatos y las longitudes son exactamente
  los de los diseños de registro oficiales (F-1), y cada campo se cita en el plan.
- **FR-029**: Cada registro DEBE llevar su huella SHA-256, calculada según la especificación
  oficial (F-2) y encadenada con la del registro inmediatamente anterior del sistema, sea de alta
  o de anulación. El primer registro de la cadena se marca como tal. La cadena DEBE mantenerse
  lineal aunque haya operaciones simultáneas.

  Antes de generar cada registro, el sistema DEBE comprobar dos cosas sobre el último registro
  (F-10, Orden art. 7.i):
  - Que está bien encadenado, recalculando su huella.
  - Que su fecha de generación no es más de un minuto posterior a la actual.

  Si alguna falla, no genera el registro, no emite nada y avisa (F-8, art. 8.2.a: «detecte y
  avise»).
- **FR-030**: Cada registro DEBE guardar la modalidad del sistema de facturación con la que se
  generó (constitución IV) y un estado de remisión. En esta feature, el estado de remisión queda
  como «pendiente» porque la remisión llega con la feature 004.
- **FR-031**: El sistema DEBE ofrecer una comprobación de la integridad de la cadena y de los
  documentos. En orden de la cadena:
  - Recalcula cada huella y su enlace con el registro anterior.
  - Coteja el contenido guardado de cada registro con el que resulta de su factura.
  - Coteja los totales y el desglose de cada factura con los que resultan de sus líneas.

  Informa de si todo está íntegro o de cuál es el primer registro o factura discrepante. En esta
  feature se lanza desde la consola de administración del servidor.

#### Listado y búsqueda

- **FR-032**: El listado de facturas DEBE seguir la misma lógica que el de clientes (001, FR-031 a
  FR-033):
  - Paginado en el servidor, con 25 facturas por página por defecto y 100 como máximo.
  - Búsqueda, filtros, orden y página reflejados en la dirección de la pantalla.
  - Las acciones de todas las filas siempre visibles.
- **FR-033**: Columnas: número, fecha de expedición, cliente, identificación fiscal, base
  imponible, IVA (cuota), total y acciones. Los importes van en euros con formato español. Un
  borrador muestra «Borrador» en lugar del número. Una factura anulada o rectificada muestra una
  marca discreta junto a su número. Una factura de oro de inversión (FR-052) muestra «Exenta» en
  la columna del IVA. NO hay columna de estado ni indicadores.
  - **Según el ancho** (medido, research R-12): la identificación fiscal se muestra desde 1280 px,
    y la base imponible y el IVA desde 1440 px. El número, la fecha, el cliente, el total y las
    acciones se ven siempre; por debajo de 768 px, tarjetas (FR-049).
- **FR-034**: La búsqueda DEBE encontrar coincidencias parciales en el número, el nombre del
  cliente y su identificación, sin distinguir mayúsculas ni tildes, con las mismas normas de
  término que en clientes (001, FR-032).
- **FR-035**: Filtros y orden:
  - **Año**: el año en curso por defecto, o todos.
  - **Mes**: todos por defecto.
  - **Orden**: más recientes (por defecto), más antiguas, total mayor y total menor.

  Todos los órdenes llevan un desempate estable, para que la paginación nunca duplique ni omita
  facturas.
- **FR-036**: Estados de pantalla, confirmaciones y avisos iguales que en 001 (FR-057 y FR-058):
  - Carga sin saltos.
  - Error con opción de reintentar.
  - Dos estados vacíos: «no hay resultados» y «todavía no hay facturas».
  - Aviso breve tras cada acción.
  - Confirmación al descartar cambios.

#### Modal de factura

- **FR-037**: Crear, consultar, editar y modificar una factura DEBE hacerse en un modal por encima
  del listado, que sigue visible detrás. El modal tiene tres secciones:
  - **Datos de emisión**:
    - Número, en solo lectura (FR-010).
    - Fecha de expedición y, si la hay, fecha de la operación.
    - Cliente, con el resumen de nombre, identificación, dirección, localidad y provincia.
  - **Detalle**: tabla de líneas con unidades, descripción, precio unitario, importe y quitar
    línea, más el botón «Añadir línea».
  - **Totales**: base imponible, IVA con su tipo y total de la factura, junto con la casilla «Sin
    IVA (oro de inversión)» (FR-052). En la consulta de una factura emitida, además, el bloque de
    pago con el IBAN (FR-053).
- **FR-038**: Botones del modal según el caso:
  - **Nueva**: «Cancelar», «Guardar borrador» y «Emitir factura».
  - **Borrador**: además, «Eliminar borrador».
  - **Emitida vigente**: «Cerrar», «Anular» y «Modificar». Los empleados solo ven «Cerrar».
  - **Anulada o rectificada**: solo «Cerrar».
- **FR-039**: El modal DEBE cumplir `docs/DESIGN.md`:
  - Elevación de nivel 2, esquinas a 0 px y campos monetarios con el símbolo € y cifras tabulares.
  - Total destacado en la tipografía de cifras.
  - Botón principal para emitir y secundarios para las demás acciones.
  - Uso completo con teclado, foco atrapado en el modal y devuelto al cerrarlo, y cierre con
    Escape sujeto a la confirmación de cambios (001, FR-052).
- **FR-040**: En móvil (menos de 768 px), el modal DEBE ocupar la pantalla completa y cada línea se
  presenta apilada, sin desplazamiento horizontal de la página.
- **FR-046**: Junto al selector de cliente, el modal DEBE ofrecer «Nuevo cliente»:
  - Abre por encima el formulario de alta de cliente de 001, con sus mismas validaciones. Un
    duplicado de identificación se trata igual que en 001.
  - Al guardarlo, vuelve al modal con el cliente nuevo elegido.
  - Al cancelarlo, vuelve sin cambios.
  - En ambos casos se conserva lo ya escrito en la factura.
  - Con las dos capas abiertas, Escape cierra solo la de encima, y el foco vuelve al botón «Nuevo
    cliente».
  - Si el cliente nuevo no tiene domicilio completo, se avisa en el resumen de que no se podrá
    emitir hasta completarlo (FR-017).
- **FR-049**: Detalle de uso del modal y del listado:
  - **Listado en móvil**: cada factura es una tarjeta con el número (o «Borrador»), la fecha, el
    cliente, el total, la marca de estado si la hay y su acción.
  - **Acciones con nombre accesible**: «Abrir borrador de {cliente}» o «Ver factura {número}».
  - **Líneas**:
    - Se puede quitar cualquier línea, también la última. Sin líneas se muestra «Añade la primera
      línea».
    - Con 100 líneas se desactiva «Añadir línea».
  - **Escritura de cifras**: unidades y precios admiten la coma decimal y los puntos de miles
    («1.200,50»). Un formato no válido se indica en el propio campo.
  - **Tras emitir**: el modal se cierra con el aviso «Factura {número} emitida».
  - **Tras «Guardar borrador» en una factura nueva**: el modal pasa al modo borrador de ese
    borrador, con el aviso «Borrador guardado».
  - **Tras modificar**: el modal pasa a mostrar la factura nueva en consulta, con el aviso de lo
    generado, por ejemplo «Se ha emitido REC-2026-0001. FAC-2026-0007 queda rectificada».
  - **Tras anular**: el modal sigue en la factura, ya marcada como anulada.
  - **Año sin facturas**: si el año del filtro no tiene facturas pero otros años sí, el estado vacío
    dice «No hay facturas en {año}» y ofrece «Ver todos los años».
  - **«Limpiar filtros»**: vuelve a los valores por defecto.

#### Integración con el resto del sistema

- **FR-041**: El menú lateral, a la izquierda, DEBE activar la entrada Facturas.
  Presupuestos sigue deshabilitada con la marca «Próximamente».
- **FR-042**: Un cliente con cualquier factura, sea borrador o emitida, NO DEBE poder borrarse
  (001, FR-037). El sistema responde con el motivo y sugiere desactivarlo.
- **FR-043**: DEBEN quedar en la auditoría:
  - La creación, la modificación y el borrado de borradores.
  - La emisión.
  - Cada corrección.
  - La comprobación de integridad.
  - Los cambios de configuración de facturación.

  Los importes que aparecen en la auditoría se guardan como texto decimal exacto, nunca como número
  de coma flotante (constitución II).
- **FR-044**: Los datos de ejemplo del entorno de desarrollo DEBEN incluir facturas ficticias,
  emitidas y en borrador, de varios meses. Su carga sigue prohibida en producción (001, FR-045).
- **FR-047**: Emitir, modificar y anular DEBEN ser **idempotentes** frente a un doble envío. Si una
  petición se repite con la misma clave de operación, devuelve el resultado de la primera y no
  genera nada nuevo. Una clave ya usada en otra operación o sobre otro documento se rechaza
  (research R-18).
- **FR-048**: Al anular una rectificativa vigente, la factura que rectificaba DEBE volver a estar
  vigente:
  - Se puede consultar, anular o modificar de nuevo, sin perder su historial, en el que la
    rectificación figura como anulada.
  - Solo se genera el registro de anulación de la rectificativa. La factura original no genera
    ningún registro nuevo, porque su alta sigue siendo válida.
- **FR-050**: Una vez generado el primer registro de facturación, la modalidad NO DEBE poder
  cambiarse desde esta feature.
  - Razón: el cambio con registros ya generados está sujeto a la permanencia y a la renuncia de
    F-10, art. 17, que gestiona la remisión (feature 004).
  - El administrador ve la modalidad bloqueada y el motivo.
- **FR-051**: Los registros de actividad del servidor NO DEBEN contener datos personales de los
  clientes ni importes, igual que en 001. Solo pueden registrar identificadores internos, números
  de factura y el tipo de operación.

### Key Entities *(include if feature involves data)*

- **Configuración de facturación**: IVA por defecto, datos del emisor con el IBAN opcional y
  modalidad. Hay una sola, y sus cambios se auditan.
- **Borrador de factura**: factura en preparación.
  - Fecha, cliente, líneas, si es de oro de inversión, autor y versión para detectar la edición
    concurrente.
  - Sin número definitivo ni registro. Se puede editar y borrar.
- **Factura emitida**: documento expedido e inalterable.
  - Número y serie, fecha de expedición, copia de los datos del emisor (IBAN incluido) y del
    destinatario, líneas con su tipo de IVA, desglose por tipo, totales, autor y fecha de emisión.
  - Si es de oro de inversión: su clave de régimen `04` y un desglose exento, sin tipo ni cuota.
  - Si es rectificativa, la referencia a la factura que rectifica.
  - Si es el caso, su estado derivado: anulada o rectificada.
- **Línea de factura**: unidades, descripción, precio unitario sin IVA, tipo de IVA e importe. En
  una factura de oro de inversión, la línea no tiene tipo de IVA.
- **Serie y contador**: uno por serie (`FAC` ordinaria y `REC` rectificativa) y año natural.
  - Guarda el último número asignado y serializa las asignaciones simultáneas.
  - Los ajustes al alza de la serie ordinaria se hacen con motivo y quedan auditados.
- **Registro de facturación**: extracto oficial de una factura, de alta o de anulación.
  - Campos de los diseños oficiales (F-1), huella, referencia al registro anterior, modalidad,
    estado de remisión y fecha y hora de generación.
  - Inalterable, y forma una cadena lineal.
- **Corrección**: enlace entre la factura original y lo que la corrige (rectificativa por
  sustitución, anulación con factura nueva o anulación sola), con motivo declarado, texto, autor y
  fecha. Es lo que alimenta el historial.
- **Cliente** (de 001): destinatario. Si tiene facturas, no se puede borrar.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un empleado crea y emite una factura de tres líneas para un cliente de la cartera en
  menos de 2 minutos desde que pulsa «Nueva factura».
- **SC-002**: En 200 emisiones repartidas entre 10 usuarios simultáneos, los números resultantes
  son consecutivos, sin ningún hueco ni duplicado, y los registros forman una única cadena sin
  bifurcaciones.
- **SC-003**: En un juego de casos de cálculo que incluye medios céntimos, cantidades con
  decimales e importes grandes, el 100 % de las bases, cuotas y totales coinciden al céntimo con
  el resultado de referencia calculado a mano con la política de FR-015.
- **SC-004**: La comprobación de integridad da por íntegra el 100 % de las cadenas generadas sin
  alterar. Detecta el 100 % de las alteraciones introducidas a propósito en una base de pruebas y
  señala el registro afectado.
- **SC-005**: Ningún intento de modificar o borrar una factura emitida o un registro de
  facturación prospera, incluidos los intentos directos sobre el almacenamiento con las
  credenciales del servicio y con las del propietario de los datos. Además, el servidor rechaza el
  100 % de los intentos de un empleado de anular o modificar una factura emitida, o de cambiar la
  configuración de facturación.
- **SC-006**: Tras una modificación de una factura emitida, en el 100 % de los casos:
  - La original sigue consultable con sus datos iniciales.
  - La corrección existe y está encadenada.
  - El historial muestra ambas.
  - Ningún número se ha reutilizado.
- **SC-007**: Con 20.000 facturas, el 95 % de las búsquedas y cambios de filtro muestran resultados
  en menos de 1 segundo. Se mide en el entorno local de pruebas de extremo a extremo.
- **SC-008**: El listado y el modal no provocan desplazamiento horizontal de la página a 360, 768 y
  1440 px. El 100 % de las filas de una página completa muestran sus acciones a 768, 1024, 1280,
  1440 y 1536 px.
- **SC-009**: Todas las pantallas de la feature superan la revisión de conformidad con
  `docs/DESIGN.md`: colores solo de sus tokens, esquinas a 0 px, tipografías y componentes
  definidos.
- **SC-010**: Las pruebas de extremo a extremo cubren las historias P1 y P2 y pasan en su totalidad
  antes de cerrar la feature.
- **SC-011**: En pruebas de doble envío de «Emitir», «Modificar» y «Anular», tanto simultáneos como
  repetidos, cada operación genera exactamente una factura o corrección y sus registros: 0
  duplicados.
- **SC-012**: Un administrador cambia el IVA por defecto a cualquier tipo de 0 a 99,99 % sin
  intervención técnica. El 100 % de los intentos de guardar un tipo fuera de la lista de la AEAT sin
  confirmarlo se rechazan.
- **SC-013**: En el 100 % de las facturas de oro de inversión emitidas, la cuota es 0, el total es
  igual a la base y el registro lleva la clave `04` y la exención `E6`, sin tipo ni cuota. La
  comprobación de integridad (FR-031) da por íntegras las cadenas que mezclan facturas exentas y
  sujetas, incluidas las emitidas antes del ajuste de cierre.

## Conformidad con el sistema de diseño y desviaciones del mockup

Conforme a la constitución (restricción "Sistema de diseño"), los mockups son orientativos y
mandan `docs/DESIGN.md` y esta spec. Diferencias deliberadas:

| Elemento del mockup | Decisión en esta feature | Motivo |
|---|---|---|
| Menú lateral a la derecha | Menú a la **izquierda** | Decisión del responsable, como en 001 |
| Marca y lema en la cabecera; usuario "Carlos Martínez" | Cabecera de 001: contexto "Gestión de facturación", fecha y menú de usuario | Coherencia con la estructura ya existente (001, FR-038) |
| Indicadores «Facturado», «Pendiente de cobro» y «Vencido» | Sin indicadores | Decisión del responsable (2026-09-28) |
| Columna «Estado» con chips redondeados (Cobrada, Pendiente, Vencida, Emitida, Pagada) | Sin columna de estado. Borrador, anulada y rectificada se marcan en la columna del número | Decisión del responsable. Los chips redondeados y el azul de «Pagada» incumplen DESIGN.md (esquinas a 0 px, colores solo de tokens) |
| Filtros «Cliente» y «Estado» | El cliente se busca con la búsqueda. No hay filtro de estado | Misma lógica que clientes (FR-034, FR-035) |
| Campo «Nº de factura» editable al crear | Número en solo lectura, asignado por el servidor al emitir. Una factura con número erróneo se anula y se reemite, y el contador se ajusta en Configuración (FR-010, FR-024) | Constitución (principio III y "Numeración"); correlatividad del ROF (F-6, art. 6.1.a) |
| «IVA (21%)» fijo | La etiqueta muestra el tipo vigente de Configuración. Junto a ella, la casilla «Sin IVA (oro de inversión)» | Decisión del responsable: el IVA se configura (FR-013), y la venta de oro de inversión va sin IVA (FR-052) |
| Botón «Nueva factura» con letra serif y caja mixta; esquinas redondeadas en campos y botones | Botón primario de DESIGN.md: Manrope en mayúsculas con espaciado; esquinas a 0 px | DESIGN.md prevalece sobre el mockup |
| Paginación numérica con recuadro redondeado | Paginación del listado de clientes | Coherencia con 001 y DESIGN.md |

Desviaciones de `docs/DESIGN.md`: **ninguna**.

## Fuentes normativas citadas

- **F-1**: AEAT, *Diseños de registro VERI\*FACTU* (`DsRegistroVeriFactu.xlsx`), versión 1.0
  (001, F-1).
  - URL:
    `https://www.agenciatributaria.es/static_files/AEAT_Desarrolladores/EEDD/IVA/VERI-FACTU/DsRegistroVeriFactu.xlsx`.
  - Los campos del registro de alta y de anulación se transcriben y citan en el plan (research).
  - Ajuste de cierre (descarga del 2026-09-30, mismo SHA-256 que en research):
    - Lista L8A: `01` «Operación de régimen general» y `04` «Régimen especial del oro de
      inversión».
    - Lista L10: `E6` «Exenta por otros». `E1` a `E5` son las exenciones de los arts. 20 a 25 de
      la Ley del IVA, y la del oro de inversión es otra (F-11).
- **F-2**: AEAT, *Detalle de las especificaciones técnicas para generación de la huella o hash de
  los registros de facturación*, versión 0.1.2 (27/08/2024).
  - URL:
    `https://www.agenciatributaria.es/static_files/AEAT_Desarrolladores/EEDD/IVA/VERI-FACTU/Veri-Factu_especificaciones_huella_hash_registros.pdf`.
  - SHA-256: `f4334c254bb875b417247b54315199f89d75a8c4814dfd1e86efec562653d7de`.
  - Índice oficial:
    `https://sede.agenciatributaria.gob.es/Sede/iva/sistemas-informaticos-facturacion-verifactu/informacion-tecnica.html`.
  - El orden de concatenación y los ejemplos oficiales se transcriben en research R-2.
- **F-3**: AEAT, *Validaciones y errores VERI\*FACTU*, v1.2.2 (08/04/2026) (001, F-3).
  - URL:
    `https://www.agenciatributaria.es/static_files/AEAT_Desarrolladores/EEDD/IVA/VERI-FACTU/Validaciones_Errores_Veri-Factu.pdf`.
  - SHA-256: `426eb926fc098a36a163f66ca5f40d9e0847ca23300bbe5008979832d3513440`.
  - Las tolerancias de importes, los tipos de IVA admitidos y las reglas de fechas se transcriben
    en research R-10 y R-17.
  - Ajuste de cierre (descarga del 2026-09-30, mismo SHA-256):
    - §15.5: con `OperacionExenta` informada, no se pueden informar `TipoImpositivo`,
      `CuotaRepercutida`, `TipoRecargoEquivalencia` ni `CuotaRecargoEquivalencia`.
    - §15.6.3: «si ClaveRegimen es igual a 04, CalificacionOperacion solo puede ser S2, o bien
      OperacionExenta».
- **F-4**: AEAT, *Aclaraciones a dudas de los desarrolladores*, versión 1.3 (4 de diciembre de
  2025).
  - URL:
    `https://sede.agenciatributaria.gob.es/static_files/AEAT_Desarrolladores/EEDD/IVA/VERI-FACTU/FAQs-Desarrolladores.pdf`.
  - Consulta: 2026-09-28. SHA-256:
    `73906dc8afbbb9da35f6cb489980352b42aed66d48828fd62a00168883c09d5e`.
  - **Aclaración 6**, "Prohibición de numeración duplicada de un registro":
    - Los borradores y las prefacturas son una operación ordinaria.
    - Hasta validar la factura, cualquier alteración previa al registro es lícita.
    - No se puede reutilizar la numeración de ninguna factura expedida, ni siquiera las de prueba,
      que se anulan.
  - **Aclaración 17**, "Forma de proceder ante errores cometidos al facturar":
    1. Antes de expedir, el error se corrige sin más.
    2. Después de expedir, depende del error:
       - a) Previsto en el ROF: factura rectificativa.
       - b) No previsto en el ROF, pero afecta a datos internos del registro: se corrige y se
         genera un registro de alta de subsanación.
       - c) Ni en el ROF ni en el registro: se corrige sin registro nuevo.
       - d) La factura no debió emitirse: registro de anulación.
    - Añade que la anulación está pensada sobre todo para facturas que no llegaron al cliente, y
      que los registros de anulación y de subsanación deben ser "muy poco frecuentes".
- **F-5**: AEAT, preguntas frecuentes VERI\*FACTU (sede electrónica; páginas actualizadas el
  22/07/2026; consulta 2026-09-28):
  - **"Registros de facturación: alta"**. Un registro ya producido no se altera. Para cambiar un
    dato se genera otro registro que lo complete, modifique o anule, sea de anulación completa o
    de subsanación. Las menciones de la factura que no están en el registro se subsanan
    directamente.
  - **"Registros de facturación: anulación"**. Las facturas emitidas, aunque sean erróneas, se
    mantienen con su numeración. El registro de alta erróneo se conserva, con un registro de
    anulación vinculado, y ambos aparecen en los listados.
  - URL base:
    `https://sede.agenciatributaria.gob.es/Sede/iva/sistemas-informaticos-facturacion-verifactu/preguntas-frecuentes/`.
- **F-6**: Reglamento por el que se regulan las obligaciones de facturación, RD 1619/2012
  (BOE-A-2012-14696, texto consolidado con última actualización publicada el 31/03/2026, consulta
  2026-09-28):
  - **Art. 4**: supuestos de factura simplificada, hasta 400 € o, en ventas al por menor, hasta
    3.000 €.
  - **Art. 6.1**: contenido de la factura.
    - a) Numeración correlativa dentro de cada serie, con series específicas obligatorias, entre
      ellas la de rectificativas.
    - b) Fecha.
    - c) Nombre o razón social de emisor y destinatario.
    - d) NIF.
    - e) Domicilio de ambos.
    - f) Descripción, con el precio unitario sin impuesto.
    - g) Tipo impositivo, etc.
    - j) Si la operación está exenta, «una referencia a las disposiciones correspondientes de la
      Directiva 2006/112/CE […] o a los preceptos correspondientes de la Ley del Impuesto o
      indicación de que la operación está exenta» (redacción vigente desde el 07/12/2023,
      consultada el 2026-09-30).
  - **Art. 7.1.a**: las simplificadas llevan serie separada de las completas del mismo año.
  - **Art. 15**: rectificativas. Son obligatorias cuando la factura no cumple los arts. 6 o 7 o
    cuando las cuotas se determinaron mal, y se hacen con una nueva factura que identifica la
    rectificada.
- **F-7**: Ley 58/2003, General Tributaria (BOE-A-2003-23186), art. 201 bis, añadido por la Ley
  11/2021, verificado en el BOE el 2026-09-28. El apartado 1.d tipifica como infracción los
  sistemas que "permitan alterar transacciones ya registradas incumpliendo la normativa
  aplicable", con multa de 150.000 € por ejercicio y tipo de sistema (apartado 4).
- **F-8**: Reglamento de requisitos de los sistemas informáticos de facturación, RD 1007/2023
  (RRSIF), BOE-A-2023-24840, texto consolidado con última actualización publicada el 03/12/2025.
  Se citan:
  - Art. 8.2: integridad, trazabilidad y conservación.
  - Art. 9: registro «simultáneo o inmediatamente anterior» a la expedición.
  - Art. 10: contenido del alta.
  - Art. 11: anulación «cuando se haya emitido erróneamente una factura».
  - Art. 12: huella y firma.
  - Art. 16: VERI\*FACTU; exención de firma y permanencia hasta fin del año natural.

  Transcripción en research R-1.
- **F-9**: AEAT, preguntas frecuentes VERI\*FACTU, página "Procedimientos de facturación"
  (actualizada el 22/07/2026; consulta 2026-09-28):
  - Criterio de las claves F1, R1 y R4. R4 incluye «cuando se haya consignado erróneamente algún
    dato no monetario de la factura».
- **F-11**: Ley 37/1992, del Impuesto sobre el Valor Añadido (BOE-A-1992-28740), título IX,
  capítulo V, «Régimen especial del oro de inversión», añadido por la Ley 55/1999 y en vigor desde
  el 01/01/2000. Consultado en la API de datos abiertos del BOE el 2026-09-30:
  - **Art. 140**: concepto de oro de inversión. Por ejemplo, los «lingotes o láminas de oro de ley
    igual o superior a 995 milésimas» con el peso del anexo, y las monedas de oro que reúnen sus
    requisitos.
  - **Art. 140 bis.Uno.1.º**: «Estarán exentas del impuesto […] Las entregas, adquisiciones
    intracomunitarias e importaciones de oro de inversión».
  - **Art. 140 ter**: la renuncia a la exención solo cabe si el transmitente produce oro de
    inversión o transforma oro en oro de inversión, y el adquirente es empresario o profesional.
  - Rectificativa por sustitución (opción 1): importes correctos en el desglose, y la «base
    rectificada» y la «cuota rectificada» de la original.
  - Fecha de operación de la rectificativa: la de la factura original.
  - Factura emitida por error: anulación y, si procede, nueva factura «con un número de factura o
    fecha de expedición diferente».
- **F-10**: Orden HAC/1177/2024 (BOE-A-2024-22138, con la corrección de errores BOE-A-2024-23180):
  - Art. 3: exenciones en VERI\*FACTU.
  - Art. 7: encadenamiento, primer registro, cadena única y margen de un minuto.
  - Art. 13: campos de la huella.
  - Art. 14: firma XAdES en no VERI\*FACTU.
  - Art. 17: permanencia en VERI\*FACTU hasta el 31 de diciembre.

  Transcripción en research R-1.
- **Preguntas abiertas** (se resuelven en `clarify` o en el research del plan): las de 001,
  research R-20.4, que afectan al destinatario del registro.

## Fuera de alcance

- **Otras features**:
  - El PDF de la factura y el código QR (003).
  - La remisión de registros a la AEAT, los certificados y la firma electrónica de los registros
    (004).
  - Los presupuestos y su conversión en factura (005).
- **Cobro**: estado de cobro, pagos, vencimientos, recordatorios e indicadores de facturación.
- **Tipos de IVA**: varios tipos en una misma factura, facturas que mezclan líneas exentas y
  sujetas, operaciones no sujetas, recargo de equivalencia en las líneas y retenciones de IRPF. El
  tipo es siempre el de Configuración, salvo en la factura de oro de inversión (FR-052).
- **Exenciones**: solo se contempla la del oro de inversión (F-11, art. 140 bis.Uno.1.º). Quedan
  fuera:
  - Las demás, como exportaciones o entregas intracomunitarias.
  - Los servicios de mediación en oro de inversión (art. 140 bis.Uno.2.º).
  - La renuncia a la exención (art. 140 ter), que solo corresponde a quien produce o transforma
    oro de inversión.
- **Salidas en papel**: el IBAN y la mención de la exención estarán en el PDF de la feature 003.
- **Líneas**: descuentos por línea o globales distintos del precio unitario.
- **Series y tipos**: facturas simplificadas (F2) y cualquier serie distinta de `FAC` y `REC`.
- **Correcciones**: rectificativas por diferencias y registros de alta de subsanación (feature
  004).
- **Contador de rectificativas**: su ajuste manual.
- **Salidas**: envío de facturas por correo y exportación a otros formatos o a la contabilidad.
- **Otros**: monedas distintas del euro y la aplicación Android.

## Assumptions

- **Permisos** (Clarifications):
  - Empleados y administradores crean, editan y borran borradores, y emiten.
  - Solo los administradores anulan y modifican facturas emitidas, y acceden a la configuración de
    facturación, igual que al resto de Configuración en 001.
- **Operaciones**: todas son entregas de bienes y prestaciones de servicios sujetas y no exentas de
  IVA, en régimen general y al tipo único de Configuración (Clarifications). La única excepción es
  la venta de oro de inversión, exenta (FR-052, ajuste de cierre). No hay ventas en REBU. La
  calificación de la operación en el registro (lista L9) se deriva de esto en el plan.
- **Oro de inversión**: la joyería no produce oro de inversión ni transforma oro en oro de
  inversión, solo lo vende (Clarifications). Por eso no puede renunciar a la exención (F-11, art.
  140 ter), y toda venta de oro de inversión es exenta.
- **Cadena de registros**: hay una sola, la del NIF del emisor. La joyería factura desde una única
  instalación del sistema.
- **Columna «Facturas» del listado de clientes** (001, FR-035): sigue oculta. Mostrarla no forma
  parte de lo pedido y alteraría los anchos medidos en 001 (research R-22).
- **Volumen**: la joyería emite del orden de cientos a pocos miles de facturas al año. Los objetivos
  de rendimiento se fijan con 20.000 facturas.
- **Hora de referencia**: las fechas de expedición y el cambio de año se calculan en hora de España
  peninsular, como en 001.
- **Remisión y validez**: sin remisión (feature 004), los registros se generan y conservan con su
  estado «pendiente».
  - En modalidad no VERI\*FACTU, además, cada registro debe firmarse al generarse y hay que llevar
    un registro de eventos (F-8, arts. 8.3 y 12; F-10, arts. 9 y 14). Ninguna de las dos cosas
    está en esta feature.
  - Por eso la modalidad debe decidirse antes de emitir facturas reales.
  - El uso en producción de facturas reales antes de terminar las features 003 y 004 es decisión del
    responsable.
  - El plazo de adaptación vigente es el 1 de enero de 2027 para contribuyentes del Impuesto sobre
    Sociedades y el 1 de julio de 2027 para el resto (constitución, marco normativo).
- **Identificación del sistema en cada registro** (F-1, bloque `SistemaInformatico`): datos del
  productor y del sistema.
  - Quién figura como productor depende de la declaración responsable, pendiente de la asesoría
    (TODO(DECLARACION_RESPONSABLE) de la constitución).
  - En desarrollo y pruebas se usan valores ficticios. En producción, la API no arranca si no
    están configurados (research R-5).
- **Tests obligatorios** (constitución VII): esta feature toca tres de los cuatro:
  - Numeración bajo concurrencia.
  - Importes y redondeos.
  - Encadenamiento de huellas.

  Además se prueba la inalterabilidad en el almacenamiento. La conversión de presupuesto a factura
  llega con la feature 005.
