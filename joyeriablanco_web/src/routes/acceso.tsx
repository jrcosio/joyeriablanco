import { createFileRoute, redirect } from '@tanstack/react-router'
import { z } from 'zod'
import { rutaSegura, sesionQuery } from '../auth/session'
import { LoginPage } from '../features/acceso/LoginPage'

export const Route = createFileRoute('/acceso')({
  validateSearch: z.object({ volver: z.string().optional() }),
  beforeLoad: async ({ context, search }) => {
    const sesion = await context.queryClient.query(sesionQuery)
    if (sesion?.usuario.contrasena_temporal) throw redirect({ to: '/cambiar-contrasena' })
    if (sesion) throw redirect({ href: rutaSegura(search.volver) })
  },
  component: Acceso,
})

function Acceso() {
  const { volver } = Route.useSearch()
  return <LoginPage volver={volver} />
}
