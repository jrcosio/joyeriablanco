# Feature Specification: Modalidad No VERI\*FACTU — registros firmados, registro de eventos y exportación

**Feature Branch**: `004-no-verifactu`

**Created**: 2026-10-03

**Status**: Draft

**Input**: Decisión del responsable del proyecto (2026-10-03): «Empieza la feature 004. Te cierro el
debate del envío y de la AEAT, ya que la modalidad es "No VeriFactu", por lo tanto esto simplifica
todo».

**Referencias**:
- Constitución 2.4.0, principios III, IV, V, VII y VIII. La enmienda 2.4.0 (2026-10-03) fija la
  modalidad No VERI\*FACTU, la firma de cada registro antes de insertarlo, el registro de eventos y la
  declaración responsable de Joyería Blanco como productora.
- Features previas:
  - [`specs/002-facturas`](../002-facturas/spec.md): registros de alta y anulación con huella
    encadenada, inalterables en la base de datos, y comprobación de la cadena. Dejó para esta
    feature la firma, el registro de eventos y la modalidad (002, «Fuera de alcance» y R-17).
  - [`specs/003-pdf-impresion`](../003-pdf-impresion/spec.md): el QR de No VERI\*FACTU, sin la
    frase VERI\*FACTU, ya está hecho.
  - [`specs/005-presupuestos`](../005-presupuestos/spec.md): las facturas convertidas generan sus
    registros como cualquier otra. Los presupuestos no generan ninguno.
- Sistema de diseño normativo: [`docs/DESIGN.md`](../../docs/DESIGN.md).

## Clarifications

### Session 2026-10-03 (decisiones previas a la especificación)

- Q: ¿Qué modalidad usa Joyería Blanco? → A: **No VERI\*FACTU** (constitución 2.4.0). Los registros
  no se envían a la AEAT. A cambio, el sistema los firma, lleva un registro de eventos y permite
  exportarlos (RRSIF, art. 16.3, a sensu contrario; Orden HAC/1177/2024, arts. 3, 6 a 9 y 14).
- Q: El RRSIF (art. 8.1, segundo párrafo) y la Orden (art. 4) exigen que el sistema tenga
  **capacidad de remitir** los registros a la AEAT, también en respuesta a un requerimiento
  (Orden, art. 18). ¿Se incluye? → A: **No. Solo exportación, sin capacidad de remisión.** Un
  requerimiento se atiende exportando los registros firmados y entregándolos por el cauce que
  indique. El responsable asume por escrito el riesgo normativo (ver «Riesgo normativo asumido»).
- Q: ¿Con qué certificado se firma? → A: Con un certificado electrónico cualificado de la empresa o
  de su representante (especificación de firma v0.1.5, §3). **Todavía no está disponible.** Se
  desarrolla y se prueba con certificados de prueba, y el real se instala al desplegar.
- Q: ¿Hay facturas reales emitidas con el sistema? → A: **No.** La modalidad se fija antes de la
  primera factura real. Los datos de desarrollo y de prueba se regeneran en la nueva modalidad.
- Q: ¿Quién es el productor del sistema y suscribe la declaración responsable? → A: **La propia
  Joyería Blanco**, desarrollo para uso propio (RRSIF, art. 13; Orden, art. 15).

### Session 2026-10-03 (clarify)

- Q: ¿Cuándo se generan los eventos de inicio y fin del funcionamiento (Orden, art. 9.1.a y b)? →
  A: **En cada arranque y en cada parada del servicio**. Al arrancar se anota el inicio. Al
  pararse, el resumen y el fin (art. 9.2: «antes de cerrarse o apagarse»). Varios procesos del
  servidor cuentan como un solo arranque.
- Q: ¿Qué entrega la exportación de un periodo? → A: **Un ZIP con un XML por registro**:
  - cada registro, tal cual se firmó y sin reempaquetarlo, para que su firma siga verificándose;
  - un índice legible en CSV, con número de secuencia, tipo, factura, fecha y huella;
  - un manifiesto con el SHA-256 de cada fichero.
- Q: ¿Quién ve la alarma de integridad (art. 6.f)? → A: **Todos los usuarios**, en todas las
  pantallas. Solo los administradores entran al detalle y lanzan la comprobación.
- Q: ¿La integridad se comprueba también de forma automática? → A: **No, solo bajo demanda**,
  desde la web o la consola. La FAQ (F-4, p. 30) no lo exige.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cada factura deja su registro firmado (Priority: P1)

Al emitir, rectificar o anular una factura, el sistema genera su registro de facturación en el
formato oficial y lo firma con el certificado de Joyería Blanco en ese mismo momento. El registro
solo existe si está firmado. Si el certificado no se puede usar, la factura no se emite y no se
consume ningún número.

**Why this priority**: en No VERI\*FACTU, un registro de facturación solo se considera generado
cuando está firmado (FAQ de la AEAT, F-4, p. 13). Sin esta historia, ninguna factura cumple.

**Independent Test**: con un certificado de prueba instalado, se emite una factura, se rectifica
otra y se anula una tercera. Cada registro sale en el formato oficial, válido contra su esquema, y
la firma se verifica. Sin certificado, ninguna emisión se completa.

