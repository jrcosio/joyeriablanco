import { useQuery } from '@tanstack/react-query'
import { Eye, ScrollText } from 'lucide-react'
import { useState } from 'react'
import { Input, Label, TextField as AriaTextField } from 'react-aria-components'
import { auditoriaQuery, TAMANO_PAGINA_AUDITORIA } from '../../api/queries/auditoria'
import { usuariosConEliminadosQuery } from '../../api/queries/usuarios'
import type { EventoSalida, TipoEvento } from '../../api/tipos'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { Drawer } from '../../components/ui/Drawer'
import { EmptyState } from '../../components/ui/EmptyState'
import { ErrorState } from '../../components/ui/ErrorState'
import { campoCaja, campoContenedor, campoEtiqueta } from '../../components/ui/field'
import { Pagination } from '../../components/ui/Pagination'
import { Select } from '../../components/ui/Select'
import { Skeleton } from '../../components/ui/Skeleton'
import { fechaHora, finDia, inicioDia } from '../../lib/fechas'
import { nombreConEstado } from '../../lib/usuarios'
import { TIPOS_EVENTO } from './tipos-evento'

export interface FiltrosAuditoriaUrl {
  desde?: string | undefined // AAAA-MM-DD
  hasta?: string | undefined
  usuario?: string | undefined
  tipo?: TipoEvento | undefined
  cliente?: string | undefined
  pagina: number
}

const TODOS = '__todos__'

function actor(evento: EventoSalida): string {
  if (evento.actor) return nombreConEstado(evento.actor)
  if (evento.actor_nombre_usuario === 'consola') return 'Consola'
  return evento.actor_nombre_usuario ?? '—'
}

function objeto(evento: EventoSalida): string {
  if (evento.usuario_afectado) return nombreConEstado(evento.usuario_afectado)
  const detalle = evento.detalle as { nombre?: unknown; instantanea?: { nombre?: unknown } }
  if (typeof detalle.instantanea?.nombre === 'string') return detalle.instantanea.nombre
  if (typeof detalle.nombre === 'string') return detalle.nombre
  if (evento.cliente_id) return `Cliente ${evento.cliente_id.slice(-8)}`
  return '—'
}

function CampoFecha({
  label,
  value,
  onChange,
}: {
  label: string
  value: string | undefined
  onChange: (v: string | undefined) => void
}) {
  return (
    <AriaTextField
      type="date"
      value={value ?? ''}
      onChange={(v) => {
        onChange(v || undefined)
      }}
      className={campoContenedor}
    >
      <Label className={campoEtiqueta}>{label}</Label>
      <Input className={`${campoCaja} [color-scheme:dark]`} />
    </AriaTextField>
  )
}

function texto(valor: unknown): string {
  if (valor === null || valor === undefined) return '—'
  if (typeof valor === 'string') return valor
  if (typeof valor === 'number' || typeof valor === 'boolean') return valor.toString()
  return JSON.stringify(valor)
}

