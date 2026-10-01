import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { parametrosFacturacionQuery } from '../../../api/queries/configuracionFacturacion'
import { NuevaFacturaModal } from '../../../features/facturas/FacturaModal'
import { precargar } from '../../../lib/precarga'

export const Route = createFileRoute('/_app/facturas/nueva')({
  loader: ({ context }) => precargar(context.queryClient.query(parametrosFacturacionQuery)),
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
