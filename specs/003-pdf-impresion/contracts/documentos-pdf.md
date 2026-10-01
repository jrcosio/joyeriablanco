# Contrato de los documentos impresos — factura, listado y página de error

Describe la disposición y el contenido de los PDF que genera la API ([openapi.yaml](openapi.yaml)).
Los tokens `paper*` y `print-*` son los de la sección «Paper» de
[`docs/DESIGN.md`](../../../docs/DESIGN.md) (research R-5). Las plantillas no llevan literales de
color ni de tamaño: solo tokens.

## Comunes

- **Papel**: fondo `paper`, texto `paper-ink` y secundarios en `paper-ink-muted`. Sin sombras ni
  fondos de color, salvo la caja de totales. Esquinas a 0.
- **Filetes**: de 1 px (`0.75pt`) en `paper-rule`.
- **Tipografías**:
  - Bodoni Moda solo en el título (`print-title`) y en el total (`print-total`).
  - Manrope en todo lo demás. Cifras tabulares (`font-variant-numeric: tabular-nums`) en importes,
    unidades, fechas y números.
- **Márgenes**: `print-margin` (15 mm), y 20 mm abajo para el pie de página.
- **Metadatos**: `<html lang="es">`, `<title>` con el nombre del documento y el autor del emisor.
  El texto es seleccionable: nada se imprime como imagen salvo el logotipo.
- **Logotipo**: `resources/marca/logo.png`, de 18 mm de alto.

## Factura (A4 vertical)

Orden de los bloques, de arriba abajo:

1. **Cabecera**, en dos columnas (F-12, anexo, ejemplo j):
   - **Izquierda: QR tributario** (R-2).
     - «QR tributario:» en `print-body-strong`, centrado sobre el QR.
     - El QR, de 35 × 35 mm con 6 mm de margen en blanco por cada lado, en `paper-qr`.
     - En VERI\*FACTU, debajo y centrada, la frase «Factura verificable en la sede electrónica de la
       AEAT» en `print-body-strong`, en dos líneas si no cabe. Ancho del bloque: 47 mm.
   - **Derecha: emisor**.
     - Logotipo.
     - Nombre o razón social en `print-body-strong`.
     - «NIF {nif}».
     - Dirección, y en otra línea código postal, localidad y provincia.
     - Contacto en `print-small`, cada dato en su línea y solo los que haya: teléfono, correo y web.
2. **Identificación del documento**, con un filete superior:
   - Título «Factura» o «Factura rectificativa» en `print-title`.
   - A su derecha, en una rejilla de etiquetas `print-label` y valores `print-body`: «Número»,
     «Fecha de expedición» y, si procede, «Fecha de la operación».
   - **Marcas** bajo el título, en una línea: «ANULADA», «Sustituida por X», «RECTIFICADA por X» y
     «DUPLICADO».
     - En `print-label` y color `paper-alert`, con un recuadro de 1 px `paper-alert` y radio 0.
     - Nunca se superponen a otros datos: no son marcas de agua.
3. **Rectificación** (solo en las rectificativas), un bloque con filete izquierdo de 1 px
   `paper-rule`:
   - «Rectifica a {número} de {fecha}».
   - «Causa: {texto de la causa}».
   - «Rectificación por sustitución».
4. **Destinatario**: la etiqueta «Cliente» (`print-heading`) y debajo:
   - nombre o razón social;
   - identificación con su etiqueta, p. ej. «NIF 52364897H» o «Pasaporte X1234567 (Francia)»;
   - dirección, y código postal, localidad, provincia y país si no es España.
5. **Detalle**: una tabla a todo el ancho.
   - Columnas: «Unidades» (12 %, a la derecha), «Descripción» (56 %), «Precio unitario» (16 %, a
     la derecha) e «Importe» (16 %, a la derecha).
   - Cabecera en `print-label`, con un filete inferior en `paper-rule`. Filas en `print-table`,
     separadas por filetes horizontales, sin verticales.
   - La cabecera se repite en cada página, y una fila no se parte entre páginas.
   - La descripción admite varias líneas.
   - En una rectificativa de devolución total, que no tiene líneas, la tabla se sustituye por
     «Devolución total de la factura {número rectificado}» en `print-body` (FR-008).
