import { ChevronLeft, ChevronRight } from 'lucide-react'
import { Button } from './Button'

export interface PaginationProps {
  pagina: number
  tamano: number
  total: number
  onChange: (pagina: number) => void
}

export function Pagination({ pagina, tamano, total, onChange }: PaginationProps) {
  const paginas = Math.max(1, Math.ceil(total / tamano))
  const desde = total === 0 ? 0 : (pagina - 1) * tamano + 1
  const hasta = Math.min(pagina * tamano, total)
  return (
    <nav
      aria-label="Paginación"
      className="flex flex-col items-center justify-between gap-3 px-6 py-4 sm:flex-row"
    >
      <p className="body-sm text-on-surface-variant tabular-nums">
        {total === 0
          ? 'Sin resultados'
          : `Mostrando ${desde}–${hasta} de ${total.toLocaleString('es-ES')}`}
      </p>
      <div className="flex items-center gap-2">
        <Button
          variant="icon"
          aria-label="Página anterior"
          isDisabled={pagina <= 1}
          onPress={() => {
            onChange(pagina - 1)
          }}
        >
          <ChevronLeft aria-hidden="true" className="size-4" />
        </Button>
        <span className="body-sm tabular-nums text-on-surface" aria-live="polite">
          Página {Math.min(pagina, paginas)} de {paginas}
        </span>
        <Button
          variant="icon"
          aria-label="Página siguiente"
          isDisabled={pagina >= paginas}
          onPress={() => {
            onChange(pagina + 1)
          }}
        >
          <ChevronRight aria-hidden="true" className="size-4" />
        </Button>
      </div>
    </nav>
  )
}
