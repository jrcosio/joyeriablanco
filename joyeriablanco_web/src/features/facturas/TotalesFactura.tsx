import { formatearEuros } from '../../lib/dinero'
import { textoTipoIva } from '../../lib/facturacion'

/**
 * Totales (DESIGN.md §Totals Section): base e IVA en Manrope y total destacado en Bodoni dentro
 * de una caja con acento `primary-container`. En el modal son una previsualización; en una
 * factura emitida, los importes del servidor.
 */
export function TotalesFactura({
  base,
  cuota,
  total,
  tipoIva,
  titulo = 'Total factura',
}: {
  base: bigint
  cuota: bigint
  total: bigint
  tipoIva: string
  titulo?: string
}) {
  return (
    <dl className="ml-auto flex w-full max-w-sm flex-col gap-2 border-l-2 border-primary-container bg-surface-container px-5 py-4">
      <div className="flex justify-between gap-6 body-md">
        <dt className="text-on-surface-variant">Base imponible</dt>
        <dd className="tabular-nums text-on-surface">{formatearEuros(base)}</dd>
      </div>
      <div className="flex justify-between gap-6 body-md">
        <dt className="text-on-surface-variant">IVA ({textoTipoIva(tipoIva)})</dt>
        <dd className="tabular-nums text-on-surface">{formatearEuros(cuota)}</dd>
      </div>
      <div className="mt-2 flex items-baseline justify-between gap-6 border-t border-primary-container/18 pt-3">
        <dt className="title-md text-on-surface">{titulo}</dt>
        <dd className="headline-md tabular-nums text-primary">{formatearEuros(total)}</dd>
      </div>
    </dl>
  )
}
