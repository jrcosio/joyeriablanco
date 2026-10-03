import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { presupuestoQuery } from '../../../../api/queries/presupuestos'
import { PresupuestoConsultaModal } from '../../../../features/presupuestos/PresupuestoConsulta'
import { precargar } from '../../../../lib/precarga'

export const Route = createFileRoute('/_app/presupuestos/$presupuestoId/')({
  loader: ({ context, params }) =>
    precargar(context.queryClient.query(presupuestoQuery(params.presupuestoId))),
  component: ConsultaPresupuesto,
})

function ConsultaPresupuesto() {
  const { presupuestoId } = Route.useParams()
  const navigate = useNavigate()
  return (
    <PresupuestoConsultaModal
      presupuestoId={presupuestoId}
      onCerrar={() => {
        void navigate({ to: '/presupuestos', search: true })
      }}
    />
  )
}
