import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useCallback } from 'react'
import { z } from 'zod'
import { requireAdmin } from '../../auth/guards'
import {
  RegistroFiscalPage,
  type BusquedaRegistroFiscal,
} from '../../features/registro-fiscal/RegistroFiscalPage'
import { TIPOS_EVENTO_SIF } from '../../lib/registro-fiscal'

const TIPOS = Object.keys(TIPOS_EVENTO_SIF) as [
  keyof typeof TIPOS_EVENTO_SIF,
  ...(keyof typeof TIPOS_EVENTO_SIF)[],
]
const fecha = z
  .string()
  .regex(/^\d{4}-\d{2}-\d{2}$/)
  .optional()
  .catch(undefined)

const busqueda = z.object({
  pestana: z
    .enum(['eventos', 'cadena', 'comprobar', 'exportar'])
    .default('eventos')
    .catch('eventos'),
  // «?tipo=10» llega como número: se pasa a texto antes de validar el código de F-17.
  tipo: z.coerce.string().pipe(z.enum(TIPOS)).optional().catch(undefined),
  desde: fecha,
  hasta: fecha,
  pagina: z.coerce.number().int().min(1).default(1).catch(1),
  secuencia: z.coerce.number().int().min(1).optional().catch(undefined),
})

/** «Registro fiscal» (004, contracts/ui-rutas.md): solo administradores, pestaña en la URL. */
export const Route = createFileRoute('/_app/registro-fiscal')({
  beforeLoad: ({ context }) => {
    requireAdmin(context.sesion)
  },
  validateSearch: busqueda,
  component: RegistroFiscal,
})

function RegistroFiscal() {
  const actual = Route.useSearch()
  const navigate = useNavigate({ from: Route.fullPath })
  const cambiar = useCallback(
    (cambios: Partial<BusquedaRegistroFiscal>) => {
      void navigate({ search: { ...actual, ...cambios }, replace: true })
    },
    [navigate, actual],
  )
  return <RegistroFiscalPage busqueda={actual} onBusqueda={cambiar} />
}
