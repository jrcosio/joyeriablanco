# Feature Specification: PDF de factura con QR de cotejo e impresión del listado

**Feature Branch**: `003-pdf-impresion`

**Created**: 2026-10-01

**Status**: Draft

**Input**: Descripción del responsable del proyecto (2026-10-01): "Vamos con la feature 003, el PDF con
el QR + imprimir. Quiero que se pueda imprimir un listado de facturas, todas las que se estén
viendo, es decir, que si se ha usado el filtrar, todas las del filtrado. También imprimir una factura
concreta, tanto con los datos de la joyería como los del cliente y el detalle, etc., y, si quiere,
que se añada el número de cuenta."

**Referencias**:
- Sistema de diseño normativo: [`docs/DESIGN.md`](../../docs/DESIGN.md), que esta feature amplía
  con la sección «Paper» (Clarifications).
- Constitución 2.2.0: principios III, IV, V y VIII y restricciones «PDF» y «Sistema de diseño».
- Features previas: [`specs/001-cimientos-clientes`](../001-cimientos-clientes/spec.md) y
  [`specs/002-facturas`](../002-facturas/spec.md). La 002 dejó para esta feature la factura en papel
  con el IBAN y la mención de la exención (002, FR-052, FR-053 y «Fuera de alcance»).
- Sin mockup: la factura impresa sigue la sección «Paper» de `docs/DESIGN.md` y la disposición
  oficial del QR (F-12, §3 y anexo).

## Clarifications

### Session 2026-10-01 (decisiones previas a la especificación)

- Q: ¿Cómo se imprime? → A: El servidor genera un PDF, tanto de la factura como del listado. Se abre
  en una pestaña nueva del navegador, y desde ahí se imprime o se guarda (constitución,
  restricción «PDF»).
- Q: ¿Cómo se añade el número de cuenta? → A: Al imprimir una factura aparece la casilla «Incluir
  número de cuenta», **desmarcada** por defecto. Se usa el IBAN copiado en la factura al emitirla
  (002, FR-016). Si la factura no tiene IBAN, la casilla no aparece.
- Q: ¿Qué facturas se pueden imprimir? → A: Todas las emitidas:
  - Las vigentes, sin marca.
  - Las anuladas, con la marca «ANULADA».
  - Las rectificadas, con la marca «RECTIFICADA por REC-…».
  - Los borradores no se imprimen, porque no tienen número ni QR.
- Q: ¿Qué entra en el listado impreso? → A: Todas las filas del filtro actual, de todas las páginas,
  en el mismo orden y con las mismas columnas que en pantalla. Los borradores entran, marcados.
  - Al final van los totales de base, IVA y total, **solo de las facturas vigentes**: sin
    borradores, anuladas ni rectificadas.
  - En la cabecera se indica el filtro aplicado.
- Q: ¿Se añaden filtros al listado? → A: No. Se imprimen con los filtros actuales: búsqueda, año,
  mes y orden (002, FR-035).
- Q: `docs/DESIGN.md` solo define un tema oscuro. ¿Cómo se diseña el papel? → A: Se enmienda
  `docs/DESIGN.md` con una sección «Paper», aprobada por el responsable el 2026-10-01:
  - Fondo blanco, tinta oscura y el dorado como acento.
  - Bodoni Moda y Manrope.
  - Filetes de 1 px y esquinas a 0.

  La reutilizarán los presupuestos (005).
- Q: ¿Qué más de la joyería sale en la factura? → A: El logotipo, el teléfono, el correo, la web y un
  pie de texto libre, por ejemplo la cláusula de protección de datos.
  - Teléfono, correo, web y pie son campos nuevos y opcionales de Configuración.
  - No son datos fiscales: se toman de la configuración vigente **al imprimir** y no se copian en la
    factura.
  - El nombre, el NIF y el domicilio del emisor y del destinatario sí salen de la copia guardada al
    emitir (002, FR-016).

### Session 2026-10-01 (clarify)

- Q: ¿Se pueden expedir duplicados de una factura, por ejemplo si el cliente pierde el original?
  → A: Sí. Al imprimir aparece la casilla «Duplicado», desmarcada. Si se marca, el PDF lleva la
  expresión «DUPLICADO» (F-6, art. 14.4). Los clientes de una joyería pierden la factura y la
  necesitan para el seguro o la garantía (FR-033).
- Q: ¿Los totales del listado impreso se desglosan por tipo de IVA? → A: Sí. Una línea por tipo,
  con su base y su cuota, incluida la base exenta, y después el total general. Es lo que necesita
  la asesoría para la declaración del IVA (FR-021).
- Q: ¿Se pone un límite al tamaño del listado impreso? → A: Sí, 5.000 filas. Por encima no se
  genera, y se pide acotar el filtro, por ejemplo por año (FR-018).
- Q: ¿La factura anulada impresa conserva su código QR? → A: Sí. Se reproduce tal como se expidió,
  con el QR y la marca «ANULADA». Si se coteja, la AEAT responde «no encontrada», lo cual es
  coherente con la anulación (FR-009; F-12, §9.1.2.1).
- Q: ¿Qué frase va debajo del QR de las facturas VERI\*FACTU? → A: La larga, «Factura verificable
  en la sede electrónica de la AEAT» (FR-015).

### Session 2026-10-01 (plan)

Decisiones técnicas del plan que cambian el comportamiento descrito (research R-7 y R-8):

- Q: ¿Cómo se abre el PDF? → A: Con un enlace a la API que se abre en una pestaña nueva. Los
  errores se muestran en esa pestaña con una página en español, no dentro de la aplicación.
  - El visor de PDF del navegador puede no funcionar con la política de seguridad de la aplicación,
    y abrir la pestaña después de comprobar nada lo bloquean algunos navegadores.
  - Afecta a FR-023, FR-028 y a los casos límite de sesión caducada, error, bloqueador y doble clic.
