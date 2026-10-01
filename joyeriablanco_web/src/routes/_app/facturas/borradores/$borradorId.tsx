import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { borradorQuery } from '../../../../api/queries/borradores'
import { parametrosFacturacionQuery } from '../../../../api/queries/configuracionFacturacion'
import { BorradorModal } from '../../../../features/facturas/FacturaModal'
import { precargar } from '../../../../lib/precarga'

export const Route = createFileRoute('/_app/facturas/borradores/$borradorId')({
  // El borrador se pide siempre al abrirlo: nunca se edita sobre una copia antigua (FR-020).
  loader: ({ context: { queryClient }, params }) =>
    precargar(
      queryClient.query(parametrosFacturacionQuery),
      queryClient.query({ ...borradorQuery(params.borradorId), staleTime: 0 }),
    ),
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
