# Research — 004 Modalidad No VERI\*FACTU

Fase 0 del plan. Todas las fuentes se consultaron o descargaron el 2026-10-03. Las copias de los
esquemas se guardan en el repositorio con su SHA-256 (R-2). Lo que no se ha podido verificar en
fuente oficial está en «Preguntas abiertas» (R-16).

## Fuentes

| Id | Documento | URL | Versión | SHA-256 |
|---|---|---|---|---|
| F-2 | Especificaciones de la huella | `https://www.agenciatributaria.es/static_files/AEAT_Desarrolladores/EEDD/IVA/VERI-FACTU/Veri-Factu_especificaciones_huella_hash_registros.pdf` | 0.1.2 (27/08/2024) | `f4334c254bb875b417247b54315199f89d75a8c4814dfd1e86efec562653d7de` (igual que en 002) |
| F-4 | FAQ de empresas de desarrollo | `https://sede.agenciatributaria.gob.es/static_files/AEAT_Desarrolladores/EEDD/IVA/VERI-FACTU/FAQs-Desarrolladores.pdf` | 1.3 (04/12/2025) | `73906dc8afbbb9da35f6cb489980352b42aed66d48828fd62a00168883c09d5e` (igual que en 002) |
| F-8 | RD 1007/2023 (RRSIF), arts. 8, 12, 13 y 16 | `https://www.boe.es/buscar/act.php?id=BOE-A-2023-24840` | consolidado al 03/12/2025 | texto HTML |
| F-10 | Orden HAC/1177/2024, arts. 3, 4, 6 a 9, 13 a 15 y 18 | `https://www.boe.es/buscar/act.php?id=BOE-A-2024-22138` | consolidada al 28/10/2024 | texto HTML |
| F-14 | Especificaciones técnicas de la firma electrónica de los registros | `https://www.agenciatributaria.es/static_files/AEAT_Desarrolladores/EEDD/IVA/VERI-FACTU/Espec-Tecnicas/EspecTecGenerFirmaElectRfact.pdf` | 0.1.5 (06/03/2025) | `60953acd5d437a745db9076377739d8ef3f05c31967c1424cd4f6a8ac04af481` |
| F-15 | `SuministroInformacion.xsd` | `https://prewww2.aeat.es/static_files/common/internet/dep/aplicaciones/es/aeat/tikeV1.0/cont/ws/SuministroInformacion.xsd` | IDVersion 1.0 | `ee4c1655175644de44c4c25055ffeb8e5f4bb4bc3834ce8254d4222ef18c8aa1` |
| F-16 | `SuministroLR.xsd` | `…/tikeV1.0/cont/ws/SuministroLR.xsd` | 1.0 | `cbdac8d427cc5ab5d77ca48974cab0f35d6bb819c4c66db361681e3710aeba36` |
| F-17 | `EventosSIF.xsd` | `…/tikeV1.0/cont/ws/EventosSIF.xsd` | IDVersion 1.0 | `cc7347c6a9a57a0c8edbc6b9ddcce55176452d0db0e68369477e207e9fbdd7e7` |
| F-18 | `AnexosEjemplosFirmaRegFact.zip`: `ejemploRegistro.xml` y `ejemploRegistro-firmado-epes-xades4j.xml` | `https://www.agenciatributaria.es/static_files/AEAT_Desarrolladores/EEDD/IVA/VERI-FACTU/Espec-Tecnicas/AnexosEjemplosFirmaRegFact.zip` | con F-14 | `66fac533bef6c93c041b08704bf538843fe552052a2994899aba0875c2c4b24e` |
| F-19 | Ejemplos de declaraciones responsables | `https://sede.agenciatributaria.gob.es/Sede/iva/sistemas-informaticos-facturacion-verifactu/informacion-tecnica/ejemplo-declaracion-responsable.html` | página HTML | — |
| F-20 | `xmldsig-core-schema.xsd` (W3C), que importan F-15 y F-17 | `http://www.w3.org/TR/xmldsig-core/xmldsig-core-schema.xsd` | REC 2002 | `d102ad3df7664c307e0c2c776ba4a90513b1969974d8a940bae1a77f9f21e15d` |