- Q: ¿En qué formato sale el listado? → A: En A4 apaisado, para no recortar el nombre del cliente
  (FR-022).
  - La pregunta del límite estimaba «unas 110 páginas» para 5.000 filas. Medido en la prueba
    técnica, son unas 190 en apaisado.
  - Se generan en unos 12 segundos con la memoria acotada, así que el límite de 5.000 se mantiene.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Imprimir una factura con su QR (Priority: P1)

Un empleado abre una factura emitida desde el listado y pulsa «Imprimir». Si quiere que el cliente
vea dónde transferir, marca antes «Incluir número de cuenta». Si el cliente ha perdido el original,
marca «Duplicado». En una pestaña nueva se abre la
factura en PDF, lista para imprimirla o guardarla. Lleva:
- arriba, el código QR tributario;
- los datos de la joyería y del cliente;
- las líneas, el desglose del IVA y los totales.

**Why this priority**: la factura en papel o en PDF es lo que recibe el cliente. Sin el QR de
cotejo, una factura expedida por el sistema no cumple el contenido obligatorio (F-6, art. 6.5;
F-10, art. 20).

**Independent Test**: se emite una factura de varias líneas y se imprime. Hay que comprobar tres
cosas:
- El PDF contiene todo el contenido obligatorio.
- El QR, al leerlo, da la dirección oficial de cotejo con los datos del registro de alta.
- El número de cuenta y la expresión «DUPLICADO» solo aparecen si se marcó su casilla.

**Acceptance Scenarios**:

1. **Given** la consulta de `FAC-2026-0005`, emitida a «María López García», **When** se pulsa
   «Imprimir», **Then** se abre en una pestaña nueva un PDF A4 con:
   - el QR tributario al principio;
   - el número, la fecha de expedición y los datos de emisor y destinatario;
   - las líneas con su precio unitario sin IVA;
   - el desglose por tipo de IVA y los totales.
2. **Given** ese PDF, **When** se lee su QR con cualquier lector, **Then** se obtiene la dirección de
   cotejo de la AEAT del entorno configurado. Lleva exactamente el NIF del emisor, el número
   `FAC-2026-0005`, la fecha de expedición en formato `DD-MM-AAAA` y el importe total con punto
   decimal, que coinciden con los de su registro de alta.
3. **Given** una factura cuya modalidad es VERI\*FACTU, **When** se imprime, **Then** encima del QR
   figura «QR tributario:» y debajo la frase «Factura verificable en la sede electrónica de la
   AEAT». En una factura de modalidad no VERI\*FACTU figura «QR tributario:» y ninguna frase debajo.
4. **Given** una factura con IBAN, **When** se abre la consulta, **Then** junto a «Imprimir» aparece
   la casilla «Incluir número de cuenta», desmarcada. Si se imprime sin marcarla, el PDF no lleva
   el número de cuenta. Si se marca, lleva un bloque de pago con el IBAN agrupado de cuatro en
   cuatro.
5. **Given** una factura emitida sin IBAN, **When** se abre la consulta, **Then** la casilla no
   aparece y el PDF nunca lleva bloque de pago.
6. **Given** una factura de oro de inversión, **When** se imprime, **Then** el PDF muestra la base
   exenta, un IVA de 0,00 € y la mención «Operación exenta de IVA (art. 140 bis.Uno.1.º de la Ley
   37/1992)».
7. **Given** la rectificativa `REC-2026-0001`, que sustituye a `FAC-2026-0007`, **When** se imprime,
   **Then** el PDF lleva el título «Factura rectificativa» e identifica la factura rectificada por
   su número y su fecha. También indica la causa de la rectificación, la base y la cuota
   rectificadas y los datos tal como quedan.
8. **Given** `FAC-2026-0007`, ya rectificada, **When** se imprime, **Then** el PDF reproduce la
   factura original con la marca «RECTIFICADA por REC-2026-0001». Una factura anulada lleva la marca
   «ANULADA» y, si se reemitió, «Sustituida por FAC-…».
9. **Given** la configuración con teléfono, correo, web y pie de factura, **When** se imprime
   cualquier factura, **Then** el PDF muestra el logotipo y esos datos de contacto junto al emisor,
   y el pie al final. Si alguno de ellos está vacío, simplemente no aparece.
10. **Given** un empleado, **When** imprime una factura, **Then** puede hacerlo igual que un
    administrador.
11. **Given** un cliente que ha perdido su factura `FAC-2026-0005`, **When** se marca «Duplicado»
    y se imprime, **Then** el PDF reproduce la factura con todo su contenido y su QR, y lleva la
    expresión «DUPLICADO» en la primera página. Sin marcar la casilla, no la lleva.

---

### User Story 2 - Imprimir el listado filtrado (Priority: P2)

En Facturas, un empleado filtra por el año 2026 y el mes de marzo, o busca un cliente, y pulsa
«Imprimir listado». En una pestaña nueva se abre un PDF con **todas** las facturas que cumplen ese
filtro, aunque en pantalla ocupen varias páginas. Van en el mismo orden y, al final, con los totales
de las facturas vigentes.

**Why this priority**: sirve para revisar la facturación de un periodo o de un cliente en papel, o
para entregarla a la asesoría. Depende de que las facturas existan, pero no del PDF de cada factura.

**Independent Test**: con más de 100 facturas que cumplen un filtro, se imprime el listado y se
comprueba que salen todas, en el orden elegido. Los totales deben coincidir al céntimo con la suma
de las vigentes.

**Acceptance Scenarios**:

1. **Given** 130 facturas de marzo de 2026 y el filtro «2026, marzo», **When** se pulsa «Imprimir
   listado», **Then** el PDF contiene las 130 filas, y no solo las 25 de la página visible.
2. **Given** el orden «Total mayor», **When** se imprime, **Then** las filas salen en ese orden, con
   el mismo desempate que la pantalla.
3. **Given** una búsqueda «maria lopez» con el año «Todos», **When** se imprime, **Then** la cabecera
   indica la búsqueda «maria lopez», «Todos los años», el mes y el orden. También indica el número
   de filas, la fecha y la hora de generación.
