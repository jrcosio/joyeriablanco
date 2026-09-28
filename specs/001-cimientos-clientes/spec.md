# Feature Specification: Cimientos del sistema, seguridad de acceso y gestión de clientes

**Feature Branch**: `001-cimientos-clientes`

**Created**: 2026-09-27

**Status**: Draft

**Input**: Descripción del responsable del proyecto: "Primera feature: fase cero. Preparar toda la
arquitectura del proyecto (servicio de datos desplegable en contenedores, base de datos, aplicación
web de gestión con lo último en desarrollo web), con seguridad por usuario y comunicación segura
entre la web y el servidor. Añadir el módulo de clientes del mockup `clientes.png`, el logo sin fondo
y ajustado, y aplicar la hoja de estilos `DESIGN.md` durante todo el proyecto. El menú, a la
izquierda." Las decisiones tomadas con el responsable el 2026-09-26 y el 2026-09-27 están
incorporadas abajo.

**Ajustes de cierre** (2026-09-28), pedidos por el responsable antes de dar la feature por
terminada: "los usuarios del sistema, cuando se desactivan, tienen que tener la posibilidad de
eliminarles después, sin que eso afecte a facturas o cosas que hayan creado" (FR-061). Y, tras
probar el listado de clientes: "si no está solo un cliente en la lista no se puede editar y eso es
raro, se tiene que editar siempre" (FR-031, FR-059).

**Referencias**: mockup [`assets/mockup-clientes.png`](assets/mockup-clientes.png) (orientativo) ·
sistema de diseño [`docs/DESIGN.md`](../../docs/DESIGN.md) (normativo, constitución 1.1.0)

## Clarifications

### Session 2026-09-27

- Q: ¿Puede haber dos clientes con la misma identificación fiscal (mismo país, tipo y número)?
  → A: No. La identificación es única entre todos los clientes, activos e inactivos. Una empresa
  con varias direcciones sigue siendo un solo cliente.
- Q: ¿Cuánto debe durar la sesión en el mostrador? → A: Caduca tras 30 minutos de inactividad y,
  en cualquier caso, a las 10 horas. Ambos valores son configurables (FR-003).
- Q: ¿Debe el administrador poder consultar la auditoría desde la propia aplicación en esta
  feature? → A: Sí, con una consulta básica. En Configuración → Auditoría, solo para
  administradores, hay un listado de solo lectura con filtros por fecha, usuario, tipo de evento y
  cliente (FR-051).
- Q: Ninguna fuente oficial publica el algoritmo del carácter de control del NIF de entidades ni de
  los NIF K/L/M. ¿Cómo se validan? → A: Solo por estructura oficial (research R-20.2). DNI y NIE se
  validan con su letra.
- Q: ¿Qué nivel de accesibilidad debe cumplir la aplicación web? → A: Buenas prácticas básicas,
  sin objetivo formal de cumplimiento (WCAG). Uso completo con teclado, formularios etiquetados y
  foco visible (FR-052).

### Session 2026-09-28

- Q: ¿Se puede eliminar un usuario del sistema? → A: Sí. Un administrador puede eliminar un usuario
  que antes haya sido desactivado. Lo que registró (clientes, auditoría y, en features posteriores,
  facturas y presupuestos) se conserva intacto y sigue mostrando quién lo hizo (FR-061).
- Q: Cuando se elimina un usuario, ¿su nombre de usuario queda libre para dar de alta a otra
  persona? → A: Sí, queda libre. El historial distingue a ambos y al eliminado lo muestra con la
  marca "(eliminado)" (FR-061).
- Q: Con el listado completo, la columna de acciones queda cortada y solo se puede editar al buscar
  hasta dejar un cliente. ¿Cómo se garantiza que cada fila tenga siempre su acción de editar? → A: La
  columna de acciones queda fija en el borde derecho de la tabla y siempre visible. El teléfono y el
  correo solo se muestran en la tabla a partir de 1280 px (umbral corregido a 1536 px en la última
  pregunta de esta sesión); por debajo quedan en la ficha. Si algún dato largo no cabe, se desplaza
  la tabla dentro de su recuadro, nunca la página (FR-031, FR-059).
- Q: El mismo corte aparece en Usuarios, cuyo menú de acciones no se ve en un móvil de 360 px, y en
  Auditoría, cuyo botón de detalle queda fuera de vista a 360 px y a 1024 px. ¿Entran en el ajuste?
  → A: Sí. Las tres tablas con acciones por fila (clientes, usuarios y auditoría) mantienen la
  columna de acciones fija en el borde derecho y siempre visible (FR-059, SC-014).
- Q: Medido durante la implementación con los datos de ejemplo, la columna fija tapa el correo entre
  1280 y 1535 px y la provincia entre 1024 y 1279 px, porque las columnas no caben junto al menú
  lateral. ¿Qué columnas se muestran en cada ancho? → A: El teléfono y el correo, desde 1536 px. La
  provincia no se muestra entre 1024 y 1279 px. Lo que no aparece en la tabla se consulta en la
  ficha (FR-059, research R-22).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Acceso seguro y navegación por la aplicación (Priority: P1)

Un usuario autorizado de la joyería (administrador o empleado) abre la aplicación web, se identifica
con su usuario y contraseña y entra en la aplicación de gestión. Ve el menú lateral a la izquierda,
con el logo y las secciones, y la cabecera con la fecha y su menú personal. Cuando termina, cierra la
sesión. Si deja la aplicación desatendida, la sesión caduca sola, y al volver a identificarse regresa
a la pantalla en la que estaba.

**Why this priority**: sin acceso controlado no se puede exponer ningún dato. Todo lo demás se apoya
en esta historia, y es además la primera prueba de que toda la base técnica (servidor, datos, web y
canal seguro) funciona de extremo a extremo.

**Independent Test**: con un administrador creado por consola, se inicia sesión, se navega por la
aplicación, se cierra sesión y se comprueba que sin sesión no se accede a ninguna pantalla ni dato.

**Acceptance Scenarios**:

1. **Given** un usuario activo con contraseña válida, **When** introduce sus credenciales, **Then**
   accede a la aplicación y ve el menú lateral izquierdo con Facturas y Presupuestos (deshabilitadas,
   marcadas "Próximamente"), Clientes y, solo si es administrador, Configuración.
2. **Given** credenciales incorrectas o un usuario inexistente, **When** intenta entrar, **Then** ve
   exactamente el mismo mensaje genérico en ambos casos y no accede.
3. **Given** una cuenta con 5 intentos fallidos consecutivos, **When** se intenta entrar de nuevo,
   incluso con la contraseña correcta, antes de que pasen 15 minutos, **Then** el acceso se rechaza
   con el mismo mensaje genérico.
4. **Given** un usuario con sesión abierta y 30 minutos sin actividad, **When** intenta cualquier
   acción, **Then** se le pide identificarse de nuevo y, tras hacerlo, vuelve a la pantalla que
   intentaba abrir.
5. **Given** un usuario cuya contraseña es temporal (recién dado de alta o restablecida), **When**
   inicia sesión, **Then** debe fijar una contraseña nueva que cumpla la política antes de poder
   hacer nada más.
6. **Given** un usuario con sesión abierta, **When** elige "Cerrar sesión" en su menú, **Then** la
   sesión deja de ser válida al instante y vuelve a la pantalla de inicio de sesión.
7. **Given** un empleado, **When** intenta abrir una dirección reservada a administradores, **Then**
   ve la pantalla de acceso denegado.
8. **Given** una dirección que no existe, **When** se abre, **Then** se muestra la pantalla de página
   no encontrada.

