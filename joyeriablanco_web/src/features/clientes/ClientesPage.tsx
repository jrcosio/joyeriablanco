import { useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { Plus, SearchX, Users } from 'lucide-react'
import type { ReactNode } from 'react'
import { useCatalogos } from '../../api/queries/catalogos'
import {
  clientesListaQuery,
  TAMANO_PAGINA,
  type FiltrosClientes as Filtros,
} from '../../api/queries/clientes'
import { PageHeader } from '../../components/layout/PageHeader'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { EmptyState } from '../../components/ui/EmptyState'
import { ErrorState } from '../../components/ui/ErrorState'
import { Pagination } from '../../components/ui/Pagination'
import { FiltrosClientes } from './FiltrosClientes'
import { IndicadoresClientes } from './IndicadoresClientes'
import { TablaClientes } from './TablaClientes'

const claseBotonPrimario =
  'inline-flex h-11 w-full items-center justify-center gap-2 bg-primary px-6 label-lg ' +
  'text-on-primary transition-colors hover:bg-tertiary hover:shadow-aura sm:w-auto'

function hayFiltros(f: Filtros): boolean {
  return Boolean(f.q || f.provincia || f.tipo || f.estado !== 'activos')
}

/** Pantalla Clientes (US3): indicadores, filtros, tabla y paginación (FR-031 a FR-034, FR-057). */
export function ClientesPage({
  filtros,
  onFiltros,
  panel,
}: {
  filtros: Filtros
  onFiltros: (cambios: Partial<Filtros>) => void
  panel: ReactNode
}) {
  const catalogos = useCatalogos()
  const lista = useQuery(clientesListaQuery(filtros))
  const conFiltros = hayFiltros(filtros)
  const limpiar = () => {
    onFiltros({ q: undefined, provincia: undefined, tipo: undefined, estado: 'activos' })
  }

  let contenido: ReactNode
  if (lista.isError) {
    contenido = (
      <ErrorState
        message={lista.error.message}
        onRetry={() => {
          void lista.refetch()
        }}
      />
    )
  } else if (lista.data && lista.data.total === 0) {
    contenido = conFiltros ? (
      <EmptyState
        icon={<SearchX className="size-10" strokeWidth={1.25} />}
        title="No hay resultados"
        description="Ningún cliente coincide con la búsqueda o los filtros aplicados."
        action={
          <Button variant="secondary" onPress={limpiar}>
            Limpiar filtros
          </Button>
        }
      />
    ) : (
      <EmptyState
        icon={<Users className="size-10" strokeWidth={1.25} />}
        title="Todavía no hay clientes"
        description="Da de alta el primer cliente de la joyería para empezar."
        action={
          <Link to="/clientes/nuevo" search className={claseBotonPrimario}>
            <Plus aria-hidden="true" className="size-4" />
            Nuevo cliente
          </Link>
        }
      />
    )
  } else {
    contenido = (
      <>
        <TablaClientes clientes={lista.data?.elementos ?? []} cargando={lista.isPending} />
        {lista.data ? (
          <div className="border-t border-primary-container/18">
            <Pagination
              pagina={filtros.pagina}
              tamano={TAMANO_PAGINA}
              total={lista.data.total}
              onChange={(pagina) => {
                onFiltros({ pagina })
              }}
            />
          </div>
        ) : null}
      </>
    )
  }

  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        title="Clientes"
        subtitle="Gestiona tu cartera de clientes y consulta su historial de facturación."
        actions={
          <Link to="/clientes/nuevo" search className={claseBotonPrimario}>
            <Plus aria-hidden="true" className="size-4" />
            Nuevo cliente
          </Link>
        }
      />
      <IndicadoresClientes />
      <FiltrosClientes filtros={filtros} catalogos={catalogos.data} onChange={onFiltros} />
      <Card className="overflow-hidden bg-surface-container-low" aria-live="polite">
        {contenido}
      </Card>
      {panel}
    </div>
  )
}
