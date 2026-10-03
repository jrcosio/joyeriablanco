import { createFileRoute, Outlet, useNavigate } from '@tanstack/react-router'
import { useCallback } from 'react'
import type { FiltrosFacturas } from '../../api/queries/facturas'
import { FacturasPage } from '../../features/facturas/FacturasPage'
import { busquedaDocumentos } from '../../lib/filtros-documentos'

// Búsqueda, año, mes, orden y página viven en la URL (contracts/ui-rutas.md), con la misma
// validación que los presupuestos (005, R-13).
const busqueda = busquedaDocumentos

/** Facturas: listado (US3) y, por encima, el modal de la factura (rutas anidadas, R-13). */
export const Route = createFileRoute('/_app/facturas')({
  validateSearch: busqueda,
  component: Facturas,
})

function Facturas() {
  const filtros = Route.useSearch()
  const navigate = useNavigate()
  const cambiar = useCallback(
    (cambios: Partial<FiltrosFacturas>) => {
      // Como en clientes: `to: '.'` no cierra el modal abierto y un cambio de filtro vuelve a la
      // primera página.
      void navigate({
        to: '.',
        search: { ...filtros, ...cambios, pagina: cambios.pagina ?? 1 },
        replace: true,
      })
    },
    [navigate, filtros],
  )
  return <FacturasPage filtros={filtros} onFiltros={cambiar} modal={<Outlet />} />
}
