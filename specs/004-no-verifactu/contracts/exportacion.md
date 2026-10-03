# Contrato del fichero de exportación (FR-022 a FR-026; research R-12)

Un ZIP (deflate) que se descarga desde «Registro fiscal → Exportar» o con
`joyeria exportar-registros`.

## Nombre

- Registros de facturación: `registros-facturacion-AAAAMMDD-AAAAMMDD.zip`.
- Registros de evento: `registros-eventos-AAAAMMDD-AAAAMMDD.zip`.

Las fechas son las del periodo pedido, en hora de Madrid.

## Contenido

```text
registros-facturacion-20260101-20261231.zip
├── facturacion/0000001-alta-FAC-2026-0001.xml
├── facturacion/0000002-alta-FAC-2026-0002.xml
├── facturacion/0000003-anulacion-FAC-2026-0001.xml
├── indice.csv
├── manifiesto.sha256
└── resumen.txt
```

- **XML**: cada registro es su `xml_firmado`, **byte a byte**. El nombre lleva la secuencia con 7
  cifras, para que se ordene como la cadena, el tipo (`alta` o `anulacion`) y el número de la
  factura, con `/` cambiada por `-`. En la exportación de eventos, la carpeta es `eventos/` y el
  nombre `0000001-01.xml`: secuencia y tipo de evento.
- **`indice.csv`**: UTF-8 con BOM, separador `;`, una fila por registro.
  - Facturación: `secuencia;tipo;num_serie;fecha_expedicion;fecha_hora_generacion;huella;certificado_titular`.
  - Eventos: `secuencia;tipo_evento;fecha_hora_generacion;huella;certificado_titular`.
- **`manifiesto.sha256`**: el formato de `sha256sum`, `<sha256>  <ruta>`, una línea por cada
  fichero del ZIP salvo él mismo. Se comprueba con `sha256sum -c manifiesto.sha256`.
- **`resumen.txt`**:
  - en facturación: el periodo, el primer y el último registro (factura y huella), el número de
    altas y de anulaciones, las sumas de cuota e importe total de las altas y la frase «Los
    registros exportados siguen conservándose en el sistema»;
  - en eventos: lo mismo, con su recuento.

## Evento que genera

El 08 o el 09 (data-model), con el contenido de `ExportacionRegFacturacionPeriodo` o
`ExportacionRegEventoPeriodo` y «dejan de conservarse» = `N`. Se genera cuando el ZIP está completo.

## Periodo sin registros

422 `sin-registros`. No hay fichero ni evento.