---

### User Story 2 - Alta y edición de clientes (Priority: P2)

Un empleado da de alta a un cliente nuevo, sea particular o empresa, con su identificación fiscal y
sus datos de contacto y dirección, y más adelante corrige sus datos. El sistema no deja guardar una
identificación fiscal española con el dígito de control incorrecto ni un cliente duplicado.

**Why this priority**: es el primer valor de negocio. La cartera de clientes es la base de la
facturación y los presupuestos de las siguientes features, y la identificación fiscal tiene que ser
válida para poder facturar.

**Independent Test**: con un usuario autenticado, se crean clientes de ambos tipos, con
identificación española y extranjera, se edita uno y se comprueba que las identificaciones inválidas
y los duplicados se rechazan con mensajes claros.

**Acceptance Scenarios**:

1. **Given** un empleado en la pantalla de clientes, **When** pulsa "Nuevo cliente", completa los
   datos obligatorios con un NIF español válido y guarda, **Then** el cliente queda creado, activo y
   visible en el listado, y consta quién lo creó y cuándo.
2. **Given** el formulario de alta, **When** se introduce un DNI o NIE con la letra de control
   incorrecta, o un NIF de entidad o K/L/M con estructura inválida, **Then** el sistema no guarda y
   señala el campo con un mensaje en español.
3. **Given** un cliente cuyo país de identificación no es España, **When** se elige un tipo de
   identificación extranjera admitido (NIF-IVA, pasaporte, documento oficial del país de residencia,
   certificado de residencia u otro documento probatorio) y se introduce el número, **Then** se
   guarda sin validación de dígito de control, respetando la longitud máxima oficial.
4. **Given** ya existe un cliente con la misma identificación (tipo, país y número normalizados),
   **When** se intenta crear otro, **Then** el sistema lo impide, indica qué cliente existe y, si
   está inactivo, ofrece reactivarlo.
5. **Given** un cliente existente, **When** un usuario edita sus datos y guarda, **Then** los cambios
   se conservan y constan quién hizo la última modificación y cuándo.
6. **Given** el país es España, **When** se introduce un código postal de 5 dígitos, **Then** la
   provincia correspondiente se asigna automáticamente. Un código postal que no corresponda a
   ninguna provincia se rechaza.
7. **Given** el formulario de alta, **When** se deja vacío un campo obligatorio o se introduce un
   correo con formato inválido, **Then** el sistema no guarda e indica cada error junto a su campo.

---

### User Story 3 - Consulta, búsqueda y filtrado de la cartera de clientes (Priority: P2)

Un empleado abre Clientes y ve dos indicadores ("Clientes activos" y "Nuevos este año") y el listado
paginado. Busca por nombre, NIF o localidad sin preocuparse de tildes ni mayúsculas, filtra por
provincia, tipo y estado, y ordena el resultado.

**Why this priority**: localizar rápido a un cliente es la operación más frecuente en mostrador y la
puerta de entrada a su edición y, más adelante, a sus facturas.

**Independent Test**: con datos de ejemplo cargados, se prueban la búsqueda, cada filtro, las
ordenaciones, la paginación y el cálculo de los indicadores.

**Acceptance Scenarios**:

1. **Given** una cartera con clientes activos e inactivos, **When** se abre Clientes, **Then** por
   defecto solo aparecen los activos, ordenados por nombre de la A a la Z, y los indicadores muestran
   el número de clientes activos y el de clientes creados en el año natural en curso.
2. **Given** un cliente llamado "María López García", **When** se busca "maria lopez", **Then**
   aparece en los resultados.
3. **Given** la búsqueda por un NIF o una localidad, total o parcial, **When** se escribe, **Then** el
   listado se reduce a los clientes que coinciden.
4. **Given** los filtros de provincia, tipo (Particular o Empresa) y estado (Activos, Inactivos o
   Todos), **When** se combinan con una búsqueda, **Then** el resultado cumple todas las condiciones
   a la vez.
5. **Given** la ordenación, **When** se elige otra opción (nombre A–Z, nombre Z–A, más recientes o
   más antiguos), **Then** el listado se reordena en consecuencia.
6. **Given** más clientes de los que caben en una página, **When** se navega entre páginas, **Then**
   se ven todos los resultados sin duplicados ni omisiones.
7. **Given** una búsqueda sin resultados, **When** se ejecuta, **Then** se muestra un estado vacío
   explicativo con la opción de limpiar los filtros.
8. **Given** el listado completo, sin búsqueda ni filtros, con una página llena de clientes, **When**
   se mira en una pantalla de 768, 1024, 1280, 1440 o 1536 px de ancho, **Then** cada fila muestra su
   acción "Editar cliente {nombre}" sin desplazar nada, y al pulsarla se abre la ficha de ese
   cliente.

---

### User Story 4 - Desactivar, reactivar y borrar clientes (Priority: P3)

Cuando un cliente deja de serlo, un empleado lo desactiva. El cliente desaparece del listado por
defecto, pero sigue disponible para consulta y puede reactivarse. Un administrador puede borrarlo
definitivamente si nunca ha tenido facturas ni presupuestos.

**Why this priority**: mantiene limpia la cartera sin perder un histórico que la normativa fiscal
obliga a conservar.

**Independent Test**: se desactiva un cliente y se comprueba que sale del listado por defecto, que se
encuentra con el filtro "Inactivos" y que se puede reactivar. Después se borra un cliente sin
documentos como administrador y se comprueba que un empleado no puede hacerlo.

**Acceptance Scenarios**:

1. **Given** un cliente activo, **When** un empleado o un administrador lo desactiva y confirma,
   **Then** desaparece del listado por defecto, deja de contar en "Clientes activos" y queda
   registrado en la auditoría.
2. **Given** un cliente inactivo, **When** se reactiva, **Then** vuelve al listado por defecto y a
   los indicadores.
3. **Given** un cliente sin facturas ni presupuestos, **When** un administrador lo borra y confirma
   explícitamente, **Then** el cliente deja de existir y el borrado queda registrado en la auditoría
   con los datos identificativos del cliente borrado.
4. **Given** un empleado, **When** consulta un cliente, **Then** no se le ofrece la opción de borrado,
   y si la intenta por otra vía, el sistema la rechaza.
5. **Given** un cliente con al menos una factura o un presupuesto (cuando esos módulos existan),
   **When** un administrador intenta borrarlo, **Then** el sistema lo impide y ofrece desactivarlo.

---

### User Story 5 - Gestión de usuarios por el administrador (Priority: P3)

El administrador da de alta a los empleados y a otros administradores, cambia su rol, los desactiva
cuando dejan la joyería, los elimina después si ya no deben figurar en la gestión y les restablece
la contraseña si la olvidan. Las sesiones afectadas se cierran al momento.

**Why this priority**: permite operar a varias personas con responsabilidad individual y trazable,
que es el sentido de la seguridad por usuario.

**Independent Test**: como administrador, se crea un empleado, se inicia sesión con él y se
comprueban sus limitaciones. Después se le restablece la contraseña y se le desactiva, y se
comprueba que su sesión abierta deja de funcionar. Por último se le elimina y se comprueba que
desaparece del listado, que los clientes que dio de alta siguen mostrando su nombre y que su nombre
de usuario puede volver a usarse.

**Acceptance Scenarios**:

1. **Given** un administrador en Configuración → Usuarios, **When** da de alta un usuario con nombre,
   nombre de usuario y rol, **Then** el sistema genera una contraseña temporal que se muestra una
   sola vez para entregarla en persona, y el usuario queda obligado a cambiarla en su primer acceso.
