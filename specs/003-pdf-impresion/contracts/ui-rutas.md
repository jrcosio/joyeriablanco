# Contrato de la interfaz — cambios de la feature 003

Este documento amplía el [ui-rutas.md de 002](../../002-facturas/contracts/ui-rutas.md). No hay
rutas nuevas en la SPA: los PDF se abren en una pestaña nueva directamente desde la API
([openapi.yaml](openapi.yaml), research R-8). Siguen vigentes los comportamientos comunes de 001 y
002.

| Ruta | Acceso | Cambio | Endpoints nuevos |
|---|---|---|---|
| `/facturas` | Sesión | «Imprimir listado» en la cabecera, junto a «Nueva factura» (FR-018) | `GET /v1/facturas/listado/pdf` |
| `/facturas/$facturaId` | Sesión | En el pie del modal de consulta: «Imprimir» y las casillas «Incluir número de cuenta» y «Duplicado» (FR-001, FR-010, FR-033) | `GET /v1/facturas/{id}/pdf` |
| `/configuracion/facturacion` | Administrador | En «Datos del emisor»: teléfono, correo, web y pie de factura (FR-024) | Los de 002, con los esquemas ampliados |

## Comportamientos

- **URL de los PDF**: `src/lib/impresion.ts` las construye con `URLSearchParams` sobre la ruta
  `/api/v1/...` del mismo origen. Funciones:
  - `urlPdfFactura(id, { iban, duplicado })`: incluye `iban=true` y `duplicado=true` solo si están
    marcadas.
  - `urlPdfListado(filtros)`: incluye `q`, `anio`, `mes` y `orden` tal como están en la URL de la
    pantalla, y nunca `pagina`. Omite los vacíos y los valores por defecto, para que el servidor
    aplique los suyos, que son los mismos que en pantalla.
- **«Imprimir» en la consulta**:
  - Es un enlace `<a href={url} target="_blank" rel="noopener">` con aspecto de botón secundario
    (`claseBotonSecundario`) y el icono `Printer` de lucide.
  - Su nombre accesible es «Imprimir factura {número}».
  - Aparece en toda factura emitida, sea vigente, anulada o rectificada, y para cualquier rol.
  - En el pie va después de «Cerrar» y antes de «Anular» y «Modificar».
- **Casillas** (`Casilla` de 001), a la izquierda de «Imprimir», en el mismo grupo:
  - «Incluir número de cuenta»: solo si `factura.emisor.iban` no es `null`.
  - «Duplicado»: solo si `factura.estado` no es `anulada`.
  - Las dos empiezan desmarcadas cada vez que se abre la consulta. No se recuerdan. Cambian el
    `href` del enlace al momento.
- **«Imprimir listado»**: enlace del mismo tipo en la cabecera de la página, con el nombre
  accesible «Imprimir listado». Se convierte en un botón deshabilitado en tres casos:
  - Mientras el listado carga.
  - Con `total === 0`, con el motivo «No hay facturas que imprimir con este filtro».
  - Con `total > 5000`, con el motivo «El listado impreso admite hasta 5.000 facturas: acota el
    filtro, por ejemplo por año».

  El motivo se muestra como texto `body-sm` bajo el botón y se enlaza con `aria-describedby`
  (FR-031).
- **Doble clic** (R-8): tras un clic, el enlace ignora los siguientes durante 2 s
  (`preventDefault`) y muestra «Preparando…» con `aria-live="polite"`. Pasado ese tiempo, vuelve a
  su estado.
- **Errores**: los muestra la pestaña nueva con la página HTML de la API (R-8). La SPA no
  intercepta nada.
- **Móvil** (menos de 768 px):
  - En la consulta, las casillas y «Imprimir» se apilan a ancho completo, como el resto de botones
    del pie (002).
  - «Imprimir listado» se coloca bajo «Nueva factura», también a ancho completo.
  - Sin desplazamiento horizontal.
- **Configuración → Facturación** (FR-024):
  - Cuatro campos opcionales al final del bloque «Datos del emisor»:
    - «Teléfono», `TextField` con `type="tel"`.
    - «Correo electrónico», `TextField` con `type="email"`.
    - «Web».
    - «Pie de factura», un área de texto de 4 filas con el contador «n / 600».
  - Ninguno lleva la marca de necesario para emitir.
  - La ayuda bajo el bloque dice: «El teléfono, el correo, la web y el pie se imprimen en todas las
    facturas, también en las ya emitidas. No forman parte de los datos fiscales».
  - Los errores de la API se muestran en su campo: `contacto.telefono`, `contacto.correo`,
    `contacto.web` y `pie_factura`.
  - Se envían siempre en el `PUT`, también vacíos (`null`), para poder borrarlos.

## Aplicación de DESIGN.md por elemento

Los elementos de la web usan los tokens existentes de [`docs/DESIGN.md`](../../../docs/DESIGN.md).
Los documentos impresos usan la sección «Paper» ([documentos-pdf.md](documentos-pdf.md)).

| Elemento | Componente | Tipografía | Notas |
|---|---|---|---|
| «Imprimir» e «Imprimir listado» | Botón secundario: filete de 1 px `primary-container` y relleno al pasar por encima de `primary-container` @ 8 % | `label-lg` en mayúsculas | Icono de 16 px en `primary`. Deshabilitado con opacidad 50 % (001) |
| Casillas de impresión | `Casilla` de 1 px y radio 0 | `body-md` | Agrupadas con `role="group"` y la etiqueta accesible «Opciones de impresión» |
| Motivo de desactivación | Texto | `body-sm` `on-surface-variant` | Bajo «Imprimir listado» |
| Campos de contacto y pie | `TextField` de 001 | Formularios de 001 | El área de texto tiene el mismo marco y foco que `TextField` |
