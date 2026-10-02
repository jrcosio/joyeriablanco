import { Link } from '@tanstack/react-router'
import type { PresupuestoReferencia } from '../../api/tipos'

/**
 * «Procede del presupuesto PRE-…» en el borrador de factura creado por «Convertir en factura» y en
 * la factura emitida desde él (005, FR-022; contracts/ui-rutas.md).
 */
export function EnlacePresupuesto({
  presupuesto,
}: {
  presupuesto: PresupuestoReferencia | null | undefined
}) {
  if (!presupuesto) return null
  return (
    <p className="body-md text-on-surface">
      Procede del presupuesto{' '}
      <Link
        to="/presupuestos/$presupuestoId"
        params={{ presupuestoId: presupuesto.id }}
        className="text-primary underline underline-offset-4 tabular-nums"
      >
        {presupuesto.num_serie}
      </Link>
    </p>
  )
}