**Acceptance Scenarios**:

1. **Given** un certificado vigente instalado, **When** se emite una factura, **Then**:
   - su registro de alta se genera en el formato oficial y es válido contra el esquema oficial;
   - lleva una firma XAdES Enveloped (clase EPES, política de firma de la AGE) sobre el registro,
     verificable con el certificado;
   - todo ocurre en la misma operación que la emisión.
2. **Given** una factura emitida, **When** se anula o se rectifica, **Then** cada registro de
   anulación o de alta que se genere queda firmado igual.
3. **Given** que no hay certificado instalado, o que está caducado, todavía no es válido o no se
   puede leer, **When** alguien intenta emitir, rectificar o anular, **Then**:
   - la operación no se completa;
   - el mensaje dice que falta un certificado utilizable y por qué;
   - no se consume ningún número ni queda ningún registro.
4. **Given** una factura emitida, **When** se abre su consulta, **Then** cada uno de sus registros
   indica «Firmado», con la fecha y el titular del certificado. Se puede comprobar al momento si su
   huella y su firma son correctas.
5. **Given** un presupuesto, **When** se emite, se modifica, se anula o se convierte, **Then** sigue
   sin generar ningún registro de facturación y no necesita certificado. Lo necesita la factura que
   salga de la conversión.

---

### User Story 2 - Registro de eventos del sistema (Priority: P1)

El sistema anota automáticamente, en un registro de eventos propio, los sucesos que exige la
normativa:
- el inicio y el fin de su funcionamiento como No VERI\*FACTU;
- cada comprobación de anomalías y cada anomalía detectada;
- cada exportación;
- un resumen periódico.

Cada evento queda encadenado con el anterior, firmado e inalterable. El administrador lo consulta
desde una pantalla.

**Why this priority**: el registro de eventos es obligatorio en No VERI\*FACTU (RRSIF, art. 8.3;
Orden, art. 9; F-4, pp. 29 y 30).

**Independent Test**: se arranca el sistema, se exporta un periodo y se lanza una comprobación. En
la pantalla del registro de eventos aparecen el inicio, la exportación, el lanzamiento de la
comprobación y, pasado el intervalo, el resumen. Cada uno encadena con el anterior y su firma se
verifica.

**Acceptance Scenarios**:

1. **Given** el sistema en No VERI\*FACTU, **When** empieza a funcionar, **Then** se genera el evento
   «Inicio del funcionamiento del sistema informático como NO VERI\*FACTU».
2. **Given** el sistema en marcha, **When** se va a cerrar o apagar, **Then** genera un resumen de
   eventos y el evento de fin de funcionamiento.
3. **Given** el sistema operativo y disponible, **When** pasan 6 horas desde el último resumen, o
   desde el inicio si no hay ninguno, **Then** se genera un registro resumen con los eventos
   sucedidos en ese intervalo y las altas y anulaciones generadas. Se genera también si no ha
   sucedido nada.
4. **Given** cualquier evento generado, **When** se consulta, **Then**:
   - está en el formato oficial y es válido contra su esquema;
   - lleva su huella, encadenada con la del evento anterior, y su firma;
   - ni la aplicación ni nadie con acceso a la base de datos lo puede modificar ni borrar.
5. **Given** un administrador, **When** abre «Registro fiscal», **Then** ve los eventos, del más
   reciente al más antiguo, con su tipo, fecha y hora, datos propios y estado de huella y firma.
   Puede filtrarlos por tipo y por fechas.
6. **Given** un empleado, **When** intenta abrir «Registro fiscal», **Then** no tiene acceso.

---

### User Story 3 - Comprobar la integridad y detectar anomalías (Priority: P1)

El administrador lanza, cuando quiere, una comprobación de la cadena de registros de facturación y
de la de eventos: huellas, firmas, encadenamiento y orden de fechas. Puede hacerlo desde la web o
desde la consola. Si algo no cuadra:
- el sistema anota la anomalía con su tipo oficial;
- muestra una alarma que no se apaga mientras no se pueda volver a garantizar la integridad.

Además, desde cualquier registro se puede saltar al anterior o al siguiente de la cadena, viendo
si cada enlace y cada fecha son correctos.

**Why this priority**: la detección y el aviso de anomalías, y el seguimiento de la cadena, son
obligatorios en No VERI\*FACTU (Orden, arts. 6.b, 6.d, 6.e, 6.f, 7.h y 7.j, y art. 9.1.c a 9.1.f).

**Independent Test**: se pulsa «Comprobar integridad» sobre una cadena correcta: quedan los
eventos de lanzamiento con sus recuentos y ninguna alarma. En el entorno de pruebas se altera un
registro por fuera del sistema y se repite: aparece la anomalía con su tipo, su evento y la
alarma.

**Acceptance Scenarios**:

