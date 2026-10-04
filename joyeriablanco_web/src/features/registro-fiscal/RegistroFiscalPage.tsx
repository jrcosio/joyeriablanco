import { Tab, TabList, TabPanel, Tabs } from 'react-aria-components'
import type { TipoEventoSif } from '../../api/tipos'
import { PageHeader } from '../../components/layout/PageHeader'
import { cx } from '../../components/ui/cx'
import type { PestanaRegistroFiscal } from '../../lib/registro-fiscal'
import { EventosTab } from './EventosTab'

export interface BusquedaRegistroFiscal {
  pestana: PestanaRegistroFiscal
  tipo?: TipoEventoSif | undefined
  desde?: string | undefined
  hasta?: string | undefined
  pagina: number
  secuencia?: number | undefined
}

const claseTab =
  'inline-flex h-11 shrink-0 cursor-pointer items-center whitespace-nowrap border-b-2 ' +
  'border-transparent px-3 label-lg text-on-surface-variant outline-none transition-colors ' +
  'hover:text-on-surface sm:px-4'

const PESTANAS: readonly { id: PestanaRegistroFiscal; label: string }[] = [
  { id: 'eventos', label: 'Eventos' },
]

/**
 * «Registro fiscal» (004; RRSIF, art. 8.3): el registro de eventos y, en las historias siguientes,
 * la cadena, la comprobación de integridad y la exportación. Pestañas de React Aria (flechas y
 * foco visible), con la pestaña en la URL.
 */
export function RegistroFiscalPage({
  busqueda,
  onBusqueda,
}: {
  busqueda: BusquedaRegistroFiscal
  onBusqueda: (cambios: Partial<BusquedaRegistroFiscal>) => void
}) {
  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        title="Registro fiscal"
        subtitle="Registro de eventos del sistema, cadena de registros, integridad y exportación."
      />
      <Tabs
        selectedKey={busqueda.pestana}
        onSelectionChange={(clave) => {
          onBusqueda({ pestana: clave as PestanaRegistroFiscal })
        }}
        className="flex flex-col gap-6"
      >
        <TabList
          aria-label="Secciones del registro fiscal"
          className="flex gap-1 overflow-x-auto border-b border-primary-container/18 sm:gap-2"
        >
          {PESTANAS.map((p) => (
            <Tab
              key={p.id}
              id={p.id}
              className={({ isSelected, isFocusVisible }) =>
                cx(
                  claseTab,
                  isSelected && 'border-primary text-primary',
                  isFocusVisible && 'ring-2 ring-primary ring-inset',
                )
              }
            >
              {p.label}
            </Tab>
          ))}
        </TabList>
        <TabPanel id="eventos" className="outline-none">
          <EventosTab
            filtros={busqueda}
            onFiltros={(cambios) => {
              onBusqueda({ ...cambios, pagina: cambios.pagina ?? 1 })
            }}
          />
        </TabPanel>
      </Tabs>
    </div>
  )
}
