import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { parametrosPresupuestoQuery, presupuestoQuery } from '../../../../api/queries/presupuestos'
import { requireAdmin } from '../../../../auth/guards'
import { ModificarPresupuestoModal } from '../../../../features/presupuestos/ModificarPresupuestoModal'
import { precargar } from '../../../../lib/precarga'

/** Solo administradores (FR-015); la API lo exige igualmente. */
export const Route = createFileRoute('/_app/presupuestos/$presupuestoId/modificar')({
  beforeLoad: ({ context }) => {
    requireAdmin(context.sesion)
  },
  // Se modifica sobre el estado actual del presupuesto (si ya no se puede, se dice).
  loader: ({ context: { queryClient }, params }) =>
    precargar(
      queryClient.query(parametrosPresupuestoQuery),
      queryClient.query({ ...presupuestoQuery(params.presupuestoId), staleTime: 0 }),
    ),
  component: ModificarPresupuesto,
})

function ModificarPresupuesto() {
  const { presupuestoId } = Route.useParams()
  const navigate = useNavigate()
  return (
    <ModificarPresupuestoModal
      presupuestoId={presupuestoId}
      onCerrar={() => {
        void navigate({
          to: '/presupuestos/$presupuestoId',
          params: { presupuestoId },
          search: true,
        })
      }}
      onModificado={(nuevo) => {
        // Como en facturas (002, FR-049): se pasa a la consulta del nuevo.
        void navigate({
          to: '/presupuestos/$presupuestoId',
          params: { presupuestoId: nuevo.id },
          search: true,
          replace: true,
        })
      }}
    />
  )
}