4. **Given** un filtro que incluye un borrador, una factura anulada, una rectificada y facturas
   vigentes, **When** se imprime, **Then** cada fila lleva su marca igual que en pantalla: el
   borrador muestra «Borrador» en lugar del número. Los totales finales suman solo las vigentes e
   indican cuántas filas quedan fuera de la suma y por qué.
5. **Given** facturas vigentes al 21 % y al 10 % y una de oro de inversión en el filtro, **When** se
   imprime, **Then** la fila de la exenta muestra «Exenta» en el IVA. Los totales llevan una línea
   «IVA 21 %» con su base y su cuota, otra «IVA 10 %» y otra «Exenta» con su base y una cuota de
   0,00 €, y después el total general.
6. **Given** un filtro sin resultados, **When** se mira el listado, **Then** «Imprimir listado» está
   desactivado.
7. **Given** un filtro con más de 5.000 facturas, por ejemplo «Todos los años» tras muchos años de
   uso, **When** se mira el listado, **Then** «Imprimir listado» está desactivado, con la
   explicación de que el listado impreso admite hasta 5.000 facturas y conviene acotar el filtro.
   Si se pide por cualquier otra vía, el servidor lo rechaza con el mismo motivo.

---

### User Story 3 - Datos de contacto y pie de factura (Priority: P3)

El administrador abre Configuración → Facturación y rellena el teléfono, el correo y la web de la
joyería, y un texto para el pie de las facturas, por ejemplo la cláusula de protección de datos. A
partir de entonces, toda factura que se imprima los lleva.

**Why this priority**: mejora la factura impresa, pero no forma parte del contenido obligatorio, y
la factura se puede imprimir sin ellos.

**Independent Test**: un administrador guarda teléfono, correo, web y pie, y se imprime una factura
emitida antes del cambio. Debe llevar los datos nuevos, y un empleado no puede cambiarlos.

**Acceptance Scenarios**:

1. **Given** Configuración → Facturación, **When** el administrador la abre, **Then** ve, junto a
   los datos del emisor, los campos opcionales «Teléfono», «Correo electrónico», «Web» y «Pie de
   factura».
2. **Given** un teléfono con letras o un correo sin formato válido, **When** se guarda, **Then** el
   sistema no guarda e indica el error en el propio campo.
3. **Given** un pie de factura de varias líneas, **When** se guarda y se imprime una factura,
   **Then** el pie aparece al final de la factura con los mismos saltos de línea.
4. **Given** un empleado, **When** intenta cambiar estos datos por cualquier vía, **Then** el sistema
   se lo impide.
5. **Given** el teléfono cambiado hoy, **When** se reimprime una factura emitida el mes pasado,
   **Then** lleva el teléfono nuevo, mientras que su emisor fiscal (nombre, NIF y domicilio) sigue
   siendo el que se copió al emitirla.

---

### Edge Cases

- **Factura larga**: con muchas líneas o descripciones de 500 caracteres, la factura ocupa varias
  páginas.
  - El QR aparece una sola vez, en la primera página (F-12, §3).
  - La cabecera de la tabla de líneas se repite en cada página.
  - Cada página lleva el número de la factura y «Página n de m».
  - Los totales y el pie van al final.
- **Borrador**: no ofrece «Imprimir». Si se pide su PDF por cualquier vía, el servidor lo rechaza
  porque un borrador no es una factura.
- **Factura que no existe**: se informa de que no existe, igual que en la consulta.
- **Cambio de estado mientras se imprime**: el PDF refleja el estado de la factura en el momento en
  que se genera. Si después se anula, una nueva impresión ya lleva la marca.
- **Factura anulada**: conserva su QR, porque el documento reproduce lo que se expidió
  (Clarifications). Según la AEAT, el cotejo de una factura anulada responde «Factura no
  encontrada» (F-12, revisión 0.4.6 y §9.1.2.1). La marca «ANULADA» lo deja claro en el papel. No
  ofrece «Duplicado», porque una factura que no debió emitirse no se duplica (FR-033).
- **Duplicado de una factura rectificada**: se admite. Lleva a la vez «DUPLICADO» y «RECTIFICADA
  por REC-…».
- **Rectificativa de una rectificativa**: identifica como rectificada a la rectificativa anterior,
  igual que en su consulta (002, casos límite).
- **Destinatario extranjero**: se muestra su tipo de identificación, su número y su país, tal como
  se copiaron al emitir.
- **Textos especiales**: tildes, eñes, comillas, «&» o saltos de línea en nombres, descripciones o en
  el pie se imprimen tal cual, sin alterar el diseño ni el contenido del QR.
- **Datos de contacto vacíos**: no queda ningún hueco ni ninguna etiqueta sin valor.
- **Listado muy grande**: con el año «Todos», el listado puede tener miles de filas.
  - Hasta 5.000 filas se genera, con su numeración de páginas. La pestaña nueva muestra la carga
    del navegador mientras tanto, y el botón no admite un segundo clic (FR-023).
  - Por encima de 5.000 no se genera, y se pide acotar el filtro (FR-018).
  - El límite se comprueba con el número de filas en el momento de generar. Si entre tanto se han
    emitido facturas y el filtro supera el límite, se rechaza con el mismo motivo.
- **Listado con filtros manipulados en la dirección**: se aplican las mismas validaciones que en la
  pantalla. Un valor no válido se trata igual que en el listado (002, FR-032).
- **Sesión caducada al imprimir**: la pestaña nueva muestra una página en español que explica que
  la sesión ha caducado, con un enlace para volver a la aplicación e iniciar sesión (FR-028).
  Nunca muestra un error técnico.
- **Error al generar el PDF**: la pestaña nueva muestra una página en español que explica que no se
  ha podido generar y que se puede volver a intentar. Nunca se abre un documento a medias.
- **Bloqueador de ventanas emergentes**: no aplica. «Imprimir» e «Imprimir listado» son enlaces que
  el usuario pulsa, y los navegadores no bloquean esas pestañas (plan, research R-8).
- **Doble clic en «Imprimir»**: abre un solo documento, porque el botón ignora un segundo clic
  durante unos segundos.