function Detalle({ evento }: { evento: EventoSalida }) {
  const cambios = (evento.detalle as { cambios?: Record<string, [unknown, unknown]> }).cambios
  const resto = Object.entries(evento.detalle).filter(([clave]) => clave !== 'cambios')
  return (
    <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-3 body-md">
      <dt className="text-on-surface-variant">Fecha y hora</dt>
      <dd className="tabular-nums">{fechaHora(evento.ocurrido_en)}</dd>
      <dt className="text-on-surface-variant">Tipo</dt>
      <dd>{TIPOS_EVENTO[evento.tipo]}</dd>
      <dt className="text-on-surface-variant">Actor</dt>
      <dd>{actor(evento)}</dd>
      <dt className="text-on-surface-variant">Afecta a</dt>
      <dd>{objeto(evento)}</dd>
      <dt className="text-on-surface-variant">Origen</dt>
      <dd className="break-all">
        {[evento.origen_ip, evento.agente].filter(Boolean).join(' · ') || '—'}
      </dd>
      {cambios ? (
        <>
          <dt className="col-span-2 mt-3 label-md text-primary">Campos cambiados</dt>
          <dd className="col-span-2">
            <table className="w-full border-collapse body-sm">
              <thead>
                <tr className="border-b border-primary-container/25 text-left label-sm text-on-surface-variant">
                  <th scope="col" className="py-2 pr-4">
                    Campo
                  </th>
                  <th scope="col" className="py-2 pr-4">
                    Antes
                  </th>
                  <th scope="col" className="py-2">
                    Después
                  </th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(cambios).map(([campo, [antes, despues]]) => (
                  <tr key={campo} className="border-b border-primary-container/18">
                    <td className="py-2 pr-4 text-on-surface-variant">{campo}</td>
                    <td className="py-2 pr-4">{texto(antes)}</td>
                    <td className="py-2">{texto(despues)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </dd>
        </>
      ) : null}
      {resto.map(([clave, valor]) => (
        <div key={clave} className="contents">
          <dt className="text-on-surface-variant">{clave}</dt>
          <dd className="break-all">{typeof valor === 'string' ? valor : JSON.stringify(valor)}</dd>
        </div>
      ))}
    </dl>
  )
}

/** Configuración → Auditoría: consulta de solo lectura (US5; FR-051). */
export function AuditoriaPage({
  filtros,
  onFiltros,
}: {
  filtros: FiltrosAuditoriaUrl
  onFiltros: (cambios: Partial<FiltrosAuditoriaUrl>) => void
}) {
  const usuarios = useQuery(usuariosConEliminadosQuery)
  const consulta = useQuery(
    auditoriaQuery({
      desde: filtros.desde ? inicioDia(filtros.desde) : undefined,
      hasta: filtros.hasta ? finDia(filtros.hasta) : undefined,
      usuario_id: filtros.usuario,
      tipo: filtros.tipo,
      cliente_id: filtros.cliente,
      pagina: filtros.pagina,
    }),
  )
  const [seleccionado, setSeleccionado] = useState<EventoSalida | null>(null)

  const opcionesUsuario = [
    { id: TODOS, label: 'Todos los usuarios' },
    ...(usuarios.data ?? []).map((u) => ({ id: u.id, label: nombreConEstado(u) })),
  ]
  const opcionesTipo = [
    { id: TODOS, label: 'Todos los tipos' },
    ...Object.entries(TIPOS_EVENTO).map(([id, label]) => ({ id, label })),
  ]

  return (
    <div className="flex flex-col gap-6">
      <div
        role="search"
        aria-label="Filtrar auditoría"
        className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4"
      >
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
        <Select
          label="Usuario"
          options={opcionesUsuario}
          value={filtros.usuario ?? TODOS}
          onChange={(v) => {
            onFiltros({ usuario: v && v !== TODOS ? v : undefined })
          }}
        />
        <Select
          label="Tipo de evento"
          options={opcionesTipo}
          value={filtros.tipo ?? TODOS}
          onChange={(v) => {
            onFiltros({ tipo: v && v !== TODOS ? (v as TipoEvento) : undefined })
          }}
        />
      </div>
      {filtros.cliente ? (
        <p className="flex items-center gap-3 body-md text-on-surface-variant">
          Filtrando por un cliente concreto.
          <Button
            variant="ghost"
            onPress={() => {
              onFiltros({ cliente: undefined })
            }}
          >
            Quitar filtro
          </Button>
        </p>
      ) : null}

      <Card className="overflow-hidden bg-surface-container-low" aria-live="polite">
        {consulta.isError ? (
          <ErrorState
            message={consulta.error.message}
            onRetry={() => {
              void consulta.refetch()
            }}
          />
        ) : consulta.isPending ? (
          <div aria-busy="true" aria-label="Cargando auditoría" className="flex flex-col gap-3 p-6">
            {Array.from({ length: 5 }, (_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : consulta.data.total === 0 ? (
          <EmptyState
            icon={<ScrollText className="size-10" strokeWidth={1.25} />}
            title="No hay eventos"
            description="Ningún evento coincide con los filtros aplicados."
          />
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full border-collapse">
                <caption className="sr-only">Eventos de auditoría</caption>
                <thead className="border-b border-primary-container/25 bg-surface-container">
                  <tr>
                    {['Fecha y hora', 'Evento', 'Actor', 'Afecta a', 'Origen', ''].map((c, i) => (
                      <th
                        key={c || 'detalle'}
                        scope="col"
                        className={`px-6 py-4 text-left label-md text-on-surface-variant ${
                          i === 3 || i === 4 ? 'hidden lg:table-cell' : ''
                        }`}
                      >
                        {c || <span className="sr-only">Detalle</span>}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {consulta.data.elementos.map((evento) => (
                    <tr
                      key={evento.id}
                      className="border-b border-primary-container/18 last:border-b-0 hover:bg-surface-container-high"
                    >
                      <td className="px-6 py-3 body-md tabular-nums whitespace-nowrap">
                        {fechaHora(evento.ocurrido_en)}
                      </td>
                      <td className="px-6 py-3 body-md">{TIPOS_EVENTO[evento.tipo]}</td>
                      <td className="px-6 py-3 body-md">{actor(evento)}</td>
                      <td className="hidden px-6 py-3 body-md lg:table-cell">{objeto(evento)}</td>
                      <td className="hidden px-6 py-3 body-sm tabular-nums text-on-surface-variant lg:table-cell">
                        {evento.origen_ip ?? '—'}
                      </td>
                      <td className="px-6 py-3 text-right">
                        <Button
                          variant="icon"
                          aria-label={`Ver detalle: ${TIPOS_EVENTO[evento.tipo]} de ${fechaHora(evento.ocurrido_en)}`}
                          onPress={() => {
                            setSeleccionado(evento)
                          }}
                        >
                          <Eye aria-hidden="true" className="size-4" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="border-t border-primary-container/18">
              <Pagination
                pagina={filtros.pagina}
                tamano={TAMANO_PAGINA_AUDITORIA}
                total={consulta.data.total}
                onChange={(pagina) => {
                  onFiltros({ pagina })
                }}
              />
            </div>
          </>
        )}
      </Card>

      {seleccionado ? (
        <Drawer
          title={TIPOS_EVENTO[seleccionado.tipo]}
          subtitle={fechaHora(seleccionado.ocurrido_en)}
          isOpen
          onOpenChange={(abierto) => {
            if (!abierto) setSeleccionado(null)
          }}
        >
          <Detalle evento={seleccionado} />
        </Drawer>
      ) : null}
    </div>
  )
}
