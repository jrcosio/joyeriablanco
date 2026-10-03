# Contrato de la interfaz — feature 004

Amplía los `ui-rutas.md` de 001, 002, 003 y 005, cuyos comportamientos comunes siguen vigentes.
Los endpoints son los de [openapi.yaml](openapi.yaml).

| Ruta | Acceso | Pantalla | Endpoints |
|---|---|---|---|
| `/registro-fiscal` | Administrador | «Registro fiscal», con las pestañas «Eventos» (lista, filtros y detalle), «Cadena», «Comprobar integridad» y «Exportar» | `GET /v1/registro-fiscal/eventos`, `…/eventos/{secuencia}`, `…/registros/{secuencia}`, `POST …/comprobaciones`, `GET …/exportacion` |
| `/acerca` | Sesión | «Acerca del sistema»: los datos del sistema y la declaración responsable, con «Descargar PDF» | `GET /v1/sistema`, `GET /v1/sistema/declaracion-responsable/pdf` |
| `/configuracion/facturacion` (002) | Administrador | **Ampliada**: modalidad fija y tarjeta del certificado | 002 |
| `/facturas/$facturaId` (002) | Sesión | **Ampliada**: cada registro muestra «Firmado», el titular y si la huella y la firma son correctas. Los administradores tienen «Ver en la cadena» | 002 |

## Comportamientos

### Banda de alarma

- **Dónde**: en el *layout* de la aplicación, encima del contenido de todas las pantallas, para
  cualquier usuario.
- **Aspecto**: tono `danger`, icono y texto («Alarma de integridad: se ha detectado una anomalía en
  los registros el dd/mm/aaaa hh:mm»), siempre con texto y nunca solo con color.
- **Accesibilidad**: `role="alert"` la primera vez que aparece.
- **Alarma de certificado**: «No se puede facturar: el certificado de firma no es utilizable
  (motivo)».
- **Detalle**: los administradores ven el enlace «Ver detalle», que lleva a «Registro fiscal».
- **Actualización**: se consulta `GET /v1/alarmas` al cambiar de ruta y cada 60 s.

### Menú

- «Registro fiscal» va en el grupo de Configuración, solo para administradores.
- «Acerca del sistema» va en el menú de usuario y en el pie del menú lateral, para todos: son dos
  clics como máximo (SC-008).

### «Registro fiscal»

- **Eventos**:
  - una tabla con secuencia, tipo (su texto en español), fecha y hora, resumen y titular del
    certificado;
  - filtros por tipo y por fechas, guardados en la URL, como en los listados de 002;
  - el detalle abre un modal con los datos propios, la huella, si la huella y la firma son
    correctas, y «Evento anterior» y «Evento siguiente». Cada salto indica si el encadenamiento y
    las fechas son correctos.
- **Cadena**:
  - se elige un número de secuencia, o se llega desde una factura, y se ve el registro;
  - «Anterior» y «Siguiente» llevan cada uno su indicador de encadenamiento y fechas: chip `success`
    «Correcto» o `danger` «Incorrecto» (Orden, art. 7.h).
- **Comprobar integridad**:
  - un rango opcional de secuencias y el botón «Comprobar integridad»;
  - mientras dura, «Comprobando…», anunciado a los lectores de pantalla;
  - el resultado: «Íntegra», con los recuentos, o la lista de anomalías con su tipo y su registro.
- **Exportar**:
  - qué se exporta (registros de facturación o de evento) y el periodo, «desde» y «hasta»;
  - «Exportar» descarga el ZIP;
  - con un periodo vacío aparece el aviso «No hay registros en ese periodo».

### Configuración → Facturación

- **Modalidad**: muestra «No VERI\*FACTU», fija. VERI\*FACTU aparece desactivada con el texto «No
  disponible: el sistema no tiene capacidad de remisión».
- **Tarjeta «Certificado de firma»**:
  - titular, identificación, emisor, válido desde y hasta, y los días restantes;
  - chip `success` «Utilizable», `warning` «Caduca pronto» o `danger` «No utilizable», con el
    motivo;
  - ninguna acción: el certificado lo instala quien despliega.

### Modal de factura (002)

- Si `faltan` incluye `certificado`, el aviso «No se puede emitir todavía: falta un certificado de
  firma utilizable».
- Si el certificado caduca pronto, el aviso «El certificado de firma caduca el dd/mm/aaaa».

### Consulta de una factura (002)

- **En cada registro**: «Firmado · {titular}», la fecha y hora de generación, la huella abreviada y
  dos chips, «Huella correcta» y «Firma correcta» (o «incorrecta»). Desaparece «Remisión:
  pendiente».
- **Administradores**: además, «Ver en la cadena», que lleva a `/registro-fiscal?pestana=cadena&secuencia=N`.

### «Acerca del sistema»

- **Datos del sistema**: nombre, código, versión, número de instalación y modalidad.
- **Declaración responsable**:
  - el título literal;
  - cada letra con su texto descriptivo del art. 15.1 seguido del valor, en una lista de
    definiciones;
  - «Descargar PDF», que abre el PDF en una pestaña nueva, como los de 003.

## Conformidad con `docs/DESIGN.md`

Se usan componentes existentes: tabla, chips, modal de nivel 2, pestañas, campos de fecha y
botones. No hay tokens nuevos, y la declaración en PDF usa la sección «Paper».