1. **Given** cadenas íntegras, **When** el administrador pulsa «Comprobar integridad», o se lanza
   `verificar-cadena` en la consola, **Then**:
   - se comprueban las huellas, las firmas, el encadenamiento y el orden de las fechas de todos los
     registros de facturación y de evento;
   - se generan los eventos de lanzamiento de la detección, con el número de registros procesados
     en cada comprobación;
   - el resultado se muestra como íntegro.
2. **Given** un registro alterado por fuera del sistema, **When** se comprueba, **Then**:
   - se genera un evento de detección de anomalías, de facturación o de evento, con el tipo
     oficial de anomalía (por ejemplo, «Integridad-huella» o «Integridad-firma») y el registro
     afectado;
   - aparece una alarma visible para todos los usuarios.
3. **Given** una alarma activa, **When** se navega por la aplicación, **Then** la alarma sigue
   visible. Solo se apaga cuando una comprobación posterior confirma la integridad de los registros
   generados después del afectado.
4. **Given** un registro cualquiera, **When** el administrador salta al anterior o al siguiente de
   la cadena, **Then** ve, para ese salto:
   - si el encadenamiento de la huella es correcto;
   - si las fechas y horas de generación respetan el orden entre sí y con la hora actual.
5. **Given** que el último registro de facturación está mal encadenado, o tiene una fecha de
   generación más de un minuto posterior a la hora actual, **When** se va a emitir una factura,
   **Then**:
   - la factura se emite igualmente, porque la facturación nunca se interrumpe por este motivo
     (F-4, p. 28);
   - se genera el evento de anomalía correspondiente y se muestra la alarma (Orden, arts. 7.i y
     7.j).

---

### User Story 4 - Exportar los registros para conservarlos o atender un requerimiento (Priority: P2)

El administrador elige un periodo y descarga los registros de facturación generados en él, cada uno
exactamente como se generó y se firmó. También puede descargar los registros de evento. Cada
exportación queda anotada como evento. Lo mismo se puede hacer desde la consola.

**Why this priority**: la exportación por periodo es obligatoria (RRSIF, art. 8.2.c; Orden,
arts. 8.2 y 9.1.h e i). Además, es el medio elegido para atender un requerimiento.

**Independent Test**: se emiten y anulan facturas y se exporta el periodo. El fichero contiene
todos los registros del periodo, en el orden de la cadena e idénticos a los guardados, con sus
firmas válidas. En el registro de eventos aparece el evento de exportación con el periodo, el
primer y el último registro, los recuentos y las sumas.

**Acceptance Scenarios**:

1. **Given** registros de facturación en un periodo, **When** el administrador lo exporta, **Then**
   recibe un fichero con:
   - todos los registros de alta y de anulación generados en el periodo, en el orden de la cadena;
   - cada registro idéntico, byte a byte, al generado y firmado;
   - un resumen legible con el periodo, los recuentos y los importes.
2. **Given** una exportación de registros de facturación, **When** termina, **Then** se genera el
   evento «Exportación de registros de facturación generados en un periodo», con:
   - el periodo;
   - el primer y el último registro;
   - el número de altas y de anulaciones;
   - la suma de cuotas y de importes totales de las altas;
   - la indicación de que los registros exportados **siguen conservándose** en el sistema.
3. **Given** registros de evento en un periodo, **When** se exportan, **Then** el fichero los
   contiene firmados y en orden, y se genera el evento «Exportación de registros de evento
   generados en un periodo».
4. **Given** un periodo sin registros, **When** se intenta exportar, **Then** se informa de que no
   hay nada que exportar. No se genera fichero ni evento.
5. **Given** la consola, **When** se lanza `exportar-registros` con un periodo, **Then** se obtiene
   el mismo fichero y el mismo evento que desde la web.

---

### User Story 5 - Modalidad, certificado y declaración responsable (Priority: P2)

En la configuración de facturación, la modalidad aparece fijada en No VERI\*FACTU, y el
administrador ve el estado del certificado de firma y cuándo caduca. Cualquier usuario puede
abrir «Acerca del sistema»: los datos del sistema informático y la declaración responsable que
Joyería Blanco suscribe como productora, legible y descargable.

**Why this priority**: la declaración responsable debe estar visible en el propio sistema (RRSIF,
art. 13.2; Orden, art. 15.3). El estado del certificado evita sorpresas, porque sin él no se
factura.

**Independent Test**:
- En Configuración se ven la modalidad fija y el certificado de prueba, con su titular y su
  caducidad.
- Desde cualquier pantalla se abre «Acerca del sistema» y se descarga la declaración.
- Con un certificado que caduca pronto aparece el aviso.

**Acceptance Scenarios**:

1. **Given** un administrador, **When** abre Configuración → Facturación, **Then**:
   - la modalidad muestra «No VERI\*FACTU» y no se puede cambiar a VERI\*FACTU, que el sistema no
     admite al no tener capacidad de remisión;
   - el certificado muestra su titular, su identificación fiscal, el emisor, la validez (desde y
     hasta) y los días que quedan.
2. **Given** un certificado que caduca en menos de 30 días, **When** se abre la configuración o el
   modal de emisión, **Then** aparece un aviso con la fecha de caducidad.
