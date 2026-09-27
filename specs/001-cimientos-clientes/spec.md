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

**Referencias**: mockup [`assets/mockup-clientes.png`](assets/mockup-clientes.png) (orientativo) ·
sistema de diseño [`docs/DESIGN.md`](../../docs/DESIGN.md) (normativo, constitución 1.1.0)

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
2. **Given** el formulario de alta, **When** se introduce un DNI, NIE o NIF de entidad con el
   carácter de control incorrecto, **Then** el sistema no guarda y señala el campo con un mensaje
   en español.
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
cuando dejan la joyería y les restablece la contraseña si la olvidan. Las sesiones afectadas se
cierran al momento.

**Why this priority**: permite operar a varias personas con responsabilidad individual y trazable,
que es el sentido de la seguridad por usuario.

**Independent Test**: como administrador, se crea un empleado, se inicia sesión con él y se
comprueban sus limitaciones. Después se le restablece la contraseña y se le desactiva, y se
comprueba que su sesión abierta deja de funcionar.

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
- **FR-004**: Al caducar la sesión, la aplicación DEBE llevar al inicio de sesión y, tras
  identificarse de nuevo, devolver al usuario a la pantalla a la que intentaba acceder.
- **FR-005**: El cierre de sesión DEBE invalidar la sesión en el servidor de forma inmediata, no solo
  en el navegador.
- **FR-006**: Tras 5 intentos fallidos consecutivos sobre una misma cuenta, esta DEBE quedar
  bloqueada 15 minutos. Además, DEBE existir un límite de intentos por origen, con 20 intentos en 10
  minutos como valor por defecto. Todos los valores son configurables.
- **FR-007**: Los mensajes de fallo de acceso DEBEN ser idénticos para usuario inexistente,
  contraseña incorrecta, cuenta bloqueada y cuenta desactivada, para no revelar qué usuarios existen.
- **FR-008**: La política de contraseñas DEBE exigir entre 12 y 128 caracteres, rechazar las
  contraseñas de una lista de contraseñas comunes y las que contengan el nombre de usuario, y NO
  DEBE imponer reglas de composición (mayúsculas, símbolos…).
- **FR-009**: Un usuario con contraseña temporal DEBE cambiarla antes de poder realizar cualquier
  otra acción.
- **FR-010**: Las contraseñas NO DEBEN almacenarse ni registrarse en claro en ningún lugar,
  incluidos los registros técnicos y la auditoría.
- **FR-011**: Todas las peticiones que modifican datos DEBEN estar protegidas frente a la
  falsificación de peticiones desde otros sitios.

#### Usuarios y roles

- **FR-012**: El sistema DEBE soportar exactamente dos roles:
  - **Administrador**: todas las operaciones, incluida la gestión de usuarios y de la configuración.
  - **Empleado**: operación de clientes, sin gestión de usuarios ni borrado definitivo de clientes.
- **FR-013**: La autorización DEBE comprobarse en el servidor en cada operación, con denegación por
  defecto. Ocultar opciones en la interfaz es complementario, nunca suficiente.
- **FR-014**: Un administrador DEBE poder listar usuarios, dar de alta usuarios (nombre visible,
  nombre de usuario único sin distinguir mayúsculas y rol), cambiar su rol, desactivarlos,
  reactivarlos y restablecer su contraseña.
- **FR-015**: En el alta y en el restablecimiento, el sistema DEBE generar una contraseña temporal
  que cumpla la política, mostrarla una única vez al administrador y marcarla como de cambio
  obligatorio.
- **FR-016**: Desactivar un usuario o restablecer su contraseña DEBE invalidar inmediatamente todas
  sus sesiones. El restablecimiento también DEBE levantar un bloqueo temporal vigente.
- **FR-017**: El sistema NO DEBE permitir desactivar ni degradar al último administrador activo, ni
  que un administrador desactive su propia cuenta.
- **FR-018**: El comando de consola DEBE permitir crear el primer administrador y restablecer la
  contraseña de un administrador existente como último recurso.
- **FR-019**: Cualquier usuario DEBE poder cambiar su propia contraseña, aportando la actual, desde
  "Mi cuenta". Al hacerlo se cierran sus demás sesiones y se mantiene la actual.

#### Auditoría

- **FR-020**: El sistema DEBE registrar en una auditoría de solo inserción:
  - Los inicios de sesión correctos y fallidos, los bloqueos y los cierres de sesión.
  - Los cambios y restablecimientos de contraseña.
  - El alta, el cambio de rol, la desactivación y la reactivación de usuarios.
  - El alta, la edición, la desactivación, la reactivación y el borrado de clientes.
