# Research — 002 Facturación con registro Verifactu

**Fecha**: 2026-09-28 · **Spec**: [spec.md](spec.md)

Cada decisión sigue el formato **Decisión** · **Razón** · **Alternativas descartadas**.

Por la constitución (principio IV), toda regla fiscal o de formato sale de una fuente oficial y se
cita con su versión y su SHA-256. Las fuentes se descargaron el 2026-09-28. Las mismas fuentes,
numeradas F-n, aparecen en la spec.

| Id | Documento | Versión / fecha | SHA-256 |
|---|---|---|---|
| F-1 | AEAT, `DsRegistroVeriFactu.xlsx` | 1.0 (28/10/2024) | `40ce191aa1def6e44a5f1e86d7ece727258745b34e3fe4d6abe1468252dac2ca` |
| F-2 | AEAT, *Detalle de las especificaciones técnicas para generación de la huella o hash de los registros de facturación* (`Veri-Factu_especificaciones_huella_hash_registros.pdf`) | 0.1.2 (27/08/2024) | `f4334c254bb875b417247b54315199f89d75a8c4814dfd1e86efec562653d7de` |
| F-3 | AEAT, *Validaciones y errores VERI\*FACTU* (`Validaciones_Errores_Veri-Factu.pdf`) | 1.2.2 (08/04/2026) | `426eb926fc098a36a163f66ca5f40d9e0847ca23300bbe5008979832d3513440` |
| F-4 | AEAT, *Aclaraciones a dudas de los desarrolladores* (`FAQs-Desarrolladores.pdf`) | 1.3 (04/12/2025) | `73906dc8afbbb9da35f6cb489980352b42aed66d48828fd62a00168883c09d5e` |
| F-5 | AEAT, FAQ «Registros de facturación: alta» y «… anulación» | páginas del 22/07/2026 | HTML (sin hash estable) |
| F-6 | RD 1619/2012 (ROF), BOE-A-2012-14696 | consolidado a 31/03/2026 | — |
| F-7 | Ley 58/2003 (LGT), art. 201 bis, BOE-A-2003-23186 | consolidado a 21/12/2024 | — |
| F-8 | RD 1007/2023 (RRSIF), BOE-A-2023-24840 | consolidado a 03/12/2025 | — |
| F-9 | AEAT, FAQ «Procedimientos de facturación» | página del 22/07/2026 | HTML |
| F-10 | Orden HAC/1177/2024, BOE-A-2024-22138 | consolidado a 28/10/2024 | PDF consolidado `a0090109d56c29c1f1d9be42df5fecc5d7b2384605dd2b2af549236ff5bcc5de` |

**URLs**:
- Documentos de desarrolladores AEAT (F-1 a F-4):
  `https://www.agenciatributaria.es/static_files/AEAT_Desarrolladores/EEDD/IVA/VERI-FACTU/<fichero>`.
  F-4 está en `sede.agenciatributaria.gob.es/static_files/…`.
- FAQ (F-5 y F-9): `https://sede.agenciatributaria.gob.es/Sede/iva/sistemas-informaticos-facturacion-verifactu/preguntas-frecuentes/`.
- BOE (F-6, F-7, F-8 y F-10): `https://www.boe.es/buscar/act.php?id=<id>`.

---

## R-1. Marco normativo que condiciona el diseño

Transcripción literal de los puntos que obligan al diseño:

- **Integridad** (F-8, art. 8.2.a): los registros «no puedan ser alterados sin que el sistema
  informático lo detecte y avise de ello». Además: «Cualquier necesidad de corrección o anulación
  de los datos registrados deberá ser realizada mediante al menos un registro de facturación
  adicional posterior, de forma que se conserven inalterables los datos originalmente
  registrados.»
- **Trazabilidad** (F-8, art. 8.2.b): los registros «deberán estar encadenados de manera que pueda
  verificarse su rastro siguiendo su secuencia de creación desde el primero al último».
- **Momento** (F-8, art. 9): el registro de alta se genera «de forma simultánea o inmediatamente
  anterior a la expedición de cada factura».
- **Anulación** (F-8, art. 11.1): «Procederá la generación de un registro de facturación de
  anulación cuando se haya emitido erróneamente una factura».
- **Firma** (F-8, art. 12 y art. 16.3; F-10, art. 14):
  - En no VERI\*FACTU, los registros se firman con XAdES Enveloped y un certificado cualificado.
  - Los sistemas VERI\*FACTU «no tendrán la obligación de realizar la firma electrónica […] siendo
    suficiente con que calculen la huella».
- **Encadenamiento** (F-10, art. 7):
  - a) Cada registro contiene NIF, número y serie, fecha de expedición y los primeros 64
    caracteres de la huella del inmediatamente anterior.
  - b) El primer registro «generado en el sistema informático desde su instalación o puesta en
    marcha inicial» se identifica como tal.
  - c) Hay una única cadena por obligado.
  - d) La cadena incluye altas y anulaciones.
  - f) El margen de error máximo de la hora es de un minuto.
  - i) Antes de generar un registro, se comprueba que el último está bien encadenado y que su
    fecha no es más de un minuto posterior a la actual.
- **Permanencia de modalidad**:
  - F-8, art. 16.5: la opción VERI\*FACTU «se prolongará, al menos, hasta la finalización del año
    natural» del primer envío.
  - F-10, art. 17.2: «deberá mantenerse siempre al menos hasta el final del último año en que haya
    funcionado como tal».
- **Correcciones** (F-4, aclaración 17; F-5; F-9):
  - Antes de expedir, se corrige sin más.
  - Después de expedir:
    - Error del ROF: rectificativa.
    - Dato interno del registro: alta de subsanación.
    - Ni del ROF ni del registro: corrección directa.
    - La factura no debió emitirse: anulación.
  - «Con carácter general, todas las facturas emitidas, en la medida en que respondan a operaciones
    realmente efectuadas […] no pueden anularse» (F-4, p. 35).
- **Numeración** (F-4, aclaración 6):
  - «ya NO es posible reutilizar la numeración de ninguna factura expedida».
  - Un alta normal sobre una factura ya anulada es ERROR(2) (F-1, cuadro A, fila 6). Solo la
    reactiva un alta de subsanación, que no se usa en esta feature.