- **Configuración sin emisor**: no puede haber facturas emitidas sin emisor (002, FR-004), así que
  toda factura imprimible tiene sus datos fiscales completos.

## Requirements *(mandatory)*

### Functional Requirements

#### Factura en PDF

- **FR-001**: La consulta de toda factura emitida, sea vigente, anulada o rectificada, DEBE ofrecer
  «Imprimir» a cualquier usuario autenticado, empleados incluidos. Los borradores no lo ofrecen, y
  el servidor DEBE rechazar el PDF de un borrador.
- **FR-002**: «Imprimir» DEBE abrir la factura en PDF en una pestaña nueva, lista para imprimirla
  o guardarla. Al guardarla, el nombre propuesto es su número, p. ej. `FAC-2026-0005.pdf`.
- **FR-003**: El PDF DEBE contener todo el contenido obligatorio de una factura completa (F-6,
  art. 6.1 y 6.2):
  - **a)** Número con su serie.
  - **b)** Fecha de expedición.
  - **c)** Nombre o razón social completa del emisor y del destinatario.
  - **d)** NIF del emisor y la identificación fiscal del destinatario, con su tipo y país si no es
    un NIF español.
  - **e)** Domicilio completo del emisor y del destinatario.
  - **f)** Líneas con unidades, descripción, precio unitario sin IVA e importe.
  - **g)** El tipo impositivo de cada tipo aplicado.
  - **h)** La cuota de cada tipo, consignada por separado.
  - **i)** La fecha de la operación, solo si es distinta de la de expedición (002, FR-018).
  - **j)** La mención de la exención, en las de oro de inversión (FR-007).
  - **Desglose**: base imponible, tipo y cuota de cada tipo aplicado, más los totales: base total,
    IVA total y total de la factura. El tipo impositivo (g) figura en el desglose y no en cada
    línea, porque una factura del sistema lleva un único tratamiento: un tipo o la exención (002,
    FR-013 y FR-052).
  - **Letras que no aplican**: k a p, porque el sistema no documenta medios de transporte nuevos,
    facturación por el destinatario, inversión del sujeto pasivo ni regímenes especiales (002,
    «Fuera de alcance» y Assumptions).
- **FR-004**: Los datos fiscales del emisor y del destinatario DEBEN tomarse de la copia guardada
  en la factura al emitirla (002, FR-016), nunca de la configuración ni de la ficha del cliente
  actuales. Todos los importes salen de la factura emitida: el PDF no recalcula nada
  (constitución VI).
- **FR-005**: El PDF DEBE llevar además:
  - El **logotipo** de la joyería en la cabecera.
  - Junto al emisor, el **teléfono**, el **correo** y la **web** de la configuración vigente al
    imprimir (FR-024), si los hay.
  - Al final, el **pie de factura** de la configuración vigente, si lo hay, respetando sus saltos
    de línea.
- **FR-006**: Los importes se muestran en euros con formato español, por ejemplo «1.560,90 €», y
  con cifras tabulares. Las unidades, con sus decimales si los tienen. Las fechas, como
  `DD/MM/AAAA`.
- **FR-007**: Factura de **oro de inversión** (002, FR-052): el desglose muestra «Base exenta» sin
  tipo ni cuota y un IVA de 0,00 €. Además lleva la mención «Operación exenta de IVA (art. 140
  bis.Uno.1.º de la Ley 37/1992)», con el mismo texto único que la consulta (002, FR-053).
- **FR-008**: Factura **rectificativa** (F-6, art. 15; 002, FR-024):
  - El título es «Factura rectificativa» en lugar de «Factura».
  - Identifica la factura rectificada por su número y su fecha de expedición.
  - Indica la causa de la rectificación con el mismo texto que la consulta.
  - Expresa el importe de la rectificación (base rectificada y cuota rectificada) junto a los datos
    tal como quedan, que son los de sus líneas y totales.
  - **Devolución total** (002, Clarifications del plan): la rectificativa no tiene líneas. En lugar
    de la tabla de líneas figura «Devolución total de la factura {número rectificado}», y los
    totales salen a 0,00 €.
- **FR-009**: **Marcas de estado**, visibles en la primera página y sin tapar ningún dato:
  - Factura anulada: «ANULADA» y, si se reemitió, «Sustituida por {número}».
  - Factura rectificada: «RECTIFICADA por {número}».
  - En los dos casos, {número} es el de la factura **vigente** que la sustituye ahora, siguiendo la
    cadena de correcciones. Es el mismo que el acceso directo de la consulta (002, FR-026). Si una
    anulada no tiene sustituta vigente, solo lleva «ANULADA».
  - Factura vigente: sin marca.
- **FR-010**: **Número de cuenta**:
  - Si la factura tiene IBAN, la consulta DEBE ofrecer junto a «Imprimir» la casilla «Incluir
    número de cuenta», desmarcada cada vez que se abre la consulta.
  - Solo con la casilla marcada, el PDF lleva un bloque de pago con el IBAN copiado en la factura,
    agrupado de cuatro en cuatro (002, FR-001).
  - Si la factura no tiene IBAN, la casilla no aparece y el PDF nunca lleva bloque de pago, aunque
    se pida por cualquier vía.
- **FR-033**: **Duplicado** (F-6, art. 14; Clarifications):
  - La consulta de una factura vigente o rectificada DEBE ofrecer junto a «Imprimir» la casilla
    «Duplicado», desmarcada cada vez que se abre la consulta. Una factura anulada no la ofrece.
  - Con la casilla marcada, el PDF lleva la expresión «DUPLICADO» en la primera página, visible y
    sin tapar ningún dato (F-6, art. 14.4). Por lo demás, su contenido es idéntico al de la factura,
    QR incluido.
  - Es compatible con «Incluir número de cuenta» y con la marca «RECTIFICADA».
  - Si se pide un duplicado de una factura anulada por cualquier vía, el servidor lo rechaza.
  - Usarla corresponde a quien imprime: el sistema no comprueba si se ha perdido el original.
