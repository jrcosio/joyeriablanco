# Modelo de datos — 003 PDF de factura con QR e impresión del listado

**Spec**: [spec.md](spec.md) · **Research**: [research.md](research.md)

La feature solo **lee** los datos fiscales de 002: `facturas`, `lineas_factura`,
`desgloses_factura`, `registros_facturacion`, `correcciones_factura` y la vista
`v_listado_facturas`. **No cambia ninguna tabla de solo inserción** (constitución III). El único
cambio de esquema amplía la fila mutable de `configuracion_facturacion`.

## Migración `0007_contacto_pie_factura` (solo DDL)

```sql
ALTER TABLE configuracion_facturacion
  ADD COLUMN emisor_telefono VARCHAR(30)  NULL,
  ADD COLUMN emisor_correo   VARCHAR(254) NULL,
  ADD COLUMN emisor_web      VARCHAR(200) NULL,
  ADD COLUMN pie_factura     VARCHAR(600) NULL,
  ADD CONSTRAINT ck_config_contacto_sin_vacios CHECK (
        (emisor_telefono IS NULL OR emisor_telefono = btrim(emisor_telefono) AND emisor_telefono <> '')
    AND (emisor_correo   IS NULL OR emisor_correo   = btrim(emisor_correo)   AND emisor_correo   <> '')
    AND (emisor_web      IS NULL OR emisor_web      = btrim(emisor_web)      AND emisor_web      <> '')
    AND (pie_factura     IS NULL OR pie_factura     = btrim(pie_factura)     AND pie_factura     <> '')
  );
```

- **Privilegios**: los de la tabla no cambian. `jb_app` ya tiene `SELECT` y `UPDATE` sobre la fila
  única (002, migración 0005).
- **`downgrade`**: borra la restricción y las cuatro columnas.
- **Auditoría**: el `CHECK` de tipos de evento no cambia. El evento sigue siendo
  `configuracion_facturacion_cambiada`, ahora también con los cuatro campos en `cambios`.

### `configuracion_facturacion`: columnas nuevas

| Columna | Tipo | Regla (FR-024) |
|---|---|---|
| `emisor_telefono` | `VARCHAR(30)` | Dígitos, espacios, `+`, paréntesis y guiones, con al menos 6 dígitos (`domain/contacto.py`, como 001 FR-055) |
| `emisor_correo` | `VARCHAR(254)` | Formato válido según `email-validator`, en minúsculas |
| `emisor_web` | `VARCHAR(200)` | Un dominio o una URL `http(s)://`. Se imprime sin esquema y sin la barra final |
| `pie_factura` | `VARCHAR(600)` | Texto libre de varias líneas, con saltos normalizados a `\n` |

Son datos **no fiscales**: no se copian en `facturas` al emitir y no se exigen para emitir
(FR-025). Cada impresión lee los vigentes.

## Lecturas nuevas (sin tablas nuevas)

### Filas del listado impreso: `repositories/facturas.list_facturas_impresion`

Es la misma consulta que `list_facturas` de 002, sobre `v_listado_facturas`, con `_filtros(q,
anio, mes)` y `_ORDENES[orden]`, pero **sin `OFFSET`/`LIMIT`**. Antes se cuenta con el mismo
`count(*)`: si da más de `LIMITE_LISTADO_IMPRESO = 5000`, no se leen las filas (R-7).

### Totales del listado impreso: `repositories/facturas.totales_vigentes`

```sql
-- Desglose por tipo de las facturas vigentes que cumplen el filtro (FR-021)
SELECT d.tipo_iva, sum(d.base) AS base, sum(d.cuota) AS cuota
FROM v_listado_facturas v
JOIN desgloses_factura d ON d.factura_id = v.id
WHERE v.tipo_documento = 'factura' AND v.estado = 'vigente' AND <filtros>
GROUP BY d.tipo_iva
ORDER BY d.tipo_iva DESC NULLS LAST;     -- NULL = base exenta (oro de inversión), al final

-- Totales generales y filas fuera de la suma
SELECT
  count(*) FILTER (WHERE tipo_documento = 'factura' AND estado = 'vigente') AS vigentes,
  sum(base)  FILTER (WHERE tipo_documento = 'factura' AND estado = 'vigente') AS base,
  sum(cuota) FILTER (WHERE tipo_documento = 'factura' AND estado = 'vigente') AS cuota,
  sum(total) FILTER (WHERE tipo_documento = 'factura' AND estado = 'vigente') AS total,
  count(*) FILTER (WHERE tipo_documento = 'borrador')    AS borradores,
  count(*) FILTER (WHERE estado = 'anulada')             AS anuladas,
  count(*) FILTER (WHERE estado = 'rectificada')         AS rectificadas
FROM v_listado_facturas
WHERE <filtros>;
```

