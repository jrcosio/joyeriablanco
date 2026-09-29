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
  return (
    <NuevaFacturaModal
      onCerrar={cerrar}
      onEmitida={cerrar}
      onBorradorCreado={(borrador) => {
        // FR-049: tras «Guardar borrador» el modal pasa al modo borrador de ese borrador.
        void navigate({
          to: '/facturas/borradores/$borradorId',
          params: { borradorId: borrador.id },
          search: true,
          replace: true,
        })
      }}
    />
  )
}
