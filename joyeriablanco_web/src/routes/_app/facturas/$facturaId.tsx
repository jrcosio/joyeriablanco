import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { FacturaConsultaModal } from '../../../features/facturas/FacturaConsulta'

export const Route = createFileRoute('/_app/facturas/$facturaId')({
  component: ConsultaFactura,
})

function ConsultaFactura() {
  const { facturaId } = Route.useParams()
  const navigate = useNavigate()
  return (
    <FacturaConsultaModal
      facturaId={facturaId}
      onCerrar={() => {
        void navigate({ to: '/facturas', search: true })
      }}
    />
  )
}