### Transcripción de lo que rige el diseño

- **RRSIF**:
  - Art. 8.2 y 8.3: integridad, trazabilidad, conservación y exportación. Registro de eventos «que
    recoja automáticamente, en el momento en que se produzcan, [...] que deberán poder ser
    consultados desde el propio sistema».
  - Art. 12: los registros de alta y de anulación «deberán ser firmados electrónicamente».
  - Art. 13: declaración responsable «por escrito y de modo visible en el propio sistema» (13.2).
    El productor conserva las de todas las versiones (13.3).
  - Art. 16.3: solo VERI\*FACTU queda exento de firmar.
- **Orden HAC/1177/2024**:
  - Art. 3: VERI\*FACTU queda exento de los arts. 6.b a 6.f, 7.f, 7.h a 7.j, 8 y 9. En No
    VERI\*FACTU **todos aplican**.
  - Art. 6, letras b a f: comprobar bajo demanda la huella y la firma de cualquier registro y toda
    o parte de la cadena, «de forma rápida, fácil e intuitiva». Ante una anomalía, «mostrar una
    alarma [...] no deberá desactivarse hasta que no se pueda volver a garantizar la integridad
    [...] de los siguientes registros» y generar el evento.
  - Art. 7.h: desde cualquier registro, saltar al anterior y al posterior indicando si el
    encadenamiento de la huella es correcto y si las fechas respetan el orden entre sí y con la
    fecha actual.
  - Art. 7.i y 7.j: comprobación previa del último registro y aviso.
  - Art. 8: conservación, exportación de un periodo con «copia fidedigna» y legibilidad en el
    formato de los arts. 10 y 11.
  - Art. 9:
    - 9.1: eventos a) a i).
    - 9.2: un resumen «por cada 6 horas que haya estado operativo y disponible», también sin
      eventos, y otro «antes de cerrarse o apagarse».
    - 9.3: arts. 6 a 8 aplicados por analogía a los eventos, salvo el 7.d.
    - 9.4: XML UTF-8 con la estructura del anexo, apartado 5.
  - Art. 13.1.c: datos de la huella del evento.
  - Art. 14: XAdES Enveloped (ETSI EN 319 132) con certificado cualificado en vigor, de la lista de
    confianza de la UE.
  - Art. 15: contenido literal de la declaración responsable.
  - Art. 4 y art. 18: capacidad de remisión y remisión ante un requerimiento. Quedan **fuera** por
    decisión del responsable (spec, «Riesgo normativo asumido»).
- **F-4 (FAQ)**:
  - P. 13: «en NO VERI\*FACTU, el RF solo se considera generado cuando está firmado».
  - P. 28: ante un último registro mal encadenado, «es preciso guardar un evento de ello [...] y
    advertir del error [...]. Pero será preciso generar el siguiente RF, ya que la facturación por
    este motivo NUNCA debe interrumpirse».
  - Pp. 29 y 30: la detección de anomalías no tiene que ejecutarse constantemente: basta con que
    esté disponible bajo demanda. La comprobación previa a cada registro es siempre obligatoria.
  - P. 38: ante un requerimiento, los registros se entregan «tal cual fueron generados, sin ninguna
    alteración».