3. **Given** cualquier usuario, **When** abre «Acerca del sistema», **Then** ve:
   - el nombre, el código identificador, la versión y el número de instalación del sistema;
   - la declaración responsable, que empieza con «DECLARACIÓN RESPONSABLE DEL SISTEMA INFORMÁTICO
     DE FACTURACIÓN» y contiene, en el orden y con los textos del art. 15.1 de la Orden, los
     datos de las letras a) a l), con Joyería Blanco como productora.
4. **Given** la declaración responsable, **When** se pide descargarla, **Then** se obtiene un
   documento en un formato de uso extendido y gratuito (Orden, art. 15.3).
5. **Given** los datos de ejemplo de desarrollo y de pruebas, **When** se cargan, **Then** están en
   No VERI\*FACTU, con sus registros firmados con el certificado de prueba y sus eventos.

---

### Edge Cases

- **Certificado no utilizable**:
  - **Casos**: no instalado, contraseña incorrecta, caducado, aún no válido, sin clave privada o
    no apto para firmar.
  - **Facturación**: se bloquea cualquier operación que genere registros, con un mensaje que dice
    cuál es el problema y que no muestra nunca la contraseña.
  - **Lo que sigue funcionando**: la consulta, la impresión, los presupuestos y los borradores.
- **El certificado caduca con el sistema en marcha**:
  - Desde ese momento no se emite y se muestra la alarma de certificado.
  - Los eventos que no se pueden firmar no se pierden: al instalar un certificado válido, el
    primer resumen cubre todo el intervalo transcurrido.
- **Fecha de la firma**: el certificado debe estar en vigor en la fecha y hora de generación del
  registro o del evento, no solo en la de la comprobación (especificación de firma, §3).
- **Anomalía en el último registro al emitir**: en No VERI\*FACTU la factura se emite igual, se anota
  la anomalía y se muestra la alarma (F-4, p. 28). Es un cambio respecto de la 002, que bloqueaba
  la emisión. En los registros de evento se aplica lo mismo, de forma análoga (Orden, art. 9.3).
- **Concurrencia**:
  - Dos emisiones a la vez siguen generando una sola cadena de registros, sin huecos.
  - Dos eventos a la vez (por ejemplo, una exportación mientras se genera un resumen) generan
    una sola cadena de eventos, sin huecos.
  - El resumen periódico no se duplica aunque haya varios procesos del servidor.
- **Reinicios frecuentes**: los reinicios de mantenimiento o de despliegue generan sus eventos de
  inicio y fin. Si el sistema se detiene sin poder cerrarse ordenadamente (caída o corte), el
  siguiente inicio lo refleja y su primer resumen cubre el intervalo.
- **Primer registro y primer evento**: los dos se identifican como primeros de su cadena (Orden,
  art. 7.b, aplicado también a los eventos por el art. 9.3).
- **Exportaciones**:
  - Repetir la exportación del mismo periodo produce el mismo contenido y un nuevo evento.
  - Un periodo que abarque registros de varios años se exporta entero.
  - Los registros exportados nunca se borran del sistema.
- **Restauración de copias de seguridad**: no la gestiona el sistema, así que no aplica el evento
  del art. 9.1.g. Las copias se siguen haciendo como hasta ahora, fuera de la aplicación (README).
- **Modalidad**: con registros generados, la modalidad sigue bloqueada (002, FR-050). El mensaje
  deja de hablar de una «remisión a la AEAT» que no llegará.
- **Presupuestos**: siguen fuera de todo esto. Ni registros, ni firma, ni eventos.

## Requirements *(mandatory)*

### Functional Requirements

#### Modalidad y certificado

- **FR-001**: La modalidad de facturación DEBE ser No VERI\*FACTU:
  - Se muestra fija en la configuración.
  - VERI\*FACTU no se puede elegir, porque el sistema no tiene capacidad de remisión.
  - Cada factura y cada registro siguen guardando su modalidad (002, FR-030).
- **FR-002**: Las firmas DEBEN hacerse con un certificado electrónico cualificado de firma, en
  vigor, de Joyería Blanco o de un representante autorizado (especificación de firma, §3; Orden,
  art. 14). Lo instala quien despliega el sistema:
  - fuera de la base de datos y fuera de la aplicación web;
  - su contraseña y su clave privada nunca se muestran, nunca se devuelven por la API y nunca
    aparecen en los registros de actividad.
- **FR-003**: Un administrador DEBE poder ver el estado del certificado:
  - **Datos**: el titular, su identificación fiscal, el emisor y la validez (desde y hasta), con
    los días que quedan.
  - **Estado**: utilizable, o no utilizable con el motivo (no instalado, ilegible, caducado,
    aún no válido o no apto para firmar).
  - **Aviso**: desde 30 días antes de la caducidad, en la configuración y en el modal de emisión.
- **FR-004**: Si el certificado no es utilizable en la fecha y hora de generación, toda operación
  que genere registros de facturación DEBE rechazarse (emitir, emitir un borrador, convertir un
  presupuesto al emitir su borrador, rectificar, anular y reemitir):
  - con `emision-no-disponible` y `faltan: ["certificado"]`, más el motivo;
  - sin consumir número ni dejar rastro en la cadena.

