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
| `/configuracion/usuarios` | Administrador | Listado y alta de usuarios, cambio de rol, desactivación y reactivación, restablecimiento de contraseña | `/v1/usuarios…` |
| `/configuracion/auditoria` | Administrador | Consulta filtrable y paginada, con detalle de cada evento | `GET /v1/auditoria` |
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
  "Tu sesión ha caducado" y se redirige a `/acceso?volver=…` (FR-004). Los formularios abiertos
  conservan lo tecleado mientras la página no se recargue.
- **CSRF**: el cliente HTTP añade `X-CSRF-Token` (obtenido de `SesionSalida`) a toda petición que
  modifica datos.
- **Shell**:
  - Menú lateral izquierdo, con cajón por debajo de 1024 px.
  - Facturas y Presupuestos deshabilitadas, con el chip "Próximamente".
  - Configuración solo para administradores.
  - Cabecera con "Gestión de facturación", la fecha larga en `es-ES` (zona `Europe/Madrid`, primera
    letra en mayúscula) y el menú de usuario con iniciales.
- **Estado en la URL**: los filtros, la búsqueda, el orden y la página del listado de clientes
  viven en los *search params* de la ruta. Se pueden compartir y sobreviven a una recarga.