- **F-14**:
  - §2: firma solo en No VERI\*FACTU, sobre las altas, las anulaciones y los eventos.
  - §3: certificado cualificado, en vigor en la fecha del registro, de la empresa o de su
    representante.
  - §4:
    - XAdES Enveloped, clase EPES;
    - política de la AGE: OID `urn:oid:2.16.724.1.3.1.1.2.1.9`, URL
      `https://sede.administracion.gob.es/politica_de_firma_anexo_1.pdf`, hash SHA-1
      `G7roucf600+f03r/o0bAOQ6WAs0=`;
    - RSA con SHA-256 y clave de 1024 bits o más;
    - sello de tiempo opcional.
  - §5 y §6: se firma el nodo `RegistroAlta`, `RegistroAnulacion` o `RegistroEvento`, con la firma
    en su `Signature`, nunca en los nodos superiores.
- **F-2, §3.c**: la huella del evento se calcula sobre
  `NIF=…&ID=…&IdSistemaInformatico=…&Version=…&NumeroInstalacion=…&NIF=…&TipoEvento=…&HuellaEvento=…&FechaHoraHusoGenEvento=…`:
  - el primer `NIF` es el del sistema informático (el productor) y el segundo, el del obligado;
  - un campo vacío o ausente va solo como `nombre=`;
  - SHA-256 en hexadecimal mayúsculas.

  F-2 no trae vectores para eventos, solo para las altas y la anulación.

## R-1. Generación del XML

**Decisión**: un módulo de dominio puro, `domain/xml_registro.py`, convierte el contenido en XML.
- **Entrada**: el `contenido` de un registro de facturación (002, `domain/registro.py`) o el de un
  evento.
- **Salida**: un elemento `RegistroAlta` o `RegistroAnulacion` en el espacio de nombres de F-15, o
  `RegistroEvento` en el de F-17.
- **Orden**: tablas explícitas de orden por tipo, sacadas de los XSD:
  - `RegistroFacturacionAltaType`: `IDVersion`, `IDFactura`, … , `TipoHuella`, `Huella` y
    `ds:Signature`;
  - `RegistroFacturacionAnulacionType`;
  - `EventoType`.

  El orden no depende del diccionario: JSONB no lo conserva.
- **Momento**: el XML se genera **en memoria, antes de insertar**, a partir del `contenido` recién
  construido. Se valida contra el XSD, se firma y se guarda.

**Razón**: el XSD es la fuente de verdad del orden y los tests lo validan (constitución VII). El
`contenido` de 002 ya tiene todos los valores como texto, en el formato oficial.

**Alternativas descartadas**: plantillas de texto, frágiles con el escapado y los bloques
opcionales.

## R-2. Validación contra los XSD oficiales

**Decisión**:
- **Copias**: F-15, F-16, F-17 y el XSD de XML-DSig del W3C (F-20) se guardan en
  `backend/app/resources/aeat/xsd/`, con un `README.md` que anota la URL, la fecha y el SHA-256 de
  cada uno.
- **Validación**: con `lxml`, y un resolvedor local para la `schemaLocation` remota de
  `xmldsig-core-schema.xsd`, así que no hace falta red.
- **Cuándo**: el XML se valida **siempre antes de guardarlo, ya firmado**, en todos los entornos.
  Es lo que se guarda y se exporta, y en `EventoType` la firma es obligatoria, así que un evento
  sin firmar no cumple el esquema. El esquema compilado se cachea. Un fallo es un error de
  programación: la operación se deshace.
- **Tests**: un test comprueba que los SHA-256 de las copias son los anotados.

## R-3. Firma XAdES-EPES

**Decisión**: `signxml` 5.1 (con `lxml` y `cryptography`, dependencias nuevas) y una subclase de
`XAdESSigner`, que reproduce el ejemplo oficial F-18:
- **SignedInfo**:
  - canonicalización C14N inclusiva (`http://www.w3.org/TR/2001/REC-xml-c14n-20010315`) y
    `rsa-sha256`;
  - una referencia `URI=""` con la transformación *enveloped* y digest SHA-256, y la referencia a
    `SignedProperties`.
