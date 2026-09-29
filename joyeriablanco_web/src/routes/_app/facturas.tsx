import { createFileRoute, Outlet, useNavigate } from '@tanstack/react-router'
import { useCallback } from 'react'
import { z } from 'zod'
import type { FiltrosFacturas } from '../../api/queries/facturas'
import { FacturasPage } from '../../features/facturas/FacturasPage'

// Búsqueda, año, mes, orden y página viven en la URL (contracts/ui-rutas.md). Sin `anio`, el
// año en curso; `todos` quita el filtro.
const busqueda = z.object({
  q: z.string().max(100).optional().catch(undefined),
  anio: z
    .union([z.literal('todos'), z.coerce.number().int().min(2024).max(9999)])
    .optional()
    .catch(undefined),
  mes: z.coerce.number().int().min(1).max(12).optional().catch(undefined),
  orden: z
    .enum(['recientes', 'antiguas', 'total_desc', 'total_asc'])
    .default('recientes')
    .catch('recientes'),
  pagina: z.coerce.number().int().min(1).default(1).catch(1),
})

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
