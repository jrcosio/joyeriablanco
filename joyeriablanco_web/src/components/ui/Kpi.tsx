import type { ReactNode } from 'react'
import { Skeleton } from './Skeleton'

export interface KpiProps {
  icon: ReactNode
  label: string
  value: number | undefined
  isLoading?: boolean
}

/** Indicador: etiqueta en body-md y cifra en Bodoni headline-lg (contracts/ui-rutas.md). */
export function Kpi({ icon, label, value, isLoading = false }: KpiProps) {
  return (
    <div className="flex items-center gap-5">
      <span className="text-primary" aria-hidden="true">
        {icon}
      </span>
      <div className="flex flex-col">
        <span className="body-md text-on-surface-variant">{label}</span>
        {isLoading || value === undefined ? (
          <Skeleton className="mt-1 h-11 w-20" />
        ) : (
          <span className="headline-lg-mobile md:headline-lg tabular-nums text-on-surface">
            {value.toLocaleString('es-ES')}
          </span>
        )}
      </div>
    </div>
  )
}
