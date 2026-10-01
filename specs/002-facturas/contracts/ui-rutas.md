# Contrato de la interfaz — rutas nuevas de la feature 002

Este documento amplía el [ui-rutas.md de 001](../../001-cimientos-clientes/contracts/ui-rutas.md). Los
comportamientos comunes de 001 siguen vigentes: guardas, 401, CSRF, shell y estado en la URL.
Los endpoints son los de [openapi.yaml](openapi.yaml).

| Ruta | Acceso | Pantalla | Endpoints |
|---|---|---|---|
| `/facturas` | Sesión | Listado de facturas y borradores: búsqueda arriba, filtros de año y mes, orden, tabla y paginación. Sin indicadores ni columna de estado (FR-032 a FR-035) | `GET /v1/facturas`, `GET /v1/facturas/parametros` |
| `/facturas/nueva` | Sesión | Modal «Nueva factura» sobre `/facturas` | `POST /v1/borradores-factura`, `POST /v1/facturas`, `GET /v1/clientes` (selector), `POST /v1/clientes` (alta desde el modal) |
| `/facturas/borradores/$borradorId` | Sesión | Modal «Borrador» editable, con «Eliminar borrador», «Guardar borrador» y «Emitir factura» | `GET/PUT/DELETE /v1/borradores-factura/{id}`, `POST …/emision` |
| `/facturas/$facturaId` | Sesión | Modal de consulta de una factura emitida: estado, enlaces e historial. «Anular» y «Modificar» solo para administradores y solo si está vigente | `GET /v1/facturas/{id}`, `POST …/anulacion` |
| `/facturas/$facturaId/modificar` | Administrador | Modal «Modificar factura» con los datos precargados, cliente y líneas editables. Al guardar pide el motivo y, en su caso, la causa | `POST /v1/facturas/{id}/modificacion` |
| `/configuracion/facturacion` | Administrador | Pestaña «Facturación». Contiene el IVA por defecto (campo libre con «%», de 0 a 99,99; R-20) y la modalidad («Sin decidir», VERI\*FACTU o no VERI\*FACTU; bloqueada con explicación si ya hay registros, FR-050). Además, los datos del emisor con el IBAN opcional (R-22) y el próximo número con ajuste al alza. Desde el ajuste de cierre no hay clave de régimen (R-23) | `GET/PUT /v1/configuracion/facturacion`, `POST /v1/configuracion/facturacion/contador` |

## Comportamientos

- **Menú lateral**: se activa Facturas (`/facturas`). Presupuestos sigue deshabilitada con el chip
  «Próximamente» (FR-041). Tras iniciar sesión se sigue entrando en `/clientes`, como en 001.
- **Estado en la URL** (R-12): `q`, `anio`, `mes`, `orden` y `pagina` son *search params*, con la
  misma validación Zod, debounce de 300 ms y `replace: true` que en clientes. Abrir y cerrar el
  modal conserva esos parámetros.
- **Modal sobre el listado** (R-13, FR-037):
  - Se renderiza en el `<Outlet/>` de `/facturas`, así que el listado sigue detrás.
  - Al cerrarlo se vuelve a `/facturas` con los mismos filtros.
  - Si hay cambios sin guardar, cerrar, pulsar Escape o «Cancelar» piden confirmación (FR-036).
- **Número**: siempre en solo lectura. En un borrador se muestra «Se asigna al emitir», con el
  próximo número previsto como ayuda. En una emitida, el número definitivo (FR-010).
- **Emitir** (FR-021):
  - **Confirmación**: siempre se pide antes de emitir.
  - **Emisión no disponible**: el botón está deshabilitado y se explica qué falta, con un enlace a
    Configuración si el usuario es administrador (FR-004).
  - **Tras emitir**: se cierra el modal, aparece el aviso «Factura FAC-2026-0001 emitida» y se
    invalida la caché `['facturas']`.
- **Previsualización**: los importes se calculan en el navegador con `lib/dinero.ts` (R-11). Tras
  cada guardado se muestran los que devuelve la API.
