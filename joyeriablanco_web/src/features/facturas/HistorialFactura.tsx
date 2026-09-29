import { Link } from '@tanstack/react-router'
import { ChevronDown } from 'lucide-react'
import { useId, useState } from 'react'
import type { FacturaSalida } from '../../api/tipos'
import { Chip } from '../../components/ui/Chip'
import { cx } from '../../components/ui/cx'
import { fechaHora } from '../../lib/fechas'
import { MOTIVOS_MODIFICACION, TIPOS_CORRECCION } from '../../lib/facturacion'
import { nombreConEstado } from '../../lib/usuarios'

const claseEnlace = 'text-primary underline underline-offset-4 tabular-nums'

function EnlaceFactura({ referencia }: { referencia: { id: string; num_serie: string } }) {
  return (
    <Link
      to="/facturas/$facturaId"
      params={{ facturaId: referencia.id }}
      search
      className={claseEnlace}
    >
      {referencia.num_serie}
    </Link>
  )
}

/** Enlaces con las facturas relacionadas (FR-026): la rectificada, la sustituida y la vigente. */
export function EnlacesFactura({ factura }: { factura: FacturaSalida }) {
  const enlaces = [
    factura.rectifica_a ? (
      <li key="rectifica">
        Rectifica a <EnlaceFactura referencia={factura.rectifica_a.factura} />
      </li>
    ) : null,
    factura.sustituye_a ? (
      <li key="sustituye">
        Sustituye a <EnlaceFactura referencia={factura.sustituye_a} />, anulada
      </li>
    ) : null,
    factura.vigente_actual ? (
      <li key="vigente">
        La factura vigente es <EnlaceFactura referencia={factura.vigente_actual} />
      </li>
    ) : null,
  ].filter(Boolean)
  if (enlaces.length === 0) return null
  return <ul className="flex flex-col gap-1 body-md text-on-surface">{enlaces}</ul>
}

/**
 * Historial plegable (FR-026, contracts/ui-rutas.md): cada corrección con su tipo, fecha, autor,
 * motivo y la factura que la materializa, y los registros de facturación con su huella abreviada.
 */
export function HistorialFactura({ factura }: { factura: FacturaSalida }) {
  const [abierto, setAbierto] = useState(true)
  const id = useId()
  return (
    <section className="flex flex-col gap-4 border-t border-primary-container/18 pt-5">
      <h3>
        <button
          type="button"
          aria-expanded={abierto}
          aria-controls={id}
          onClick={() => {
            setAbierto((a) => !a)
          }}
          className="flex w-full items-center justify-between gap-3 title-lg text-on-surface outline-none focus-visible:text-primary"
        >
          Historial
          <ChevronDown
            aria-hidden="true"
            className={cx('size-5 transition-transform', abierto && 'rotate-180')}
          />
        </button>
      </h3>
      <div id={id} hidden={!abierto} className="flex flex-col gap-6">
        <div className="flex flex-col gap-3">
          <h4 className="label-md text-primary">Correcciones</h4>
          {factura.correcciones.length === 0 ? (
            <p className="body-md text-on-surface-variant">Sin correcciones.</p>
          ) : (
            <ol className="flex flex-col gap-3">
              {factura.correcciones.map((c) => (
                <li
                  key={`${c.tipo}-${c.creada_en}`}
                  className="flex flex-col gap-1 border border-primary-container/18 bg-surface-container px-4 py-3"
                >
                  <span className="flex flex-wrap items-center gap-2 body-md text-on-surface">
                    {TIPOS_CORRECCION[c.tipo]}
                    {c.en_vigor ? null : <Chip tone="neutral">Sin efecto</Chip>}
                  </span>
                  <span className="body-sm text-on-surface-variant">
                    {fechaHora(c.creada_en)} · {nombreConEstado(c.creada_por)}
                  </span>
                  <span className="body-sm text-on-surface-variant">
                    {MOTIVOS_MODIFICACION[c.motivo]}: {c.motivo_texto}
                  </span>
                  {c.factura_nueva ? (
                    <span className="body-sm text-on-surface">
                      Factura nueva: <EnlaceFactura referencia={c.factura_nueva} />
                      {c.en_vigor ? null : ' (anulada después)'}
                    </span>
                  ) : null}
                </li>
              ))}
            </ol>
          )}
        </div>
        <div className="flex flex-col gap-3">
          <h4 className="label-md text-primary">Registros de facturación</h4>
          <ul className="flex flex-col gap-2 body-sm text-on-surface-variant">
            {factura.registros.map((r) => (
              <li key={r.secuencia} className="flex flex-wrap gap-x-4 gap-y-1">
                <span className="text-on-surface">
                  Registro de {r.tipo === 'alta' ? 'alta' : 'anulación'} nº {r.secuencia}
                </span>
                <span>{r.fecha_hora_huso_gen}</span>
                <span className="font-mono tabular-nums" title={r.huella}>
                  Huella {r.huella.slice(0, 16)}…
                </span>
                <span>Remisión: pendiente</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  )
}