- **FR-011**: **Formato**: A4 vertical. Si la factura ocupa varias páginas, cada página lleva el
  número de la factura y «Página n de m», y la cabecera de la tabla de líneas se repite. El QR va
  solo en la primera página (FR-013).
- **FR-012**: El PDF se genera bajo demanda en cada impresión y no se almacena en el servidor. Se
  sirve indicando que no debe guardarse en caché, ni en el navegador ni en intermediarios. Dos
  impresiones de la misma factura con las mismas opciones (número de cuenta y duplicado), el mismo
  estado y la misma configuración de contacto tienen el mismo contenido.

#### Código QR tributario (F-12; F-10, arts. 20 y 21; F-6, art. 6.5)

- **FR-013**: **Ubicación** (F-12, §3 y anexo, ejemplos h a k):
  - Toda factura impresa DEBE llevar el QR tributario una sola vez, en la primera página.
  - Va al principio de la factura, antes de su contenido y cerca del margen superior.
  - Va centrado o hacia el margen superior izquierdo.
  - A sus lados pueden ir los datos del emisor con el logotipo, o los del destinatario, como
    admite el anexo de F-12.
  - Es el primer QR de la factura, y la factura no lleva ningún otro.
- **FR-014**: **Presentación** (F-10, art. 21.1; F-12, §2 y §3):
  - Tamaño de 30 × 30 a 40 × 40 mm.
  - Norma ISO/IEC 18004, con el nivel M de corrección de errores.
  - Contraste alto: módulos oscuros sobre fondo blanco.
  - Al menos 2 mm de margen en blanco por los cuatro lados; se recomiendan 6 mm.
- **FR-015**: **Textos** (F-12, §3; F-10, art. 20.1.b; F-6, art. 6.5.b):
  - Encima del QR, y centrado respecto a él, DEBE figurar «QR tributario:».
  - En las facturas cuya modalidad es VERI\*FACTU, justo debajo del QR y centrada, DEBE figurar la
    frase larga «Factura verificable en la sede electrónica de la AEAT», en una o varias líneas
    (Clarifications). No se usa la frase corta «VERI\*FACTU».
  - En las de modalidad no VERI\*FACTU, ninguna frase.
  - Ambos textos usan un tipo y un tamaño de letra iguales o mayores que los del resto de datos de
    la factura.
- **FR-016**: **Contenido del QR** (F-12, §4 a §6): una dirección con el siguiente formato.
  - **Dirección base**, según la modalidad guardada en la factura y el entorno (FR-017):

    | Modalidad | Entorno de pruebas | Entorno de producción |
    |---|---|---|
    | VERI\*FACTU | `https://prewww2.aeat.es/wlpl/TIKE-CONT/ValidarQR` | `https://www2.agenciatributaria.gob.es/wlpl/TIKE-CONT/ValidarQR` |
    | No VERI\*FACTU | `https://prewww2.aeat.es/wlpl/TIKE-CONT/ValidarQRNoVerifactu` | `https://www2.agenciatributaria.gob.es/wlpl/TIKE-CONT/ValidarQRNoVerifactu` |

  - **Parámetros**: únicamente estos cuatro, en este orden:
    - `nif`: el NIF del emisor, de 9 caracteres.
    - `numserie`: el número con su serie, p. ej. `FAC-2026-0005`, de 60 caracteres como máximo.
    - `fecha`: la fecha de expedición, en formato `DD-MM-AAAA`.
    - `importe`: el importe total, con punto decimal y dos decimales, y como máximo 12 cifras
      enteras.
  - **Valores**: DEBEN coincidir con los campos `IDEmisorFactura`, `NumSerieFactura`,
    `FechaExpedicionFactura` e `ImporteTotal` del registro de alta de la factura.
  - **Codificación**: se aplica la codificación de URL en UTF-8. Los valores solo contienen
    caracteres ASCII imprimibles (32 a 126).
  - **Parámetros opcionales**: no se incluye ninguno de los del servicio de cotejo. `formato` está
    expresamente prohibido en el QR (F-12, §7), e `idioma` no forma parte de los cuatro
    obligatorios (F-12, §6).
- **FR-017**: **Entorno de la AEAT** (pruebas o producción):
  - Es un ajuste de la instalación, no de la factura, y no se cambia desde la aplicación.
  - Fuera de producción apunta siempre al entorno de pruebas (CLAUDE.md: integración primero
    contra preproducción).
  - En producción DEBE fijarse expresamente. La API no arranca si falta, igual que con los datos
    del sistema informático (002, research R-5).

#### Listado en PDF

- **FR-018**: El listado de facturas DEBE ofrecer «Imprimir listado».
  - Genera un PDF con **todas** las filas que cumplen los filtros actuales de la pantalla (búsqueda,
    año y mes), sin paginar y en el orden actual, con el mismo desempate (002, FR-034 y FR-035).
  - Se abre en una pestaña nueva, igual que la factura (FR-002).
  - Está desactivado mientras el listado de la pantalla carga y cuando el filtro no tiene
    resultados. Si se pide por otra vía con un filtro
    sin resultados, el PDF se genera igualmente: la cabecera, la indicación «No hay facturas con
    este filtro» y los totales a 0,00 €.
  - **Límite de 5.000 filas** (Clarifications):
    - Si el filtro tiene más, el botón está desactivado y explica que el listado impreso admite
      hasta 5.000 facturas y que conviene acotar el filtro, por ejemplo por año.
    - El servidor DEBE rechazar con el mismo motivo cualquier petición que supere el límite en el
      momento de generarla.
- **FR-019**: **Columnas**: número, fecha de expedición, cliente, identificación fiscal, base
  imponible, IVA y total.
  - Todas las columnas aparecen siempre, sin depender del ancho de la pantalla.
  - Un borrador muestra «Borrador» en lugar del número.
  - Las facturas anuladas y rectificadas llevan su marca junto al número.
  - Las de oro de inversión muestran «Exenta» en la columna del IVA (002, FR-033).
  - Los importes de un borrador son los previstos, igual que en pantalla.