**Decisión**: el diseño se atiene a esos puntos. Cada uno tiene un requisito en la spec (FR-022,
FR-024 a FR-031) y una solución técnica en R-5 a R-9.

---

## R-2. Huella SHA-256 (F-2)

**Algoritmo y salida**:
- **Algoritmo**: SHA-256, `TipoHuella = "01"` (lista L12).
- **Entrada**: la cadena, codificada en UTF-8 (p. 7).
- **Salida**: «En sistema hexadecimal. En mayúsculas. El tamaño será de 64 caracteres» (p. 9).

**Cadena**:
- **Formato**: `nombreCampo1=valor1&nombreCampo2=valor2&…`. Los nombres son constantes, tal como
  están en el XML, y no hay `&` al final (p. 6 y el ejemplo Java de la p. 8).
- **Espacios**: se eliminan al inicio y al final de cada valor. Los interiores se conservan.
- **Campo ausente o vacío**: se pone solo `nombre=`. Es el caso de la huella anterior en el primer
  registro (pp. 6–7).
- **Sin URL-encoding**: la `/` va tal cual, como confirman los vectores.

**Orden de los campos**:
- **Alta** (p. 5; F-10, art. 13.1.a):
  1. `IDEmisorFactura`
  2. `NumSerieFactura`
  3. `FechaExpedicionFactura`
  4. `TipoFactura`
  5. `CuotaTotal`
  6. `ImporteTotal`
  7. `Huella` (la del registro anterior)
  8. `FechaHoraHusoGenRegistro`
- **Anulación** (p. 5):
  1. `IDEmisorFacturaAnulada`
  2. `NumSerieFacturaAnulada`
  3. `FechaExpedicionFacturaAnulada`
  4. `Huella` (la del registro anterior)
  5. `FechaHoraHusoGenRegistro`

**Formatos de los valores** (los mismos del XML, según F-1):
- **Fechas**: `dd-mm-yyyy`.
- **`FechaHoraHusoGenRegistro`**: `YYYY-MM-DDThh:mm:ssTZD`, en ISO 8601 con desfase. Por ejemplo,
  `2024-01-01T19:20:30+01:00`.

**Vectores oficiales** (pp. 10–12). Se comprobaron recalculándolos y se usan tal cual en
`tests/unit/test_huella.py`:

| Caso | Cadena de entrada | Huella |
|---|---|---|
| Primer alta | `IDEmisorFactura=89890001K&NumSerieFactura=12345678/G33&FechaExpedicionFactura=01-01-2024&TipoFactura=F1&CuotaTotal=12.35&ImporteTotal=123.45&Huella=&FechaHoraHusoGenRegistro=2024-01-01T19:20:30+01:00` | `3C464DAF61ACB827C65FDA19F352A4E3BDC2C640E9E9FC4CC058073F38F12F60` |
| Alta encadenada | `IDEmisorFactura=89890001K&NumSerieFactura=12345679/G34&FechaExpedicionFactura=01-01-2024&TipoFactura=F1&CuotaTotal=12.35&ImporteTotal=123.45&Huella=3C464DAF61ACB827C65FDA19F352A4E3BDC2C640E9E9FC4CC058073F38F12F60&FechaHoraHusoGenRegistro=2024-01-01T19:20:35+01:00` | `F7B94CFD8924EDFF273501B01EE5153E4CE8F259766F88CF6ACB8935802A2B97` |
| Anulación encadenada | `IDEmisorFacturaAnulada=89890001K&NumSerieFacturaAnulada=12345679/G34&FechaExpedicionFacturaAnulada=01-01-2024&Huella=F7B94CFD8924EDFF273501B01EE5153E4CE8F259766F88CF6ACB8935802A2B97&FechaHoraHusoGenRegistro=2024-01-01T19:20:40+01:00` | `177547C0D57AC74748561D054A9CEC14B4C4EA23D1BEFD6F2E69E3A388F90C68` |

**Decisión (representación canónica de importes)**: los importes van **siempre con dos decimales
y punto** (`123.10`, `0.00`), y exactamente igual en la cadena de la huella y en el contenido del
registro.
- **Razón**:
  - F-2 dice que «se tratarán indistintamente los valores con una o dos posiciones en los
    decimales» (p. 6). Aun así, `123.1` y `123.10` dan huellas distintas a nivel de bytes.
  - Fijar una sola forma hace la huella reproducible por nosotros y por la AEAT, sin depender de
    cómo normalice ella.
  - Los vectores oficiales usan dos decimales.
- **Alternativas descartadas**: el formato mínimo sin ceros finales (`123.1`). Es igual de válido
  según F-2, pero se pierde la coincidencia literal con `NUMERIC(12,2)` y con los vectores.

**Decisión (implementación)**: `app/domain/huella.py`, sin E/S:
- `cadena_alta(...) -> str`, `cadena_anulacion(...) -> str` y `calcular(cadena) -> str`.
- Los importes llegan como `Decimal` y se formatean con `f"{valor:.2f}"`, tras cuantizar según
  R-10.
- El test de encadenamiento, obligatorio por la constitución VII, cubre los tres vectores, una
  cadena de N registros mezclando altas y anulaciones y la detección de una alteración.

---

## R-3. Registro de facturación de alta: contenido (F-1, hoja 2)

**Decisión**: cada registro guarda una copia estructurada de su contenido según el diseño oficial.
- **Dónde**: columna `contenido` `JSONB`, con todos los valores como texto y en los formatos de R-2.
- **Para qué**: servirá para generar el XML en la feature 004.
- **Consultas**: los campos de la huella y los que se consultan se guardan además en columnas
  propias.

Correspondencia para una factura F1 de esta feature:

