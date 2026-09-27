import { createFileRoute, redirect, useNavigate } from '@tanstack/react-router'
import { sesionQuery } from '../auth/session'
import { Marca } from '../components/layout/Marca'
import { Card } from '../components/ui/Card'
import { toast } from '../components/ui/toast-store'
import { CambioContrasenaForm } from '../features/cuenta/CambioContrasenaForm'

/** Cambio obligatorio de la contraseña temporal, sin shell (FR-009, FR-056). */
export const Route = createFileRoute('/cambiar-contrasena')({
  beforeLoad: async ({ context, location }) => {
    const sesion = await context.queryClient.query(sesionQuery)
    if (!sesion) throw redirect({ to: '/acceso', search: { volver: location.href } })
    if (!sesion.usuario.contrasena_temporal) throw redirect({ to: '/cuenta' })
  },
  component: CambiarContrasena,
})

function CambiarContrasena() {
  const navigate = useNavigate()
  return (
    <main className="flex min-h-dvh items-center justify-center px-4 py-10">
      <Card className="flex w-full max-w-md flex-col gap-8 px-6 py-10 sm:px-10">
        <Marca />
        <div className="flex flex-col gap-2 text-center">
          <h1 className="headline-md text-on-surface">Cambia tu contraseña</h1>
          <p className="body-md text-on-surface-variant">
            Estás usando una contraseña temporal. Elige una contraseña personal para continuar.
          </p>
        </div>
        <CambioContrasenaForm
          onHecho={() => {
            toast('Contraseña actualizada.')
            void navigate({ to: '/clientes' })
          }}
        />
      </Card>
    </main>
  )
}