- **FR-020**: **Cabecera**:
  - Título «Listado de facturas», con el logotipo y el nombre del emisor de la configuración
    vigente. Un listado no es una factura, así que no usa ninguna copia guardada. Si el emisor no
    está configurado, solo lleva el logotipo.
  - El filtro aplicado, en palabras: búsqueda (o «Sin búsqueda»), año (o «Todos los años»), mes (o
    «Todos los meses») y orden.
  - El número de filas, y la fecha y la hora de generación.
- **FR-021**: **Totales**, al final del listado, solo de las facturas vigentes del filtro
  (Clarifications):
  - **Desglose por tipo de IVA**: una línea por cada tipo aplicado, p. ej. «IVA 21 %» o «IVA 10 %»,
    con su base imponible y su cuota. Las bases exentas de oro de inversión van en una línea
    «Exenta», con una cuota de 0,00 €. Las líneas se ordenan de mayor a menor tipo, y la exenta va
    al final.
  - **Total general**: número de facturas vigentes y suma de su base imponible, IVA y total.
  - **Filas fuera de la suma**: cuántos borradores, anuladas y rectificadas hay.
  - **Por qué solo las vigentes**: una factura corregida deja de estar vigente, y su sustituta
    (reemitida o rectificativa por sustitución) sí lo está. La suma de las vigentes es, por tanto,
    lo facturado neto, sin contar dos veces una venta corregida. Si la sustituta queda fuera del
    filtro, por ejemplo por ser de otro año, no se suma en este listado.
  - **Cuadre**: las sumas DEBEN coincidir al céntimo con los desgloses y totales guardados en esas
    facturas (constitución II). La suma de las líneas por tipo es igual al total general.
- **FR-022**: **Formato**: A4 apaisado, para que quepan todas las columnas sin recortar el nombre
  del cliente (plan, research R-7). Cada página lleva «Página n de m» y la cabecera de la tabla se
  repite. Una fila nunca se parte entre dos páginas.
- **FR-023**: Tras pulsar «Imprimir» o «Imprimir listado», el botón indica «Preparando…» y no
  admite otro clic durante 2 segundos. La pestaña nueva muestra la carga del navegador hasta que
  el PDF está listo (casos límite).

#### Configuración: contacto y pie de factura

- **FR-024**: Configuración → Facturación DEBE añadir, en el bloque de datos del emisor, cuatro
  campos opcionales, solo para administradores (002, FR-001):
  - **Teléfono**: solo dígitos, espacios, `+`, paréntesis y guiones, con al menos 6 dígitos (001,
    FR-055). Como máximo 30 caracteres.
  - **Correo electrónico**: con validación de formato, guardado en minúsculas (001, FR-027 y
    FR-055). Como máximo 254 caracteres.
  - **Web**: un dominio o una dirección `http` o `https`, de 200 caracteres como máximo. Se
    imprime sin el esquema (`https://` o `http://`) y sin la barra final.
  - **Pie de factura**: texto libre de varias líneas, de 600 caracteres como máximo, con sus saltos
    de línea.

  Todos se guardan sin espacios al principio ni al final. Un campo vacío equivale a «sin dato», y
  vaciarlo lo borra. Una petición que no incluye estos campos los deja como estaban, para no
  borrarlos por omisión.
- **FR-025**: Estos datos NO son datos fiscales ni forman parte de la factura emitida:
  - No se copian al emitir.
  - Cada impresión usa los vigentes en ese momento, también al reimprimir facturas antiguas
    (Clarifications).
  - No se exigen para emitir (002, FR-004).
- **FR-026**: Sus cambios DEBEN quedar en la auditoría con el valor anterior y el nuevo, como el
  resto de la configuración de facturación (002, FR-003). La edición simultánea por dos
  administradores se detecta igual que en el resto de Configuración.

#### Comunes

- **FR-027**: El servidor DEBE exigir una sesión válida para generar cualquier PDF, y los permisos
  son los de la consulta: la factura y el listado, cualquier usuario autenticado. Los cambios de
  contacto y pie, solo un administrador.
- **FR-028**: Ante una sesión caducada, una factura que no existe, un duplicado no admitido, un
  listado demasiado grande o un fallo al generar, la pestaña nueva DEBE mostrar una página en
  español con un mensaje comprensible y un enlace para volver a la aplicación. Nunca muestra un
  error técnico ni un documento incompleto. El resto de clientes de la API siguen recibiendo los
  errores habituales (plan, research R-8).
- **FR-029**: Los registros de actividad del servidor NO DEBEN contener datos personales ni
  importes al generar un PDF (002, FR-051). Solo pueden registrar el número de factura o los
  filtros del listado, sin el texto de búsqueda, y el tipo de documento.
- **FR-030**: La factura y el listado impresos DEBEN cumplir la sección «Paper» de
  `docs/DESIGN.md`:
  - Fondo blanco, tinta oscura y el dorado como acento.
  - Bodoni Moda en el título y en el total de la factura; Manrope en los datos, con cifras
    tabulares.
  - Filetes de 1 px, esquinas a 0 y sin sombras.

  Los valores se definen una sola vez como tokens de papel y se consumen desde ahí (constitución,
  «Sistema de diseño»). El texto del documento DEBE poder seleccionarse y copiarse: no se imprime
  como imagen.
- **FR-031**: Los botones «Imprimir» e «Imprimir listado» DEBEN tener nombre accesible, p. ej.
  «Imprimir factura FAC-2026-0005», y usarse por completo con teclado. Las casillas «Incluir número
  de cuenta» y «Duplicado» tienen su etiqueta asociada. Cuando «Imprimir listado» está desactivado,
  el motivo es accesible, no solo visual. El estado «Preparando…» se anuncia a los lectores de
  pantalla.
- **FR-032**: Los datos de ejemplo del entorno de desarrollo DEBEN incluir teléfono, correo, web y
  pie de factura ficticios. Su carga sigue prohibida en producción (001, FR-045).

### Key Entities *(include if feature involves data)*

- **Factura impresa**: representación en PDF de una factura emitida.
  - Se genera bajo demanda a partir de la factura y su registro de alta, que son inalterables, más
    los datos de contacto vigentes.
  - Lleva, si procede, la marca de estado, la expresión «DUPLICADO» y el bloque de pago.
  - No se almacena.