2. **Given** un usuario con sesión abierta, **When** un administrador lo desactiva o le restablece
   la contraseña, **Then** todas las sesiones de ese usuario dejan de ser válidas de inmediato.
3. **Given** un único administrador activo, **When** se intenta desactivarlo o cambiarle el rol a
   Empleado, **Then** el sistema lo impide con un mensaje claro.
4. **Given** un administrador, **When** intenta desactivar su propia cuenta, **Then** el sistema lo
   impide.
5. **Given** un empleado, **When** intenta ver o usar la gestión de usuarios por cualquier vía,
   **Then** se le deniega el acceso.
6. **Given** un nombre de usuario ya existente, sin distinguir mayúsculas, **When** se intenta dar
   de alta otro igual, **Then** el sistema lo impide.
7. **Given** un usuario desactivado, **When** un administrador lo reactiva, **Then** puede volver a
   entrar con su contraseña.
8. **Given** un administrador en Configuración → Auditoría, **When** filtra por un rango de fechas,
   un usuario, un tipo de evento o un cliente, **Then** ve los eventos que cumplen todos los filtros,
   del más reciente al más antiguo, sin poder modificarlos ni borrarlos.
9. **Given** un empleado, **When** intenta consultar la auditoría por cualquier vía, **Then** se le
   deniega el acceso.
10. **Given** un usuario desactivado que dio de alta clientes, **When** un administrador lo elimina
    escribiendo su nombre de usuario para confirmar, **Then**:
    - Desaparece del listado de usuarios y no puede volver a entrar ni reactivarse.
    - Sus clientes y sus eventos de auditoría se conservan sin cambios y muestran su nombre con la
      marca "(eliminado)".
    - La auditoría registra la eliminación.
11. **Given** un usuario activo, **When** un administrador intenta eliminarlo por cualquier vía,
    **Then** el sistema lo impide y le indica que antes debe desactivarlo.
12. **Given** un usuario eliminado, **When** un administrador da de alta otro usuario con el mismo
    nombre de usuario, **Then** el alta se permite, el nuevo usuario entra con normalidad y la
    auditoría distingue a ambos.
13. **Given** la lista de usuarios o una página de la auditoría, **When** un administrador la abre en
    una pantalla de 360, 768, 1024, 1280 o 1440 px de ancho, **Then** cada fila muestra su acción
    (el menú de acciones del usuario o el detalle del evento) sin desplazar nada.

---

### User Story 6 - Mi cuenta: cambio de la propia contraseña (Priority: P4)

Cualquier usuario cambia su contraseña desde "Mi cuenta", en el menú de usuario de la cabecera.

**Why this priority**: es higiene de seguridad básica, pero la aplicación ya es operable sin ella
gracias al restablecimiento por el administrador.

**Independent Test**: un usuario cambia su contraseña y se comprueba que la antigua deja de valer,
que la nueva funciona y que sus otras sesiones abiertas se cierran.

**Acceptance Scenarios**:

1. **Given** un usuario autenticado, **When** introduce su contraseña actual y una nueva que cumple
   la política, **Then** la contraseña cambia, su sesión actual sigue abierta y el resto de sus
   sesiones se cierran.
2. **Given** una contraseña nueva de menos de 12 caracteres, incluida en la lista de contraseñas
   comunes o que contiene el nombre de usuario, **When** se intenta guardar, **Then** el sistema la
   rechaza y explica el motivo.
3. **Given** una contraseña actual incorrecta, **When** se intenta el cambio, **Then** se rechaza.

---

### User Story 7 - Puesta en marcha del entorno de trabajo (Priority: P2)

El responsable técnico levanta el sistema completo (servidor, base de datos y aplicación web) en su
equipo siguiendo una guía breve. Crea el primer administrador con un comando de consola y, en
desarrollo, carga datos de ejemplo ficticios para trabajar y hacer demostraciones.

**Why this priority**: es el cimiento del que dependen todas las demás historias y las pruebas de
extremo a extremo.

**Independent Test**: en un equipo limpio que solo tiene los requisitos previos documentados, se
sigue la guía y se llega a una aplicación funcionando, con un administrador y datos de ejemplo.

**Acceptance Scenarios**:

1. **Given** un equipo con los requisitos previos documentados, **When** se siguen los pasos de la
   guía, **Then** el sistema completo queda en marcha y la base de datos conserva sus datos entre
   reinicios.
2. **Given** el sistema en marcha y sin usuarios, **When** se ejecuta el comando de creación del
   primer administrador, **Then** se crea con contraseña temporal y cambio obligatorio en el primer
   acceso.
3. **Given** un entorno de desarrollo, **When** se ejecuta la carga de datos de ejemplo, **Then**
   aparecen clientes y usuarios ficticios, marcados como tales. La operación puede repetirse sin
   duplicar datos.
4. **Given** un entorno de producción, **When** se intenta cargar datos de ejemplo, **Then** el
   sistema se niega.

---

### User Story 8 - Despliegue seguro en producción (Priority: P3)

El responsable técnico despliega el sistema en un servidor con dominio propio. La aplicación queda
accesible solo por canal cifrado, con certificado obtenido y renovado automáticamente, y la base de
datos no es accesible desde fuera.

**Why this priority**: es imprescindible antes de usar datos reales, pero no bloquea el desarrollo de
las funciones.

**Independent Test**: se despliega en un servidor de pruebas, o en local simulando el dominio, y se
comprueba que todo acceso sin cifrar se redirige al canal cifrado, que la base de datos no responde
desde el exterior y que la aplicación funciona igual que en desarrollo.

**Acceptance Scenarios**:

1. **Given** el sistema desplegado con su dominio, **When** se accede sin cifrado, **Then** se
   redirige automáticamente al acceso cifrado.
2. **Given** el sistema desplegado, **When** se intenta conectar a la base de datos desde fuera del
   servidor, **Then** no hay ningún punto de acceso.
3. **Given** el certificado próximo a caducar, **When** llega el plazo de renovación, **Then** se
   renueva sin intervención manual.
4. **Given** los secretos del despliegue (contraseñas de base de datos y claves), **When** se revisa
   el repositorio, **Then** ninguno está versionado. Solo existe una plantilla con valores de
   ejemplo.

---

### Edge Cases

- **Dos pestañas abiertas y cierre de sesión en una**: la otra deja de funcionar en su siguiente
  acción y lleva al inicio de sesión.
- **Usuario desactivado a mitad de una edición**: la siguiente acción se rechaza. Los datos del
  formulario no se guardan y el usuario vuelve al inicio de sesión.
- **Eliminar un usuario mientras otro administrador lo reactiva**: las dos operaciones no se cruzan.
  Si la reactivación llega antes, la eliminación se rechaza porque el usuario está activo. Si llega
  después, el usuario ya no existe para la gestión.
- **Varios fallos de acceso desde el mismo origen con usuarios distintos**: se aplica el límite por
  origen además del bloqueo por cuenta.
- **Bloqueo de un administrador**: el bloqueo es temporal. Si no hay otro administrador que pueda
  restablecer su contraseña, basta con esperar a que caduque. El comando de consola también permite
  restablecer la contraseña de un administrador como último recurso.
- **Dos usuarios editando a la vez el mismo cliente**: el segundo en guardar recibe un aviso de que
  el cliente ha cambiado desde que lo abrió, y no pisa en silencio los cambios del primero.
- **Identificación introducida con espacios, guiones, puntos o en minúsculas**: se normaliza
  (mayúsculas, sin separadores) antes de validarla y de comprobar duplicados.