#### Registros de facturación firmados

- **FR-005**: Cada registro de alta y de anulación DEBE generarse:
  - en XML con codificación UTF-8;
  - con la estructura, el contenido y el formato del diseño oficial (Orden, arts. 10 y 11; F-1;
    `SuministroInformacion.xsd`, F-15);
  - válido contra ese esquema.
- **FR-006**: Cada registro DEBE firmarse con «XAdES Enveloped» (ETSI EN 319 132):
  - clase EPES, con la política de firma de la AGE (`urn:oid:2.16.724.1.3.1.1.2.1.9`);
  - RSA con hash SHA-256;
  - sobre el nodo `RegistroAlta` o `RegistroAnulacion`, con la firma en su nodo `Signature`;
  - nunca sobre los nodos superiores (especificación de firma, §4 a §6).
- **FR-007**: La firma DEBE generarse **antes** de guardar el registro y en la misma operación que
  la emisión o la anulación. Un registro sin firma no existe: si la firma falla, la operación entera
  se deshace (F-4, p. 13).
- **FR-008**: El registro firmado DEBE guardarse con su registro:
  - inalterable en la base de datos, con las mismas garantías que el resto del registro (002,
    FR-029);
  - idéntico, byte a byte, a lo que se exporta.
- **FR-009**: La huella y el encadenamiento DEBEN seguir calculándose como en la 002 (Orden,
  art. 13.1.a y b). La firma no forma parte de la huella.
- **FR-010**: Antes de generar cada registro, el sistema DEBE comprobar que el último está bien
  encadenado y que su fecha de generación no supera en más de un minuto la hora actual (Orden,
  art. 7.i). Si no se cumple:
  - genera el evento de detección de anomalías con su tipo;
  - activa la alarma (art. 7.j);
  - **genera el registro igualmente**, porque la facturación nunca se interrumpe por este motivo
    (F-4, p. 28).

  En No VERI\*FACTU esto sustituye al bloqueo de la 002 (`cadena-inconsistente`).
- **FR-011**: La consulta de una factura DEBE mostrar, en cada uno de sus registros:
  - «Firmado», con la fecha y hora y el titular del certificado, en lugar de «Remisión:
    pendiente»;
  - una comprobación inmediata de su huella y de su firma (Orden, arts. 6.b y 6.d).

#### Registro de eventos

- **FR-012**: El sistema DEBE detectar y registrar, cuando se produzcan, los eventos del art. 9.1 de
  la Orden:
  - a) inicio del funcionamiento como No VERI\*FACTU, en cada arranque del servicio;
  - b) fin del funcionamiento, en cada parada ordenada del servicio;
  - c) y e) lanzamiento de la detección de anomalías en los registros de facturación y en los de
    evento;
  - d) y f) detección de anomalías en unos y otros;
  - h) e i) exportación de registros de facturación y de evento de un periodo.

  Varios procesos del servidor que arrancan a la vez cuentan como un solo arranque
  (Clarifications). El g), restauración de copias desde el propio sistema, no aplica.
- **FR-013**: El sistema DEBE generar un registro resumen de eventos (Orden, art. 9.2):
  - por cada 6 horas operativo y disponible;
  - aunque no haya pasado nada en ese tiempo;
  - antes de cerrarse o apagarse.

  El resumen recoge cuántos eventos de cada tipo ha habido y las altas y anulaciones generadas
  desde el resumen anterior, con su primer y su último registro y las sumas de cuotas e importes
  (`ResumenEventos`, F-17).
- **FR-014**: Cada registro de evento DEBE:
  - generarse en XML UTF-8, válido contra `EventosSIF.xsd` (F-17; Orden, art. 9.4);
  - llevar su huella SHA-256, calculada sobre los datos del art. 13.1.c, encadenada con la del
    evento anterior (`EventoAnterior`) o identificado como primero;
  - firmarse igual que los registros de facturación, sobre el nodo `RegistroEvento` (FR-006);
  - guardarse inalterable en la base de datos, con las mismas garantías (art. 9.3).
- **FR-015**: Antes de generar cada evento se DEBE comprobar el último evento, igual que en
  FR-010 (art. 9.3: arts. 6 a 8 aplicados por analogía, salvo el 7.d).
- **FR-016**: Un administrador DEBE poder consultar el registro de eventos desde «Registro fiscal»
  (RRSIF, art. 8.3):
  - una lista paginada, del más reciente al más antiguo;
  - filtros por tipo y por fechas;
  - el detalle de cada evento, con sus datos propios, su huella y el estado de su firma.

#### Comprobación de integridad y anomalías

- **FR-017**: Un administrador DEBE poder lanzar la comprobación de toda la cadena o de una parte
  desde la web («Comprobar integridad», con un rango opcional) y desde la consola
  (`verificar-cadena`). Es **solo bajo demanda**: no hay comprobación automática periódica
  (Clarifications; F-4, p. 30). La comprobación revisa, de los registros de facturación y de los de
  evento:
  - la integridad de las huellas;
  - la integridad de las firmas;
  - la trazabilidad de la cadena;
  - la trazabilidad de las fechas.

  Así cubre los arts. 6.b, 6.d, 6.e y 7.h de la Orden.
