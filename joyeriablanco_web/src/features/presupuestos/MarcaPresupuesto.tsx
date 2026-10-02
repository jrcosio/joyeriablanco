import type { EstadoPresupuesto } from '../../api/tipos'
import { Chip, type ChipTone } from '../../components/ui/Chip'

/**
 * Marca del estado de un presupuesto (FR-024; contracts/ui-rutas.md; DESIGN.md 1.3, «Status
 * Chips»): siempre con texto, nunca solo con color. Un pendiente no lleva marca.
 */
const MARCAS: Record<Exclude<EstadoPresupuesto, 'pendiente'>, { texto: string; tono: ChipTone }> = {
  borrador: { texto: 'Borrador', tono: 'warning' },
  en_facturacion: { texto: 'En facturación', tono: 'warning' },
  caducado: { texto: 'Caducado', tono: 'danger' },
  convertido: { texto: 'Convertido', tono: 'success' },
  sustituido: { texto: 'Sustituido', tono: 'neutral' },
  anulado: { texto: 'Anulado', tono: 'neutral' },
}

export function MarcaPresupuesto({
  estado,
  className,
}: {
  estado: EstadoPresupuesto
  className?: string
}) {
  if (estado === 'pendiente') return null
  const { texto, tono } = MARCAS[estado]
  return (
    <Chip tone={tono} {...(className ? { className } : {})}>
      {texto}
    </Chip>
  )
}
