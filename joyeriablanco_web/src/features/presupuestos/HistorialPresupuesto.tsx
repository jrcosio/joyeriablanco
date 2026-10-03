import { Link } from '@tanstack/react-router'
import type { PresupuestoSalida } from '../../api/tipos'
import { fechaHora } from '../../lib/fechas'
import { nombreConEstado } from '../../lib/usuarios'

const claseEnlace = 'text-primary underline underline-offset-4'

function EnlacePresupuesto({ id, numSerie }: { id: string; numSerie: string }) {
  return (
    <Link
      to="/presupuestos/$presupuestoId"
      params={{ presupuestoId: id }}
      search
      className={claseEnlace}
    >
      {numSerie}
    </Link>
  )
}

function EnlaceFactura({ id, numSerie }: { id: string; numSerie: string }) {
  return (
    <Link to="/facturas/$facturaId" params={{ facturaId: id }} className={claseEnlace}>
      {numSerie}
    </Link>
  )
}

/** «Sustituye a PRE-…» y, si está sustituido, el último de la cadena (FR-017). */
export function EnlacesPresupuesto({ presupuesto }: { presupuesto: PresupuestoSalida }) {
  const { sustituye_a: origen, vigente_actual: vigente } = presupuesto
  if (!origen && !vigente) return null
  return (
    <div className="flex flex-col gap-1 body-md text-on-surface">
      {origen ? (
        <p>
          Sustituye a <EnlacePresupuesto id={origen.id} numSerie={origen.num_serie} />
        </p>
      ) : null}
      {vigente && presupuesto.estado === 'sustituido' ? (
        <p>
          Sustituido por <EnlacePresupuesto id={vigente.id} numSerie={vigente.num_serie} />
        </p>
      ) : null}
    </div>
  )
}

const TITULOS = {
  anulacion: 'Anulado',
  sustitucion: 'Sustituido',
  conversion: 'Convertido en factura',
} as const

/** El cierre del presupuesto, con su fecha, su autor, su motivo y el documento (FR-017). */
export function HistorialPresupuesto({ presupuesto }: { presupuesto: PresupuestoSalida }) {
  const cierre = presupuesto.cierre
  if (!cierre) return null
  return (
    <section className="flex flex-col gap-3 border-t border-primary-container/18 pt-5">
      <h3 className="title-lg text-on-surface">Historial</h3>
      <dl className="grid grid-cols-1 gap-4 border border-primary-container/18 bg-surface-container p-5 md:grid-cols-3">
        <div>
          <dt className="label-sm text-on-surface-variant">Cierre</dt>
          <dd className="body-md text-on-surface">{TITULOS[cierre.tipo]}</dd>
        </div>
        <div>
          <dt className="label-sm text-on-surface-variant">Fecha</dt>
          <dd className="body-md tabular-nums text-on-surface">{fechaHora(cierre.creado_en)}</dd>
        </div>
        <div>
          <dt className="label-sm text-on-surface-variant">Por</dt>
          <dd className="body-md text-on-surface">{nombreConEstado(cierre.creado_por)}</dd>
        </div>
        {cierre.motivo_texto ? (
          <div className="md:col-span-3">
            <dt className="label-sm text-on-surface-variant">Motivo</dt>
            <dd className="body-md text-on-surface">{cierre.motivo_texto}</dd>
          </div>
        ) : null}
        {cierre.presupuesto_nuevo ? (
          <div className="md:col-span-3">
            <dt className="label-sm text-on-surface-variant">Presupuesto nuevo</dt>
            <dd className="body-md text-on-surface">
              <EnlacePresupuesto
                id={cierre.presupuesto_nuevo.id}
                numSerie={cierre.presupuesto_nuevo.num_serie}
              />
            </dd>
          </div>
        ) : null}
        {cierre.factura ? (
          <div className="md:col-span-3">
            <dt className="label-sm text-on-surface-variant">Factura</dt>
            <dd className="body-md text-on-surface">
              <EnlaceFactura id={cierre.factura.id} numSerie={cierre.factura.num_serie} />
              {cierre.factura_vigente ? (
                <>
                  {' '}
                  · corregida, la vigente es{' '}
                  <EnlaceFactura
                    id={cierre.factura_vigente.id}
                    numSerie={cierre.factura_vigente.num_serie}
                  />
                </>
              ) : null}
            </dd>
          </div>
        ) : null}
      </dl>
    </section>
  )
}