- **«Nuevo cliente» desde el modal** (FR-046): abre `ClienteAltaPanel` por encima. Al guardar,
  vuelve al modal con el cliente elegido y todo lo escrito intacto. Se invalida `['clientes']`.
  Ante un duplicado se muestra el mismo aviso que en 001, pero sin el enlace «Ir al cliente»
  (saldría del modal y se perdería la factura): en su lugar, «Usar este cliente» o, si está
  inactivo, «Reactivar y usar», que lo reactiva como en 001 y lo deja elegido.
- **Fecha de expedición** (FR-018): editable en todos los modos, también al modificar. Propone la
  de hoy; el campo no admite fechas posteriores a hoy ni anteriores al 28/10/2024 y, al modificar,
  tampoco anteriores a la fecha de la operación heredada, que se muestra debajo. La API vuelve a
  validarlo.
- **Modificar** (FR-023, FR-024): al pulsar «Guardar» se abre un diálogo con:
  - El motivo, con dos opciones.
  - Si es «ya entregada», la causa, también con dos opciones.
  - Un texto libre obligatorio.
  - El aviso de lo que se va a generar («Se anulará FAC-2026-0007 y se emitirá una factura
    nueva» o «Se emitirá la rectificativa REC-2026-000N»).
  - El aviso de IVA si el tipo vigente difiere del de la original.
- **En una rectificativa vigente**, el diálogo de motivo solo ofrece «Hay que corregir una factura
  ya entregada».
- **Anular** (FR-025): diálogo con la casilla obligatoria «Declaro que esta factura no debió
  emitirse» y el motivo. Advierte de que no se puede deshacer. Si la factura es una rectificativa,
  avisa además de que «{número original} volverá a estar vigente» (FR-048).
- **Clave de idempotencia** (R-18):
  - El modal genera un UUID al abrirse en cada modo de acción (nueva, borrador, modificar o anular)
    y lo envía como `Idempotency-Key`.
  - Lo reutiliza si reintenta tras un error de red.
  - Lo renueva solo cuando la operación ha terminado con éxito.
  - Mientras hay una petición en curso, el botón está deshabilitado.
- **Después de cada acción**: lo que muestra la interfaz está descrito en la spec, FR-049.
- **IVA por defecto** (FR-001, R-20; ajuste de cierre):
  - El campo es un `CampoDecimal` con el sufijo «%» y admite la coma decimal. Si el valor no es un
    porcentaje de 0 a 99,99, el propio campo muestra «Escribe un porcentaje entre 0 y 99,99, con
    dos decimales como mucho».
  - Si el valor escrito no está en `tipos_iva_oficiales`, un aviso bajo el campo lo dice mientras
    se escribe: «22 % no está entre los tipos que admite hoy la AEAT (0, 4, 10 y 21)».
  - Al guardar, si la API responde `422 tipo-iva-sin-confirmar`, se abre el diálogo «¿Guardar un
    tipo de IVA que la AEAT no admite hoy?», que explica el riesgo (research R-17, Q-11). «Guardar
    igualmente» reenvía con `confirmar_tipo_iva: true`, y «Cancelar» deja el formulario como
    estaba.
- **IBAN** (FR-001, R-22): es un campo de texto en «Datos del emisor», opcional y sin la marca de
  necesario para emitir. Al salir del campo y al mostrarse, aparece agrupado de cuatro en cuatro.
  Un error de la API se muestra en el propio campo.
- **«Sin IVA (oro de inversión)»** (FR-052, R-21; ajuste de cierre):
  - Es una `Casilla` en la sección de totales, antes de la base, desmarcada por defecto en una
    factura nueva.
  - En un borrador se carga su valor. En «Modificar», el de la factura original.
  - Con la casilla marcada, los totales muestran «Base exenta», «IVA 0,00 €» y el total, y debajo
    la mención `mencion_exencion_oro_inversion` de `/v1/facturas/parametros` en `body-sm`.
  - El aviso de cambio de IVA del borrador no se muestra si el borrador es exento.
  - En el diálogo de motivo de «Modificar», el aviso de IVA distinto solo aparece si la original y
    la corrección van con IVA.
  - El orden de tabulación es: líneas, «Añadir línea», la casilla y los botones del pie. Su nombre
    accesible es la etiqueta visible.
  - En móvil (menos de 768 px), la casilla ocupa todo el ancho encima de los totales y la mención
    se parte en varias líneas, sin desplazamiento horizontal (FR-040, SC-008).