- **Código QR tributario**: la dirección de cotejo de la factura, formada con la modalidad de la
  factura, el entorno de la instalación y cuatro datos de su registro de alta.
- **Listado impreso**: representación en PDF del resultado completo de un filtro del listado, con
  la descripción del filtro y los totales de las facturas vigentes. No se almacena.
- **Configuración de facturación** (de 002): se amplía con teléfono, correo, web y pie de factura.
  Son datos no fiscales, opcionales y auditados.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El PDF de una factura de hasta 20 líneas está listo para imprimir en menos de
  3 segundos en el 95 % de las generaciones. Se mide con 20 generaciones seguidas en el entorno
  local de pruebas.
- **SC-002**: Al leer con un lector estándar el QR de facturas impresas de todos los tipos
  (ordinaria, exenta y rectificativa) y de ambas modalidades, el 100 % da exactamente la dirección
  oficial de FR-016, con los valores de su registro de alta.
- **SC-003**: El 100 % de las facturas impresas de un juego de pruebas (ordinaria, exenta,
  rectificativa por error, rectificativa por devolución total, anulada y rectificada) contienen
  cada dato obligatorio de FR-003 y FR-008 que les corresponde.
- **SC-004**: En el 100 % de las pruebas, el número de cuenta aparece solo cuando se pidió y la
  factura lo tiene, y la expresión «DUPLICADO» solo cuando se pidió y la factura no está anulada.
- **SC-005**: Un listado de 1.000 facturas está listo para imprimir en menos de 15 segundos, y uno
  de 5.000, el máximo, en menos de 60 segundos. Sus totales por tipo y generales coinciden al
  céntimo con la suma de los desgloses de las vigentes calculada aparte, y el número de filas
  coincide con el total que muestra la pantalla para ese filtro. Generar un listado de 5.000 filas
  no ocupa más de unos 300 MB de memoria en el servidor, de modo que dos generaciones simultáneas
  caben junto al resto del sistema.
- **SC-006**: Medido sobre el PDF, el QR mide entre 30 y 40 mm de lado y tiene al menos 2 mm de
  margen en blanco por los cuatro lados. «QR tributario:» y la frase VERI\*FACTU tienen un tamaño de
  letra igual o mayor que el de los datos de la factura.
- **SC-007**: El servidor rechaza el 100 % de estos intentos: que un empleado cambie el contacto o
  el pie, pedir el PDF de un borrador, pedir el duplicado de una factura anulada, pedir un listado
  de más de 5.000 filas o generar un PDF sin sesión.
- **SC-008**: La factura y el listado impresos superan la revisión de conformidad con la sección
  «Paper» de `docs/DESIGN.md`. Los botones nuevos de la web superan la de `docs/DESIGN.md`, con sus
  colores solo de tokens y las esquinas a 0 px.
- **SC-009**: Las pruebas de extremo a extremo cubren las historias P1 y P2 y pasan en su totalidad
  antes de cerrar la feature.

## Conformidad con el sistema de diseño

- **Paper**: `docs/DESIGN.md` solo define el tema oscuro de la aplicación. Los documentos impresos
  siguen la sección nueva «Paper (print and PDF)», que esta feature añade a `docs/DESIGN.md` con la aprobación del
  responsable (Clarifications, 2026-10-01). Sus valores concretos (colores de papel derivados de los
  tokens existentes, escala tipográfica en puntos y márgenes) se fijan en el plan y se escriben en
  `docs/DESIGN.md` antes de implementarlos.
- **Web**: los botones «Imprimir» e «Imprimir listado» y las casillas «Incluir número de cuenta» y
  «Duplicado» usan los componentes ya definidos: botón secundario y casilla de verificación.

Desviaciones de `docs/DESIGN.md`: **ninguna**. La sección «Paper» es una enmienda aprobada, no una
desviación.

## Fuentes normativas citadas

Se mantiene la numeración de las fuentes de 002 (F-1 a F-11). Esta feature cita F-6 y F-10, con
consultas nuevas, y añade F-12.

- **F-6**: Reglamento por el que se regulan las obligaciones de facturación, RD 1619/2012
  (BOE-A-2012-14696, texto consolidado). Consultado en la API de datos abiertos del BOE el
  2026-10-01:
  - **Art. 6.1**: «Toda factura y sus copias contendrán los datos o requisitos que se citan a
    continuación […]»: letras a) a j), transcritas en FR-003.
  - **Art. 6.2**: la base imponible se especifica por separado, entre otros casos, cuando se
    documentan operaciones exentas y no exentas o sujetas a distintos tipos.
  - **Art. 6.5**, añadido por la disposición final 1.1 del RD 1007/2023: las facturas expedidas con
    los sistemas del art. 7 del RRSIF incluirán:
    - «a) La representación gráfica del contenido parcial de la factura mediante un código “QR”».
    - «b) […] la frase “Factura verificable en la sede electrónica de la AEAT” o “VERI\*FACTU”
      únicamente en aquellos casos en los que el sistema informático realice la remisión de todos
      los registros de facturación a la Agencia Estatal de Administración Tributaria».
  - **Art. 14**: duplicados. «Sólo podrán expedir un original de cada factura». Los duplicados solo
    se admiten con varios destinatarios o por pérdida del original (art. 14.2), tienen la misma
    eficacia que el original (art. 14.3) y llevan la expresión «duplicado» (art. 14.4). Base de
    FR-033.
  - **Art. 15**: rectificativas (002, F-6).
- **F-10**: Orden HAC/1177/2024 (BOE-A-2024-22138). Consultada en la API de datos abiertos del BOE
  el 2026-10-01:
  - **Art. 20.1**: «Una factura, tanto si está impresa en soporte papel como si se trata de la
    imagen de la misma en soporte digital», incluirá el código QR y, en VERI\*FACTU, la frase
    «Factura verificable en la sede electrónica de la AEAT» o «VERI\*FACTU», «con un tipo de letra y
    tamaño bien visibles, similares a los del resto de datos de la factura».
  - **Art. 21.1**: tamaño de 30 × 30 a 40 × 40 mm, norma ISO/IEC 18004 y nivel M de corrección de
    errores.
  - **Art. 21.2**: contenido: la dirección del servicio de cotejo, con el NIF del obligado, el
    número de serie y número, la fecha de expedición y el importe total.