- **QualifyingProperties** (XAdES 1.3.2):
  - `SigningTime`, en hora de Madrid;
  - `SigningCertificate`, la forma del ejemplo con SHA-1 e `IssuerSerial`, con la cadena del
    PKCS#12. Va **sola**: el verificador de `signxml` rechaza una firma que lleve a la vez
    `SigningCertificateV2` (comprobado en la implementación, 2026-10-03);
  - `SignaturePolicyIdentifier`: OID, `SigPolicyHash` SHA-1 `G7roucf6…` y el calificador `SPURI`
    con la URL de la política. Se añade sobrescribiendo `add_signature_policy_identifier`.
  - `DataObjectFormat`: `MimeType` `text/xml` y `Encoding` `UTF-8`. Se añade sobrescribiendo
    `add_data_object_format`.
- **KeyInfo**: `X509Data` con la cadena de certificados del PKCS#12 y `KeyValue`. Sin referencia
  al `KeyInfo` en `SignedInfo`: F-18 solo firma los datos y las `SignedProperties`, esta con su
  transformación C14N explícita.
- **Verificación**: con el certificado que lleva la firma y la vigencia comprobada en la fecha de
  generación del registro, no en la de hoy (F-14 §3). Si no, un registro firmado con un certificado
  que caducó después daría «firma incorrecta». Quien comprueba la integridad coteja además la
  huella del certificado guardada.
- **Comprobación con el ejemplo oficial**: firmando `ejemploRegistro.xml`, la referencia a los datos
  da el mismo `DigestValue` que F-18 (`89qWVKHv…`): la canonicalización coincide byte a byte.
  `signxml` no verifica F-18 tal cual, porque su `SigningCertificate` cita tres certificados y el
  `KeyInfo` solo trae uno. Nuestras firmas llevan en `KeyInfo` la misma cadena que citan.
- **Versión**: la subclase sobrescribe métodos de `signxml` 5.1, que se fija en `>=5.1,<5.2`.

**Prototipo (2026-10-03)**: `signxml` 5.1.0 firmó `ejemploRegistro.xml` de F-18 con un
certificado autofirmado, y `XAdESVerifier` lo verificó con la política esperada.

**Razón**: es una librería pura en Python sobre `lxml` y `cryptography`, sin bibliotecas del
sistema como `xmlsec1`, y verifica en los tests y en la comprobación de integridad. Con la subclase,
la firma coincide con el ejemplo de la AEAT nodo a nodo.

**Alternativas descartadas**:
- `xmlsec`: depende de `libxmlsec1` en la imagen.
- XAdES hecho a mano: más código criptográfico propio que auditar.

## R-4. El registro existe solo si está firmado

**Decisión**: en `services/cadena.py` (`create_registro_alta` y `create_registro_anulacion`), tras
calcular la huella y el `contenido`, y **antes de `repo.insert`**, en la misma transacción, si la
modalidad es `no_verifactu`:
1. Se obtiene el certificado utilizable en la fecha de generación (R-6).
2. Se genera el XML (R-1) y se valida (R-2).
3. Se firma (R-3).
4. Se guarda junto al registro: `xml_firmado` (bytes UTF-8 tal cual), `certificado_titular` y
   `certificado_huella` (SHA-256 del DER).

Si algo falla:
- `EmisionNoDisponible(faltan=["certificado"], motivo=…)`. La transacción se deshace entera:
  número, factura y registro.
- Para que el problema se vea antes del modal, los parámetros de facturación incluyen
  `certificado` en `faltan` (`ParametrosFacturacionSalida`, 002).

**Razón**: FR-007, F-4 p. 13. Las tablas son de solo inserción y no hay UPDATE posterior posible.

## R-5. La facturación no se interrumpe por una anomalía de la cadena

**Decisión**: en `no_verifactu`, `cadena.verify_tail` deja de bloquear. Si `tail_problem` encuentra
una huella recalculada distinta o una fecha más de un minuto en el futuro:
1. Mantiene el evento de auditoría `CADENA_INCONSISTENTE` (002).
2. Genera el evento fiscal 04, con su tipo de anomalía (R-10), en **otra transacción que se
   confirma ya**.
