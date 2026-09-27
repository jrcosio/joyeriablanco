import { useSesion } from '../../auth/session'
import { PageHeader } from '../../components/layout/PageHeader'
import { Card } from '../../components/ui/Card'
import { toast } from '../../components/ui/toast-store'
import { CambioContrasenaForm } from './CambioContrasenaForm'

/** Mi cuenta: cambio de la propia contraseña (US6). */
export function MiCuentaPage() {
  const { usuario } = useSesion()
  return (
    <div className="flex flex-col gap-8">
      <PageHeader title="Mi cuenta" subtitle={`${usuario.nombre} · ${usuario.nombre_usuario}`} />
      <Card className="max-w-xl p-6 md:p-8">
        <h2 className="mb-6 headline-sm text-on-surface">Cambiar contraseña</h2>
        <CambioContrasenaForm
          onHecho={() => {
            toast('Contraseña actualizada. Se han cerrado tus otras sesiones.')
          }}
        />
      </Card>
    </div>
  )
}
