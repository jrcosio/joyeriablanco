import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { BorradorModal } from '../../../../features/facturas/FacturaModal'

export const Route = createFileRoute('/_app/facturas/borradores/$borradorId')({
  component: Borrador,
})

function Borrador() {
  const { borradorId } = Route.useParams()
  const navigate = useNavigate()
  const cerrar = () => {
    void navigate({ to: '/facturas', search: true })
  }
  return <BorradorModal borradorId={borradorId} onCerrar={cerrar} onEmitida={cerrar} />
}
