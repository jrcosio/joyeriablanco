import { useState } from 'react'
import type { PresupuestoSalida } from '../../api/tipos'
import { Casilla } from '../../components/ui/Casilla'
import { urlPdfPresupuesto } from '../../lib/impresion'
import { EnlaceImprimir } from '../documentos/EnlaceImprimir'

/**
 * «Imprimir» de la consulta de un presupuesto emitido (005, US2; contracts/ui-rutas.md). La casilla
 * «Incluir número de cuenta» solo aparece si el presupuesto tiene IBAN y empieza desmarcada cada vez
 * que se abre la consulta. No hay «Duplicado»: es un concepto de factura (ROF art. 14).
 */
export function ImprimirPresupuesto({
  presupuesto,
}: {
  presupuesto: Pick<PresupuestoSalida, 'id' | 'num_serie' | 'emisor'>
}) {
  const [iban, setIban] = useState(false)
  const conIban = presupuesto.emisor.iban != null

  return (
    <div
      role="group"
      aria-label="Opciones de impresión"
      className="flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-5"
    >
      {conIban ? (
        <Casilla isSelected={iban} onChange={setIban}>
          Incluir número de cuenta
        </Casilla>
      ) : null}
      <EnlaceImprimir
        href={urlPdfPresupuesto(presupuesto.id, { iban: conIban && iban })}
        etiqueta={`Imprimir presupuesto ${presupuesto.num_serie}`}
      >
        Imprimir
      </EnlaceImprimir>
    </div>
  )
}
