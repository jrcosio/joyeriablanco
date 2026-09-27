import { createFileRoute, Outlet } from '@tanstack/react-router'
import { requireSession } from '../auth/guards'
import { useSesion } from '../auth/session'
import { AppShell } from '../components/layout/AppShell'

/** Layout protegido: exige sesión y muestra el shell (US1). */
export const Route = createFileRoute('/_app')({
  beforeLoad: requireSession,
  component: AppLayout,
})

function AppLayout() {
  const sesion = useSesion()
  return (
    <AppShell sesion={sesion}>
      <Outlet />
    </AppShell>
  )
}
