import { CircleCheck } from 'lucide-react'
import { useState } from 'react'
import { useComprobarIntegridad } from '../../api/queries/registroFiscal'
import { Alerta } from '../../components/forms/Alerta'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { Chip } from '../../components/ui/Chip'
import { TextField } from '../../components/ui/TextField'
import { TEXTO_ANOMALIA } from '../../lib/registro-fiscal'

function entero(texto: string): number | undefined {
  return /^\d+$/.test(texto) && Number(texto) >= 1 ? Number(texto) : undefined
}

/**
 * «Registro fiscal → Comprobar integridad» (FR-017, FR-018): toda la cadena o un rango de
 * registros de facturación; los eventos se comprueban siempre enteros. Bajo demanda.
 */
export function ComprobarTab() {
  const comprobar = useComprobarIntegridad()
  const [desde, setDesde] = useState('')
  const [hasta, setHasta] = useState('')
  const errorDesde = desde && entero(desde) === undefined ? 'Un número entero desde 1.' : undefined
  const errorHasta =
    hasta && entero(hasta) === undefined
      ? 'Un número entero desde 1.'
      : entero(desde) && entero(hasta) && Number(hasta) < Number(desde)
        ? 'No puede ser menor que «desde».'
        : undefined
  const resultado = comprobar.data

  return (
    <div className="flex flex-col gap-6">
      <p className="max-w-3xl body-md text-on-surface-variant">
        Revisa las huellas, las firmas, la cadena y las fechas de los registros de facturación y de
        evento, y deja constancia en el registro de eventos. Sin rango, toda la cadena.
      </p>
      <form
        className="flex flex-wrap items-end gap-3"
        onSubmit={(evento) => {
          evento.preventDefault()
          if (errorDesde || errorHasta) return
          comprobar.mutate({
            desde_secuencia: entero(desde) ?? null,
            hasta_secuencia: entero(hasta) ?? null,
          })
        }}
      >
        <TextField
          label="Desde el registro nº"
          value={desde}
          onChange={setDesde}
          inputMode="numeric"
          className="w-48"
          error={errorDesde}
        />
        <TextField
          label="Hasta el registro nº"
          value={hasta}
          onChange={setHasta}
          inputMode="numeric"
          className="w-48"
          error={errorHasta}
        />
        <Button type="submit" isDisabled={comprobar.isPending}>
          Comprobar integridad
        </Button>
      </form>

      <div aria-live="polite" className="flex flex-col gap-4">
        {comprobar.isPending ? (
          <p className="body-md text-on-surface-variant">Comprobando…</p>
        ) : null}
        {comprobar.isError ? <Alerta mensaje={comprobar.error.message} /> : null}
        {resultado ? (
          resultado.integra ? (
            <Card className="flex flex-wrap items-center gap-3 bg-surface-container-low p-6">
              <CircleCheck aria-hidden="true" className="size-6 text-success" />
              <Chip tone="success">Íntegra</Chip>
              <span className="body-md text-on-surface">
                {resultado.registros} registros de facturación y {resultado.eventos} de evento
                comprobados, sin anomalías.
              </span>
            </Card>
          ) : (
            <Card className="flex flex-col gap-4 bg-surface-container-low p-6">
              <p className="flex flex-wrap items-center gap-3 body-md text-on-surface">
                <Chip tone="danger">Anomalías</Chip>
                {resultado.anomalias.length} anomalías en {resultado.registros} registros de
                facturación y {resultado.eventos} de evento.
              </p>
              <ul className="flex flex-col gap-2 body-sm">
                {resultado.anomalias.map((a) => (
                  <li
                    key={`${a.cadena}-${String(a.secuencia)}-${a.tipo_anomalia}`}
                    className="flex flex-col gap-1 border border-danger/40 px-4 py-3"
                  >
                    <span className="text-on-surface">
                      {a.cadena === 'facturacion'
                        ? 'Registro de facturación'
                        : 'Registro de evento'}{' '}
                      nº {a.secuencia ?? '—'} · Anomalía {a.tipo_anomalia} (
                      {TEXTO_ANOMALIA[a.tipo_anomalia] ?? a.tipo_anomalia})
                    </span>
                    <span className="text-on-surface-variant">{a.descripcion}</span>
                  </li>
                ))}
              </ul>
            </Card>
          )
        ) : null}
      </div>
    </div>
  )
}
