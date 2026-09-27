import { createFileRoute, Link, Outlet } from '@tanstack/react-router'
import { Plus } from 'lucide-react'
import { PageHeader } from '../../components/layout/PageHeader'

export const Route = createFileRoute('/_app/clientes')({
  component: Clientes,
})

function Clientes() {
  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        title="Clientes"
        subtitle="Gestiona tu cartera de clientes y consulta su historial de facturación."
        actions={
          <Link
            to="/clientes/nuevo"
            search={(previa) => previa}
            className="inline-flex h-11 w-full items-center justify-center gap-2 bg-primary px-6 label-lg text-on-primary transition-colors hover:bg-tertiary hover:shadow-aura sm:w-auto"
          >
            <Plus aria-hidden="true" className="size-4" />
            Nuevo cliente
          </Link>
        }
      />
      <Outlet />
    </div>
  )
}
