import { useQuery } from '@tanstack/react-query'
import { Eye, ScrollText } from 'lucide-react'
import { useState } from 'react'
import { eventoQuery, eventosQuery, TAMANO_PAGINA_EVENTOS } from '../../api/queries/registroFiscal'
import type { EventoSifResumen, Salto, TipoEventoSif } from '../../api/tipos'
import { Button } from '../../components/ui/Button'
import { CampoFecha } from '../../components/ui/CampoFecha'
import { Card } from '../../components/ui/Card'
import { Chip } from '../../components/ui/Chip'
import { Dialog } from '../../components/ui/Dialog'
import { EmptyState } from '../../components/ui/EmptyState'
import { ErrorState } from '../../components/ui/ErrorState'
import { Pagination } from '../../components/ui/Pagination'
import { Select } from '../../components/ui/Select'
import { Skeleton } from '../../components/ui/Skeleton'
import { accionesCabecera, accionesCelda, tablaDesplazable } from '../../components/ui/tabla'
import { fechaHora } from '../../lib/fechas'
import { TIPOS_EVENTO_SIF } from '../../lib/registro-fiscal'

export interface FiltrosEventosUrl {
  tipo?: TipoEventoSif | undefined
  desde?: string | undefined
  hasta?: string | undefined
  pagina: number
}

const TODOS = '__todos__'
const celda = 'px-4 py-3 body-md align-middle xl:px-6'
const cabecera = 'px-4 py-4 text-left label-md text-on-surface-variant xl:px-6'

/** Resultado de una comprobación como chip, siempre con texto (nunca solo color). */
export function ChipComprobacion({
  correcto,
  si,
  no,
}: {
  correcto: boolean
  si: string
  no: string
}) {
  return <Chip tone={correcto ? 'success' : 'danger'}>{correcto ? si : no}</Chip>
}

function SaltoEvento({
  etiqueta,
  salto,
  onIr,
}: {
  etiqueta: string
  salto: Salto | null | undefined
  onIr: (secuencia: number) => void
}) {
  if (!salto) {
    return <p className="body-sm text-on-surface-variant">{etiqueta}: no hay.</p>
  }
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Button
        variant="secondary"
        onPress={() => {
          onIr(salto.secuencia)
        }}
      >
        {etiqueta} (nº {salto.secuencia})
      </Button>
      <ChipComprobacion
        correcto={salto.encadenamiento_correcto}
        si="Encadenamiento correcto"
        no="Encadenamiento incorrecto"
      />
      <ChipComprobacion
        correcto={salto.fechas_en_orden}
        si="Fechas en orden"
        no="Fechas fuera de orden"
      />
    </div>
  )
}

/** Datos propios del evento con los nombres oficiales de F-17, aplanados en «Grupo › Campo». */
function lineas(datos: unknown, prefijo = ''): [string, string][] {
  if (datos === null || typeof datos !== 'object') return [[prefijo, String(datos)]]
  if (Array.isArray(datos)) return datos.flatMap((d, i) => lineas(d, `${prefijo} ${String(i + 1)}`))
  return Object.entries(datos as Record<string, unknown>).flatMap(([clave, valor]) =>
    lineas(valor, prefijo ? `${prefijo} › ${clave}` : clave),
  )
}

