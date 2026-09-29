import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { NuevaFacturaModal } from '../../../features/facturas/FacturaModal'

export const Route = createFileRoute('/_app/facturas/nueva')({
  component: NuevaFactura,
})

function NuevaFactura() {
  const navigate = useNavigate()
  const cerrar = () => {
    void navigate({ to: '/facturas', search: true })
  }
  return <NuevaFacturaModal onCerrar={cerrar} onEmitida={cerrar} />
}