| Campo (fila F-1) | Valor | Origen |
|---|---|---|
| `IDVersion` (2) | `1.0` | L15 |
| `IDFactura/IDEmisorFactura` (3) | NIF del emisor | Copia de Configuración al emitir |
| `IDFactura/NumSerieFactura` (4) | `FAC-2026-0001` | Contador (R-7). Cumple F-3 §3.1.3.1: ASCII 32–126 sin `" ' < > =`, ≤ 60 |
| `IDFactura/FechaExpedicionFactura` (5) | `dd-mm-yyyy` | FR-018 |
| `NombreRazonEmisor` (7) | ≤ 120 | Copia de Configuración |
| `Subsanacion` (8), `RechazoPrevio` (9) | No se informan (equivale a «N») | Alta normal (F-1, cuadro A, fila 6) |
| `TipoFactura` (10) | `F1` | L2: «Factura (art. 6, 7.2 y 7.3 del RD 1619/2012)» |
| `FechaOperacion` (21) | Solo en reemisiones y rectificativas (FR-018) | F-3 §3.1.3.7: la de expedición no puede ser anterior |
| `DescripcionOperacion` (22) | FR-045, ≤ 500 | Obligatorio en F-1. F-3 no tiene reglas para este campo |
| `Destinatarios/IDDestinatario` (32–36) | `NombreRazon` + `NIF` (España) o `IDOtro` (`CodigoPais`, `IDType` L7, `ID`) | Copia del cliente. Obligatorio en F1 (F-3 §13, error 1189) |
| `Desglose/DetalleDesglose` (38–47) | Uno por tipo de IVA, con `Impuesto` `01`, `ClaveRegimen` de Configuración (`01`), `CalificacionOperacion` `S1`, `TipoImpositivo` `21.00`, `BaseImponibleOimporteNoSujeto` y `CuotaRepercutida` | FR-013 a FR-015 |
| `CuotaTotal` (48), `ImporteTotal` (49) | Suma de cuotas; suma de bases y cuotas | R-10 |
| `Encadenamiento` (50–54) | `PrimerRegistro` `S` o `RegistroAnterior` (NIF, número, fecha y huella del anterior) | R-6 |
| `SistemaInformatico` (55) | R-5 | Configuración del despliegue |
| `FechaHoraHusoGenRegistro` (56) | R-6 | Reloj del servidor, en `Europe/Madrid` |
| `TipoHuella` (59), `Huella` (60) | `01` y la huella de R-2 | — |
| `Signature` (61–63) | No se genera en esta feature | Solo en no VERI\*FACTU (F-10, art. 14): feature 004 |

**Campos opcionales que no se informan**:
- `RefExterna`, `FacturaSimplificadaArt7273`, `FacturaSinIdentifDestinatarioArt61d`, `Macrodato`,
  `EmitidaPorTerceroODestinatario`, `Tercero` y `Cupon`.
- `NumRegistroAcuerdoFacturacion` e `IdAcuerdoSistemaInformatico`.
- En el desglose: `OperacionExenta`, `BaseImponibleACoste` y recargo de equivalencia. El régimen es
  general y no hay exenciones.

**Destinatario con NIF español no censado** (001, R-20.1 y R-20.4): el tipo `07` no se genera en
esta feature. Se envía el NIF tal como está en la ficha. Lo que devuelva la AEAT (errores 1193 o
2001) se trata en la feature 004.

**`Impuesto`** (fila 38): el diseño dice «Alfanumérico (1)», pero la lista L1 tiene valores de dos
caracteres (`01`…`05`). Como es opcional y su ausencia equivale a IVA (F-3 §15.1), **no se
informa**. Se evita así la incoherencia, que queda anotada para cotejarla con el XSD en la 004.

---

## R-4. Rectificativa por sustitución y reemisión tras anulación

**Rectificativa** (FR-024, «factura ya entregada»):
- **Tipo** (F-9 y la lista L2 de F-1):
  - `R1` si la causa es «devolución, descuento o cambio de precio posterior, o IVA mal aplicado».
    F-9 lo define como «error fundado de derecho o alguna de las causas del art. 80.Uno, Dos y Seis
    LIVA (devoluciones de mercancías, descuentos o alteraciones en el precio posteriores…)».
  - `R4` si es «error en datos o importes». F-9 dice «modificación de la base imponible […] por
    causas distintas a las previstas en el artículo 80 LIVA y no se deba a un error fundado de
    derecho» y «Cuando se haya consignado erróneamente algún dato no monetario de la factura».
- **Campos del registro** (F-9, «opción 1»; F-3 §3.1.3.3–6):
  - `TipoRectificativa = "S"`, obligatorio con R1–R5.
  - `FacturasRectificadas/IDFacturaRectificada`: NIF, número y fecha de la original. Es opcional
    según F-3 §3.1.3.4, pero se informa siempre, porque el ROF art. 15.4 exige identificar la
    factura rectificada.
  - `ImporteRectificacion`: `BaseRectificada` y `CuotaRectificada`. **Son la base y la cuota
    totales de la factura rectificada** (F-9, ejemplo 1: «la base rectificada (1.000) y la cuota
    rectificada (210)»). Es obligatorio con `S` (F-3 §3.1.3.6).
  - **Desglose, `CuotaTotal` e `ImporteTotal`**: los importes **correctos tras la rectificación**
    (F-9, ejemplo 1: «Desglose IVA: base imponible: 800, cuota repercutida 168»).
  - `FechaOperacion`: la de la factura original (F-9: «La fecha de realización de la operación
    correspondiente a la factura original»). Es su `FechaOperacion` o, si no tenía, su fecha de
    expedición.
- **Serie**: `REC-AAAA-NNNN` (constitución 2.2.0; F-6, art. 6.1.a, 2.º).
- **Destinatarios**: obligatorios (F-3 §13).
- **Devolución total** (Clarifications de plan):
  - Rectificativa R1 sin líneas.
  - Desglose con un único `DetalleDesglose` a base `0.00` y cuota `0.00`, al tipo de
    Configuración. F-1 exige entre 1 y 12 detalles.
  - Totales a 0 e `ImporteRectificacion` con los importes de la original.
  - F-3 §15.7 exige que la base y la cuota tengan el mismo signo, y con cero se cumple.
- **Signo**: los totales de una rectificativa por sustitución son ≥ 0 en esta feature, porque solo
  hay facturas originales positivas y devoluciones hasta cero. F-3 no regula el signo de
  `ImporteRectificacion` (pregunta abierta Q-4). Siempre se consigna el de la original, que es ≥ 0.