- **Empresa identificada con DNI**, como un autónomo: se permite. El tipo de cliente y el tipo de
  identificación son independientes.
- **País distinto de España**: la provincia pasa a ser texto libre opcional y el código postal no se
  valida con el formato español.
- **Nombre o razón social de más de 120 caracteres**: se rechaza. El límite oficial del registro de
  facturación es 120.
- **Fechas y el cambio de año natural**: "Nuevos este año" se calcula con la fecha y el huso horario
  de España peninsular, en el año natural en curso.
- **Pantallas estrechas** (móvil, menos de 768 px): el menú lateral se convierte en cajón, las
  acciones se apilan a ancho completo y la tabla sigue siendo legible sin desplazamiento horizontal
  de la página.
- **Datos largos en una tabla** (nombres, localidades, correos o descripciones extensos, en
  clientes, usuarios o auditoría): la acción de cada fila sigue visible. Si el resto de columnas no
  cabe, se desplaza la tabla dentro de su recuadro y la página no.
- **Caída momentánea del servidor**: la web muestra un mensaje de error comprensible y permite
  reintentar, sin perder lo tecleado en un formulario abierto.

## Requirements *(mandatory)*

### Functional Requirements

#### Acceso y sesiones

- **FR-001**: El sistema DEBE exigir autenticación con nombre de usuario y contraseña para acceder a
  cualquier pantalla o dato, salvo la pantalla de inicio de sesión.
- **FR-002**: El sistema NO DEBE ofrecer autorregistro. Los usuarios los crea un administrador o, en
  el caso del primero, un comando de consola ejecutado en el servidor.
- **FR-003**: Las sesiones DEBEN caducar tras 30 minutos de inactividad y, en cualquier caso, a las
  10 horas de iniciarse. Ambos valores son configurables por el responsable técnico sin cambiar el
  código.
  - **Actividad**: cuenta como actividad cualquier petición autenticada que haga el usuario.
  - **Sin renovación artificial**: la web NO DEBE hacer peticiones automáticas periódicas que
    mantengan la sesión viva.
  - **Varias sesiones**: un usuario puede tener sesiones abiertas en varios equipos a la vez, sin
    límite.
- **FR-004**: Al caducar la sesión, la aplicación DEBE llevar al inicio de sesión y, tras
  identificarse de nuevo, devolver al usuario a la pantalla a la que intentaba acceder.
- **FR-005**: El cierre de sesión DEBE invalidar la sesión en el servidor de forma inmediata, no solo
  en el navegador.
- **FR-006**: Tras 5 intentos fallidos consecutivos sobre una misma cuenta, esta DEBE quedar
  bloqueada 15 minutos.
  - **Fallo consecutivo**: el que se produce sin un acceso correcto intermedio.
  - **Reinicio del contador**: con un acceso correcto, con un restablecimiento de contraseña o al
    expirar el bloqueo.
  - **Límite por origen**: además, DEBE existir un límite de intentos por origen. El origen es la
    dirección del cliente tal como la ve el sistema detrás de su proxy. Por defecto, con 20
    intentos fallidos en una ventana deslizante de 10 minutos se rechazan los nuevos intentos
    desde ese origen hasta que la ventana baja del umbral.
  - **Configuración**: todos los valores son configurables.