3. Activa la alarma (R-11).
4. **Sigue con la emisión.** El nuevo registro se encadena con la huella **guardada** del último,
   que es lo que exige el trigger `validar_encadenamiento`.

En `verifactu` se conserva el bloqueo de la 002, aunque no se use.

**Razón**: F-4 p. 28 y Orden 7.j.

## R-6. Certificado de firma

**Decisión**:
- **Ajustes nuevos**:
  - `CERTIFICADO_RUTA`: un fichero PKCS#12 (`.p12` o `.pfx`).
  - `CERTIFICADO_CONTRASENA`: un `SecretStr`.

  Si faltan, el certificado está «no instalado».
- **Producción**: el fichero se monta con un *secret* de Docker Compose, en solo lectura, en
  `/run/secrets/certificado.p12`, y la contraseña va en un secreto o variable aparte.
  `docker-compose.prod.yml` declara el *secret*; la API no lo guarda nunca en la BD.
- **Carga**: `services/certificado.py`.
  - Usa `cryptography.hazmat.primitives.serialization.pkcs12` y cachea por proceso, recargando si
    cambia la fecha de modificación del fichero.
  - Expone el estado: titular (CN y `serialNumber`), identificación (el NIF que aparezca en el
    sujeto), emisor, validez y días restantes.
  - Los motivos de no utilizable son `no_instalado`, `ilegible` (incluida la contraseña errónea),
    `caducado`, `aun_no_valido`, `sin_clave_privada`, `no_apto_para_firmar` (el `KeyUsage` no
    permite `digitalSignature` ni `nonRepudiation`) y `de_pruebas_en_produccion`.
- **Fecha**: la validez se comprueba en la fecha y hora de generación del registro (F-14 §3).
- **Certificados de prueba**:
  - `joyeria generar-certificado-pruebas --destino … --contrasena …` crea un PKCS#12 autofirmado
    con el sujeto marcado `O=PRUEBAS - SIN VALIDEZ`.
  - Lo usan el desarrollo y el E2E. Los tests generan los suyos en una carpeta temporal.
  - En producción, un certificado autofirmado o con esa marca es `de_pruebas_en_produccion`.
- **Aviso**: «caduca pronto» cuando quedan 30 días o menos (FR-003).

**Lo que no se hace**: comprobar la lista de confianza de la UE y la revocación en línea (spec,
«Assumptions»).

## R-7. Registro de eventos: datos y cadena

**Decisión**:
- **Tabla**: `registros_evento`, de solo inserción (data-model).
- **Cerrojo**: un cerrojo consultivo propio, `JBEVEN`.
- **Trigger**: `validar_encadenamiento_eventos`, como el de 002. Exige `secuencia = max+1` y que
  `huella_anterior` sea la huella del último.
- **Servicio**: `services/eventos_sif.py → record_evento(tipo, datos, …)`, en **su propia sesión y
  transacción**, confirmada al terminar. Así un evento nunca se pierde porque falle la operación
  que lo originó.
  1. Toma el cerrojo y comprueba el último evento por analogía con el 7.i. Si falla, genera antes
     el evento 06 y la alarma.
  2. Construye el `contenido`: `SistemaInformatico`, `ObligadoEmision` (el emisor de la
     configuración), `FechaHoraHusoGenEvento`, `TipoEvento`, `DatosPropiosEvento` según el tipo,
     `Encadenamiento` (`PrimerEvento` «S», o `EventoAnterior` con tipo, fecha y huella),
     `TipoHuella` «01» y `HuellaEvento`.
  3. Calcula la huella (F-2 §3.c) en `domain/huella.py` → `CamposHuellaEvento`.
  4. Genera el XML, lo valida contra F-17, lo firma (R-3) e inserta.
