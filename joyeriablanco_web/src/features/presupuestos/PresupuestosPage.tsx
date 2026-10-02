import { useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { ClipboardList, Plus, SearchX } from 'lucide-react'
import type { ReactNode } from 'react'
import { presupuestosListaQuery, TAMANO_PAGINA_PRESUPUESTOS } from '../../api/queries/presupuestos'
import { PageHeader } from '../../components/layout/PageHeader'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { EmptyState } from '../../components/ui/EmptyState'
import { ErrorState } from '../../components/ui/ErrorState'
import { Pagination } from '../../components/ui/Pagination'
import { anioEnCurso } from '../../lib/fechas'
import type { FiltrosDocumentos as Filtros } from '../../lib/filtros-documentos'
import { FiltrosDocumentos } from '../documentos/FiltrosDocumentos'
import { TablaPresupuestos } from './TablaPresupuestos'

const claseBotonPrimario =
  'inline-flex h-11 w-full items-center justify-center gap-2 bg-primary px-6 label-lg ' +
  'text-on-primary transition-colors hover:bg-tertiary hover:shadow-aura sm:w-auto'

function NuevoPresupuesto() {
  return (
    <Link to="/presupuestos/nuevo" search className={claseBotonPrimario}>
      <Plus aria-hidden="true" className="size-4" />
      Nuevo presupuesto
    </Link>
  )
}

/** Estados vacíos (FR-023): la búsqueda o el mes, un año sin presupuestos o ninguno todavía. */
function SinPresupuestos({
  filtros,
  onFiltros,
}: {
  filtros: Filtros
  onFiltros: (cambios: Partial<Filtros>) => void
}) {
  if (filtros.q || filtros.mes !== undefined) {
    return (
      <EmptyState
        icon={<SearchX className="size-10" strokeWidth={1.25} />}
        title="No hay resultados"
        description="Ningún presupuesto coincide con la búsqueda o los filtros aplicados."
        action={
          <Button
            variant="secondary"
            onPress={() => {
              onFiltros({ q: undefined, anio: undefined, mes: undefined })
            }}
          >
            Limpiar filtros
          </Button>
        }
      />
    )
  }
  if (filtros.anio !== 'todos') {
    return (
      <EmptyState
        icon={<SearchX className="size-10" strokeWidth={1.25} />}
        title={`No hay presupuestos en ${String(filtros.anio ?? anioEnCurso())}`}
        description="Puede que los haya en otros años."
        action={
          <Button
            variant="secondary"
            onPress={() => {
              onFiltros({ anio: 'todos' })
            }}
          >
            Ver todos los años
          </Button>
        }
      />
    )
  }
  return (
    <EmptyState
      icon={<ClipboardList className="size-10" strokeWidth={1.25} />}
      title="Todavía no hay presupuestos"
      description="Prepara el primer presupuesto de la joyería para empezar."
      action={<NuevoPresupuesto />}
    />
  )
}

/** Pantalla Presupuestos (US1): filtros, tabla y paginación, como la de facturas (FR-023). */
export function PresupuestosPage({
  filtros,
  onFiltros,
  modal,
}: {
  filtros: Filtros
  onFiltros: (cambios: Partial<Filtros>) => void
  modal: ReactNode
}) {
  const lista = useQuery(presupuestosListaQuery(filtros))

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
    contenido = <SinPresupuestos filtros={filtros} onFiltros={onFiltros} />
  } else {
    contenido = (
      <>
        <TablaPresupuestos filas={lista.data?.elementos ?? []} cargando={lista.isPending} />
        {lista.data ? (
          <div className="border-t border-primary-container/18">
            <Pagination
              pagina={filtros.pagina}
              tamano={TAMANO_PAGINA_PRESUPUESTOS}
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
      <PageHeader title="Presupuestos" actions={<NuevoPresupuesto />} />
      <FiltrosDocumentos filtros={filtros} onChange={onFiltros} etiqueta="Filtrar presupuestos" />
      <Card className="overflow-hidden bg-surface-container-low" aria-live="polite">
        {contenido}
      </Card>
      {modal}
    </div>
  )
}