function DetalleEvento({
  secuencia,
  onIr,
  onCerrar,
}: {
  secuencia: number
  onIr: (secuencia: number) => void
  onCerrar: () => void
}) {
  const consulta = useQuery(eventoQuery(secuencia))
  const evento = consulta.data
  return (
    <Dialog
      title={
        evento
          ? `Evento nº ${String(secuencia)} · ${TIPOS_EVENTO_SIF[evento.tipo_evento]}`
          : `Evento nº ${String(secuencia)}`
      }
      isOpen
      onOpenChange={(abierto) => {
        if (!abierto) onCerrar()
      }}
      className="max-w-2xl"
    >
      {consulta.isError ? (
        <ErrorState message={consulta.error.message} />
      ) : !evento ? (
        <div aria-busy="true" aria-label="Cargando el evento" className="flex flex-col gap-3">
          <Skeleton className="h-5 w-full" />
          <Skeleton className="h-5 w-2/3" />
        </div>
      ) : (
        <div className="flex max-h-[70vh] flex-col gap-5 overflow-y-auto">
          <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 body-md">
            <dt className="text-on-surface-variant">Fecha y hora</dt>
            <dd className="tabular-nums">{fechaHora(evento.fecha_hora_huso_gen)}</dd>
            <dt className="text-on-surface-variant">Firmado por</dt>
            <dd>{evento.certificado_titular}</dd>
            <dt className="text-on-surface-variant">Huella</dt>
            <dd className="break-all font-mono body-sm tabular-nums">{evento.huella}</dd>
          </dl>
          <div className="flex flex-wrap gap-2">
            <ChipComprobacion
              correcto={evento.huella_correcta}
              si="Huella correcta"
              no="Huella incorrecta"
            />
            <ChipComprobacion
              correcto={evento.firma_correcta}
              si="Firma correcta"
              no="Firma incorrecta"
            />
          </div>
          {Object.keys(evento.datos).length > 0 ? (
            <div className="flex flex-col gap-2">
              <h3 className="label-md text-primary">Datos del evento</h3>
              <dl className="flex flex-col gap-1 body-sm">
                {lineas(evento.datos).map(([clave, valor]) => (
                  <div key={clave} className="flex flex-wrap gap-x-2">
                    <dt className="text-on-surface-variant">{clave}:</dt>
                    <dd className="break-all text-on-surface">{valor}</dd>
                  </div>
                ))}
              </dl>
            </div>
          ) : null}
          <div className="flex flex-col gap-3 border-t border-primary-container/18 pt-4">
            <SaltoEvento etiqueta="Evento anterior" salto={evento.anterior} onIr={onIr} />
            <SaltoEvento etiqueta="Evento siguiente" salto={evento.siguiente} onIr={onIr} />
          </div>
        </div>
      )}
    </Dialog>
  )
}

function Accion({ evento, onVer }: { evento: EventoSifResumen; onVer: () => void }) {
  return (
    <Button
      variant="icon"
      aria-label={`Ver el evento nº ${String(evento.secuencia)}: ${TIPOS_EVENTO_SIF[evento.tipo_evento]}`}
      onPress={onVer}
    >
      <Eye aria-hidden="true" className="size-4" />
    </Button>
  )
}