- **Sin certificado utilizable**: el evento no se puede firmar. Se registra un aviso en los logs y
  se mantiene la alarma de certificado. El siguiente resumen, ya con certificado, cubre el
  intervalo (spec, «Edge Cases»). Los eventos de anomalía y de exportación no se pierden porque
  sus operaciones exigen certificado.
- **Orden de cerrojos**: una emisión tiene el cerrojo de la cadena en su transacción, y el evento
  usa otra conexión con el de eventos. Nadie toma los dos en orden inverso, así que no hay ciclo.

## R-8. Inicio, fin y resumen: un líder por servicio

**Decisión**: en el `lifespan` de la API, cada proceso intenta `pg_try_advisory_lock(JBSIFL)` en
una conexión propia que mantiene abierta.
- **El que lo consigue es el líder**:
  - al arrancar, genera el evento 01;
  - cada minuto mira si han pasado 6 horas desde el último resumen, o desde el último inicio si
    no hay resumen posterior, y si es así genera el 10;
  - al apagarse, genera el resumen y el 02, y suelta el cerrojo.
- **Los demás procesos** reintentan cada minuto. Si el líder cae sin cerrarse, otro toma el relevo
  y genera un 01 nuevo. Su primer resumen cubre el intervalo (spec, «Edge Cases»).
- **Fuera de esto**: los comandos de consola no son el servicio y no generan inicio ni fin. Los
  tests no ejecutan el `lifespan` salvo los que lo prueban.
- **Contenido del resumen**:
  - los eventos por tipo desde el resumen anterior;
  - el primer y el último registro de facturación generados en el intervalo, con su huella;
  - el número de altas y de anulaciones;
  - las sumas de `CuotaTotal` e `ImporteTotal` de las altas.

**Razón**: se cumplen los arts. 9.1.a y b y 9.2 (Clarifications) con dos *workers* en producción
(`uvicorn --workers 2`) sin duplicar eventos.

## R-9. Comprobación de integridad

**Decisión**:
- **Servicio**: `services/integridad.py` amplía `verify_chain` de 002 con un rango opcional (de la
  secuencia X a la Y) y comprueba los registros de facturación y los de evento.
- **Por cada registro**:
  1. **Huella**: la del XML y la de la columna coinciden con la recalculada → anomalía 01.
  2. **Firma**: la firma XAdES se verifica con el certificado incluido, y su SHA-256 coincide con
     `certificado_huella` → anomalía 02.
  3. **Datos**: los del XML firmado coinciden con las columnas → anomalía 03.
  4. **Cadena**:
     - secuencias consecutivas → 04 y 05;
     - `huella_anterior` igual a la del anterior → 07 y 08.
  5. **Fechas**: la de generación no es anterior a la del registro anterior → 11, ni posterior a
     la actual → 13.
- **Eventos que genera**:
  - 03 y 05, con los recuentos de las cuatro comprobaciones;
  - un 04 o un 06 por cada anomalía, con `RegistroFacturacionAnomalo` (IDFactura) o
    `RegEventoAnomalo` (tipo, fecha y huella).
- **Registro de la comprobación**: cada una se guarda en `comprobaciones_integridad` (alcance,
  resultado y actor), que sirve para la alarma (R-11). La comprobación previa de cada emisión
  (7.i, R-5) no se guarda ahí: solo genera su evento 04.
- **Desde dónde**: «Comprobar integridad» en la web (síncrono) y `verificar-cadena` en la consola.
- **Medición**: SC-006 (20.000 registros en menos de 3 minutos) se mide en el test lento. Si la
  verificación de las firmas no llega, se paraleliza en hilos.

- **Una anomalía ya registrada no se repite**: si una comprobación vuelve a encontrar la misma
  (mismo tipo de anomalía y mismo registro o evento afectado), la cuenta en su resultado pero no
  genera otro 04 o 06 (art. 9.1: los eventos se registran «cuando se produzcan»).