- **Rectificar una rectificativa**: el mecanismo es el mismo, y `ImporteRectificacion` lleva los
  importes de la rectificativa vigente (F-9, ejemplos 4–6).

**Reemisión tras anulación** (FR-024, «no debió emitirse o no llegó a entregarse»):
1. Se genera el registro de anulación de la original (R-4b).
2. Se emite una F1 normal con el **siguiente número** de `FAC`. F-9 dice «con un número de factura
   o fecha de expedición diferente», y F-3 (anexo 6.1, ERROR(2)) impide un alta normal con la
   misma clave de una factura ya anulada.
3. La F1 nueva lleva la fecha de expedición de hoy y la `FechaOperacion` de la original (FR-018).

**IVA de las correcciones**:
- **Decisión**: el tipo de Configuración vigente al emitir, igual que en cualquier factura
  (decisión del responsable, FR-013). Si no coincide con el de la original, el modal lo avisa
  (spec, casos límite).
- **Razón**: respeta la decisión «IVA siempre el de Configuración» y cubre el caso R1 «IVA mal
  aplicado», en el que el administrador corrige primero la configuración.
- **Alternativa descartada**: heredar siempre el tipo de la original. Impide corregir un IVA mal
  aplicado y contradice la decisión del responsable.

**R-4b. Registro de anulación** (F-1, hoja 3):
- **Se informa**:
  - `IDVersion 1.0`.
  - `IDFactura`: `IDEmisorFacturaAnulada`, `NumSerieFacturaAnulada` y
    `FechaExpedicionFacturaAnulada`, de la factura anulada.
  - `Encadenamiento`, `SistemaInformatico`, `FechaHoraHusoGenRegistro`, `TipoHuella 01` y
    `Huella`.
- **No se informan**:
  - `SinRegistroPrevio` (equivale a «N»): la factura anulada siempre tiene su alta en este sistema.
  - `RechazoPrevio`.
  - `GeneradoPor`: sin él se entiende que lo genera el expedidor.
- **Causa**: el registro no lleva el motivo. El motivo declarado y su texto se guardan en la
  corrección (FR-026).

---

## R-5. Identificación del sistema informático (`SistemaInformatico`, F-1, hoja 5)

**Decisión**: los valores salen de variables de entorno de `Settings`, con prefijo `SIF_`. Se
copian en cada registro.

| Campo | Valor | Regla |
|---|---|---|
| `NombreRazon` | Productor. **Pendiente**: TODO(DECLARACION_RESPONSABLE) | ≤ 120 |
| `NIF` | NIF del productor | FormatoNIF |
| `NombreSistemaInformatico` | `Joyería Blanco Gestión` (22 caracteres) | ≤ 30 |
| `IdSistemaInformatico` | `JB` | Dos posiciones: mayúscula sin Ñ o dígito (F-3 §3.1.5) |
| `Version` | Versión de la API (`app.__version__`) | ≤ 50 |
| `NumeroInstalacion` | `SIF_NUMERO_INSTALACION`, por defecto `1` | ≤ 100 |
| `TipoUsoPosibleSoloVerifactu` | `N` | El diseño admite las dos modalidades (constitución IV) |
| `TipoUsoPosibleMultiOT` | `N` | Un solo obligado |
| `IndicadorMultiplesOT` | `N` | Lo calcula el sistema: solo hay un emisor |

**Validación por entorno**:
- **Producción**: `Settings` exige `SIF_PRODUCTOR_NOMBRE` y `SIF_PRODUCTOR_NIF` con NIF válido, como
  ya hace con la cookie segura.
- **Desarrollo, test y e2e**: se usan valores ficticios marcados como tales.

**Razón**: el registro es inalterable. Un productor mal consignado quedaría así para siempre, así
que en producción se impide antes de la primera emisión.

**Alternativa descartada**: guardarlo en la configuración de la base de datos. Son datos del
producto y del despliegue, no del negocio, y no deben cambiarse desde la aplicación.

---

## R-6. Encadenamiento, hora de generación y concurrencia de la cadena

**Decisión**:

1. **Cerrojo de la cadena**: toda operación que genera registros (emitir, anular, modificar)
   empieza con `SELECT pg_advisory_xact_lock(<clave fija de la cadena>)`.
   - El cerrojo serializa la cadena, que es única por obligado (F-10, art. 7.c).
   - Se libera al terminar la transacción.
   - **Orden de cerrojos**: siempre primero la cadena y después el contador de la serie (R-7).
     Así no hay interbloqueos.
2. **Cola de la cadena**: el último registro es el de `secuencia` máxima. `secuencia` es un
   `bigint`, único, contiguo y asignado bajo el cerrojo.
3. **Comprobación previa** (F-10, art. 7.i; FR-029):
   - Se recalcula la huella del último registro a partir de sus columnas y se compara con la
     guardada.
   - Se comprueba que su hora de generación ≤ ahora + 1 minuto.
   - Si algo falla, error `cadena-inconsistente` (409), no se genera nada, se deja un evento de
     auditoría y el log lo registra como error.
4. **Hora**: se genera en `Europe/Madrid` con su desfase (`+01:00` o `+02:00`), con precisión de
   segundos, formateada `YYYY-MM-DDThh:mm:ss±hh:mm`. Viene de `app/core/tiempo.ahora()`, que ya
   existe.
   - La hora del servidor debe estar sincronizada por NTP (quickstart, verificación de
     producción).
   - Se registra siempre la hora real de generación, aunque sea ligeramente anterior a la del
     último registro. Sustituirla por otra incumpliría el «correctamente fechados» de F-8, art.
     8.2.b.
   - Si el último registro va más de un minuto por delante, se aplica la comprobación previa del
     punto 3.
5. **Defensa en la BD**: un trigger `BEFORE INSERT` en `registros_facturacion` verifica:
   - `NEW.secuencia = max + 1`.
   - `NEW.huella_anterior = huella del registro max`.
   - `primer_registro` si y solo si la tabla está vacía.

   Así la cadena no se puede bifurcar ni con un `INSERT` manual.

