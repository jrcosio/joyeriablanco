# Contrato de la consola — feature 004

Comandos de `joyeria` (Typer). Se ejecutan en el contenedor de la API, con el entorno del servicio,
el certificado incluido. Ninguno genera los eventos de inicio y fin, que son del servicio (research
R-8). En la auditoría figuran con el actor «Consola», como en 002.

## `verificar-cadena` (002, ampliado)

```text
joyeria verificar-cadena [--desde N] [--hasta M]
```

- **Qué comprueba**: registros de facturación y de evento, en sus cuatro comprobaciones (FR-017).
  `--desde` y `--hasta` acotan el rango de secuencias de facturación; sin ellos se comprueba la
  cadena entera.
- **Qué genera**: los eventos 03 y 05 y, por cada anomalía, un 04 o un 06.
- **Salida**:
  - íntegra: «Cadena íntegra (N registros de facturación y M de evento)», con código 0;
  - con anomalías: la primera, con su tipo y su secuencia, y el total, con código 1.
- **Sin certificado utilizable**: los eventos no se pueden firmar. La comprobación se hace igual,
  se dice que sus eventos quedan pendientes y termina con código 2.

## `exportar-registros`

```text
joyeria exportar-registros --tipo facturacion|eventos --desde AAAA-MM-DD --hasta AAAA-MM-DD --destino RUTA.zip
```

- **Qué hace**: el mismo ZIP y el mismo evento que la web ([exportacion.md](exportacion.md)).
- **Salida**: la ruta, el número de registros y el SHA-256 del ZIP, con código 0.
- **Errores**:
  - periodo sin registros: «No hay registros en ese periodo», código 1, sin fichero;
  - fechas no válidas, «desde» posterior a «hasta» o un `--tipo` desconocido: código 2;
  - sin certificado utilizable, con el que se firma su evento: código 3, sin fichero.

## `generar-certificado-pruebas`

```text
joyeria generar-certificado-pruebas --destino RUTA.p12 --contrasena TEXTO [--dias 365]
```

- **Qué hace**: crea un PKCS#12 autofirmado, RSA de 2048 bits, con el sujeto marcado
  `O=PRUEBAS - SIN VALIDEZ` y el NIF del emisor de la configuración. Si todavía no hay BD o emisor
  (el E2E lo genera antes de reconstruir la BD), usa un NIF ficticio.
- **En producción**: se niega a ejecutarse (código 1). Un certificado así no es utilizable en
  producción (`de_pruebas_en_produccion`).

## `estado-certificado`

```text
joyeria estado-certificado
```

- **Salida**: el estado del certificado (FR-003): titular, emisor, validez, días restantes y, si no
  es utilizable, el motivo. Nunca la contraseña.
- **Código**:
  - 0 si es utilizable;
  - 1 si no lo es;
  - 3 si es utilizable pero caduca en 30 días o menos.
- **Para qué sirve**: lo usa `deploy/verificar-produccion.sh` para comprobar el certificado
  instalado.