- **Anomalías en los datos de la factura**: líneas, desglose o totales que ya no cuadran con el
  registro (la comprobación de 002) son la anomalía 03, «Integridad - Otros».

## R-10. Tipos de anomalía (F-17, `TipoAnomaliaType`)

| Código | Cuándo |
|---|---|
| 01 | La huella recalculada no coincide |
| 02 | La firma no verifica, o el certificado no es el registrado |
| 03 | El XML firmado y las columnas no coinciden |
| 04 | Un registro que no es el primero tiene el anterior inexistente (hueco) |
| 05 | Un registro que no es el último tiene el posterior inexistente |
| 07 | La huella del registro no coincide con la «huella del anterior» del posterior |
| 08 | La «huella del anterior» no coincide con la huella del anterior |
| 11 | La fecha de generación es anterior a la del registro anterior |
| 13 | La fecha de generación es posterior a la hora actual del sistema (más de un minuto, 7.i) |

Los códigos 06, 09, 10, 12, 14, 15 y 90 no se usan: sus casos ya los cubren los anteriores.

## R-11. Alarma

**Decisión**: es un estado **derivado**, sin tabla propia.
- **Integridad**: cada evento 04 o 06 guarda la secuencia del registro o del evento afectado
  (`secuencia_afectada`). La alarma de esa anomalía se apaga con una comprobación lanzada
  **después** del evento que:
  - cubre todo lo posterior al afectado: empieza en él o antes y llega al final de la cadena;
  - no encuentra ninguna anomalía **posterior** al afectado (`max_secuencia_anomala` o
    `max_evento_anomalo`, según la cadena).

  La anomalía antigua sigue ahí, porque los registros no se pueden corregir, pero ya se garantizan
  los siguientes (Orden, art. 6.f; FR-019). Sin registro afectado, hace falta una comprobación
  completa sin anomalías.
- **Certificado**: activa si el certificado no es utilizable.
- **Endpoint**: `GET /v1/alarmas`, accesible a cualquier sesión. La web lo consulta al cambiar de
  ruta y cada minuto. La banda la ven todos (Clarifications), y el detalle, solo los
  administradores.

## R-12. Exportación

**Decisión**:
- **Endpoint**: `GET /v1/registro-fiscal/exportacion?tipo=facturacion|eventos&desde=…&hasta=…`
  (fecha y hora de generación, hora de Madrid), solo para administradores. La consola tiene
  `exportar-registros`.
- **Fichero**: un ZIP que se construye en un fichero temporal (`/tmp`, tmpfs en producción) y se
  sirve con `Content-Disposition: attachment`:
  - `facturacion/0000123-alta-FAC-2026-0045.xml`: el `xml_firmado` **tal cual**, byte a byte;
  - `indice.csv`: secuencia, tipo, factura, fecha y hora de generación, huella y titular del
    certificado;
  - `manifiesto.sha256`: una línea `sha256  ruta` por fichero;
  - `resumen.txt`: periodo, primer y último registro, recuentos y sumas.
- **Evento**: el 08 o el 09 se genera cuando el ZIP está completo, con
  `RegistrosFacturacionExportadosDejanDeConservarse` o `RegEventoExportadosDejanDeConservarse`
  «N».
- **Periodo vacío**: 422 `sin-registros`, sin fichero y sin evento.

**Razón**: FR-022 a FR-026 y Clarifications. No se reempaqueta, así que la canonicalización no
cambia y la firma sigue verificándose fuera del sistema.

## R-13. Declaración responsable