- Las sumas son `NUMERIC` y viajan como `Decimal` (constitución II). Si no hay vigentes, las sumas
  son 0, no `NULL`, con `coalesce`.
- **Invariante probado**: Σ(base por tipo) = base general, Σ(cuota por tipo) = cuota general y
  base general + cuota general = total general. Cuadran al céntimo porque cada factura cumple
  `base_total = Σ desgloses.base` y `importe_total = base_total + cuota_total` (002, `CHECK` de
  la 0005 y 0006).

### Datos de la factura impresa: `services/facturas.get_factura` (de 002)

Se reutiliza tal cual: factura con líneas y desgloses, estado derivado, `rectifica_a`,
`sustituye_a`, `vigente_actual`, correcciones y registros. El QR toma el registro de tipo `alta`
(R-1).

## Modelos de vista (inmutables, sin persistencia)

Son `dataclass(frozen=True, slots=True)` en `app/services/impresion.py`. Las plantillas solo los
pintan: todo el texto ya viene formateado por `app/domain/formato.py` (R-6).

### `FacturaImpresa`

| Campo | Contenido |
|---|---|
| `titulo` | «Factura» o «Factura rectificativa» |
| `num_serie`, `fecha_expedicion`, `fecha_operacion` | Textos. `fecha_operacion` vale `None` si no existe o coincide con la de expedición |
| `marcas` | Lista ordenada de `MarcaImpresa(texto)`: «ANULADA», «Sustituida por X», «RECTIFICADA por X» y «DUPLICADO» |
| `qr` | `QrImpreso(svg, url, frase)`. `frase` es `None` en modalidad no VERI\*FACTU |
| `emisor` | `ParteImpresa(nombre, identificacion, lineas_domicilio)` de la copia guardada en la factura |
| `contacto` | `ContactoImpreso(telefono, correo, web)` de la configuración vigente. Cada uno es opcional |
| `destinatario` | `ParteImpresa` desde `dest_*`, con la etiqueta del tipo de identificación y el país si no es `ES` |
| `lineas` | `LineaImpresa(unidades, descripcion, precio_unitario, importe)` |
| `desglose` | `DesgloseImpreso(etiqueta_base, base, etiqueta_cuota, cuota)`, p. ej. («Base imponible al 21 %», «IVA 21 %») o («Base exenta», «IVA») |
| `base_total`, `cuota_total`, `importe_total` | Textos en euros |
| `mencion_exencion` | Texto de `MENCION_EXENCION_ORO_INVERSION` o `None` |
| `rectificacion` | `RectificacionImpresa(num_serie, fecha, causa, base_rectificada, cuota_rectificada)` o `None` |
| `iban` | IBAN agrupado si se pidió y la factura lo tiene; si no, `None` |
| `pie` | Pie de la configuración vigente o `None` |

### `ListadoImpreso`

| Campo | Contenido |
|---|---|
| `emisor_nombre` | Nombre del emisor de la configuración vigente, o `None` |
| `filtro` | Textos: búsqueda, año, mes y orden (R-7) |
| `generado_en` | Fecha y hora en hora de Madrid |
| `filas` | `FilaImpresa(numero, marca, fecha, cliente, identificacion, base, iva, total)`. `numero` vale «Borrador» en un borrador; `iva` vale «Exenta» en una de oro de inversión |
| `desglose` | `DesgloseImpreso` por tipo, de mayor a menor tipo, con la exenta al final |
| `totales` | Número de vigentes, base, IVA y total |
| `excluidas` | Número de borradores, anuladas y rectificadas, solo los que no son 0 |

## Configuración de la instalación (no es BD)

| Variable | Valores | Regla (R-3) |
|---|---|---|
| `AEAT_ENTORNO` | `pruebas` · `produccion` | Fuera de producción, vacío equivale a `pruebas`. Con `ENTORNO=produccion` es obligatoria, y la API no arranca sin ella |

## Estados y transiciones

Sin cambios. El PDF lee el estado derivado de 002 (`vigente`, `anulada` o `rectificada`) en el
momento de generarse. Imprimir no cambia ningún estado ni deja evento de auditoría (spec,
Assumptions).