- **Consulta de una factura emitida** (FR-053):
  - Si `mencion_exencion` no es `null`, se muestra junto a los totales.
  - Si `emisor.iban` no es `null`, se muestra un bloque «Pago» con «IBAN» y el número agrupado.
- **Listado** (FR-033): en la columna del IVA, las filas con `oro_inversion` muestran «Exenta» en
  lugar de la cuota. Las tarjetas de móvil no muestran el IVA (FR-049), así que tampoco la marca.
- **Rol**: un empleado no ve «Anular», «Modificar» ni la pestaña Facturación. La API decide en
  cualquier caso (FR-023, FR-025).
- **Historial** (FR-026): una sección plegable del modal de consulta con las correcciones y los
  registros de facturación (tipo, secuencia, huella abreviada y fecha y hora de generación), y
  enlaces a la factura anulada o a la vigente.

## Aplicación de DESIGN.md por elemento

Se usan los tokens del frontmatter de [`docs/DESIGN.md`](../../../docs/DESIGN.md). Los elementos
que no aparecen aquí se aplican como en 001.

| Elemento | Nivel / superficie | Tipografía | Notas |
|---|---|---|---|
| Tabla de facturas | Igual que clientes | Número en `title-md` con cifras tabulares; importes alineados a la derecha en `body-md` tabular | Marcas «Borrador», «Anulada» y «Rectificada» como chip de 1 px, radio 0 y `label-sm`: `warning` para borrador y `on-surface-variant` para anulada y rectificada. No hay columna de estado. Acciones fijas a la derecha (001, R-22) |
| Columnas según el ancho | — | — | Por debajo de 768 px, tarjetas. Medido al implementar (R-12): NIF/CIF desde 1280 px; base imponible e IVA desde 1440 px. SC-008 exige que las acciones se vean en todos los anchos |
| Modal de factura (`ModalDocumento`) | Nivel 2 · `surface-container-high`, borde `tertiary` @ 35 %, `shadow-nivel-2` | Título en Bodoni `headline-md`; secciones en `title-lg` | `max-w-5xl` centrado; pantalla completa por debajo de 768 px. Cuerpo desplazable y pie fijo con filete superior de 1 px `primary-container` @ 18 % |
| Resumen del cliente | Nivel 1 · `surface-container` | Etiquetas `label-sm` en `on-surface-variant`; datos `body-md` | Filete de 1 px `primary-container` @ 18 % |
| Tabla de líneas | Contenedor `surface-container-low` | Cabecera `label-md` en mayúsculas | Campos de DESIGN.md. Unidades y precio con `CampoDecimal`; el precio lleva el símbolo € fijo en `primary-container`. Importe en solo lectura, alineado a la derecha y tabular |
| Totales | Caja de resumen con acento `primary-container` (DESIGN.md, «Totals Section») | Base e IVA en `body-md`; total en Bodoni `headline-md` en `primary` | Etiqueta «IVA (21 %)» con el tipo vigente. Casilla «Sin IVA (oro de inversión)» con la `Casilla` de 1 px y radio 0 ya existente. En modo exento, «Base exenta» y la mención en `body-sm` `on-surface-variant` |
| Bloque «Pago» de la consulta | Dentro de la caja de totales, con filete superior de 1 px `primary-container` @ 18 % | Etiqueta `label-sm`; IBAN en `body-md` tabular | Solo si la factura tiene IBAN (FR-053) |
| Botones del modal | «Emitir factura»: primario. «Guardar borrador», «Modificar» y «Añadir línea»: secundario. «Cancelar» y «Cerrar»: ghost. «Anular» y «Eliminar borrador»: destructivo | `label-lg` en mayúsculas | En móvil se apilan a ancho completo |
| Diálogos (confirmar, motivo, anular, contador) | Nivel 2, `Dialog` de 001 | `title-lg` y `body-md` | Radio 0 en las opciones del motivo y la causa |
| Pestaña Facturación | Tarjeta nivel 1 | Formularios de 001 | El próximo número se muestra en Bodoni `headline-sm` con el botón secundario «Ajustar» |