**Razón**:
- El cerrojo transaccional es explícito y no deja estado que haya que limpiar.
- El trigger lleva la linealidad de la cadena a la base de datos, igual que la inalterabilidad
  (constitución III: «no solo en la capa de aplicación»).

**Alternativas descartadas**:
- Una fila de «cola de la cadena» con `FOR UPDATE`: sería una tabla mutable más y un puntero que
  habría que proteger.
- `SERIALIZABLE` con reintentos: complica la emisión y no aporta más garantía.

---

## R-7. Numeración: contadores por serie y año

**Decisión**:
- **Tabla**: `contadores_factura (serie, anio, ultimo_numero)`.
- **Asignación**, dentro del cerrojo de la cadena:
  1. `INSERT … ON CONFLICT DO NOTHING`, para que la fila exista.
  2. `SELECT … FOR UPDATE`.
  3. `UPDATE ultimo_numero = ultimo_numero + 1 RETURNING`.

  La asignación va en la misma transacción que la factura y su registro. Si algo falla, se
  deshace entero y no queda hueco (FR-007).
- **Año**: el de la fecha de expedición, no el del reloj (edge case «Cambio de año»).
- **Formato**: `f"{serie}-{anio}-{numero:04d}"`. A partir de 10.000 crece sin truncar (FR-006).
- **Ajuste al alza** (FR-010; constitución 2.2.0):
  - Con los mismos cerrojos: `UPDATE ultimo_numero = :proximo - 1 WHERE ultimo_numero < :proximo - 1`.
  - Solo en la serie `FAC` del año en curso.
  - Motivo obligatorio y evento `contador_ajustado` con el número anterior, el nuevo, el hueco y el
    motivo.
  - La respuesta de «vista previa» del endpoint informa del hueco antes de confirmar.
- **Defensa en la BD**: un trigger `BEFORE UPDATE` impide que `ultimo_numero` baje, y el
  `REVOKE DELETE` impide borrar filas. Además, `facturas` tiene
  `UNIQUE (serie, anio, numero)`.

**Razón**:
- Es el «bloqueo explícito sobre una tabla de contadores» que exige la constitución, y queda
  prohibido `MAX+1`.
- La secuencia de PostgreSQL se descarta porque deja huecos en los rollback y no se reinicia por
  año.

**Test obligatorio** (constitución VII): se lanzan 200 emisiones con `asyncio.gather` sobre 10
sesiones reales, siguiendo el patrón de
`test_usuarios.py::test_regla_del_ultimo_administrador_bajo_concurrencia`. Se comprueba:
- Números `1..200` sin huecos ni duplicados.
- Una sola cadena con 200 registros y `secuencia` contigua.
- Que una emisión que falla a propósito no consume número.

---

## R-8. Inalterabilidad en la BD y estado derivado

**Decisión**:
- **Tablas protegidas** (solo inserción): `facturas`, `lineas_factura`, `desgloses_factura`,
  `correcciones_factura` y `registros_facturacion`. Se aplica el patrón de la migración 0002:
  - `REVOKE UPDATE, DELETE, TRUNCATE … FROM jb_app`.
  - Trigger por fila `BEFORE UPDATE OR DELETE` y trigger por sentencia `BEFORE TRUNCATE`, que
    ejecutan una función nueva, `impedir_modificacion_facturacion()`. La función lanza SQLSTATE
    `42501` con «Los documentos de facturación emitidos son inalterables».
  - Esos triggers bloquean también a `jb_owner`.
- **Sin columnas de estado mutables**: «anulada» y «rectificada» **se derivan** de
  `correcciones_factura`, que también es de solo inserción. Como una rectificativa se puede anular y
  la original vuelve a estar vigente (FR-048), una factura puede acumular varias correcciones.
  - **Estado de una factura F**:
    - `anulada` si existe una corrección `anulacion*` sobre F. Es definitivo: una anulación nunca se
      revierte.
    - `rectificada` si existe una corrección `rectificacion_sustitucion` sobre F cuya
      `factura_nueva` no está anulada.
    - `vigente` en cualquier otro caso.
  - **Guarda en la BD**: el trigger `BEFORE INSERT` `validar_correccion` en `correcciones_factura`
    recalcula el estado de F y rechaza la inserción (`42501`) si no es `vigente`. Además hay un
    índice único parcial sobre `factura_id` para `anulacion*` y otro `UNIQUE (factura_nueva_id)`.
  - **Concurrencia**: todas las correcciones van bajo el cerrojo de la cadena (R-6), así que dos
    administradores sobre la misma factura se serializan. El segundo recibe `409
    factura-no-modificable`.
  - **Sin bloqueo de filas en tablas protegidas**: PostgreSQL exige privilegio `UPDATE` para
    `SELECT … FOR UPDATE/SHARE`, y `jb_app` no lo tiene en esas tablas. La serialización la aporta
    el cerrojo consultivo.
- **Referencias**:
  - FK a `clientes ON DELETE RESTRICT`, que es la segunda barrera de FR-042.
  - FK a `usuarios`: nunca se borran, se entierran (001, R-21).
- **Límite conocido, heredado de 001 (R-10)**:
  - `jb_owner`, como dueño de las tablas, podría ejecutar `ALTER TABLE … DISABLE TRIGGER`. Ese rol
    solo lo usan las migraciones y no está en la API.
  - La comprobación de integridad (FR-031) detecta cualquier alteración hecha así. Es el «detecte y
    avise» de F-8, art. 8.2.a.
  - El test de SC-004 reproduce exactamente ese escenario dentro de una transacción de test que
    después se deshace.

**Alternativa descartada**: una columna `estado` en `facturas` que se actualiza al anular.
Exigiría `UPDATE` sobre un documento emitido.

---

## R-9. Borradores y flujo de emisión

**Decisión**:
- **Tablas mutables**: `borradores_factura` y `lineas_borrador`, con `version` para la concurrencia
  optimista, como `clientes` en 001 (FR-020).