- **FR-007**: Los mensajes de fallo de acceso DEBEN ser idénticos para usuario inexistente,
  contraseña incorrecta, cuenta bloqueada y cuenta desactivada, para no revelar qué usuarios existen.
  El rechazo por límite de origen usa un mensaje propio ("Demasiados intentos desde este equipo.
  Inténtalo de nuevo en unos minutos."), que no depende del usuario introducido.
- **FR-008**: La política de contraseñas DEBE exigir entre 12 y 128 caracteres y NO DEBE imponer
  reglas de composición (mayúsculas, símbolos…). DEBE rechazar:
  - Las que coincidan, sin distinguir mayúsculas, con una lista de contraseñas comunes de fuente
    reconocida (research R-7).
  - Las que contengan el nombre de usuario, también sin distinguir mayúsculas.
- **FR-009**: Un usuario con contraseña temporal DEBE cambiarla antes de poder realizar cualquier
  otra acción. Mientras tanto solo puede consultar su propia sesión, cambiar la contraseña y cerrar
  sesión.
- **FR-010**: Las contraseñas NO DEBEN almacenarse ni registrarse en claro en ningún lugar,
  incluidos los registros técnicos y la auditoría. Los identificadores de sesión solo DEBEN
  almacenarse como huella irreversible.
- **FR-011**: Todas las peticiones que modifican datos DEBEN estar protegidas frente a la
  falsificación de peticiones desde otros sitios. Si una petición se rechaza por esa protección, la
  web la trata como una sesión no válida: vuelve a pedir la identificación y conserva la ruta.

#### Usuarios y roles

- **FR-012**: El sistema DEBE soportar exactamente dos roles:
  - **Administrador**: todas las operaciones, incluida la gestión de usuarios y de la configuración.
  - **Empleado**: operación de clientes, sin gestión de usuarios ni borrado definitivo de clientes.
- **FR-013**: La autorización DEBE comprobarse en el servidor en cada operación, con denegación por
  defecto. Ocultar opciones en la interfaz es complementario, nunca suficiente.
- **FR-014**: Un administrador DEBE poder listar usuarios, dar de alta usuarios (nombre visible,
  nombre de usuario único sin distinguir mayúsculas y rol), cambiar su rol, desactivarlos,
  reactivarlos, restablecer su contraseña y eliminar los que estén desactivados (FR-061). La
  unicidad del nombre de usuario se aplica entre los usuarios no eliminados.
- **FR-015**: En el alta y en el restablecimiento, el sistema DEBE generar una contraseña temporal
  que cumpla la política y marcarla como de cambio obligatorio.
  - **Visualización**: se muestra una única vez al administrador, en pantalla, con opción de copiarla
    y aviso de que no volverá a mostrarse.
  - **Caducidad**: la contraseña temporal caduca a las 72 horas si no se ha usado. Después, el
    acceso falla y el administrador tiene que restablecerla de nuevo.
- **FR-016**: Desactivar un usuario, restablecer su contraseña o cambiar su rol DEBE invalidar
  inmediatamente todas sus sesiones. El restablecimiento también DEBE levantar un bloqueo temporal
  vigente.
- **FR-017**: El sistema NO DEBE permitir desactivar ni degradar al último administrador activo.
  Tampoco DEBE permitir que un administrador desactive o elimine su propia cuenta ni cambie su
  propio rol.
- **FR-018**: El comando de consola DEBE permitir crear el primer administrador y restablecer la
  contraseña de un administrador existente como último recurso.
- **FR-019**: Cualquier usuario DEBE poder cambiar su propia contraseña, aportando la actual, desde
  "Mi cuenta". Al hacerlo se cierran sus demás sesiones y se mantiene la actual.
- **FR-061**: Un administrador DEBE poder eliminar un usuario desactivado:
  - **Condición previa**: solo se eliminan usuarios desactivados. Con un usuario activo, la
    operación se rechaza con un mensaje que indica que antes hay que desactivarlo.
  - **Efecto**: el usuario desaparece del listado de usuarios y no puede volver a identificarse,
    reactivarse, editarse ni recibir una contraseña nueva. Se descartan su contraseña y sus
    sesiones. La eliminación es irreversible.
  - **Conservación**: nada de lo que registró se modifica ni se pierde: clientes, eventos de
    auditoría y, en features posteriores, facturas y presupuestos. Todo ello sigue mostrando su
    nombre, con la marca "(eliminado)". Para eso se conservan solo su nombre visible, su nombre de
    usuario y su rol.
  - **Nombre de usuario**: queda libre para un alta nueva (clarificación del 2026-09-28).
  - **Consulta de la auditoría**: el filtro por usuario sigue ofreciendo a los usuarios eliminados,
    marcados como tales, para poder consultar su historial.
  - **Confirmación**: reforzada, escribiendo el nombre de usuario (FR-058).

#### Auditoría

- **FR-020**: El sistema DEBE registrar en una auditoría de solo inserción:
  - Los inicios de sesión correctos y fallidos, los bloqueos, los rechazos por límite de origen y
    los cierres de sesión.
  - Las acciones ejecutadas con el comando de consola, con la consola como actor.
  - Los cambios y restablecimientos de contraseña.
  - El alta, el cambio de rol, la desactivación, la reactivación y la eliminación de usuarios. La
    eliminación guarda en el detalle el nombre, el nombre de usuario y el rol del eliminado.
  - El alta, la edición, la desactivación, la reactivación y el borrado de clientes.
- **FR-021**: Cada evento de auditoría DEBE incluir:
  - El tipo de evento y la fecha y hora con huso horario.
  - El usuario que actúa, o el nombre de usuario intentado en un acceso fallido.
  - El origen de la petición (dirección y agente).
  - El objeto afectado y, en las ediciones, qué campos cambiaron, con el valor anterior y el nuevo
    (nunca contraseñas ni tokens).
- **FR-022**: Los eventos de auditoría NO DEBEN poder modificarse ni borrarse desde la aplicación, y
  la restricción DEBE imponerse también en el almacenamiento de datos, no solo en la aplicación.
  Los eventos se conservan indefinidamente: la aplicación no ofrece ninguna purga.
- **FR-051**: Los administradores DEBEN poder consultar la auditoría en Configuración → Auditoría:
  - Listado paginado de solo lectura, del evento más reciente al más antiguo.
  - Filtros combinables por rango de fechas, usuario, tipo de evento y cliente afectado.
  - Detalle de cada evento, incluidos los campos que cambiaron.

  Los empleados NO DEBEN tener acceso.

#### Clientes: datos y validación

- **FR-023**: Cada cliente DEBE tener:
  - **Tipo**: Particular o Empresa.
  - **Nombre o razón social**: campo único, obligatorio, máximo 120 caracteres
    (ver [Fuentes normativas](#fuentes-normativas-citadas), F-1).
  - **Identificación fiscal obligatoria**, compuesta por:
    - País de la identificación: ISO 3166-1 alfa-2, España por defecto.
    - Tipo de identificación.
    - Número.
- **FR-024**: El tipo NIF solo se admite con país de identificación España. Tiene 9 caracteres y el
  sistema DEBE validarlo según su clase (F-4, F-5):
  - **DNI** (8 dígitos + letra) y **NIE** (X, Y o Z + 7 dígitos + letra): formato y letra de
    control.
  - **NIF de persona jurídica o entidad** (letra de forma jurídica A, B, C, D, E, F, G, H, J, P, Q,
    R, S, U, V, N o W + 7 dígitos + carácter de control) y **NIF K, L o M** (letra + 7
    alfanuméricos + letra): **solo estructura**. Su algoritmo de control no está publicado en fuente
    oficial (Clarifications; research R-20.2).
- **FR-025**: Los tipos de identificación distintos de NIF son los de la lista L7 del registro de
  facturación oficial (F-2), con las combinaciones que admiten las validaciones de la AEAT (F-3):
  - **País España**: además de NIF, solo **03 Pasaporte**.
  - **Estados de la tabla oficial de estructuras NIF-IVA** (UE, más Irlanda del Norte):
    - **02 NIF-IVA**: se valida su estructura según esa tabla y se guarda con el prefijo del
      Estado.
    - **03 Pasaporte**.
    - **04 Documento oficial** de identificación expedido por el país o territorio de residencia.
    - **05 Certificado de residencia**.
    - **06 Otro documento probatorio**.
  - **Resto de países**: 03, 04, 05 o 06.

  Los números de los tipos 03 a 06 tienen un máximo de 20 caracteres (F-1) y no se valida su
  carácter de control.
- **FR-026**: La identificación DEBE normalizarse (mayúsculas, sin espacios, guiones, puntos ni
  barras) antes de validarla. Tras normalizarla, su longitud no puede superar los 20 caracteres (el
  NIF, exactamente 9). DEBE ser única entre todos los clientes, activos e inactivos, por la
  combinación de país, tipo y número.
- **FR-027**: Cada cliente DEBE poder tener estos datos opcionales:
  - Dirección.
  - Código postal y localidad.
  - Provincia.
  - País de residencia (ISO 3166-1 alfa-2, España por defecto).
  - Teléfono.
  - Correo electrónico, con validación de formato.
  - Observaciones, en texto libre.
- **FR-028**: Si el país de residencia es España:
  - El código postal DEBE tener 5 dígitos y corresponder a una provincia.
  - La provincia DEBE asignarse automáticamente a partir del código postal, según la lista oficial
    de provincias.
  - Si no hay código postal, la provincia se elige de esa misma lista.

  Si el país es otro, la provincia es texto libre opcional.

  Si llegan a la vez un código postal y una provincia que no corresponden, el sistema DEBE rechazar
  el guardado con un error en el campo provincia. Al cambiar el país de residencia se descarta el
  dato de provincia que ya no aplica: la de la lista oficial al salir de España, y el texto libre al
  pasar a España.
- **FR-055**: Normas de texto y formato para todos los datos del cliente:
  - **Espacios**: todos los campos de texto se guardan sin espacios iniciales ni finales. Un campo
    opcional vacío equivale a "sin dato".
  - **Teléfono**: solo admite dígitos, espacios, `+`, paréntesis y guiones, con al menos 6 dígitos.
  - **Correo**: se guarda en minúsculas.
- **FR-029**: El sistema DEBE guardar para cada cliente quién lo creó y cuándo, y quién lo modificó
  por última vez y cuándo, y mostrarlo en su ficha.
- **FR-030**: El sistema DEBE detectar la edición concurrente de un mismo cliente e impedir que un
  guardado sobrescriba sin aviso cambios posteriores a la apertura del formulario.
  - **Alcance**: el control se aplica a la edición de datos. Desactivar y reactivar son cambios de
    estado idempotentes: desactivar un cliente ya inactivo, o reactivar uno activo, no produce error
    ni un evento de auditoría nuevo.
  - **Ante un conflicto**: el usuario puede recargar los datos actuales (descartando los suyos) o
    seguir con el formulario abierto para copiar lo que necesite. Nunca se sobrescribe a la fuerza.

#### Clientes: listado, búsqueda e indicadores

- **FR-031**: El listado de clientes DEBE:
  - Estar paginado en el servidor, con 25 elementos por página por defecto y 100 como máximo.
  - Mostrar por fila el nombre con su tipo, la identificación, la localidad, la provincia, el
    teléfono, el correo y las acciones. Las columnas visibles según el ancho se fijan en FR-059.
  - Mantener visibles las acciones de **todas** las filas, sin tener que buscar, filtrar ni
    desplazar, sea cual sea el número de filas o la longitud de sus datos.
  - Devolver una lista vacía con el total real cuando se pide una página posterior a la última.
- **FR-032**: La búsqueda DEBE encontrar coincidencias parciales en el nombre, la identificación y la
  localidad, sin distinguir mayúsculas ni tildes.
  - **Término**: se recorta y tiene como máximo 100 caracteres. Los caracteres especiales se buscan
    literalmente.
  - **Identificación con separadores**: una identificación escrita con separadores (p. ej.
    "12.345.678-Z") encuentra la guardada sin ellos.
- **FR-033**: Filtros y orden del listado:
  - Filtros combinables: provincia, tipo y estado (Activos por defecto, Inactivos, Todos).
  - Ordenación: nombre A–Z (por defecto), nombre Z–A, más recientes, más antiguos. Todas usan un
    criterio de desempate estable, para que la paginación nunca duplique ni omita clientes.
- **FR-034**: La pantalla DEBE mostrar los indicadores:
  - "Clientes activos".
  - "Nuevos este año": clientes creados en el año natural en curso, hora de España peninsular.

  Los indicadores son globales: no dependen de la búsqueda ni de los filtros activos.
- **FR-035**: La columna "Facturas" del mockup NO DEBE mostrarse hasta que exista el módulo de
  facturas.

#### Clientes: ciclo de vida

- **FR-036**: Cualquier usuario autenticado DEBE poder desactivar y reactivar clientes, con
  confirmación previa a la desactivación. Un cliente inactivo sigue siendo consultable y editable.
- **FR-037**: Solo un administrador DEBE poder borrar definitivamente un cliente, con confirmación
  explícita, y solo si el cliente nunca ha tenido facturas ni presupuestos. En esta feature esos
  documentos aún no existen, pero la regla DEBE quedar aplicada y probada para cuando existan.

#### Estructura de la aplicación y diseño

- **FR-038**: La aplicación DEBE presentar:
  - **Un menú lateral a la izquierda** con:
    - El logo de la joyería.
    - El nombre "JOYERÍA BLANCO" con un filete dorado.
    - Las entradas Facturas y Presupuestos, deshabilitadas y marcadas "Próximamente".
    - La entrada Clientes.
    - La entrada Configuración, visible solo para administradores, con las secciones Usuarios y
      Auditoría.
  - **Una cabecera** con:
    - El contexto "Gestión de facturación".
    - La fecha actual en formato largo en español (p. ej. "Martes, 27 de mayo de 2025").
    - Un menú de usuario con sus iniciales y las opciones "Mi cuenta" y "Cerrar sesión".
- **FR-039**: La campana de notificaciones del mockup NO DEBE mostrarse hasta que existan
  notificaciones reales.
- **FR-040**: La interfaz DEBE cumplir `docs/DESIGN.md` (constitución 1.1.0), con solo tema oscuro,
  y adaptarse a sus tres puntos de corte:
  - **Móvil** (menos de 768 px): el menú lateral pasa a ser un cajón y las acciones se apilan a
    ancho completo.
  - **Tableta** (768–1024 px).
  - **Escritorio** (más de 1024 px), con el contenido limitado a 1440 px.
- **FR-041**: El sistema DEBE ofrecer pantallas propias de acceso denegado y de página no
  encontrada, cada una con un título, una explicación breve y un botón para volver a Clientes.
- **FR-056**: El menú de usuario DEBE mostrar sus iniciales, su nombre y su rol.
  - **Iniciales**: la primera letra de las dos primeras palabras del nombre o, si solo hay una, sus
    dos primeras letras, en mayúsculas.
  - **Configuración**: se abre por defecto en Usuarios.
  - **Pantallas fuera del shell**: el cambio obligatorio de contraseña se presenta, como el inicio
    de sesión, sin menú lateral ni cabecera.
- **FR-057**: Estados de las pantallas:
  - **Carga**: toda pantalla con datos del servidor DEBE mostrar un estado de carga que no desplace
    el contenido al terminar (listado, indicadores, ficha, catálogos, usuarios y auditoría).
  - **Error**: ante un error de red o de servidor DEBE mostrarse un aviso comprensible con la opción
    de reintentar, sin perder lo tecleado.
  - **Vacío**: DEBE haber un estado vacío propio tanto para "no hay resultados" como para "todavía no
    hay clientes".
- **FR-058**: Confirmaciones:
  - **Tras cada acción**: guardar, desactivar, reactivar, borrar y operaciones de usuarios DEBEN
    mostrar un aviso breve de confirmación.
  - **Antes de desactivar**: DEBE pedirse confirmación.
  - **Antes de borrar**: la confirmación es reforzada: hay que escribir la identificación del
    cliente.
  - **Antes de eliminar un usuario**: la confirmación es reforzada: hay que escribir su nombre de
    usuario.
  - **Al cerrar con cambios sin guardar**: si se cierra un formulario con cambios, DEBE pedirse
    confirmación antes de descartarlos.
- **FR-059**: Según el ancho de la pantalla, la interfaz DEBE adaptarse así:
  - **Móvil** (menos de 768 px): cada cliente del listado se presenta como una tarjeta con nombre y
    tipo, identificación, localidad y provincia, contacto y acciones. Los filtros y el botón
    "Nuevo cliente" se apilan a ancho completo. Los paneles de alta y edición ocupan la pantalla
    completa.
  - **Tableta** (de 768 a 1023 px): la tabla muestra cliente, identificación, localidad, provincia
    y acciones. El teléfono y el correo quedan en la ficha.
  - **Escritorio de 1024 a 1279 px**: la tabla muestra cliente, identificación, localidad y
    acciones. La provincia, el teléfono y el correo quedan en la ficha, porque el menú lateral fijo
    deja menos espacio útil que en una tableta.
  - **Escritorio de 1280 a 1535 px**: la tabla muestra cliente, identificación, localidad, provincia
    y acciones. El teléfono y el correo quedan en la ficha.
  - **Escritorio de 1536 px o más**: la tabla muestra todas las columnas de FR-031.
  - Estos anchos solo deciden las columnas de la tabla de clientes. El menú lateral y el resto de la
    estructura siguen los puntos de corte de FR-040.
  - **Tablas con acciones por fila** (clientes, usuarios y auditoría), en cualquier ancho en que se
    presenten como tabla: la columna de acciones queda fija en el borde derecho y siempre visible.
    Si el contenido de las demás columnas no cabe, se desplaza la tabla dentro de su recuadro, nunca
    la página.
- **FR-060**: Fechas, países e iconos:
  - **Fechas y horas**: en la ficha y en la auditoría se muestran en formato español, en hora de
    España peninsular (p. ej. "27/05/2025, 14:32").
  - **Países**: se muestran por su nombre en español, en orden alfabético y con España en primer
    lugar.
  - **Logo e iconos sin texto**: tienen un texto alternativo descriptivo (p. ej. "Editar cliente
    María López García").
- **FR-042**: El logo DEBE ser el original, con un tratamiento concreto:
  - **Diseño**: círculo negro con el monograma blanco y el texto "BLANCO JOYEROS".
  - **Limpieza**: fondo transparente, borde circular limpio, sin el brillo gris del borde y
    recortado a su contenido.
  - **Iconos**: se usa también como icono de la pestaña del navegador y de la aplicación.
- **FR-043**: Todos los textos, mensajes de error y formatos de fecha y número de la interfaz DEBEN
  estar en español de España.
- **FR-052**: La interfaz DEBE seguir estas buenas prácticas básicas de accesibilidad, sin objetivo
  formal de cumplimiento de WCAG:
  - Todas las operaciones se pueden hacer solo con teclado.
  - Cada campo de formulario tiene su etiqueta asociada.
  - El foco del teclado siempre es visible.
  - Los errores se anuncian junto al campo afectado.

#### Plataforma, entornos y despliegue

- **FR-044**: El sistema DEBE poder levantarse al completo en un equipo de desarrollo siguiendo una
  guía de inicio rápido. La base de datos DEBE conservar los datos entre reinicios.
- **FR-045**: DEBE existir una carga de datos de ejemplo ficticios (clientes y usuarios de prueba)
  repetible sin duplicados y que se niegue a ejecutarse en producción.
- **FR-046**: En producción, toda la comunicación entre el navegador y el sistema DEBE ir cifrada
  con un certificado que se obtenga y renueve automáticamente. El acceso sin cifrar DEBE redirigirse
  al cifrado. Las respuestas DEBEN:
  - Obligar al navegador a usar siempre el canal cifrado.
  - Restringir la carga de recursos al propio origen.
  - Prohibir que la aplicación se incruste en otros sitios.
  - Impedir la interpretación errónea de tipos de contenido.
  - No enviar la dirección de procedencia a terceros.
- **FR-047**: En producción, la base de datos NO DEBE ser accesible desde fuera del servidor. Con
  sus credenciales, el servicio de la aplicación NO DEBE poder:
  - Crear, alterar ni borrar tablas.
  - Modificar ni borrar eventos de auditoría.
- **FR-048**: Ningún secreto (contraseñas, claves) DEBE estar versionado. El repositorio incluye solo
  una plantilla de configuración con valores de ejemplo y la guía documenta cómo cambiar las
  contraseñas de la base de datos.
- **FR-049**: Los errores mostrados al usuario NO DEBEN revelar detalles internos del sistema. La
  comprobación pública de estado solo indica si el servicio está operativo, sin versiones ni
  detalles.
- **FR-053**: Los registros técnicos NO DEBEN contener contraseñas, tokens ni datos personales de
  clientes (identificación, correo, teléfono, dirección). Solo pueden contener identificadores
  internos.
- **FR-054**: Las sesiones caducadas o revocadas DEBEN purgarse pasados 30 días. No son registros de
  auditoría: la auditoría conserva los eventos de acceso.

#### Calidad

- **FR-050**: La feature DEBE incluir pruebas automáticas de:
  - Las reglas de negocio: validación de identificaciones, política de contraseñas, bloqueo,
    caducidad de sesión, permisos, regla del último administrador, unicidad, borrado condicionado,
    eliminación de usuarios (condición previa, conservación de lo registrado y nombre de usuario
    liberado) e indicadores.
  - La auditoría.
  - Recorridos de extremo a extremo en navegador real: inicio de sesión, alta, edición, filtrado,
    desactivación y reactivación de clientes, gestión de usuarios (incluida su eliminación) y
    sesión caducada.
  - Al menos un recorrido completo, del inicio de sesión al alta de cliente, hecho solo con teclado
    (FR-052).

### Key Entities *(include if feature involves data)*

- **Usuario**: persona que opera el sistema.
  - Nombre visible, nombre de usuario único entre los no eliminados y rol (Administrador o
    Empleado).
  - Estado activo, inactivo o eliminado, e indicador de contraseña temporal. Un usuario eliminado
    se conserva solo como referencia histórica (nombre, nombre de usuario y rol).
  - Contadores de fallos y bloqueo temporal.
  - Fechas de alta y de último acceso.
- **Sesión**: acceso abierto de un usuario desde un navegador.
  - Momento de inicio, última actividad y caducidad.
  - Origen y estado (vigente, cerrada, caducada o revocada).
  - Un usuario puede tener varias sesiones.
- **Evento de auditoría**: registro inalterable de un hecho de seguridad o de un cambio de datos.
  - Tipo, fecha y hora, actor, origen, objeto afectado y detalle de cambios.
  - Referencia al usuario y, en su caso, al cliente.
- **Cliente**: persona física o entidad a la que la joyería presupuesta o factura.
  - Tipo, nombre o razón social e identificación fiscal (país, tipo y número normalizado, única).
  - Datos de contacto y dirección.
  - Estado activo o inactivo y trazabilidad de alta y modificación.
  - En features posteriores lo referenciarán facturas y presupuestos.
- **Provincia** (catálogo): lista oficial de provincias españolas con su código, que coincide con
  los dos primeros dígitos del código postal.
- **País** (catálogo): países según ISO 3166-1 alfa-2.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un empleado localiza un cliente concreto por nombre, NIF o localidad en menos de
  10 segundos desde que abre la pantalla de clientes, con una cartera de 5.000 clientes.
- **SC-002**: Un empleado completa el alta de un cliente con todos sus datos en menos de 2 minutos.
- **SC-003**: El 95 % de las búsquedas y cambios de filtro muestran resultados en menos de 1 segundo,
  con 10.000 clientes. Se mide sobre 100 búsquedas variadas en el entorno local de pruebas de
  extremo a extremo, porque la carga de datos de ejemplo está prohibida en producción (FR-045).
- **SC-004**: En un juego de pruebas de identificaciones españolas:
  - El 100 % de los DNI y NIE con la letra de control incorrecta se rechazan.
  - El 100 % de los NIF con estructura inválida se rechazan.
  - El 100 % de las identificaciones válidas se aceptan.

  El carácter de control de los NIF de entidad y K/L/M no se comprueba (FR-024).
- **SC-005**: Ninguna pantalla ni dato es accesible sin sesión válida. El 100 % de los intentos de
  un empleado de gestionar usuarios o borrar clientes se rechazan en el servidor.
- **SC-006**: Tras desactivar un usuario o restablecer su contraseña, su siguiente acción desde
  cualquier sesión abierta se rechaza en el 100 % de los casos.
- **SC-007**: El 100 % de los eventos enumerados en FR-020 aparecen en la auditoría con actor, fecha
  y origen. Ningún intento de modificarlos o borrarlos prospera, incluidos los intentos directos
  sobre el almacenamiento con las credenciales del servicio y con las del propietario de los datos.
- **SC-008**: La interfaz es utilizable sin desplazamiento horizontal de la página a 360 px, 768 px y
  1440 px de ancho.
- **SC-009**: Todas las pantallas de la feature superan la revisión de conformidad con
  `docs/DESIGN.md`: colores solo de sus tokens, esquinas a 0 px, tipografías y componentes
  definidos.
- **SC-010**: Siguiendo la guía de inicio rápido, una persona con los requisitos previos pone en
  marcha el entorno completo, con administrador y datos de ejemplo, en menos de 15 minutos.
- **SC-011**: En producción, el 100 % de los accesos sin cifrar se redirigen al canal cifrado y un
  análisis público estándar de la configuración de cifrado obtiene una calificación A o superior.
- **SC-012**: Las pruebas de extremo a extremo cubren las historias P1 a P3 y pasan en su totalidad
  antes de cerrar la feature.
- **SC-013**: Tras eliminar un usuario:
  - El 100 % de los clientes y eventos de auditoría que registró se conservan sin cambios y siguen
    mostrando su nombre.
  - El 100 % de sus intentos de acceso se rechazan.
  - El 100 % de los intentos de eliminar un usuario activo se rechazan en el servidor.
- **SC-014**: El 100 % de las filas muestran su acción sin desplazar nada:
  - En el listado completo de clientes (una página de 25, sin búsqueda ni filtros), a 768 px,
    1024 px, 1280 px, 1440 px y 1536 px de ancho. Por debajo de 768 px los clientes se muestran en tarjetas,
    que ya incluyen la acción (FR-059).
  - En la lista de usuarios y en una página completa de la auditoría, a 360 px, 768 px, 1024 px,
    1280 px y 1440 px de ancho.

## Conformidad con el sistema de diseño y desviaciones del mockup

Conforme a la constitución 1.1.0 ("Sistema de diseño"), el mockup es orientativo y mandan
`docs/DESIGN.md` y esta spec. Diferencias deliberadas respecto al mockup:

| Elemento del mockup | Decisión en esta feature | Motivo |
|---|---|---|
| Menú lateral a la derecha | Menú lateral a la **izquierda** | Decisión del responsable (2026-09-26): más práctico y natural |
| Marca "JOYERÍA BLANCO" repetida en la cabecera | La marca va en el menú lateral y la cabecera muestra el contexto "Gestión de facturación" | Evitar duplicar la marca al mover el menú |
| Columna "Facturas" | Oculta hasta que exista el módulo de facturas | Decisión del responsable: no mostrar datos que aún no existen |
| Campana de notificaciones | Oculta hasta que existan notificaciones | Decisión del responsable |
| Botón "Nuevo cliente" con letra serif en caja mixta | Manrope en mayúsculas con espaciado (botón primario de DESIGN.md) | DESIGN.md prevalece sobre el mockup |
| Cabeceras de la tabla en caja mixta | Mayúsculas con espaciado (`label-md`) | DESIGN.md prevalece sobre el mockup |
| Nombre del cliente en la tabla con letra serif | Manrope (`title-md`) con el tipo en `label-sm` en mayúsculas y color `primary` | DESIGN.md reserva Bodoni para titulares y cifras; los datos tabulares van en Manrope |
| Teléfono, correo y provincia en la tabla en cualquier ancho de escritorio | Teléfono y correo en la tabla a partir de 1536 px; provincia oculta entre 1024 y 1279 px. Lo que no aparece, en la ficha (FR-059) | Con el menú lateral a la izquierda esas columnas no caben: la de acciones, fija, las taparía (medido en research R-22; ajuste de cierre, 2026-09-28) |

Desviaciones de `docs/DESIGN.md`: **ninguna**.

## Fuentes normativas citadas

- **F-1**: AEAT, *Diseños de registro VERI\*FACTU* (`DsRegistroVeriFactu.xlsx`), **versión 1.0**
  (2024-10-28, versión oficial tras la Orden HAC/1177/2024).
  - URL:
    `https://www.agenciatributaria.es/static_files/AEAT_Desarrolladores/EEDD/IVA/VERI-FACTU/DsRegistroVeriFactu.xlsx`.
  - Consulta: 2026-09-27. SHA-256 del fichero consultado:
    `40ce191aa1def6e44a5f1e86d7ece727258745b34e3fe4d6abe1468252dac2ca`.
  - Pestaña "2) D. Registro Facturación Alta", bloque `Destinatarios/IDDestinatario` (filas 32–36):
    - `NombreRazon`: alfanumérico (120).
    - `NIF`: FormatoNIF (9).
    - `IDOtro/CodigoPais`: alfanumérico (2), ISO 3166-1 alpha-2.
    - `IDOtro/IDType`: alfanumérico (2), lista L7.
    - `IDOtro/ID`: alfanumérico (20).
- **F-2**: mismo documento, pestaña "6) Listas", **lista L7** (filas 47–55):
  - 02 NIF-IVA.
  - 03 Pasaporte.
  - 04 Documento oficial de identificación expedido por el país o territorio de residencia.
  - 05 Certificado de residencia.
  - 06 Otro documento probatorio.
  - 07 No censado.
- **F-3**: AEAT, *Validaciones y errores VERI\*FACTU*, **v1.2.2** (08/04/2026).
  - Apartado 3.1.3, punto 13, p. 10: reglas de `IDOtro` del destinatario.
  - Nota (1), pp. 17–18: tabla de estructuras NIF-IVA.
  - URL, SHA-256 y transcripción en research R-20.1.
- **F-4**: composición del NIF, verificada en el BOE:
  - RD 1065/2007 (BOE-A-2007-15984), arts. 19, 20 y 22.
  - Orden EHA/451/2008 (BOE-A-2008-3580), arts. 2–5, en la redacción de la Orden HAP/5/2016
    (BOE-A-2016-358).
  - Orden INT/2058/2008 (BOE-A-2008-12050).
- **F-5**: algoritmo de la letra del DNI y del NIE, en web oficial: Ministerio del Interior y
  Dirección General de Ordenación del Juego (research R-20.2). No está publicado en el BOE.
- **F-6**: INE, *Relación de provincias con sus códigos*, a 1 de enero de 2026 (research R-20.3).
- **F-7**: correspondencia entre código postal y provincia:
  - Orden de 23/01/1984 (BOE-A-1984-3487), art. 2.
  - Orden de 27/09/1995 (BOE-A-1995-21835) para Ceuta (51) y Melilla (52).
  - La equivalencia con los códigos INE es una interpretación documentada (research R-20.3).
- **Preguntas abiertas** para features posteriores, que no bloquean esta: ver research R-20.4.

## Fuera de alcance

- Facturas, presupuestos, generación de PDF, registros Verifactu y comunicación con la AEAT. En
  esta feature solo se alinean los datos identificativos del cliente con el formato oficial.
- Doble factor de autenticación. Queda como mejora futura.
- Recuperación de contraseña por correo electrónico y cualquier envío de correo.
- Exportar la auditoría. En esta feature solo se consulta en pantalla.
- Integración continua y copias de seguridad automáticas.
- Validación de identificaciones contra el censo de la AEAT o contra VIES.
- La aplicación Android.
- Tema claro.

## Assumptions

- La joyería tiene pocos usuarios simultáneos (menos de 10) y una cartera del orden de miles de
  clientes. Los objetivos de rendimiento se fijan para 10.000 clientes.
- El tipo "07 No censado" de la lista L7 no se ofrece en la ficha. Según las validaciones de la AEAT
  (F-3), es un NIF correcto de persona física que no figura en el censo. Por tanto, ese cliente se
  guarda con su NIF, y declararlo como 07 es una decisión de la generación del registro de
  facturación (feature de facturas).
- La exclusión de copias de seguridad automáticas es un **riesgo asumido** para esta feature. DEBEN
  existir antes de cargar datos reales en producción.
- La fiabilidad del límite por origen depende de que la dirección real del cliente llegue
  correctamente a través del proxy de producción.
- Ver o cerrar las propias sesiones abiertas en otros equipos queda fuera de alcance.
- Los umbrales de bloqueo (5 fallos consecutivos, 15 minutos de bloqueo y 20 intentos en 10
  minutos por origen) siguen las prácticas habituales de seguridad y son configurables. Los tiempos
  de sesión están confirmados en Clarifications.
- El nombre de usuario se usa solo para identificarse. No es un correo, porque no hay envío de
  correos.
- La contraseña temporal la genera el sistema y el administrador se la entrega en persona. El
  administrador no la elige.
- Un cliente inactivo se puede consultar y editar. Cuando existan facturas, no se podrá elegir para
  documentos nuevos.
- El derecho de supresión del RGPD se atiende con el borrado definitivo cuando no hay documentos.
  Cuando los hay, prevalece la obligación legal de conservación.
- De un usuario eliminado se conservan su nombre, su nombre de usuario y su rol porque la
  trazabilidad lo exige: la auditoría es inalterable y los futuros registros de facturación
  tampoco podrán modificarse. Su contraseña y sus sesiones se descartan.
- Los datos de ejemplo son ficticios y no reproducen personas reales.
- El entorno de producción es un único servidor con dominio propio, gestionado por el responsable
  técnico.
- Esta feature no toca numeración, importes, huellas ni conversión presupuesto → factura, así que no
  le aplica ninguno de los cuatro tests obligatorios del principio VII de la constitución.