/** «Registro fiscal → Eventos» (FR-016): lista paginada del más reciente al más antiguo. */
export function EventosTab({
  filtros,
  onFiltros,
}: {
  filtros: FiltrosEventosUrl
  onFiltros: (cambios: Partial<FiltrosEventosUrl>) => void
}) {
  const consulta = useQuery(eventosQuery(filtros))
  const [seleccionado, setSeleccionado] = useState<number | null>(null)
  const filtrando = Boolean(filtros.tipo ?? filtros.desde ?? filtros.hasta)
  const opcionesTipo = [
    { id: TODOS, label: 'Todos los tipos' },
    ...Object.entries(TIPOS_EVENTO_SIF).map(([id, label]) => ({ id, label: `${id} · ${label}` })),
  ]

  return (
    <div className="flex flex-col gap-6">
      <div
        role="search"
        aria-label="Filtrar eventos"
        className="grid grid-cols-1 gap-3 sm:grid-cols-3"
      >
        <Select
          label="Tipo de evento"
          options={opcionesTipo}
          value={filtros.tipo ?? TODOS}
          onChange={(v) => {
            onFiltros({ tipo: v && v !== TODOS ? (v as TipoEventoSif) : undefined })
          }}
        />
        <CampoFecha
          label="Desde"
          value={filtros.desde}
          onChange={(desde) => {
            onFiltros({ desde })
          }}
        />
        <CampoFecha
          label="Hasta"
          value={filtros.hasta}
          onChange={(hasta) => {
            onFiltros({ hasta })
          }}
        />
      </div>

      <Card className="overflow-hidden bg-surface-container-low" aria-live="polite">
        {consulta.isError ? (
          <ErrorState
            message={consulta.error.message}
            onRetry={() => {
              void consulta.refetch()
            }}
          />
        ) : consulta.isPending ? (
          <div aria-busy="true" aria-label="Cargando eventos" className="flex flex-col gap-3 p-6">
            {Array.from({ length: 5 }, (_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : consulta.data.total === 0 ? (
          <EmptyState
            icon={<ScrollText className="size-10" strokeWidth={1.25} />}
            title={filtrando ? 'No hay eventos con este filtro' : 'Todavía no hay eventos'}
          />
        ) : (
          <>
            <div className={`hidden md:block ${tablaDesplazable}`}>
              <table className="w-full border-collapse">
                <caption className="sr-only">Registro de eventos</caption>
                <thead className="border-b border-primary-container/25 bg-surface-container">
                  <tr>
                    <th scope="col" className={cabecera}>
                      Nº
                    </th>
                    <th scope="col" className={cabecera}>
                      Evento
                    </th>
                    <th scope="col" className={cabecera}>
                      Fecha y hora
                    </th>
                    <th scope="col" className={`${cabecera} hidden lg:table-cell`}>
                      Resumen
                    </th>
                    <th scope="col" className={`${cabecera} hidden xl:table-cell`}>
                      Firmado por
                    </th>
                    <th scope="col" className={`${cabecera} ${accionesCabecera}`}>
                      <span className="sr-only">Detalle</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {consulta.data.elementos.map((evento) => (
                    <tr
                      key={evento.secuencia}
                      className="group border-b border-primary-container/18 last:border-b-0 hover:bg-surface-container-high"
                    >
                      <td className={`${celda} tabular-nums`}>{evento.secuencia}</td>
                      <td className={celda}>
                        <span className="tabular-nums text-on-surface-variant">
                          {evento.tipo_evento}
                        </span>{' '}
                        {TIPOS_EVENTO_SIF[evento.tipo_evento]}
                      </td>
                      <td className={`${celda} whitespace-nowrap tabular-nums`}>
                        {fechaHora(evento.fecha_hora_huso_gen)}
                      </td>
                      <td className={`${celda} hidden text-on-surface-variant lg:table-cell`}>
                        {evento.resumen ?? '—'}
                      </td>
                      <td className={`${celda} hidden text-on-surface-variant xl:table-cell`}>
                        {evento.certificado_titular}
                      </td>
                      <td className={`${celda} ${accionesCelda} text-right`}>
                        <Accion
                          evento={evento}
                          onVer={() => {
                            setSeleccionado(evento.secuencia)
                          }}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <ul aria-label="Registro de eventos" className="flex flex-col md:hidden">
              {consulta.data.elementos.map((evento) => (
                <li
                  key={evento.secuencia}
                  className="flex items-start justify-between gap-4 border-b border-primary-container/18 px-4 py-4 last:border-b-0"
                >
                  <div className="flex min-w-0 flex-col gap-1">
                    <span className="title-md text-on-surface">
                      Nº {evento.secuencia} · {TIPOS_EVENTO_SIF[evento.tipo_evento]}
                    </span>
                    <span className="body-sm tabular-nums text-on-surface-variant">
                      {fechaHora(evento.fecha_hora_huso_gen)}
                    </span>
                    {evento.resumen ? (
                      <span className="body-sm text-on-surface-variant">{evento.resumen}</span>
                    ) : null}
                  </div>
                  <Accion
                    evento={evento}
                    onVer={() => {
                      setSeleccionado(evento.secuencia)
                    }}
                  />
                </li>
              ))}
            </ul>
            <div className="border-t border-primary-container/18">
              <Pagination
                pagina={filtros.pagina}
                tamano={TAMANO_PAGINA_EVENTOS}
                total={consulta.data.total}
                onChange={(pagina) => {
                  onFiltros({ pagina })
                }}
              />
            </div>
          </>
        )}
      </Card>

      {seleccionado === null ? null : (
        <DetalleEvento
          secuencia={seleccionado}
          onIr={setSeleccionado}
          onCerrar={() => {
            setSeleccionado(null)
          }}
        />
      )}
    </div>
  )
}
