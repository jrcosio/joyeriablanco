import { createFileRoute, Outlet, useNavigate } from '@tanstack/react-router'
import { useCallback } from 'react'
import { z } from 'zod'
import type { FiltrosClientes } from '../../api/queries/clientes'
import { ClientesPage } from '../../features/clientes/ClientesPage'

// Filtros, búsqueda, orden y página viven en la URL (contracts/ui-rutas.md).
const busqueda = z.object({
  q: z.string().max(100).optional().catch(undefined),
  provincia: z
    .string()
    .regex(/^\d{2}$/)
    .optional()
    .catch(undefined),
  tipo: z.enum(['particular', 'empresa']).optional().catch(undefined),
  estado: z.enum(['activos', 'inactivos', 'todos']).default('activos').catch('activos'),
  orden: z
    .enum(['nombre_asc', 'nombre_desc', 'recientes', 'antiguos'])
    .default('nombre_asc')
    .catch('nombre_asc'),
  pagina: z.coerce.number().int().min(1).default(1).catch(1),
})

export const Route = createFileRoute('/_app/clientes')({
  validateSearch: busqueda,
  component: Clientes,
})

function Clientes() {
  const filtros = Route.useSearch()
  const navigate = useNavigate()
  const cambiar = useCallback(
    (cambios: Partial<FiltrosClientes>) => {
      // `to: '.'` conserva la ruta actual: si la ficha de un cliente está abierta, un cambio de
      // filtro (p. ej. la búsqueda aplazada) no la cierra. Cualquier cambio de filtro vuelve a
      // la primera página.
      void navigate({
        to: '.',
        search: { ...filtros, ...cambios, pagina: cambios.pagina ?? 1 },
        replace: true,
      })
    },
    [navigate, filtros],
  )
  return <ClientesPage filtros={filtros} onFiltros={cambiar} panel={<Outlet />} />
}