- **Contenido del borrador**: no guarda el tipo de IVA. Se aplica al emitir (FR-013).
- **Emitir un borrador** (`POST /v1/borradores-factura/{id}/emision`): recibe el contenido actual
  del modal más la `version`. En una sola transacción:
  1. Cerrojo de la cadena (R-6).
  2. Bloqueo del borrador con `FOR UPDATE` y comprobación de la versión.
  3. Validaciones de emisión: emisor, modalidad, cliente activo con domicilio, líneas y fecha
     (FR-004, FR-011, FR-017 y FR-018).
  4. Cálculo (R-10).
  5. Asignación del número (R-7).
  6. `INSERT` de la factura, sus líneas, su desglose y su registro de alta.
  7. `DELETE` del borrador.
  8. Auditoría.
- **Emitir sin borrador previo** (`POST /v1/facturas`): el mismo flujo, sin los pasos 2 y 7.
- **Corrección de una emitida** (`POST /v1/facturas/{id}/modificacion` y `/anulacion`): el mismo
  cerrojo de la cadena.
  1. Se comprueba que la factura está `vigente` (R-8) y se inserta la corrección, que el trigger
     `validar_correccion` vuelve a comprobar.
  2. Se generan los registros en este orden:
     - En una reemisión, la anulación y después el alta nueva.
     - En una rectificación, el alta de la rectificativa.
     - En una anulación de una rectificativa, solo su anulación. La original vuelve a estar
       vigente por derivación, sin registro nuevo (FR-048).
- **Modificación sin cambios** (spec, casos límite):
  - Se compara el cliente y las líneas normalizadas con la factura vigente.
  - Con `factura_entregada`, una modificación idéntica se rechaza con `422 sin-cambios`.
  - Con `no_debio_emitirse` se admite: es la reemisión con número nuevo.

**Razón**: el registro se genera «de forma simultánea» a la expedición (F-8, art. 9). Número,
factura y registro se crean en la misma transacción.

---

## R-10. Importes, redondeo y tipos de IVA

**Decisión (política única, FR-015)**:
- `importe_linea = redondear(unidades × precio_unitario)`.
- `base_tipo = Σ importe_linea`, para las líneas de ese tipo.
- `cuota_tipo = redondear(base_tipo × tipo / 100)`.
- `cuota_total = Σ cuota_tipo`.
- `importe_total = Σ (base_tipo + cuota_tipo)`.
- `redondear(x) = x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)`. En `decimal` de Python,
  `ROUND_HALF_UP` redondea el medio alejándose de cero.
- Todo con `Decimal` y un contexto con precisión suficiente (28 dígitos, el valor por defecto).
- Vive en `app/domain/importes.py`.

**Contraste con F-3 §15.7** (tolerancias):
- La cuota es exacta al céntimo. Queda dentro de «+/- 10,00 euros» de `(Base * TipoImpositivo) /
  100`.
- `CuotaTotal` e `ImporteTotal` son sumas exactas de los desgloses (F-3, puntos 16 y 17).

**Límites**:
- `Decimal (12,2)` en F-1: importes hasta `9.999.999.999,99`.
- Entrada:
  - Unidades `0 < u ≤ 99.999,99`.
  - Precio `0 ≤ p ≤ 99.999.999,99`.
  - Como máximo 100 líneas.
- Si algún total supera el límite, error de validación.

**Tipos de IVA admitidos** (F-3 §15.1, con `CalificacionOperacion S1`):
- «Solo se permiten TipoImpositivo = 0; 2; 4; 5; 7,5; 10 y 21», con estas ventanas:
  - El 5 solo del 01/07/2022 al 30/09/2024.
  - El 2 y el 7,5 solo del 01/10/2024 al 31/12/2024.
- La constante `TIPOS_IVA_S1` de `app/domain/importes.py` recoge esas ventanas.
  - Configuración solo admite los tipos válidos para la fecha actual: hoy son 0, 4, 10 y 21.
  - Al emitir se revalida el tipo frente a la fecha de expedición.

**JSON sin `float`** (constitución II):
- **Salida**: los importes van como cadena (`"1290.00"`). Es el comportamiento por defecto de
  Pydantic v2 para `Decimal` en modo JSON, y lo refuerza el tipo `ImporteSalida`.
- **Entrada**: los tipos `Importe` y `Cantidad` son `Annotated[Decimal, BeforeValidator(...)]`:
  - Solo aceptan `str` con el patrón `^\d{1,10}(\.\d{1,2})?$`.
  - Rechazan cualquier número JSON con 422 y un mensaje en el campo. Así el valor nunca pasa por
    un `float`.
  - En OpenAPI aparecen como `type: string` con `pattern`, mediante `WithJsonSchema`.
- **Auditoría**: `services/auditoria.to_json` serializa `Decimal` con `format(valor, "f")` (FR-043).

**Test obligatorio** (constitución VII): `tests/unit/test_importes.py` es una tabla de casos
calculados a mano (SC-003):
- Medio céntimo positivo, por ejemplo 1 × 0,125 y base 0,05 al 21 %, que da 0,0105.
- Cantidades con decimales.
- El importe máximo.
- La suma de líneas redondeadas frente a la base.
- El ejemplo de la captura, 1.290,00 + 270,90 = 1.560,90.

---

## R-11. Previsualización en la web sin `float`

**Decisión**: `src/lib/dinero.ts` trabaja con enteros escalados sobre `BigInt`, en céntimos y
centésimas de unidad:
- `parsear("1.200,5")` → `120050n`.
- Multiplicación con redondeo del medio alejándose de cero, idéntica a R-10.
- `formatear(120050n)` → `"1.200,50 €"` con `Intl.NumberFormat('es-ES')` aplicado sobre la
  representación en texto, no sobre un `number`.
- Valor para la API: `"1200.50"`.

**Otras reglas**:
- El modal nunca envía totales (FR-014).
- Tras guardar, se muestran los totales que devuelve la API.
- Una prueba unitaria compara la previsualización con los casos de `test_importes.py`.

**Razón**: la constitución prohíbe `float` «en cualquier punto de la cadena». `number` de JS es
binario de doble precisión.

**Alternativa descartada**: `decimal.js` o `big.js`. Con cuatro operaciones y `BigInt` nativo no
compensa añadir una dependencia.

---

## R-12. Listado de facturas

