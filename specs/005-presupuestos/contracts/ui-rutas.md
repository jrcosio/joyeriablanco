# Contrato de la interfaz — rutas nuevas de la feature 005

Este documento amplía los `ui-rutas.md` de [001](../../001-cimientos-clientes/contracts/ui-rutas.md),
[002](../../002-facturas/contracts/ui-rutas.md) y [003](../../003-pdf-impresion/contracts/ui-rutas.md).
Siguen vigentes sus comportamientos comunes: guardas, 401, CSRF, estado en la URL, modal sobre el
listado, previsualización con `lib/dinero.ts`, clave de idempotencia por modal y enlaces de PDF en
pestaña nueva. Los endpoints son los de [openapi.yaml](openapi.yaml).

| Ruta | Acceso | Pantalla | Endpoints |
|---|---|---|---|
| `/presupuestos` | Sesión | Listado de presupuestos y borradores: búsqueda, año, mes, orden, tabla y paginación, con «Nuevo presupuesto» e «Imprimir listado» (FR-023 a FR-025, FR-030) | `GET /v1/presupuestos`, `GET /v1/presupuestos/parametros`, `GET /v1/presupuestos/listado/pdf` |
| `/presupuestos/nuevo` | Sesión | Modal «Nuevo presupuesto» sobre `/presupuestos` | `POST /v1/borradores-presupuesto`, `POST /v1/presupuestos`, `GET /v1/clientes`, `POST /v1/clientes` |
| `/presupuestos/borradores/$borradorId` | Sesión | Modal «Borrador de presupuesto» editable | `GET/PUT/DELETE /v1/borradores-presupuesto/{id}`, `POST …/emision` |
| `/presupuestos/$presupuestoId` | Sesión | Consulta: estado, validez, historial y acciones según el estado y el rol (FR-027) | `GET /v1/presupuestos/{id}`, `GET …/pdf`, `POST …/conversion`, `POST …/anulacion` |
| `/presupuestos/$presupuestoId/modificar` | Administrador | Modal «Modificar presupuesto» con los datos precargados. Al guardar pide el motivo | `POST /v1/presupuestos/{id}/modificacion` |
| `/facturas/borradores/$borradorId` (002) | Sesión | **Ampliado**: si el borrador procede de un presupuesto, muestra «Procede del presupuesto PRE-…» con un enlace | 002 |
| `/facturas/$facturaId` (002) | Sesión | **Ampliado**: si la factura procede de un presupuesto, muestra «Procede del presupuesto PRE-…» con un enlace | 002 |
| `/configuracion/facturacion` (002) | Administrador | **Ampliado**: «Validez de los presupuestos (días)» y «Pie de presupuesto» | 002 |

## Comportamientos

- **Menú lateral**: se activa «Presupuestos» (`/presupuestos`) con su icono actual, y desaparece la
  marca «Próximamente» (FR-032). Tras iniciar sesión se sigue entrando en `/clientes`.
- **Listado**: los mismos *search params* (`q`, `anio`, `mes`, `orden` y `pagina`), validación,
  espera de 300 ms, estados vacíos y anchos que facturas (002, R-12 y R-22).
  - **Marcas en la columna del número**, en chips de 1 px con esquinas a 0 (DESIGN.md 1.3):

    | Marca | Tono |
    |---|---|
    | «Borrador» | `warning`, como en facturas |
    | «En facturación» | `warning` |
    | «Caducado» | `danger` |
    | «Convertido» | `success` |
    | «Sustituido» | `neutral` |
    | «Anulado» | `neutral` |

    Un pendiente no lleva marca.
  - **Acción de cada fila**: «Abrir borrador de {cliente}» o «Ver presupuesto {número}».
- **Modal** (FR-026):
  - **Datos del presupuesto**: número en solo lectura, fecha y «Válido hasta».
    - La fecha va entre la mínima y hoy.
    - «Válido hasta» propone la fecha más `validez_dias`. Si el usuario no lo ha tocado, se
      recalcula al cambiar la fecha. No admite un valor anterior a la fecha.
  - **Cliente**: selector y «Nuevo cliente», como en 002. El resumen avisa de que la factura no se
    podrá emitir si al cliente le falta el domicilio.
  - **Detalle y totales**: los de la factura, con «Sin IVA (oro de inversión)». El título de la caja
    es «Total presupuesto».
  - **Botones**: los de FR-027. Al emitir se confirma: «El presupuesto no podrá editarse. Los
    cambios posteriores se harán con Modificar».
- **Consulta**:
  - **Historial**, si hay cierre: el tipo, la fecha, el autor y el motivo, con un enlace al
    presupuesto nuevo o a la factura. Si la factura se corrigió después, se enlaza también la
    vigente.
  - **Enlace de origen**: «Sustituye a PRE-…».
  - **En facturación**: aviso «Este presupuesto tiene un borrador de factura en curso» y el botón
    «Abrir borrador de factura».
- **«Convertir en factura»** (FR-018):
  1. **Confirmación**: «Se creará un borrador de factura con los datos de PRE-…. Podrás revisarlo
     antes de emitirlo». Si está caducado, añade el aviso «La validez de este presupuesto venció el
     dd/mm/aaaa».
  2. Al confirmar, `POST …/conversion`. Tanto 201 como 200 navegan a `/facturas/borradores/$id`
     con el aviso «Borrador de factura creado a partir de PRE-…».
  3. Se invalidan `['presupuestos']`, `['facturas']` y `['clientes']`, y el borrador se guarda en
     la caché.
- **Emitir el borrador vinculado** (002): tras emitir, el aviso es «Factura FAC-… emitida.
  PRE-… queda convertido» y se invalida también `['presupuestos']`. Eliminar ese borrador también
  invalida `['presupuestos']`.
- **Modificar** (solo administradores): un modal con los datos precargados y la fecha de hoy. Al
  guardar pide el motivo en un diálogo con un texto libre obligatorio. Tras guardar, se abre la
  consulta del presupuesto nuevo con el aviso «Se ha emitido PRE-…. PRE-… queda sustituido».
- **Anular** (solo administradores): un diálogo con el motivo obligatorio, p. ej. «Rechazado por
  el cliente». Tras anular, la consulta sigue en el presupuesto, ya marcado.
- **Imprimir** (003): «Imprimir», con la casilla «Incluir número de cuenta» si tiene IBAN. No hay
  casilla «Duplicado». El nombre accesible es «Imprimir presupuesto PRE-…».
- **«Imprimir listado»**: igual que en facturas, desactivado con 0 filas o con más de 5.000, con su
  motivo.
- **Errores**: `presupuesto-no-modificable` se muestra como un aviso que recarga la consulta, con el
  estado nuevo. Si lleva `borrador_factura_id`, ofrece abrir el borrador. Los demás errores se
  tratan como en 002.

## Conformidad con `docs/DESIGN.md`

- Componentes y tokens de 002: modal de nivel 2, botones primario y secundario, tabla, chips,
  campos monetarios y estados.
- Los chips nuevos usan los tonos de «Status Chips & Badges», con el tono neutro que añade la 1.3.
- No hay colores ni radios literales: `check:tokens`.
