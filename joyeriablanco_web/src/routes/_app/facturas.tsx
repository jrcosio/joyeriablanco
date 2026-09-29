import { createFileRoute, Link, Outlet } from '@tanstack/react-router'
import { Plus } from 'lucide-react'
import { PageHeader } from '../../components/layout/PageHeader'

const claseBotonPrimario =
  'inline-flex h-11 w-full items-center justify-center gap-2 bg-primary px-6 label-lg ' +
  'text-on-primary transition-colors hover:bg-tertiary hover:shadow-aura sm:w-auto'

/** Facturas: listado (US3) y, por encima, el modal de la factura (rutas anidadas, R-13). */
export const Route = createFileRoute('/_app/facturas')({
  component: Facturas,
})

function Facturas() {
  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        title="Facturas"
        actions={
          <Link to="/facturas/nueva" className={claseBotonPrimario}>
            <Plus aria-hidden="true" className="size-4" />
            Nueva factura
          </Link>
        }
      />
      <Outlet />
    </div>
  )
}
