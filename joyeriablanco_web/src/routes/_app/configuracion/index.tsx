import { createFileRoute, redirect } from '@tanstack/react-router'

export const Route = createFileRoute('/_app/configuracion/')({
  beforeLoad: () => {
    throw redirect({ to: '/configuracion/usuarios' })
  },
})
