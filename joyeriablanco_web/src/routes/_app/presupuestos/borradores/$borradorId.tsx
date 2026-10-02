import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { borradorPresupuestoQuery } from '../../../../api/queries/borradoresPresupuesto'
import { parametrosPresupuestoQuery } from '../../../../api/queries/presupuestos'
import { BorradorPresupuestoModal } from '../../../../features/presupuestos/PresupuestoModal'
import { precargar } from '../../../../lib/precarga'

export const Route = createFileRoute('/_app/presupuestos/borradores/$borradorId')({
  // El borrador se pide siempre al abrirlo: nunca se edita sobre una copia antigua (FR-013).
  loader: ({ context: { queryClient }, params }) =>
    precargar(
      queryClient.query(parametrosPresupuestoQuery),
      queryClient.query({ ...borradorPresupuestoQuery(params.borradorId), staleTime: 0 }),
    ),
  component: BorradorPresupuesto,
})

function BorradorPresupuesto() {
  const { borradorId } = Route.useParams()
  const navigate = useNavigate()
  const cerrar = () => {
    void navigate({ to: '/presupuestos', search: true })
  }
  return <BorradorPresupuestoModal borradorId={borradorId} onCerrar={cerrar} onEmitido={cerrar} />
}