- **F-12**: AEAT, *Detalle de las especificaciones técnicas del código «QR» de la factura y de la
  «URL» del servicio de cotejo o remisión de información por parte del receptor de la factura*,
  versión 0.5.0 (10/12/2025).
  - URL:
    `https://www.agenciatributaria.es/static_files/AEAT_Desarrolladores/EEDD/IVA/VERI-FACTU/DetalleEspecificacTecnCodigoQRfactura.pdf`.
  - Enlazado desde la página oficial «Características del QR y especificaciones del servicio de
    cotejo o remisión de información por parte del receptor de la factura», en el índice de
    información técnica de VERI\*FACTU
    (`https://sede.agenciatributaria.gob.es/Sede/iva/sistemas-informaticos-facturacion-verifactu/informacion-tecnica.html`).
  - Descarga del 2026-10-01. SHA-256:
    `f86b3c260d8a4963dbc18c5007732b53199156c5d1db63242e68db71501b49eb`.
  - Se citan:
    - **§2**: transcribe los arts. 20.1 y 21 de F-10.
    - **§3**: contraste; margen en blanco de al menos 2 mm, y se recomiendan 6. El QR va al
      principio, una sola vez y en la primera página. En vertical va arriba, centrado o hacia la
      izquierda. Lleva «QR tributario:» encima, y la frase VERI\*FACTU debajo y centrada, con letra
      igual o mayor que el resto de datos.
    - **§4**: codificación de URL en UTF-8 y caracteres ASCII de 32 a 126.
    - **§5**: las cuatro direcciones base de FR-016.
    - **§6**: los cuatro parámetros, con su formato y longitud.
    - **§7**: `idioma` y `formato` son opcionales del servicio, y `formato` nunca va en el QR.
    - **§9.1.2.1** y revisión 0.4.6: una factura anulada responde «no encontrada».
    - **Anexo (§12)**, ejemplos h a k: disposición en A4 vertical con el emisor y el logotipo a los
      lados del QR.
- **F-11**: Ley 37/1992 del IVA, art. 140 bis.Uno.1.º, para la mención de la exención (002, F-11).
- **Preguntas abiertas**: ninguna nueva de fuente oficial. Siguen abiertas las de 002 (research
  R-17) y el TODO(MODALIDAD_VERIFACTU) de la constitución. Esta feature no depende de ellos, porque
  cada factura guarda su modalidad.

## Fuera de alcance

- **Otras features**:
  - La remisión de los registros a la AEAT (004). Hasta entonces, el cotejo de una factura
    VERI\*FACTU puede responder que no consta.
  - El PDF de los presupuestos (005), que reutilizará la sección «Paper».
- **Envío**: por correo electrónico o por cualquier otro canal.
- **Factura electrónica estructurada** (F-10, art. 20.2), en la que la dirección del QR va como
  campo y no como imagen.
- **Exportación**: a hojas de cálculo, CSV o a la contabilidad (002, «Fuera de alcance»). El
  listado impreso es un documento para leer o archivar, no una exportación de datos.
- **Plantillas**: personalización del diseño de la factura por el usuario, más allá del contacto y
  el pie.
- **Idiomas**: factura en otros idiomas.
- **Almacén de PDFs**: almacenamiento o histórico de los PDF generados.
- **Filtros nuevos en el listado**: estado, cliente o rango de fechas (Clarifications).
- **Duplicados por varios destinatarios** (F-6, art. 14.2.a): exigen consignar en cada ejemplar la
  porción de base y cuota de cada destinatario, y una factura de este sistema tiene un único
  destinatario (002, FR-005). Solo se contempla el duplicado por pérdida del original (FR-033).

## Assumptions

- **Permisos**: imprimir una factura o el listado está al alcance de cualquier usuario autenticado,
  igual que consultarlos (002, Assumptions). Solo los administradores cambian el contacto y el pie.
- **Impresiones no auditadas**: imprimir no cambia ningún dato y no deja evento en la auditoría.
  Solo queda constancia técnica en los registros de actividad, sin datos personales (FR-029).
- **Copias y duplicados**: imprimir la misma factura varias veces sin marcar «Duplicado» produce
  copias del mismo documento, que el art. 6.1 de F-6 contempla («Toda factura y sus copias»). El
  duplicado del art. 14, con su expresión, solo sale cuando quien imprime lo marca (FR-033).
  Imprimir no lleva la cuenta de las copias ni de los duplicados expedidos.
- **Tamaño del QR**: 35 × 35 mm, el centro del intervalo de 30 a 40 mm, con el margen en blanco
  recomendado de 6 mm (plan, research R-2).
- **Logotipo**: es el monograma «Blanco Joyeros» que ya usa la aplicación (001, FR-042). No se
  configura desde la aplicación.
- **Idioma y moneda**: castellano y euros, como el resto del sistema.
- **Volumen**: del orden de cientos a pocos miles de facturas al año (002, Assumptions). El listado
  de un año completo cabe holgadamente en el límite de 5.000 filas (FR-018). El de «Todos los
  años» puede superarlo, y entonces se pide acotar el filtro.
- **Cotejo antes de la 004**: mientras no se remitan los registros, el cotejo de una factura
  VERI\*FACTU responderá que no consta en la AEAT. Es lo esperado hasta la feature 004 (002,
  Assumptions, «Remisión y validez»).
- **Tests obligatorios** (constitución VII): esta feature no cambia la numeración, ni los cálculos,
  ni el encadenamiento, ni la conversión de presupuestos. Sí comprueba que lo impreso coincide al
  céntimo con lo registrado (SC-003, SC-005) y que el QR coincide con el registro de alta (SC-002).