- **FR-021**: Cada evento de auditoría DEBE incluir:
  - El tipo de evento y la fecha y hora con huso horario.
  - El usuario que actúa, o el nombre de usuario intentado en un acceso fallido.
  - El origen de la petición (dirección y agente).
  - El objeto afectado y, en las ediciones, qué campos cambiaron.
- **FR-022**: Los eventos de auditoría NO DEBEN poder modificarse ni borrarse desde la aplicación, y
  la restricción DEBE imponerse también en el almacenamiento de datos, no solo en la aplicación.

#### Clientes: datos y validación

- **FR-023**: Cada cliente DEBE tener:
  - **Tipo**: Particular o Empresa.
  - **Nombre o razón social**: campo único, obligatorio, máximo 120 caracteres
    (ver [Fuentes normativas](#fuentes-normativas-citadas), F-1).
  - **Identificación fiscal obligatoria**, compuesta por:
    - País de la identificación: ISO 3166-1 alfa-2, España por defecto.
    - Tipo de identificación.
    - Número.
- **FR-024**: Si el país de la identificación es España, el tipo DEBE ser NIF (DNI, NIE o NIF de
  persona jurídica o entidad), de 9 caracteres, y el sistema DEBE verificar su formato y su carácter
  de control conforme a la normativa de composición del NIF.
- **FR-025**: Si el país de la identificación no es España, el tipo DEBE ser uno de los admitidos
  por el registro de facturación oficial (lista L7, F-2):
  - 02 NIF-IVA.
  - 03 Pasaporte.
  - 04 Documento oficial de identificación expedido por el país o territorio de residencia.
  - 05 Certificado de residencia.
  - 06 Otro documento probatorio.

  El número tiene un máximo de 20 caracteres (F-1) y no se valida su carácter de control.
- **FR-026**: La identificación DEBE normalizarse (mayúsculas, sin espacios, guiones ni puntos) y ser
  única entre todos los clientes, activos e inactivos, por la combinación de país, tipo y número.
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
- **FR-029**: El sistema DEBE guardar para cada cliente quién lo creó y cuándo, y quién lo modificó
  por última vez y cuándo, y mostrarlo en su ficha.
- **FR-030**: El sistema DEBE detectar la edición concurrente de un mismo cliente e impedir que un
  guardado sobrescriba sin aviso cambios posteriores a la apertura del formulario.

#### Clientes: listado, búsqueda e indicadores

- **FR-031**: El listado de clientes DEBE:
  - Estar paginado en el servidor.
  - Mostrar por fila el nombre con su tipo, la identificación, la localidad, la provincia, el
    teléfono, el correo y las acciones.
- **FR-032**: La búsqueda DEBE encontrar coincidencias parciales en el nombre, la identificación y la
  localidad, sin distinguir mayúsculas ni tildes.
- **FR-033**: Filtros y orden del listado:
  - Filtros combinables: provincia, tipo y estado (Activos por defecto, Inactivos, Todos).
  - Ordenación: nombre A–Z (por defecto), nombre Z–A, más recientes, más antiguos.
- **FR-034**: La pantalla DEBE mostrar los indicadores:
  - "Clientes activos".
  - "Nuevos este año": clientes creados en el año natural en curso, hora de España peninsular.
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
    - La entrada Configuración, visible solo para administradores.
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
  encontrada.
- **FR-042**: El logo DEBE ser el original, con un tratamiento concreto:
  - **Diseño**: círculo negro con el monograma blanco y el texto "BLANCO JOYEROS".
  - **Limpieza**: fondo transparente, borde circular limpio, sin el brillo gris del borde y
    recortado a su contenido.
  - **Iconos**: se usa también como icono de la pestaña del navegador y de la aplicación.
- **FR-043**: Todos los textos, mensajes de error y formatos de fecha y número de la interfaz DEBEN
  estar en español de España.

#### Plataforma, entornos y despliegue

- **FR-044**: El sistema DEBE poder levantarse al completo en un equipo de desarrollo siguiendo una
  guía de inicio rápido. La base de datos DEBE conservar los datos entre reinicios.
- **FR-045**: DEBE existir una carga de datos de ejemplo ficticios (clientes y usuarios de prueba)
  repetible sin duplicados y que se niegue a ejecutarse en producción.
- **FR-046**: En producción, toda la comunicación entre el navegador y el sistema DEBE ir cifrada
  con un certificado que se obtenga y renueve automáticamente. El acceso sin cifrar DEBE redirigirse
  al cifrado.
- **FR-047**: En producción, la base de datos NO DEBE ser accesible desde fuera del servidor, y el
  servicio de la aplicación DEBE operar con permisos de datos mínimos, sin capacidad de alterar la
  estructura de la base de datos.
- **FR-048**: Ningún secreto (contraseñas, claves) DEBE estar versionado. El repositorio incluye solo
  una plantilla de configuración con valores de ejemplo.
- **FR-049**: Los errores mostrados al usuario NO DEBEN revelar detalles internos del sistema.

#### Calidad

- **FR-050**: La feature DEBE incluir pruebas automáticas de:
  - Las reglas de negocio: validación de identificaciones, política de contraseñas, bloqueo,
    caducidad de sesión, permisos, regla del último administrador, unicidad, borrado condicionado e
    indicadores.
  - La auditoría.
  - Recorridos de extremo a extremo en navegador real: inicio de sesión, alta, edición, filtrado,
    desactivación y reactivación de clientes, gestión de usuarios y sesión caducada.

### Key Entities *(include if feature involves data)*

- **Usuario**: persona que opera el sistema.
  - Nombre visible, nombre de usuario único y rol (Administrador o Empleado).
  - Estado activo o inactivo e indicador de contraseña temporal.
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
  con 10.000 clientes.
- **SC-004**: En un juego de pruebas de identificaciones españolas, el 100 % de las que tienen el
  carácter de control incorrecto se rechazan y el 100 % de las válidas se aceptan.
- **SC-005**: Ninguna pantalla ni dato es accesible sin sesión válida. El 100 % de los intentos de
  un empleado de gestionar usuarios o borrar clientes se rechazan en el servidor.
- **SC-006**: Tras desactivar un usuario o restablecer su contraseña, su siguiente acción desde
  cualquier sesión abierta se rechaza en el 100 % de los casos.
- **SC-007**: El 100 % de los eventos enumerados en FR-020 aparecen en la auditoría con actor, fecha
  y origen, y ningún intento de modificarlos o borrarlos prospera.
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
- **Pendientes de verificación en `/speckit.plan`** (research.md). Si no se pueden verificar en
  fuente oficial, pasan a pregunta abierta:
  - La normativa de composición y el cálculo del carácter de control del NIF (DNI, NIE y NIF de
    personas jurídicas y entidades).
  - Las reglas de validación de la AEAT para `IDOtro` (combinaciones admitidas de país y tipo),
    según *Validaciones y errores* v1.2.2.
  - La lista oficial de provincias y la correspondencia con el código postal.

## Fuera de alcance

- Facturas, presupuestos, generación de PDF, registros Verifactu y comunicación con la AEAT. En
  esta feature solo se alinean los datos identificativos del cliente con el formato oficial.
- Doble factor de autenticación. Queda como mejora futura.
- Recuperación de contraseña por correo electrónico y cualquier envío de correo.
- Consulta de la auditoría desde la interfaz. En esta feature la auditoría se registra y se consulta
  con herramientas de operación.
- Integración continua y copias de seguridad automáticas.
- Validación de identificaciones contra el censo de la AEAT o contra VIES.
- La aplicación Android.
- Tema claro.

## Assumptions

- La joyería tiene pocos usuarios simultáneos (menos de 10) y una cartera del orden de miles de
  clientes. Los objetivos de rendimiento se fijan para 10.000 clientes.
- El tipo "07 No censado" de la lista L7 no se ofrece, porque el responsable exige identificación
  fiscal siempre. Candidato a confirmar en `/speckit.clarify`.
- La identificación es única por país, tipo y número. Una misma persona o entidad no se duplica
  aunque tenga varias direcciones. Candidato a confirmar en `/speckit.clarify`.
- Los tiempos de sesión (30 minutos de inactividad y 10 horas en total) y los umbrales de bloqueo
  (5 fallos o 15 minutos; 20 intentos en 10 minutos por origen) son valores por defecto razonables y
  configurables. Candidatos a confirmar en `/speckit.clarify`.
- El nombre de usuario se usa solo para identificarse. No es un correo, porque no hay envío de
  correos.
- La contraseña temporal la genera el sistema y el administrador se la entrega en persona. El
  administrador no la elige.
- Un cliente inactivo se puede consultar y editar. Cuando existan facturas, no se podrá elegir para
  documentos nuevos.
- El derecho de supresión del RGPD se atiende con el borrado definitivo cuando no hay documentos.
  Cuando los hay, prevalece la obligación legal de conservación.
- Los datos de ejemplo son ficticios y no reproducen personas reales.
- El entorno de producción es un único servidor con dominio propio, gestionado por el responsable
  técnico.
- Esta feature no toca numeración, importes, huellas ni conversión presupuesto → factura, así que no
  le aplica ninguno de los cuatro tests obligatorios del principio VII de la constitución.
