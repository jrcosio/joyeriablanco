# Contrato de los documentos impresos — presupuesto y listado de presupuestos

Amplía el [documentos-pdf.md de 003](../../003-pdf-impresion/contracts/documentos-pdf.md), cuyos
apartados «Comunes» y «Página de error» siguen vigentes. Se usan los tokens de la sección «Paper»
de [`docs/DESIGN.md`](../../../docs/DESIGN.md), con su versión 1.3.

## Presupuesto (A4 vertical)

Tiene la disposición de la factura de 003, con estas diferencias:

1. **Cabecera**: solo el emisor (logotipo, nombre, NIF, domicilio y contacto), alineado a la
   derecha. **No hay QR tributario, «QR tributario:» ni la frase VERI\*FACTU**, ni ningún otro
   código (FR-029; F-13).
2. **Identificación del documento**, con un filete superior:
   - Título **«PRESUPUESTO»** en `print-title`.
   - Justo debajo, el **aviso no fiscal**: «Documento sin validez fiscal. No es una factura.» en
     `print-body-strong` y `paper-ink`, dentro de un recuadro de 1 px `paper-rule` con radio 0
     (DESIGN.md 1.3, «Non-fiscal notice»). Va siempre, en la primera página, y nunca como marca de
     agua.
   - **Datos**, en la rejilla de etiquetas: «Número», «Fecha» y «Válido hasta».
   - **Marcas**, en `paper-alert` como en la factura, bajo el aviso:
     - «ANULADO».
     - «SUSTITUIDO por {PRE vigente}».
     - «CONVERTIDO en {FAC}».

     Un pendiente, un caducado o uno en facturación no llevan marca.
3. **Cliente**: el de la factura. El domicilio puede faltar, y entonces no se deja ninguna línea
   vacía.
4. **Detalle**: la tabla de líneas de la factura. No existe la devolución total.
5. **Totales**: la caja de la factura, con la mención de la exención si es de oro de inversión.
6. **Pago**: «Pago por transferencia» con el IBAN, solo si se pidió y lo tiene.
7. **Pie**: `pie_presupuesto` si lo hay, o si no `pie_factura`. En `print-small` y
   `paper-ink-muted`.
8. **Pie de página**: «{número} · Página n de m».

**Metadatos**: `<title>` «Presupuesto PRE-…», el autor del emisor y el fichero `PRE-AAAA-NNNN.pdf`.

## Listado de presupuestos (A4 apaisado)

Es el listado de 003, con estos textos:
- **Título**: «Listado de presupuestos».
- **Sin resultados**: «No hay presupuestos con este filtro».
- **Columnas**: número (o «Borrador»), fecha, cliente, identificación fiscal, base imponible, IVA
  y total. Junto al número van las marcas de la pantalla: «En facturación», «Caducado»,
  «Convertido», «Sustituido» y «Anulado».
- **Totales**: «Totales de los presupuestos pendientes, caducados, en facturación y convertidos»,
  con el desglose por tipo de IVA y el total general.
- **Filas fuera de la suma**: «No se suman: {n} borradores, {n} sustituidos y {n} anulados».
- **Fichero**: `presupuestos-{anio}[-{mes}].pdf` o `presupuestos-todos.pdf`.

## Página de error

La de 003. En las rutas `/api/v1/presupuestos/…`:
- El 404 dice «El presupuesto no existe.».
- El enlace vuelve a `/presupuestos`.
