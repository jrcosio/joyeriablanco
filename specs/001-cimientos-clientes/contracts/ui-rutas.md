# Contrato de la interfaz — rutas y acceso

Rutas de la aplicación web, quién puede acceder y qué endpoints de
[openapi.yaml](openapi.yaml) consume cada una. El sistema de diseño normativo es
[`docs/DESIGN.md`](../../../docs/DESIGN.md).

| Ruta | Acceso | Pantalla | Endpoints |
|---|---|---|---|
| `/acceso` | Pública (con sesión redirige a `/clientes`) | Inicio de sesión. Acepta `?volver=<ruta>` | `POST /v1/sesion` |
| `/cambiar-contrasena` | Sesión con contraseña temporal | Cambio obligatorio (FR-009); no muestra el shell | `PUT /v1/cuenta/contrasena` |
| `/` | Sesión | Redirige a `/clientes` | — |
| `/clientes` | Sesión | Indicadores, filtros, tabla y paginación. Panel de alta y edición | `GET /v1/clientes`, `GET /v1/clientes/indicadores`, `GET /v1/catalogos` |
| `/clientes/nuevo` | Sesión | Panel de alta (nivel 2) sobre `/clientes` | `POST /v1/clientes` |
| `/clientes/$clienteId` | Sesión | Panel de ficha y edición, con trazabilidad y acciones de desactivar, reactivar y borrar (solo admin) | `GET/PUT/DELETE /v1/clientes/{id}`, `POST …/desactivacion`, `POST …/reactivacion` |
| `/configuracion/usuarios` | Administrador | Listado y alta de usuarios, cambio de rol, desactivación y reactivación, restablecimiento de contraseña y eliminación de los desactivados (FR-061) | `/v1/usuarios…`, `DELETE /v1/usuarios/{id}` |
| `/configuracion/auditoria` | Administrador | Consulta filtrable y paginada, con detalle de cada evento. El filtro de usuario incluye a los eliminados, marcados "(eliminado)" | `GET /v1/auditoria`, `GET /v1/usuarios?incluir_eliminados=true` |
| `/cuenta` | Sesión | Mi cuenta: cambio de contraseña | `PUT /v1/cuenta/contrasena` |
| `/acceso-denegado` | Sesión | Pantalla 403 | — |
| `*` | — | Pantalla 404 | — |

## Comportamientos comunes

- **Guardas de ruta**:
  - Sin sesión (401) → `/acceso?volver=<ruta actual>`.
  - Contraseña temporal → `/cambiar-contrasena`.
  - Rol insuficiente → `/acceso-denegado`.

  Las guardas son solo comodidad; la API decide (FR-013).
