import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { parametrosPresupuestoQuery } from '../../../api/queries/presupuestos'
import { NuevoPresupuestoModal } from '../../../features/presupuestos/PresupuestoModal'
import { precargar } from '../../../lib/precarga'

export const Route = createFileRoute('/_app/presupuestos/nuevo')({
  loader: ({ context }) => precargar(context.queryClient.query(parametrosPresupuestoQuery)),
  component: NuevoPresupuesto,
})

function NuevoPresupuesto() {
  const navigate = useNavigate()
  const cerrar = () => {
    void navigate({ to: '/presupuestos', search: true })
  }
  return (
    <NuevoPresupuestoModal
      onCerrar={cerrar}
      onEmitido={cerrar}
      onBorradorCreado={(borrador) => {
        // Tras «Guardar borrador» el modal pasa al modo borrador de ese borrador.
        void navigate({
          to: '/presupuestos/borradores/$borradorId',
          params: { borradorId: borrador.id },
          search: true,
          replace: true,
        })
      }}
    />
  )
}
