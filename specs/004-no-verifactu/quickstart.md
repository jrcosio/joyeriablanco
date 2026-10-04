# Quickstart — 004 Modalidad No VERI\*FACTU

Guía de validación. La puesta en marcha general está en `specs/001-cimientos-clientes/quickstart.md`.

## Requisitos previos

- La pila de desarrollo en marcha (`docker compose up -d --build`) y las migraciones aplicadas
  (`alembic upgrade head`, hasta la 0009).
- Un certificado de prueba. `docker-compose.yml` ya apunta `CERTIFICADO_RUTA` y
  `CERTIFICADO_CONTRASENA` a `/app/var/certificados/pruebas.p12`, que está en `backend/var/`, fuera
  de git y montado en el contenedor:

  ```bash
  docker compose exec api joyeria generar-certificado-pruebas \
      --destino /app/var/certificados/pruebas.p12 --contrasena pruebas
  docker compose restart api        # el evento de inicio ya sale firmado
  ```

- Datos de desarrollo regenerados. Los de antes de la 004 están en VERI\*FACTU y, con registros, la
  modalidad queda bloqueada:

  ```bash
  docker compose down -v && docker compose up -d --build
  docker compose exec api alembic upgrade head
  docker compose exec api joyeria crear-admin --usuario admin --nombre "Administrador"
  docker compose exec api joyeria cargar-datos-ejemplo
  ```

## 1. Pruebas automáticas

```bash
# Backend (desde backend/)
uv run pytest                     # incluye firma, eventos, integridad, exportación y XSD
uv run pytest -k "firma or eventos or integridad or exportacion"
uv run pytest -m lento            # integridad y exportación con 20.000 registros (SC-005 y SC-006)
uv run ruff check . && uv run ruff format --check . && uv run mypy .
uv run joyeria verificar-cadena   # registros de facturación y de evento

# Web (desde joyeriablanco_web/)
uv --directory ../backend run joyeria exportar-openapi && npm run gen:api
npm run lint && npm run typecheck && npm run test && npm run build && npm run check:tokens
npx playwright test               # incluye e2e/registro-fiscal.spec.ts
```

Tests de cobertura obligatoria (constitución VII, 2.4.0):
- Numeración y encadenamiento de 002, en verde con la firma.
- Firma de los registros: se verifica y sigue la política EPES de F-14.
- Encadenamiento y firma de los registros de evento, también con eventos simultáneos.
- XML de alta, de anulación y de evento, válido contra los XSD oficiales guardados.

## 2. Validaciones manuales clave

| # | Paso | Resultado esperado | Requisito |
|---|---|---|---|
| 1 | Configuración → Facturación | Modalidad fija «No VERI\*FACTU». Tarjeta del certificado de prueba con su titular y su caducidad | FR-001, FR-003 |
| 2 | Emitir una factura y abrir su consulta | El registro dice «Firmado» con el titular, «Huella correcta» y «Firma correcta» | FR-005 a FR-011 |
| 3 | Exportar el día de hoy en «Registro fiscal → Exportar» y abrir el ZIP | Un XML por registro, `indice.csv`, `manifiesto.sha256` (`sha256sum -c` correcto) y `resumen.txt`. En «Eventos» aparece la exportación | FR-022 a FR-024 |
| 4 | Validar la firma de uno de los XML exportados con un validador oficial: VALIDe (`https://valide.redsara.es`), o el portal de pruebas de la AEAT si admite registros No VERI\*FACTU | Firma XAdES-EPES válida en su estructura, con la política de la AGE reconocida. Con el certificado de prueba, el validador avisará de que no es de confianza: es lo esperado | FR-006, Q-12 |
| 5 | Parar y arrancar la API (`docker compose restart api`) | En «Eventos», un resumen y un fin, y después un inicio nuevo, todos encadenados | FR-012, FR-013 |
| 6 | «Comprobar integridad» | Resultado «Íntegra», y en «Eventos», los lanzamientos 03 y 05 con sus recuentos | FR-017, FR-018 |
| 7 | Desde la consulta de una factura, «Ver en la cadena», y saltar a la anterior y a la siguiente | Indicadores «Correcto» de encadenamiento y de fechas | FR-020 |
| 8 | Quitar `CERTIFICADO_RUTA`, reiniciar e intentar emitir | La emisión se rechaza por el certificado, sin consumir número. Aparece la banda «No se puede facturar…» | FR-004, FR-019 |
| 9 | Como empleado: abrir «Acerca del sistema» y descargar la declaración | Declaración completa (art. 15.1, a a l) con Joyería Blanco como productora. «Registro fiscal» no aparece en el menú | FR-027, FR-028 |
| 10 | Simular una alteración: con `jb_owner`, desactivar los triggers y cambiar un dato de un registro. Después, «Comprobar integridad» | Anomalía del tipo correspondiente, evento 04 y banda de alarma para todos. Después se restaura la BD | FR-018, FR-019 |

## 3. Producción

- **Certificado real**:
  - se copia el `.p12` cualificado de Joyería Blanco al servidor y se indica su ruta en
    `CERTIFICADO_FICHERO`. Se monta como *secret* de Docker, en solo lectura, en
    `/run/secrets/certificado.p12` (`docker-compose.prod.yml`);
  - lo lee el usuario de la imagen: `chown 10001 certificado.p12 && chmod 0400 certificado.p12`;
  - la contraseña, en `CERTIFICADO_CONTRASENA`;
  - comprobar con `docker compose -f docker-compose.prod.yml exec api joyeria estado-certificado`
    o con `deploy/verificar-produccion.sh`, que lo incluye.
- **Variables**: `SIF_PRODUCTOR_NOMBRE`, `SIF_PRODUCTOR_NIF`, `SIF_PRODUCTOR_DIRECCION`,
  `SIF_DECLARACION_FECHA` y `SIF_DECLARACION_LUGAR` con los datos reales. La API no arranca sin
  ellas.
- **Declaración**: archivar el PDF de la declaración de la versión desplegada en
  `docs/declaraciones/` (RRSIF, art. 13.3).
- **Hora**: comprobar que el servidor sincroniza con NTP (Orden, art. 7.f: un minuto como máximo).
- **Asesoría**: antes de producción, validar la decisión de no tener capacidad de remisión (spec,
  «Riesgo normativo asumido»).

## Resultado de la validación

*(Se completa al cerrar la feature.)*
