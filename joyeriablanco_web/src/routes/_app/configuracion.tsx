import { createFileRoute, Link, Outlet } from '@tanstack/react-router'
import { requireAdmin } from '../../auth/guards'
import { PageHeader } from '../../components/layout/PageHeader'

/** Configuración: solo administradores (FR-013, FR-038). Por defecto abre Usuarios (FR-056). */
export const Route = createFileRoute('/_app/configuracion')({
  beforeLoad: ({ context }) => {
    requireAdmin(context.sesion)
  },
  component: Configuracion,
})

const claseTab =
  'inline-flex h-11 shrink-0 items-center whitespace-nowrap border-b-2 border-transparent px-3 ' +
  'label-lg text-on-surface-variant transition-colors hover:text-on-surface sm:px-4'

function Configuracion() {
  return (
    <div className="flex flex-col gap-8">
      <PageHeader title="Configuración" subtitle="Usuarios, auditoría y facturación." />
      <nav
        aria-label="Secciones de configuración"
        className="flex gap-1 overflow-x-auto border-b border-primary-container/18 sm:gap-2"
      >
        <Link
          to="/configuracion/usuarios"
          className={claseTab}
          activeProps={{ className: 'border-primary text-primary', 'aria-current': 'page' }}
        >
          Usuarios
        </Link>
        <Link
          to="/configuracion/auditoria"
          className={claseTab}
          activeProps={{ className: 'border-primary text-primary', 'aria-current': 'page' }}
        >
          Auditoría
        </Link>
        <Link
          to="/configuracion/facturacion"
          className={claseTab}
          activeProps={{ className: 'border-primary text-primary', 'aria-current': 'page' }}
        >
          Facturación
        </Link>
      </nav>
      <Outlet />
    </div>
  )
}
