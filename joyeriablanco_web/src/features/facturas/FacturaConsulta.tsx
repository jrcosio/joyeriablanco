import { useQuery } from '@tanstack/react-query'
import { facturaQuery } from '../../api/queries/facturas'
import type { FacturaSalida } from '../../api/tipos'
import { Alerta } from '../../components/forms/Alerta'
import { Button } from '../../components/ui/Button'
import { ModalDocumento } from '../../components/ui/ModalDocumento'
import { Skeleton } from '../../components/ui/Skeleton'
import { desdeApi, formatearCantidad, formatearEuros } from '../../lib/dinero'
import { fechaCorta } from '../../lib/fechas'
import { nombreConEstado } from '../../lib/usuarios'
import { FichaDestinatario } from './ResumenCliente'
import { TotalesFactura } from './TotalesFactura'

function Seccion({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-4">
      <h3 className="title-lg text-on-surface">{titulo}</h3>
      {children}
    </section>
  )
}

function Lineas({ factura }: { factura: FacturaSalida }) {
  if (factura.lineas.length === 0) {
    return <p className="body-md text-on-surface-variant">Sin líneas: devolución total.</p>
  }
  return (
    <div className="overflow-x-auto border border-primary-container/18 bg-surface-container-low">
      <table className="w-full">
        <caption className="sr-only">Líneas de la factura {factura.num_serie}</caption>
        <thead className="bg-surface-container">
          <tr className="label-md text-on-surface-variant">
            <th scope="col" className="px-4 py-3 text-right">
              Unidades
            </th>
            <th scope="col" className="px-4 py-3 text-left">
              Descripción
            </th>
            <th scope="col" className="px-4 py-3 text-right">
              Precio unitario
            </th>
            <th scope="col" className="px-4 py-3 text-right">
              Importe
            </th>
          </tr>
        </thead>
        <tbody>
          {factura.lineas.map((linea) => (
            <tr key={linea.orden} className="border-t border-primary-container/10 body-md">
              <td className="px-4 py-3 text-right tabular-nums">
                {formatearCantidad(desdeApi(linea.unidades))}
              </td>
              <td className="px-4 py-3">{linea.descripcion}</td>
              <td className="px-4 py-3 text-right tabular-nums">
                {formatearEuros(desdeApi(linea.precio_unitario))}
              </td>
              <td className="px-4 py-3 text-right tabular-nums">
                {formatearEuros(desdeApi(linea.importe))}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function Registros({ factura }: { factura: FacturaSalida }) {
  return (
    <ul className="flex flex-col gap-2 body-sm text-on-surface-variant">
      {factura.registros.map((r) => (
        <li key={r.secuencia} className="flex flex-wrap gap-x-4 gap-y-1">
          <span className="text-on-surface">
            Registro de {r.tipo === 'alta' ? 'alta' : 'anulación'} nº {r.secuencia}
          </span>
          <span>{r.fecha_hora_huso_gen}</span>
          <span className="font-mono tabular-nums" title={r.huella}>
            Huella {r.huella.slice(0, 16)}…
          </span>
          <span>Remisión: pendiente</span>
        </li>
      ))}
    </ul>
  )
}

/** Detalle de una factura emitida en modo consulta (FR-026, FR-038). */
export function FacturaDetalle({ factura }: { factura: FacturaSalida }) {
  const desglose = factura.totales.desglose[0]
  return (
    <div className="flex flex-col gap-8">
      <Seccion titulo="Datos de emisión">
        <dl className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <div>
            <dt className="label-sm text-on-surface-variant">Nº de factura</dt>
            <dd className="body-md tabular-nums text-on-surface">{factura.num_serie}</dd>
          </div>
          <div>
            <dt className="label-sm text-on-surface-variant">Fecha</dt>
            <dd className="body-md tabular-nums text-on-surface">
              {fechaCorta(factura.fecha_expedicion)}
            </dd>
          </div>
          {factura.fecha_operacion ? (
            <div>
              <dt className="label-sm text-on-surface-variant">Fecha de la operación</dt>
              <dd className="body-md tabular-nums text-on-surface">
                {fechaCorta(factura.fecha_operacion)}
              </dd>
            </div>
          ) : null}
          <div>
            <dt className="label-sm text-on-surface-variant">Emitida por</dt>
            <dd className="body-md text-on-surface">{nombreConEstado(factura.emitida_por)}</dd>
          </div>
        </dl>
        <FichaDestinatario datos={factura.cliente} />
      </Seccion>
      <Seccion titulo="Detalle de la factura">
        <Lineas factura={factura} />
      </Seccion>
      <TotalesFactura
        base={desdeApi(factura.totales.base_total)}
        cuota={desdeApi(factura.totales.cuota_total)}
        total={desdeApi(factura.totales.importe_total)}
        tipoIva={desglose?.tipo_iva ?? '0.00'}
      />
      <Seccion titulo="Registro de facturación">
        <Registros factura={factura} />
      </Seccion>
    </div>
  )
}

/** Modal de consulta de una factura emitida (US2; en US5 se añaden anular, modificar e historial). */
export function FacturaConsultaModal({
  facturaId,
  onCerrar,
}: {
  facturaId: string
  onCerrar: () => void
}) {
  const consulta = useQuery(facturaQuery(facturaId))
  const factura = consulta.data
  return (
    <ModalDocumento
      title={factura ? `Factura ${factura.num_serie}` : 'Factura'}
      isOpen
      onOpenChange={(abierto) => {
        if (!abierto) onCerrar()
      }}
      footer={
        <Button variant="ghost" onPress={onCerrar}>
          Cerrar
        </Button>
      }
    >
      {consulta.isError ? (
        <Alerta mensaje={consulta.error.message} />
      ) : factura ? (
        <FacturaDetalle factura={factura} />
      ) : (
        <div className="flex flex-col gap-5" aria-busy="true" aria-label="Cargando">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
      )}
    </ModalDocumento>
  )
}
