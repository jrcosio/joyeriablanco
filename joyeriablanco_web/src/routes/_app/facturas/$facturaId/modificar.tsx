import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { requireAdmin } from '../../../../auth/guards'
import { ModificarFacturaModal } from '../../../../features/facturas/ModificarFacturaModal'

/** Solo administradores (FR-023); la API lo exige igualmente. */
export const Route = createFileRoute('/_app/facturas/$facturaId/modificar')({
  beforeLoad: ({ context }) => {
    requireAdmin(context.sesion)
  },
  component: ModificarFactura,
})

function ModificarFactura() {
  const { facturaId } = Route.useParams()
  const navigate = useNavigate()
  return (
    <ModificarFacturaModal
      facturaId={facturaId}
      onCerrar={() => {
        void navigate({ to: '/facturas/$facturaId', params: { facturaId }, search: true })
      }}
      onModificada={(nueva) => {
        // FR-049: el modal pasa a mostrar la factura nueva en consulta.
        void navigate({
          to: '/facturas/$facturaId',
          params: { facturaId: nueva.id },
          search: true,
          replace: true,
        })
      }}
    />
  )
}
