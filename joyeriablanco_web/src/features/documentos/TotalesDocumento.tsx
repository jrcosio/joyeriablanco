import { formatearEuros } from '../../lib/dinero'
import { formatearIban, textoTipoIva } from '../../lib/facturacion'

/**
 * Totales (DESIGN.md §Totals Section): base e IVA en Manrope y total destacado en Bodoni dentro
 * de una caja con acento `primary-container`. En el modal son una previsualización; en una
 * factura o un presupuesto emitidos, los importes del servidor (005, R-13).
 *
 * Sin tipo (`tipoIva` nulo), la factura es de oro de inversión: «Base exenta», IVA a cero y la
 * mención de F-6, art. 6.1.j (FR-052). En la consulta, el bloque «Pago» con el IBAN (FR-053).
 */
export function TotalesDocumento({
  base,
  cuota,
  total,
  tipoIva,
  mencion,
  iban,
  titulo = 'Total factura',
}: {
  base: bigint
  cuota: bigint
  total: bigint
  tipoIva: string | null
  mencion?: string | null | undefined
  iban?: string | null | undefined
  titulo?: string
}) {
  const exenta = tipoIva === null
  return (
    <div className="ml-auto flex w-full max-w-sm flex-col gap-2">
      <dl className="flex flex-col gap-2 border border-primary-container bg-surface-container px-5 py-4">
        <div className="flex justify-between gap-6 body-md">
          <dt className="text-on-surface-variant">{exenta ? 'Base exenta' : 'Base imponible'}</dt>
          <dd className="tabular-nums text-on-surface">{formatearEuros(base)}</dd>
        </div>
        <div className="flex justify-between gap-6 body-md">
          <dt className="text-on-surface-variant">
            {exenta ? 'IVA' : `IVA (${textoTipoIva(tipoIva)})`}
          </dt>
          <dd className="tabular-nums text-on-surface">{formatearEuros(cuota)}</dd>
        </div>
        <div className="mt-2 flex items-baseline justify-between gap-6 border-t border-primary-container/18 pt-3">
          <dt className="title-md text-on-surface">{titulo}</dt>
          <dd className="headline-md tabular-nums text-primary">{formatearEuros(total)}</dd>
        </div>
        {iban ? (
          <div
            role="group"
            aria-label="Pago"
            className="mt-2 flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1 border-t border-primary-container/18 pt-3"
          >
            <dt className="label-sm text-on-surface-variant">IBAN</dt>
            <dd className="body-md tabular-nums text-on-surface">{formatearIban(iban)}</dd>
          </div>
        ) : null}
      </dl>
      {mencion ? <p className="body-sm text-on-surface-variant">{mencion}</p> : null}
    </div>
  )
}