- **FR-018**: Cada comprobación DEBE generar:
  - los eventos de lanzamiento (c y e), con el número de registros procesados en cada una de las
    cuatro comprobaciones;
  - un evento de detección (d o f) por cada anomalía, con su tipo oficial (`TipoAnomalia`, F-17)
    y la identificación del registro o evento afectado.
- **FR-019**: Al detectarse una anomalía, el sistema DEBE mostrar una alarma visible para todos los
  usuarios en todas las pantallas (Orden, art. 6.f.1.º). La alarma:
  - indica claramente el hecho y la fecha;
  - no se desactiva hasta que una comprobación posterior confirma la integridad de los registros
    generados después del afectado;
  - incluye la alarma de certificado no utilizable (FR-004).
- **FR-020**: Desde cualquier registro de facturación, y de forma análoga desde cualquier evento, un
  administrador DEBE poder saltar al anterior y al siguiente de la cadena (Orden, art. 7.h). Para
  cada salto se indica:
  - si el encadenamiento de la huella es correcto;
  - si las fechas y horas de generación respetan el orden entre sí y con la hora actual.
- **FR-021**: `verificar-cadena` DEBE terminar con código de error y señalar la primera anomalía si
  alguna comprobación falla. Amplía el comportamiento de la 002.

#### Exportación

- **FR-022**: Un administrador DEBE poder exportar, por periodo de fecha y hora de generación,
  desde la web y desde la consola (`exportar-registros`):
  - los registros de facturación generados en él;
  - los registros de evento.

  El resultado es un fichero descargable.
- **FR-023**: La exportación DEBE ser un fichero ZIP con (Clarifications):
  - un fichero XML por registro, copia fidedigna e idéntica byte a byte a la firmada, sin
    reempaquetar, nombrado por su número de secuencia para que se ordene como la cadena (Orden,
    art. 8.2; F-4, p. 38);
  - un índice legible en CSV con número de secuencia, tipo, factura, fecha y hora de generación y
    huella;
  - un manifiesto con el SHA-256 de cada fichero;
  - un resumen con el periodo, el primer y el último registro, los recuentos y las sumas.

  Cada XML mantiene la estructura y el formato de los arts. 10 y 11 (art. 8.5).
- **FR-024**: Cada exportación DEBE generar su evento (h o i) con el contenido de
  `ExportacionRegFacturacionPeriodo` o `ExportacionRegEventoPeriodo` (F-17). La indicación de que
  los registros exportados dejan de conservarse va siempre en «N».
- **FR-025**: La exportación NUNCA DEBE borrar ni alterar registros. No hay ninguna funcionalidad
  para dejar de conservarlos (Orden, art. 8.2, tercer párrafo). Es independiente de las copias de
  seguridad.
- **FR-026**: Un periodo sin registros DEBE responder con un aviso de que no hay nada que exportar,
  sin fichero y sin evento. El esquema exige un primer y un último registro.

#### Declaración responsable y datos del sistema

- **FR-027**: Cualquier usuario DEBE poder abrir «Acerca del sistema» desde todas las pantallas, a
  dos clics como máximo. Muestra:
  - los datos del sistema informático: nombre, código identificador, versión, número de
    instalación y productor;
  - la declaración responsable vigente para la versión en uso.
- **FR-028**: La declaración responsable DEBE comenzar con «DECLARACIÓN RESPONSABLE DEL SISTEMA
  INFORMÁTICO DE FACTURACIÓN» y contener, en el orden y con los textos descriptivos del art. 15.1
  de la Orden, las letras a) a l). Entre ellas:
  - e) que **no** funciona exclusivamente como VERI\*FACTU;
  - f) que **no** admite varios obligados tributarios;
  - g) que firma con «XAdES Enveloped»;
  - h) a j): Joyería Blanco como productora, con su NIF y su dirección postal;
  - k) la declaración de cumplimiento;
  - l) la fecha y el lugar de la suscripción.

  Se puede descargar en un formato de uso extendido y gratuito (art. 15.3).
- **FR-029**: Se DEBEN conservar las declaraciones de todas las versiones del sistema (RRSIF,
  art. 13.3). Una versión nueva lleva su propia declaración.

#### Integración con el resto del sistema

- **FR-030**: El QR de las facturas DEBE seguir usando la dirección de cotejo de No VERI\*FACTU, sin
  la frase VERI\*FACTU. Ya está hecho en la 003, y se comprueba que se mantiene.
- **FR-031**: El estado de remisión de los registros DEBE dejar de presentarse como «pendiente».
  En No VERI\*FACTU no aplica, y los textos de la web dejan de anunciar una «remisión a la AEAT».
- **FR-032**: Los datos de ejemplo DEBEN cargarse en No VERI\*FACTU, con un certificado de prueba,
  registros firmados y sus eventos. El certificado de prueba no se puede usar en producción.
