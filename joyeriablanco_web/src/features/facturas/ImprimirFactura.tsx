import { useState } from 'react'
import type { FacturaSalida } from '../../api/tipos'
import { Casilla } from '../../components/ui/Casilla'
import { urlPdfFactura } from '../../lib/impresion'
import { EnlaceImprimir } from './EnlaceImprimir'

/**
 * «Imprimir» de la consulta de una factura emitida (003, US1; contracts/ui-rutas.md). Las casillas
 * empiezan desmarcadas cada vez que se abre la consulta:
 * - «Incluir número de cuenta», solo si la factura tiene IBAN (FR-010).
 * - «Duplicado», salvo en una anulada (FR-033).
 */
export function ImprimirFactura({
  factura,
}: {
  factura: Pick<FacturaSalida, 'id' | 'num_serie' | 'estado' | 'emisor'>
}) {
  const [iban, setIban] = useState(false)
  const [duplicado, setDuplicado] = useState(false)
  const conIban = factura.emisor.iban != null
  const admiteDuplicado = factura.estado !== 'anulada'

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
      {admiteDuplicado ? (
        <Casilla isSelected={duplicado} onChange={setDuplicado}>
          Duplicado
        </Casilla>
      ) : null}
      <EnlaceImprimir
        href={urlPdfFactura(factura.id, {
          iban: conIban && iban,
          duplicado: admiteDuplicado && duplicado,
        })}
        etiqueta={`Imprimir factura ${factura.num_serie}`}
      >
        Imprimir
      </EnlaceImprimir>
    </div>
  )
}
