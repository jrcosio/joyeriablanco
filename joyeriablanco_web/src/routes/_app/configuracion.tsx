import { createFileRoute, Outlet } from '@tanstack/react-router'
import { requireAdmin } from '../../auth/guards'
import { PageHeader } from '../../components/layout/PageHeader'

/** Configuración: solo administradores (FR-013, FR-038). */
export const Route = createFileRoute('/_app/configuracion')({
  beforeLoad: ({ context }) => {
    requireAdmin(context.sesion)
  },
  component: Configuracion,
})

function Configuracion() {
  return (
    <div className="flex flex-col gap-8">
      <PageHeader title="Configuración" subtitle="Usuarios y auditoría del sistema." />
      <Outlet />
    </div>
  )
}