- **FR-033**: La auditoría DEBE recoger quién lanza cada comprobación y cada exportación, como un
  evento de auditoría distinto del evento fiscal. Los registros de actividad solo contienen
  números, tipos y recuentos, nunca datos personales, importes ni secretos del certificado.
- **FR-034**: Los presupuestos NO DEBEN generar registros, firmas ni eventos (005, FR-005).

### Key Entities *(include if feature involves data)*

- **Registro de facturación** (ampliado): el de la 002, más su versión firmada en el formato oficial,
  el titular del certificado con que se firmó y un estado de remisión «no aplica». Inalterable.
- **Registro de evento**: tipo oficial, fecha y hora de generación con huso, datos propios según el
  tipo y sistema informático. Lleva también el obligado, el encadenamiento con el evento anterior,
  la huella y la versión firmada en el formato oficial. Forma su propia cadena, inalterable.
- **Certificado de firma**: el de la empresa o su representante, con su titular, identificación,
  emisor y validez. No se guarda en la base de datos: lo instala quien despliega.
- **Exportación**: un fichero con los registros de un periodo y su resumen. No se guarda: queda su
  evento.
- **Declaración responsable**: el texto del art. 15.1 para cada versión del sistema, con la fecha y
  el lugar de la suscripción.
- **Alarma de integridad**: el estado activo o inactivo, el motivo y el registro o evento afectado,
  derivado de las anomalías detectadas y de las comprobaciones posteriores.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100 % de los registros de facturación y de evento generados en las pruebas es
  válido contra el esquema oficial, y su firma se verifica con el certificado.
- **SC-002**: Sin un certificado utilizable, el 100 % de los intentos de emitir, anular o rectificar
  termina sin factura nueva, sin número consumido y sin registro.
- **SC-003**: El 100 % de las alteraciones de un registro o de un evento hechas por fuera del sistema
  en las pruebas se detecta con el tipo de anomalía correcto. Las alteraciones cubren un dato, la
  huella, la firma, un borrado y una fecha.
- **SC-004**: En una ejecución continua de 24 horas hay al menos 4 resúmenes de eventos. Cada
  exportación y cada comprobación dejan su evento, y la cadena de eventos queda íntegra.
- **SC-005**: Exportar los registros de un año con 20.000 facturas termina en menos de 1 minuto. El
  fichero contiene todos los registros, idénticos a los guardados.
- **SC-006**: Comprobar la integridad completa con 20.000 registros de facturación y sus eventos
  termina en menos de 3 minutos.
- **SC-007**: Con la firma, el 95 % de las emisiones sigue completándose en menos de 1 segundo, igual
  que en la 002.
- **SC-008**: Cualquier usuario llega a la declaración responsable en 2 clics como máximo desde
  cualquier pantalla.
- **SC-009**: Una anomalía detectada se ve como alarma en la siguiente pantalla que abra cualquier
  usuario.

## Conformidad con el sistema de diseño

- **Pantallas nuevas**: «Registro fiscal» (eventos, comprobación y exportación) y «Acerca del
  sistema». Usan los componentes de DESIGN.md: tablas, chips, modal de nivel 2 y botones.
- **Alarma de integridad y aviso del certificado**: usan los tonos `danger` y `warning` de
  DESIGN.md, siempre con texto y nunca solo con color.
- **La declaración responsable descargable** es un documento «Paper» (DESIGN.md, sección «Paper»).

## Fuentes normativas citadas

La numeración continúa la de las features 002, 003 y 005.

| Id | Documento | Versión o fecha | Verificación |
|---|---|---|---|
| F-1 | Diseños de registro, `DsRegistroVeriFactu.xlsx` (002) | 1.0 | SHA-256 en 002, R-1 |
| F-4 | FAQ de empresas de desarrollo, `FAQs-Desarrolladores.pdf`: pp. 12 y 13 (firma y eventos en No VERI\*FACTU), 28 a 30 (anomalías y continuidad de la facturación) y 38 (requerimientos) | 1.3 (04/12/2025) | SHA-256 `73906dc8…09d5e`, igual que en 002, descargado de nuevo el 2026-10-03 |
| F-8 | RD 1007/2023 (RRSIF), arts. 8, 12, 13 y 16 | consolidado al 03/12/2025 | BOE-A-2023-24840, consultado el 2026-10-03 |
| F-10 | Orden HAC/1177/2024, arts. 3, 4, 6 a 9, 13 a 15 y 18 | consolidada al 28/10/2024 | BOE-A-2024-22138, consultada el 2026-10-03 |
| F-14 | «VERI\*FACTU - Especificaciones técnicas para generación de la firma electrónica de los registros de facturación», `EspecTecGenerFirmaElectRfact.pdf`: §2 a §6 | 0.1.5 (06/03/2025) | SHA-256 `60953acd5d437a745db9076377739d8ef3f05c31967c1424cd4f6a8ac04af481` |
| F-15 | `SuministroInformacion.xsd` (registros de alta y anulación) | IDVersion 1.0 | SHA-256 `ee4c1655175644de44c4c25055ffeb8e5f4bb4bc3834ce8254d4222ef18c8aa1` |
| F-16 | `SuministroLR.xsd` (agrupación de registros) | 1.0 | SHA-256 `cbdac8d427cc5ab5d77ca48974cab0f35d6bb819c4c66db361681e3710aeba36` |
| F-17 | `EventosSIF.xsd` (registro de eventos de No VERI\*FACTU) | IDVersion 1.0 | SHA-256 `cc7347c6a9a57a0c8edbc6b9ddcce55176452d0db0e68369477e207e9fbdd7e7` |
| F-18 | `AnexosEjemplosFirmaRegFact.zip` (registro sin firmar y firmado) | con F-14 | SHA-256 `66fac533bef6c93c041b08704bf538843fe552052a2994899aba0875c2c4b24e` |
| F-19 | Ejemplos de declaraciones responsables (Sede de la AEAT, «Información técnica») | página HTML | consultada el 2026-10-03 |

