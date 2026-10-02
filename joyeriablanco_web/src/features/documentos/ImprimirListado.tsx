import { Printer } from 'lucide-react'
import { useId } from 'react'
import { Button } from '../../components/ui/Button'
import { LIMITE_LISTADO_IMPRESO } from '../../lib/impresion'
import { EnlaceImprimir } from './EnlaceImprimir'

const ETIQUETA = 'Imprimir listado'

/**
 * «Imprimir listado» (003, US2; 005, FR-030; contracts/ui-rutas.md): abre en una pestaña nueva el
 * PDF con todas las filas del filtro actual. Se desactiva mientras carga el listado, sin resultados
 * o con más de 5.000, con el motivo enlazado para los lectores de pantalla (FR-018, FR-031).
 * `documentos` es el plural del motivo («facturas» o «presupuestos»).
 */
export function ImprimirListado({
  href,
  documentos,
  total,
  cargando,
}: {
  href: string
  documentos: string
  total: number | undefined
  cargando: boolean
}) {
  const idMotivo = useId()
  let motivo: string | null = null
  if (total === 0) {
    motivo = `No hay ${documentos} que imprimir con este filtro`
  } else if (total !== undefined && total > LIMITE_LISTADO_IMPRESO) {
    motivo = `El listado impreso admite hasta 5.000 ${documentos}: acota el filtro, por ejemplo por año`
  }

  if (cargando || total === undefined || motivo) {
    return (
      <div className="flex flex-col gap-1 sm:max-w-xs">
        <Button
          variant="secondary"
          isDisabled
          aria-describedby={motivo ? idMotivo : undefined}
          className="w-full sm:w-auto"
        >
          <Printer aria-hidden="true" className="size-4 text-primary" />
          {ETIQUETA}
        </Button>
        {motivo ? (
          <p id={idMotivo} className="body-sm text-on-surface-variant">
            {motivo}
          </p>
        ) : null}
      </div>
    )
  }

  return (
    <EnlaceImprimir href={href} etiqueta={ETIQUETA} className="w-full sm:w-auto">
      {ETIQUETA}
    </EnlaceImprimir>
  )
}