**Decisión**:
- **Vista `v_listado_facturas`**: es de solo lectura y hace `UNION ALL` de:
  - Borradores, con el cliente actual, número nulo y fecha propuesta.
  - Facturas emitidas, con la copia del destinatario y su estado derivado (`vigente`, `anulada` o
    `rectificada`) mediante un `LEFT JOIN` con `correcciones_factura`.
- **Búsqueda** (FR-034): sobre `texto_busqueda`, con el mismo `ILIKE` sin tildes que en clientes
  (`_escapar_like` e `inmutable_unaccent`).
  - `texto_busqueda` es una columna generada en `facturas` con el número, el nombre y la
    identificación del destinatario, e índice GIN trigram.
  - En borradores se busca por el cliente enlazado.
  - Una identificación con separadores se normaliza igual que en clientes.
- **Filtros**:
  - `anio`: por defecto el actual; `todos` quita el filtro.
  - `mes`: de 1 a 12.
  - Sobre `fecha_expedicion`, que en un borrador es la fecha propuesta.
- **Órdenes** (FR-035), todos con desempate estable por `id`:
  - `recientes`: fecha desc, número desc, id desc. Un borrador va antes que las emitidas de su
    misma fecha.
  - `antiguas`.
  - `total_desc` y `total_asc`. El total de un borrador es el calculado al vuelo, igual que en el
    modal.
- **Índices**:
  - `facturas (fecha_expedicion DESC, serie, numero DESC)`.
  - GIN trigram sobre `texto_busqueda`.
  - `borradores_factura (fecha_expedicion DESC)`.
- **Respuesta**: `Pagina[FacturaResumenSalida]`, con `tipo_documento` (`borrador` o `factura`), `id`,
  `numero`, `fecha`, `cliente`, `identificacion`, `base`, `cuota`, `total` y `estado`.
- **Rendimiento**: SC-007 se mide con `scripts/medir_busqueda_facturas.py`, sobre 20.000 facturas
  en la BD e2e, como en 001 (SC-003).

**Alternativa descartada**: dos listados separados. El responsable pidió un único listado con
borradores marcados.

---

## R-13. Modal de factura y alta de cliente por encima

**Decisión**:
- **`components/ui/ModalDocumento.tsx`**:
  - Modal centrado ancho: `max-w-5xl` en escritorio y pantalla completa por debajo de 768 px.
  - Cabecera con título en Bodoni `headline-md`, cuerpo desplazable y pie fijo con las acciones.
  - Se construye como `Drawer.tsx`, sobre `ModalOverlay`, `Modal` y `Dialog` de react-aria. Así
    tiene foco atrapado y devuelto, Escape y bloqueo del scroll.
  - Nivel 2: `surface-container-high`, borde `tertiary` al 35 % y `shadow-nivel-2`.
  - Se reutilizará en presupuestos.
- **Rutas anidadas bajo `/facturas`**, igual que clientes: `nueva`, `borradores/$borradorId`,
  `$facturaId` y `$facturaId/modificar`. Así el listado sigue detrás y el estado de la URL se
  conserva.
- **«Nuevo cliente» desde el modal** (FR-046):
  - Se extrae de `ClientePanel.tsx` un `ClienteAltaPanel`, controlado por props (`isOpen`,
    `onCreado(cliente)` y `onCerrar`), que usa el mismo `ClienteForm`.
  - Se abre como un segundo overlay sobre el modal. react-aria admite modales anidados y gestiona
    el foco en pila.
  - Al guardar, el cliente queda elegido en el formulario de la factura sin perder lo escrito.
- **Diálogos secundarios** con el `Dialog` existente:
  - Confirmar la emisión (FR-021).
  - Motivo de la modificación y causa R1/R4 (FR-024).
  - Anular (FR-025).
  - Ajustar el contador (FR-010).
  - Descartar cambios (FR-036).
- **Campos nuevos**:
  - `CampoDecimal`, con el símbolo € opcional de ancho fijo en `primary-container` y cifras
    tabulares (DESIGN.md, «Monetary Inputs»).
  - `CampoFecha`, extraído de `AuditoriaPage.tsx`.
  - Las líneas son una tabla editable en escritorio y tarjetas apiladas en móvil (FR-040).

**Alternativa descartada**: abrir la factura en un `Drawer`. El responsable pidió expresamente un
modal por encima, como en la captura.

---

## R-14. API: recursos y permisos

**Decisión**:

| Recurso | Operaciones | Permiso |
|---|---|---|
| `/v1/configuracion/facturacion` | `GET` y `PUT` (con `version`) | Administrador |
| `/v1/configuracion/facturacion/contador` | `POST` (ajuste al alza). Con `simular: true`, solo calcula el hueco | Administrador |
| `/v1/facturas/parametros` | `GET`: IVA vigente, si se puede emitir, qué falta y el próximo número previsto | Sesión |
| `/v1/facturas` | `GET` (listado, R-12) y `POST` (emitir sin borrador) | Sesión |
| `/v1/facturas/{id}` | `GET`: detalle con líneas, desglose, estado, enlaces e historial | Sesión |
| `/v1/facturas/{id}/anulacion` | `POST` | Administrador |
| `/v1/facturas/{id}/modificacion` | `POST` | Administrador |
| `/v1/borradores-factura` | `POST` | Sesión |
| `/v1/borradores-factura/{id}` | `GET`, `PUT` (con `version`) y `DELETE` | Sesión |
| `/v1/borradores-factura/{id}/emision` | `POST` | Sesión |

**Problemas nuevos** (RFC 9457, catálogo de 001). Además, `sin-cambios` (422) y
`modalidad-bloqueada` (409), de R-9 y R-19, y la cabecera `Idempotency-Key` (R-18):
- `emision-no-disponible` (409): falta el emisor o la modalidad, o falta el productor en producción.
  Lleva la lista `faltan`.
- `cliente-no-facturable` (422): cliente inactivo o sin domicilio. Lleva `faltan`.
- `fecha-expedicion` (422).
- `tipo-iva-no-admitido` (422).
- `factura-no-modificable` (409): factura anulada o rectificada.
- `contador-no-ajustable` (409): el valor no supera el último usado.
- `cadena-inconsistente` (409, R-6).
- Se reutilizan `conflicto-version`, `sin-permiso` y `cliente-con-documentos`.

