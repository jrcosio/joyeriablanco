import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { facturaQuery } from '../../../../api/queries/facturas'
import { FacturaConsultaModal } from '../../../../features/facturas/FacturaConsulta'
import { precargar } from '../../../../lib/precarga'

export const Route = createFileRoute('/_app/facturas/$facturaId/')({
  loader: ({ context, params }) =>
    precargar(context.queryClient.query(facturaQuery(params.facturaId))),
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
