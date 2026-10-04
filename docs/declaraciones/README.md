# Declaraciones responsables del sistema

RRSIF (RD 1007/2023), art. 13.3: la persona o entidad productora conserva las declaraciones
responsables de **todas las versiones** del sistema. Joyería Blanco es productora y usuaria del
sistema (uso propio, constitución 2.4.0), así que las archiva aquí.

## Procedimiento, en cada versión que se despliega

1. Antes de desplegar, comprobar en el `.env` de producción los datos de la declaración:
   - `SIF_PRODUCTOR_NOMBRE`, `SIF_PRODUCTOR_NIF` y `SIF_PRODUCTOR_DIRECCION`;
   - `SIF_DECLARACION_FECHA` (la de la suscripción) y `SIF_DECLARACION_LUGAR` (localidad y país,
     en ese orden).

   La API no arranca en producción sin ellos.
2. Desplegar y abrir «Acerca del sistema» → «Descargar PDF».
3. Revisar que la versión, la fecha y el lugar son los correctos y guardar el PDF aquí, con su
   nombre: `declaracion-responsable-<versión>.pdf`.
4. Añadirlo a git en el mismo commit que la etiqueta de la versión. Nunca se borra ni se sustituye
   el de una versión anterior.

El texto sigue el art. 15.1 de la Orden HAC/1177/2024 (letras a a l) y lo genera
`backend/app/services/sistema.py`.

## Versiones

| Versión | Fecha de suscripción | Fichero |
|---|---|---|
| 0.4.0 | *(al desplegar en producción)* | *(pendiente)* |