6. **Totales**: una caja alineada a la derecha, de 80 mm de ancho, con marco de 1 px `paper-rule`
   («Totals Section»). No se parte entre páginas.
   - Una línea por desglose: «Base imponible al 21 %» con su importe e «IVA 21 %» con su cuota. En
     las exentas, «Base exenta» e «IVA 0,00 €».
   - Base imponible total e IVA total.
   - Filete y «Total» en `print-label`, con el importe en `print-total` y color `paper-accent`.
   - En una rectificativa, debajo de la caja: «Importe de la rectificación: base {base
     rectificada} · IVA {cuota rectificada}» en `print-small`.
   - Mención de la exención, si la hay, en `print-body`, debajo de la caja y a todo el ancho.
7. **Pago** (solo si se pidió y hay IBAN): «Pago por transferencia», con la etiqueta «IBAN» y el
   número agrupado de cuatro en cuatro en `print-body-strong`, con cifras tabulares.
8. **Pie de factura** (si hay): el texto en `print-small` `paper-ink-muted`, respetando los saltos
   de línea y con un filete superior. Va después de todo el contenido, no en el margen.
9. **Pie de página**, en cada página: «{número} · Página n de m» en `print-small`, en el margen
   inferior derecho.

## Listado (A4 apaisado)

1. **Cabecera** (solo en la primera página):
   - El logotipo y el nombre del emisor actual a la izquierda, y «Listado de facturas» en
     `print-title`.
   - Debajo, una línea en `print-body` con el filtro: «Búsqueda: “maria lopez” · Año: 2026 · Mes:
     marzo · Orden: Más recientes».
   - Otra línea en `print-small` `paper-ink-muted`: «{n} facturas · Generado el 01/10/2026 a las
     18:42».
2. **Tabla**: columnas «Número» (13 %), «Fecha» (9 %), «Cliente» (36 %), «Identificación» (12 %),
   «Base imponible» (10 %, a la derecha), «IVA» (9 %, a la derecha) y «Total» (11 %, a la
   derecha).
   - Se usan `table-layout: fixed` y `print-table`.
   - Sin filas, cuando se pide por otra vía que no es el botón: «No hay facturas con este filtro» en
     `print-body` en lugar de la tabla, y totales a 0,00 € (FR-018).
   - El cliente se parte en varias líneas si es largo, sin recortes.
   - Las marcas «Borrador», «Anulada» y «Rectificada» van en `print-label`, recuadradas con 1 px
     `paper-ink-muted`. El borrador muestra la suya en lugar del número.
   - «Exenta» en la columna del IVA.
   - La cabecera se repite en cada página, y una fila no se parte.
3. **Totales** (al final, sin partirse):
   - Etiqueta «Totales de las facturas vigentes» en `print-heading`.
   - Una tabla de dos columnas de importes, base y cuota, con una fila por tipo («IVA 21 %», «IVA
     10 %»… y «Exenta» al final).
   - Fila de total general: número de facturas, base, IVA y total. El total, en `print-total`.
   - Si hay filas fuera de la suma, debajo y en `print-small`: «No se suman: 2 borradores, 1
     anulada y 1 rectificada».
4. **Pie de página**, en cada página: «Listado de facturas · Página n de m», superpuesto al final
   de la generación por bloques (R-7).

## Página de error (HTML, solo en navegaciones; R-8)

- Documento HTML mínimo con los mismos tokens de papel, en un único `<style>` en línea autorizado
  por su *hash* en la CSP de la respuesta, sin scripts ni recursos externos.
- Contenido:
  - El logotipo **no** se incluye, para no depender de rutas de recursos.
  - Un título con la pila `'Bodoni Moda', serif`: «No se ha podido abrir el PDF». No se cargan
    fuentes: si Bodoni Moda no está instalada en el equipo, se usa la serif del sistema.
  - El mensaje del caso (R-8), con la pila `Manrope, sans-serif`.
  - Un enlace «Volver a la aplicación» a `/facturas`, o a `/` si la sesión ha caducado.
- No muestra el `type` del problema, trazas, identificadores internos ni el `request id`.
