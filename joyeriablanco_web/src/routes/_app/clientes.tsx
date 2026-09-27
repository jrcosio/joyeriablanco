import { createFileRoute, Outlet } from '@tanstack/react-router'
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
      />
      <Outlet />
    </div>
  )
}
