import { TriangleAlert } from 'lucide-react'
import { textoTipoIva } from '../../lib/facturacion'

/**
 * Aviso de que el IVA por defecto cambió después de guardar el borrador (002, casos límite). El
 * borrador de factura vinculado a un presupuesto lo muestra igual (005, US3-9).
 */
export function AvisoCambioIva({ previsto, vigente }: { previsto: string; vigente: string }) {
  return (
    <div
      role="status"
      className="flex items-start gap-3 border border-warning/40 bg-warning/8 px-4 py-3"
    >
      <TriangleAlert aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-warning" />
      <p className="body-md text-on-surface">
        El IVA por defecto ha cambiado desde que se guardó este borrador (del{' '}
        {textoTipoIva(previsto)} al {textoTipoIva(vigente)}). Al emitirlo se aplicará el{' '}
        {textoTipoIva(vigente)}.
      </p>
    </div>
  )
}
