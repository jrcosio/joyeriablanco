import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useCallback } from 'react'
import { z } from 'zod'
import { AuditoriaPage, type FiltrosAuditoriaUrl } from '../../../features/auditoria/AuditoriaPage'
import { TIPOS_EVENTO } from '../../../features/auditoria/tipos-evento'

const TIPOS = Object.keys(TIPOS_EVENTO) as [
  keyof typeof TIPOS_EVENTO,
  ...(keyof typeof TIPOS_EVENTO)[],
]
const fecha = z
  .string()
  .regex(/^\d{4}-\d{2}-\d{2}$/)
  .optional()
  .catch(undefined)

const busqueda = z.object({
  desde: fecha,
  hasta: fecha,
  usuario: z.uuid().optional().catch(undefined),
  tipo: z.enum(TIPOS).optional().catch(undefined),
  cliente: z.uuid().optional().catch(undefined),
  pagina: z.coerce.number().int().min(1).default(1).catch(1),
})

export const Route = createFileRoute('/_app/configuracion/auditoria')({
  validateSearch: busqueda,
  component: Auditoria,
})

function Auditoria() {
  const filtros = Route.useSearch()
  const navigate = useNavigate({ from: Route.fullPath })
  const cambiar = useCallback(
    (cambios: Partial<FiltrosAuditoriaUrl>) => {
      void navigate({
        search: { ...filtros, ...cambios, pagina: cambios.pagina ?? 1 },
        replace: true,
      })
    },
    [navigate, filtros],
  )
  return <AuditoriaPage filtros={filtros} onFiltros={cambiar} />
}
