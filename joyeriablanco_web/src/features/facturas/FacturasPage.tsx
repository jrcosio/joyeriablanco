import { useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { FileText, Plus, SearchX } from 'lucide-react'
import type { ReactNode } from 'react'
import {
  facturasListaQuery,
  TAMANO_PAGINA_FACTURAS,
  type FiltrosFacturas as Filtros,
} from '../../api/queries/facturas'
import { PageHeader } from '../../components/layout/PageHeader'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { EmptyState } from '../../components/ui/EmptyState'
import { ErrorState } from '../../components/ui/ErrorState'
import { Pagination } from '../../components/ui/Pagination'
import { anioEnCurso } from '../../lib/fechas'
import { urlPdfListado } from '../../lib/impresion'
import { FiltrosDocumentos } from '../documentos/FiltrosDocumentos'
import { ImprimirListado } from '../documentos/ImprimirListado'
import { TablaFacturas } from './TablaFacturas'

const claseBotonPrimario =
  'inline-flex h-11 w-full items-center justify-center gap-2 bg-primary px-6 label-lg ' +
  'text-on-primary transition-colors hover:bg-tertiary hover:shadow-aura sm:w-auto'

function NuevaFactura() {
  return (
    <Link to="/facturas/nueva" search className={claseBotonPrimario}>
      <Plus aria-hidden="true" className="size-4" />
      Nueva factura
    </Link>
  )
}

/**
 * Estado vacío según lo que lo provoca (FR-036): la búsqueda o el mes, un año sin facturas o que
 * todavía no haya ninguna.
 */
function SinFacturas({
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
        description="Ninguna factura coincide con la búsqueda o los filtros aplicados."
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
        title={`No hay facturas en ${String(filtros.anio ?? anioEnCurso())}`}
        description="Puede que las haya en otros años."
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
      icon={<FileText className="size-10" strokeWidth={1.25} />}
      title="Todavía no hay facturas"
      description="Emite la primera factura de la joyería para empezar."
      action={<NuevaFactura />}
    />
  )
}

/** Pantalla Facturas (US3): filtros, tabla y paginación, sin indicadores (FR-032 a FR-036). */
export function FacturasPage({
  filtros,
  onFiltros,
  modal,
}: {
  filtros: Filtros
  onFiltros: (cambios: Partial<Filtros>) => void
  modal: ReactNode
}) {
  const lista = useQuery(facturasListaQuery(filtros))

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
    contenido = <SinFacturas filtros={filtros} onFiltros={onFiltros} />
  } else {
    contenido = (
      <>
        <TablaFacturas filas={lista.data?.elementos ?? []} cargando={lista.isPending} />
        {lista.data ? (
          <div className="border-t border-primary-container/18">
            <Pagination
              pagina={filtros.pagina}
              tamano={TAMANO_PAGINA_FACTURAS}
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
        title="Facturas"
        actions={
          <>
            <NuevaFactura />
            <ImprimirListado
              href={urlPdfListado('facturas', filtros)}
              documentos="facturas"
              total={lista.data?.total}
              cargando={lista.isPending || lista.isPlaceholderData}
            />
          </>
        }
      />
      <FiltrosDocumentos filtros={filtros} onChange={onFiltros} etiqueta="Filtrar facturas" />
      <Card className="overflow-hidden bg-surface-container-low" aria-live="polite">
        {contenido}
      </Card>
      {modal}
    </div>
  )
}
