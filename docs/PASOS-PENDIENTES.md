# Pasos pendientes para facturar en real

Situación a 2026-10-04. La Fase 1 (facturación y presupuestos) está terminada y fusionada en
`main`, con las features 001 a 005. No hay ninguna otra prevista en `specs/`. Lo que queda es
preparar la puesta en marcha, y casi todo depende del responsable.

Marca cada paso al completarlo.

## 1. Certificado real (sin él no se factura)

- [ ] Conseguir el certificado electrónico cualificado (`.p12`) de la empresa o de su
      representante.
- [ ] Instalarlo en el servidor según el apartado 3 de
      [`specs/004-no-verifactu/quickstart.md`](../specs/004-no-verifactu/quickstart.md):
      - ruta en `CERTIFICADO_FICHERO` y contraseña en `CERTIFICADO_CONTRASENA`;
      - permisos: `chown 10001 certificado.p12 && chmod 0400 certificado.p12`.
- [ ] Comprobarlo con `joyeria estado-certificado` o con `deploy/verificar-produccion.sh`.

Con él se firma cada factura y cada evento. En producción la API rechaza el certificado de
pruebas, así que sin el real no se puede facturar.

## 2. Validar la firma en VALIDe

- [ ] Exportar un periodo desde «Registro fiscal → Exportar».
- [ ] Subir uno de los XML a <https://valide.redsara.es>.
- [ ] Comprobar que reconoce una firma XAdES-EPES válida, con la política de la AGE.

Es la única comprobación externa de la firma: los tests ya la comparan con el ejemplo oficial de
la AEAT (pregunta Q-12 de
[`specs/004-no-verifactu/research.md`](../specs/004-no-verifactu/research.md)). Con el
certificado de pruebas, VALIDe avisará de que no es de confianza; es lo esperado.

## 3. Declaración responsable

- [ ] Poner en el `.env` de producción los datos reales: `SIF_PRODUCTOR_NOMBRE`,
      `SIF_PRODUCTOR_NIF`, `SIF_PRODUCTOR_DIRECCION`, `SIF_DECLARACION_FECHA` y
      `SIF_DECLARACION_LUGAR`. Sin ellos, la API no arranca en producción.
- [ ] Descargar el PDF desde «Acerca del sistema» y archivarlo en
      [`docs/declaraciones/`](declaraciones/README.md), siguiendo su procedimiento.

La norma obliga a conservar la declaración de cada versión (RRSIF, art. 13.3).

## 4. Asesoría (antes de la primera factura real)

Decisiones tomadas en el desarrollo que debe confirmar un profesional:

- [ ] **No poder enviar los registros a la AEAT** (Q-13). Se eligió la modalidad No VERI\*FACTU
      sin esa capacidad. Es el principal riesgo normativo asumido (spec de la 004, «Riesgo
      normativo asumido»).
- [ ] **La fecha de expedición libre** (Q-9), incluso anterior al día de emisión, y sin orden
      entre fecha y número dentro de la serie.
- [ ] **El oro de inversión**: clave de régimen 04, exención E6 y la mención del art. 140 bis de
      la Ley 37/1992, además de la clave 01 para las ventas normales (Q-10).
- [ ] **El texto del pie de factura**, como la cláusula de protección de datos: lo aporta la
      joyería y el sistema solo lo imprime.

Q-9 y Q-10 están en
[`specs/002-facturas/research.md`](../specs/002-facturas/research.md) (R-17). Q-13, en
[`specs/004-no-verifactu/research.md`](../specs/004-no-verifactu/research.md) (R-16).

## 5. Servidor de producción

- [ ] Desplegar con `docker-compose.prod.yml` y el dominio real (README, «Despliegue en
      producción»).
- [ ] `AEAT_ENTORNO=pruebas` mientras se valida y `produccion` al facturar de verdad. Fija la
      dirección de cotejo del QR.
- [ ] Reloj sincronizado por NTP (`timedatectl`). La norma admite como máximo un minuto de
      desfase (Orden HAC/1177/2024, art. 7.f).
- [ ] Copias de seguridad configuradas **antes de cargar datos reales**, por la obligación legal
      de conservación. El sistema aún no las hace solo; el README tiene un procedimiento manual
      probado («Copias de seguridad»).

## 6. Menor

- [ ] Cronometrar con alguien de la tienda una factura de tres líneas. El objetivo es menos de
      2 minutos (SC-001 de la 002); el recorrido automático tarda unos 3,5 s.

## Plazo de adaptación

Disposición final cuarta del RD 1007/2023, en la redacción del RD-ley 15/2025:

- Si Joyería Blanco tributa por el Impuesto sobre Sociedades: **antes del 1 de enero de 2027**.
- Si es autónomo: antes del 1 de julio de 2027.

## Próximo desarrollo (propuesta)

- **Copias de seguridad automáticas.** Hoy son manuales y el README lo advierte. Sería una feature
  nueva, con su ciclo de Spec Kit.
