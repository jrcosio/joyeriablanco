import { createFileRoute, Outlet, useNavigate } from '@tanstack/react-router'
import { useCallback } from 'react'
import { PresupuestosPage } from '../../features/presupuestos/PresupuestosPage'
import { busquedaDocumentos, type FiltrosDocumentos } from '../../lib/filtros-documentos'

/** Presupuestos (005, US1): listado y, por encima, el modal del presupuesto (rutas anidadas). */
export const Route = createFileRoute('/_app/presupuestos')({
  validateSearch: busquedaDocumentos,
  component: Presupuestos,
})

function Presupuestos() {
  const filtros = Route.useSearch()
  const navigate = useNavigate()
  const cambiar = useCallback(
    (cambios: Partial<FiltrosDocumentos>) => {
      // Como en facturas: `to: '.'` no cierra el modal abierto y un cambio de filtro vuelve a la
      // primera página.
      void navigate({
        to: '.',
        search: { ...filtros, ...cambios, pagina: cambios.pagina ?? 1 },
        replace: true,
      })
    },
    [navigate, filtros],
  )
  return <PresupuestosPage filtros={filtros} onFiltros={cambiar} modal={<Outlet />} />
}