- **401 durante el uso**, por sesión caducada o revocada: se vacía la caché, aparece el aviso
  "Tu sesión ha caducado" y se redirige a `/acceso?volver=…` (FR-004).
  - **Lo tecleado no se conserva**, conforme al caso límite de la spec ("los datos del formulario no
    se guardan"). Así se evita que otra persona que se identifique en el mismo equipo herede un
    borrador ajeno.
  - **Errores de red o de servidor**: aquí sí se conserva lo tecleado (FR-057).
- **CSRF**: el cliente HTTP añade `X-CSRF-Token` (obtenido de `SesionSalida`) a toda petición que
  modifica datos.
- **Shell**:
  - Menú lateral izquierdo, con cajón por debajo de 1024 px.
  - Facturas y Presupuestos deshabilitadas, con el chip "Próximamente".
  - Configuración solo para administradores.
  - Cabecera con "Gestión de facturación", la fecha larga en `es-ES` (zona `Europe/Madrid`, primera
    letra en mayúscula) y el menú de usuario con iniciales.
- **Usuarios eliminados** (FR-061): dondequiera que aparezca una referencia a un usuario eliminado
  (ficha del cliente, auditoría y su filtro), se muestra su nombre seguido de "(eliminado)". La
  acción "Eliminar" solo se ofrece en el menú de un usuario desactivado.
- **Estado en la URL**: los filtros, la búsqueda, el orden y la página del listado de clientes
  viven en los *search params* de la ruta. Se pueden compartir y sobreviven a una recarga.

## Aplicación de DESIGN.md por elemento

Los tokens se nombran como en el frontmatter de [`docs/DESIGN.md`](../../../docs/DESIGN.md).

| Elemento | Nivel / superficie | Tipografía | Notas |
|---|---|---|---|
| Lienzo de página | Nivel 0 · `background` | — | Márgenes de 2.5rem en escritorio y 1rem en móvil; contenido limitado a 1440 px |
| Menú lateral | `surface-container-lowest`, filete derecho de 1 px en `primary-container` @ 18 % | Marca en Bodoni `headline-sm` con espaciado; entradas en `title-md` | Activo: fondo `surface-container-high`, texto e icono en `primary`. Deshabilitado: `on-surface-variant` @ 50 % con chip "Próximamente" (`warning`) |
| Cabecera | Nivel 0, filete inferior de 1 px en `primary-container` @ 18 % | Contexto en `body-lg` `on-surface-variant`; fecha en `body-md` | Avatar cuadrado (radio 0) con las iniciales en `label-lg` |
| Título de página | — | Bodoni `headline-xl` (`headline-xl-mobile` por debajo de 768 px) | Subtítulo en `body-lg` `on-surface-variant` |
| Tarjeta de indicadores | Nivel 1 · `surface-container` | Etiqueta en `body-md`; cifra en Bodoni `headline-lg` | Iconos Lucide en `primary` |
| Barra de filtros | Campos de DESIGN.md (`surface-container-low`) | `body-md` | Foco: borde de 1 px en `primary-container` |
| Tabla | Contenedor `surface-container-low`; cabecera `surface-container` | Cabecera en `label-md` en mayúsculas; nombre en `title-md`; tipo en `label-sm` en `primary`; datos en `body-md` con cifras tabulares | Hover: `surface-container-high`. Solo filetes horizontales. Filas con 1rem × 1.5rem de relleno. Clientes: teléfono y correo desde 1280 px (FR-059) |
| Columna de acciones (clientes, usuarios y auditoría) | Fija en el borde derecho, con el fondo sólido de su fila: `surface-container` en la cabecera, `surface-container-low` en las filas y `surface-container-high` en hover | — | Siempre visible sin desplazar (FR-031, FR-059, SC-014). Si el resto no cabe, la tabla se desplaza en horizontal dentro de su tarjeta, nunca la página. Sin filete vertical ni sombra (R-22) |
| Chips de estado | 1 px de borde, radio 0 | `label-sm` | Activo: `success`. Inactivo: `danger`. Próximamente y contraseña temporal: `warning` |
| Panel de alta y edición | Nivel 2 · `surface-container-high`, borde `tertiary` @ 35 %, sombra de DESIGN.md | Título en Bodoni `headline-md` | Lateral derecho de 560 px en escritorio y tableta; pantalla completa en móvil |
| Diálogos de confirmación | Nivel 2 | `title-lg` y `body-md` | Borrado de cliente: campo de confirmación con la identificación y botón destructivo. Eliminación de usuario: campo de confirmación con el nombre de usuario y botón destructivo |
| Avisos breves | Nivel 3 · `surface-container-lowest` con borde de 1 px en `primary-container` | `body-md` | Esquina inferior derecha, 5 s, se pueden cerrar |
| Botones | Primario, Secundario y Ghost/Destructivo de DESIGN.md | `label-lg` en mayúsculas | "Nuevo cliente" es el primario |
| Foco visible (FR-052) | Controles que no son campos: contorno de 1 px en `tertiary` con separación de 2 px | — | Los campos usan su propio foco de DESIGN.md |
| Estados de carga | Esqueletos en `surface-container-high` con la geometría final | — | Sin desplazamiento del contenido al terminar (FR-057) |
