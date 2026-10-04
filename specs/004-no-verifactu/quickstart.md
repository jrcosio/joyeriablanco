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

## Resultado de la validación (2026-10-04)

**Rendimiento** (`uv run pytest -m lento`, `test_no_verifactu_rendimiento.py`). Se emitieron
20.000 facturas con el servicio real, cada una con su XML firmado y validado contra el XSD, en un
Mac con Apple M5 Pro:

| Medida | Resultado | Objetivo |
|---|---|---|
| Emisión con firma, p95 (SC-007) | 21 ms | < 1 s |
| Exportación de los 20.000 registros (SC-005) | 3,0 s, con todos idénticos a los guardados | < 1 min |
| Comprobación completa de registros y eventos (SC-006) | 76,5 s, íntegra | < 3 min |

**Puertas**:
- Backend: 1.004 tests y los 6 lentos en verde. Además, ruff y mypy sin avisos.
- Web: lint, typecheck, 274 tests de Vitest, build y check:tokens en verde, y la E2E completa con
  87 pruebas, incluidas `registro-fiscal.spec.ts` y `acerca.spec.ts`.
- `test_logs_facturacion.py` compara ahora los logs sin escapar lo que no es ASCII. Con `í`, la
  comprobación nunca habría encontrado «María» ni «López». Firmar, comprobar y exportar no dejan
  contraseñas, claves, XML, datos personales ni importes (FR-033).
- La E2E completa destapó una regresión, ya corregida en `src/auth/perdida.ts` con su test
  `perdida.test.tsx`. Al caducar la sesión, la banda de alarma repetía su consulta, y su 401
  llegaba ya en el acceso: el aviso «Tu sesión ha caducado» salía dos veces.
- **Pila de desarrollo**: se migró de la 0008 a la 0009 sin perder datos. `joyeria
  verificar-cadena` da la cadena íntegra, con 61 registros de facturación y 8 de evento. Cada
  reinicio de la API deja un resumen (10), un fin (02) y un inicio (01), encadenados y firmados.
  Los datos de ejemplo siguen siendo los de antes de la 004, en VERI\*FACTU: para emitir en No
  VERI\*FACTU hay que regenerarlos (requisitos previos).

**Validaciones de §2**:

| # | Cómo se ha validado |
|---|---|
| 1 | `test_configuracion_facturacion.py`, `FacturacionPage.test.tsx` y E2E `configuracion-facturacion.spec.ts`: modalidad fija y tarjeta del certificado con titular, caducidad y aviso |
| 2 | `test_firma_registros.py`: emitir, anular, rectificar y convertir un presupuesto dejan su registro firmado, y la consulta muestra la firma verificada. También `FacturaModal.consulta.test.tsx` y E2E `facturas.spec.ts` |
| 3 | `test_exportacion.py`: ZIP con un XML por registro, índice, manifiesto SHA-256 y resumen, eventos 08 y 09, 422 `sin-registros` y 20.000 registros en el lento. También `ExportarTab.test.tsx` y E2E `registro-fiscal.spec.ts`, que descarga el ZIP y ve su evento |
| 4 | **Pendiente del responsable**: VALIDe necesita un navegador y subir el fichero a un servicio externo. La estructura está comprobada contra el ejemplo oficial F-18 (`test_firma.py`, mismo `DigestValue` de los datos) y contra el XSD |
| 5 | `test_eventos_lider.py`: inicio con un solo líder, resumen cada 6 horas aunque no pase nada (SC-004), resumen y fin al parar, y relevo si el líder cae. En la pila de desarrollo, el reinicio de la API deja resumen, fin e inicio encadenados |
| 6 | `test_integridad_anomalias.py`: lanzamientos 03 y 05 con sus recuentos, guardados. También `RegistroFiscalPage.test.tsx` y E2E `registro-fiscal.spec.ts`, sin alarma |
| 7 | `test_api_cadena.py`: indicadores de encadenamiento y de fechas, anterior y siguiente. También E2E `registro-fiscal.spec.ts`, de la factura a su registro |
| 8 | `test_firma_registros.py`: sin certificado utilizable no se emite, no se anula, no se rectifica ni se emite un borrador, y no se consume número (SC-002). También `test_alarmas.py` y `BandaAlarma.test.tsx` |
| 9 | `test_sistema.py`: declaración con las letras a) a l) y el PDF. También `AcercaPage.test.tsx`, `Sidebar.test.tsx` y E2E `acerca.spec.ts`, como empleado, en 2 clics (SC-008) |
| 10 | `test_integridad_anomalias.py`: dato, huella, firma, borrado y fecha dan su anomalía y el evento 04, y un evento alterado da el 06 (SC-003). `test_alarmas.py` cubre la banda para todos y cuándo se apaga (SC-009) |

**Producción** (T070): la imagen `prod`, construida con `docker compose -f docker-compose.prod.yml
build api`, se ejecutó como en el compose de producción: `read_only`, `cap_drop: ALL`,
`no-new-privileges`, `/tmp` en tmpfs, el usuario `app` (uid 10001) y un certificado de prueba
montado en solo lectura en `/run/secrets/certificado.p12`. Resultado:
- firmó el registro del ejemplo oficial F-18, lo validó contra el XSD empaquetado en la imagen y
  verificó la firma con el certificado;
- `/app` no admite escritura;
- `joyeria estado-certificado` da «Utilizable» (código 0) fuera de producción y «No utilizable:
  es un certificado de pruebas» (código 1) con `ENTORNO=produccion`.

**Pendiente del responsable**:
- Paso 4: validar un XML exportado en VALIDe.
- Instalar el certificado real y comprobarlo con `deploy/verificar-produccion.sh` (§3).
- Datos reales de la declaración (`SIF_*`) y archivo de su PDF en `docs/declaraciones/`.
- Consulta a la asesoría sobre la falta de capacidad de remisión (spec, «Riesgo normativo
  asumido»).