**CLI**: `joyeria verificar-cadena` (FR-031). Informa «íntegra (N registros)» o el primer registro
que no cuadra, termina con código 1 si hay discrepancia y deja el evento `cadena_verificada`.

**Contrato**:
- `contracts/openapi.yaml` de 002 solo contiene las rutas y los esquemas nuevos.
- `test_contrato_openapi.py` pasa a comparar la API con la **unión** de
  `specs/*/contracts/openapi.yaml`, de modo que cada feature es dueña de su contrato.

---

## R-15. Auditoría

**Decisión**: se añaden a `TipoEvento`, y al `CHECK` con la misma técnica que la migración 0004,
estos tipos:
- `borrador_factura_creado`, `borrador_factura_editado` y `borrador_factura_eliminado`.
- `factura_emitida`, `factura_anulada` y `factura_rectificada`.
- `configuracion_facturacion_cambiada`.
- `contador_ajustado`.
- `cadena_verificada` y `cadena_inconsistente`.

El `detalle` guarda los números de factura y los importes como texto. Hoy no se añade una columna
`factura_id`: basta con el `detalle`, y la consulta de auditoría ya filtra por tipo.

---

## R-16. Datos de ejemplo y E2E

**Decisión**:
- `cargar-datos-ejemplo` pasa a crear, a través de los **servicios**, para que los registros queden
  bien encadenados:
  - La configuración de facturación ficticia: emisor «Joyería Blanco (demo)», NIF ficticio válido y
    modalidad VERI\*FACTU.
  - Unas 60 facturas de los últimos 6 meses, con algunas correcciones.
  - 5 borradores.
- `reiniciar-bd-e2e` también las deja en su estado inicial.
- **Carga de volumen**: un script aparte genera 20.000 facturas en la BD e2e para SC-007. Sigue
  prohibido en producción (001, FR-045).

---

## R-18. Idempotencia de las operaciones fiscales (FR-047, SC-011)

**Decisión**:
- **Clave**: `POST /v1/facturas`, `POST /v1/borradores-factura/{id}/emision`, `POST
  /v1/facturas/{id}/modificacion` y `POST /v1/facturas/{id}/anulacion` exigen la cabecera
  `Idempotency-Key` (UUID). La web la genera una vez por modal y la reutiliza en los reintentos.
- **Almacenamiento**: `facturas.clave_idempotencia` y `correcciones_factura.clave_idempotencia`
  (`uuid UNIQUE NULL`).
- **Consulta**: bajo el cerrojo de la cadena, antes de emitir o corregir, se busca la clave:
  - Si ya existe, se devuelve **200** con el mismo recurso que devolvió la primera, sin generar
    nada.
  - Si no existe, se ejecuta la operación y responde 201 o 200, según el contrato.
- **Emitir un borrador ya emitido por otra petición**: con la misma clave se devuelve la factura.
  Con otra clave, `404` (el borrador ya no existe), y la web informa de «Este borrador ya se ha
  emitido».

**Razón**: un doble clic o un reintento tras un corte de red no debe expedir dos facturas. Deshacer
una emisión duplicada exigiría una anulación ante Hacienda.

**Alternativa descartada**: basarse solo en desactivar el botón en la web. No cubre los reintentos
de red ni dos pestañas.

---

## R-19. Modalidad bloqueada con registros (FR-050)

**Decisión**:
- El `PUT` de configuración rechaza cambiar `modalidad` si existe algún registro (`409
  modalidad-bloqueada`).
- `ConfiguracionFacturacionSalida.modalidad_bloqueada` informa a la web.

**Razón**:
- F-10, art. 17, y F-8, art. 16.5, fijan la permanencia en VERI\*FACTU hasta el 31 de diciembre y
  una renuncia que se comunica en la remisión.
- Sin remisión (feature 004) no se puede aplicar correctamente, así que se bloquea hasta que la 004
  implemente las transiciones legales.
- Los datos de desarrollo se reinician, así que no afecta a las pruebas.

---

## R-17. Preguntas abiertas

Ninguna bloquea esta feature. Todas quedan anotadas para la 004 o para la asesoría.

| Id | Pregunta | Fuente | Tratamiento en 002 |
|---|---|---|---|
| Q-1 | Margen de `FechaHoraHusoGenRegistro` frente a la hora de la AEAT, sin cuantificar (código 2004 truncado) | F-3, punto 20 | Solo es un aviso. Se usa el minuto de F-10, art. 7.f, para la comprobación propia |
| Q-2 | Límite de 20 años en `FechaExpedicionFactura`: solo figura en `errores.properties` (1133) | F-3 | Queda cubierto por FR-018, porque la fecha no es anterior a la última de la serie |
| Q-3 | Qué código de error corresponde a cada casilla de la matriz alta/anulación | F-3, anexo 6 | Se resuelve en la 004 |
| Q-4 | Signo de `ImporteRectificacion` | F-3 no lo regula | Se consigna el de la original (≥ 0), como en F-9 |
| Q-5 | `Impuesto` tiene longitud (1) en F-1, pero sus valores tienen 2 caracteres | F-1, fila 38 | No se informa (R-3) |
| Q-6 | Modalidad VERI\*FACTU o no VERI\*FACTU | Constitución, TODO | Configuración sin valor inicial. Se decide antes de la 004 |
| Q-7 | Productor del sistema y declaración responsable | F-8, art. 13; constitución, TODO | Variables `SIF_*`, exigidas en producción (R-5) |
| Q-8 | NIF español no censado (L7 `07`) y errores 1193/2001 | 001, R-20.4 | Se envía el NIF de la ficha. Se trata en la 004 |
| Q-9 | Fecha de expedición anterior al día de emisión, cuando el registro se genera ese día, frente a la exigencia de F-8, art. 9, de generarlo «simultánea o inmediatamente anterior» | F-8, art. 9; F-3 solo prohíbe fechas futuras | El responsable mantiene la fecha editable hacia atrás (Clarifications 2026-09-29). La asesoría debe validarlo antes de producción |