Las URL completas y la transcripción de los artículos citados van en `research.md`. Los XSD se
descargaron el 2026-10-03 de
`https://prewww2.aeat.es/static_files/common/internet/dep/aplicaciones/es/aeat/tikeV1.0/cont/ws/`,
y la especificación de firma de
`https://www.agenciatributaria.es/static_files/AEAT_Desarrolladores/EEDD/IVA/VERI-FACTU/Espec-Tecnicas/`.

## Riesgo normativo asumido por el responsable

- **Lo que dice la norma**:
  - El RRSIF (art. 8.1, segundo párrafo) dice que el sistema «deberá tener capacidad de remitir
    por medios electrónicos a la Administración tributaria [...] todos los registros de
    facturación generados».
  - La Orden HAC/1177/2024 (art. 4) concreta que esa capacidad implica conectarse a los servicios
    de la AEAT, gestionar certificados, remitir los registros, «tanto el envío automatizado [...]
    como, en su caso, el envío en respuesta a un requerimiento», y procesar las respuestas.
  - El art. 18 prevé que, ante un requerimiento, el obligado «podrá» suministrar los registros por
    un servicio web específico.
- **Decisión del responsable (2026-10-03)**: esta feature **no** implementa esa capacidad. Un
  requerimiento se atiende con la exportación de los registros firmados, exactamente como se
  generaron (FR-022 a FR-026).
- **Consecuencias**:
  - El sistema no puede funcionar como VERI\*FACTU (FR-001).
  - La declaración responsable describe el sistema tal como es (FR-028, letra e).
- **Pendiente**: el responsable valida esta decisión con su asesoría antes de la puesta en
  producción. Si la asesoría exige la capacidad de remisión, se tratará en una feature posterior,
  que también se haría primero contra el entorno de pruebas de la AEAT.

## Fuera de alcance

- **Cualquier envío a la AEAT**:
  - el funcionamiento VERI\*FACTU;
  - el servicio web de remisión ante un requerimiento (Orden, art. 18);
  - la consulta de registros remitidos;
  - la subsanación por rechazo (002, FR-027).
- **Preguntas abiertas de la 002 que solo tenían sentido con envío**: Q-3 (códigos de error de
  la matriz de alta y anulación), Q-8 (NIF no censado) y Q-11 (rechazo por un tipo de IVA). Quedan
  cerradas como «no aplica».
- **Cambio de modalidad**: sigue bloqueado con registros (002, FR-050).
- **Copias de seguridad gestionadas desde la aplicación**, y por tanto el evento del art. 9.1.g.
- **Eventos voluntarios del productor** (tipo 90).
- **Dejar de conservar registros exportados** (Orden, art. 8.2, tercer párrafo).
- **Uso por varios obligados tributarios** (`IndicadorMultiplesOT`).

## Assumptions

- **Hora del servidor**: está sincronizada con una fuente horaria fiable. El margen de error de un
  minuto del art. 7.f de la Orden es responsabilidad del obligado, y la puesta en producción lo
  comprueba.
- **Certificado**:
  - Lo obtiene Joyería Blanco como certificado cualificado de un prestador de la lista de
    confianza de la UE, en un formato exportable con su clave privada.
  - El sistema comprueba su validez temporal y su aptitud para firmar, pero no su presencia en la
    lista de confianza: eso queda a cargo de quien lo obtiene.
  - La revocación no se consulta en línea, porque la feature no se conecta a servicios externos.
    El responsable avisará si el certificado se revoca.
- **Pruebas**: se usan certificados de prueba, autofirmados, generados para los tests. No son
  cualificados y el sistema impide usarlos en producción.
- **Validación externa**: la conformidad de la firma con lo que espera la AEAT se valida a mano,
  con un validador oficial, sobre un registro exportado (quickstart).
- **Datos del productor**: el NIF y la dirección postal salen de los datos del sistema informático.
  Son los mismos que los del emisor, porque Joyería Blanco es productora y usuaria. La fecha y el
  lugar de la suscripción los fija el responsable para cada versión.
- **Resumen periódico**: lo genera el propio servidor mientras está operativo. El intervalo de 6
  horas se cuenta desde el resumen anterior o desde el inicio.