**Decisión**:
- **Texto**: `services/sistema.py` lo construye con la letra y el orden del art. 15.1:
  - a) a c): `SIF_NOMBRE_SISTEMA`, `SIF_ID_SISTEMA` y `app.__version__`;
  - d): componentes (servidor con API y base de datos en contenedores, aplicación web y
    navegador) y funciones;
  - e) «No»; f) «No»; g) «XAdES Enveloped (EPES)»;
  - h) a j): `SIF_PRODUCTOR_NOMBRE`, `SIF_PRODUCTOR_NIF` y el nuevo `SIF_PRODUCTOR_DIRECCION`;
  - k): el texto literal de cumplimiento;
  - l): los nuevos `SIF_DECLARACION_FECHA` y `SIF_DECLARACION_LUGAR`.
- **En producción**: los ajustes nuevos son obligatorios, igual que el productor (002, R-5).
- **Dónde se ve**:
  - `GET /v1/sistema`, para cualquier sesión, con los datos del sistema y la declaración
    estructurada;
  - `GET /v1/sistema/declaracion-responsable/pdf`, un documento «Paper» con WeasyPrint (003);
  - la página web `/acerca`.
- **Versiones anteriores** (RRSIF 13.3): el productor archiva el PDF de cada versión en
  `docs/declaraciones/`, como paso del despliegue (quickstart).
- **Versión**: `app.__version__` pasa a `0.4.0` con esta feature.

## R-14. Modalidad, estado de remisión y datos de ejemplo

**Decisión**:
- **Migración 0009**:
  - fija `configuracion_facturacion.modalidad = 'no_verifactu'` si está a NULL;
  - amplía el CHECK de `registros_facturacion.estado_remision` con `no_aplica`.
- **Registros nuevos en `no_verifactu`**: llevan `no_aplica` (`EstadoRemision.NO_APLICA`).
- **API**: `PUT /configuracion/facturacion` rechaza `modalidad: verifactu` con 422 `validacion` en
  el campo («VERI\*FACTU no está disponible: el sistema no tiene capacidad de remisión»). El
  bloqueo con registros (002) se mantiene, con el mensaje revisado.
- **Datos de ejemplo**:
  - se cargan en `no_verifactu`;
  - si no hay certificado configurado, la carga genera uno de prueba en una carpeta temporal o
    usa el de `CERTIFICADO_RUTA`;
  - en E2E, `global-setup` genera el `.p12` y lo pasa a `api-e2e`.

## R-15. Pantallas

**Decisión**:
- **«Registro fiscal»** (`/registro-fiscal`, solo administradores), con pestañas:
  - «Eventos»: lista, filtros y detalle;
  - «Cadena»: navegación de los registros de facturación y de evento (7.h);
  - «Comprobar integridad»;
  - «Exportar».
- **«Acerca del sistema»** (`/acerca`): para cualquier sesión, enlazada desde el menú de usuario y
  el pie del menú lateral.
- **Banda de alarma**: en el *layout* de la aplicación.
- **Tarjeta del certificado**: en Configuración → Facturación.
- **Consulta de la factura**: cada registro muestra «Firmado», el titular, si la huella y la firma
  son correctas, y el enlace a la cadena (solo administradores).
- Todo con los componentes y tokens de DESIGN.md.

## R-16. Preguntas abiertas

| Id | Pregunta | Fuente | Tratamiento |
|---|---|---|---|
| Q-12 | La firma que espera la AEAT: ¿le basta `SigningCertificateV2` o requiere la forma heredada del ejemplo? | F-14 no lo dice; F-18 usa la heredada | Se emite la del ejemplo, `SigningCertificate` (R-3). Se valida a mano con VALIDe (quickstart) |
| Q-13 | Capacidad de remisión (RRSIF 8.1, Orden 4) | F-8, F-10 | Fuera de alcance por decisión del responsable, que lo consulta con su asesoría (spec) |
| Q-14 | Cómo nombrar la versión y el número de instalación en el `SistemaInformatico` cuando cambie la versión | F-10 art. 15.1.c | Un registro guarda la versión con la que se generó. La versión nueva lleva su declaración |

Las preguntas Q-3, Q-8 y Q-11 de 002 quedan cerradas como «no aplica», porque no hay envío.
