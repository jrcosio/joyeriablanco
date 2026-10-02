import { z } from 'zod'

/**
 * Filtros de los listados de documentos en la URL: facturas (002) y presupuestos (005). Sin
 * `anio`, el año en curso; `todos` quita el filtro (contracts/ui-rutas.md).
 */
export type OrdenDocumentos = 'recientes' | 'antiguas' | 'total_desc' | 'total_asc'

export interface FiltrosDocumentos {
  q?: string | undefined
  anio?: number | 'todos' | undefined
  mes?: number | undefined
  orden: OrdenDocumentos
  pagina: number
}

/** Validación de los *search params*, compartida por las rutas de los dos listados (R-13). */
export const busquedaDocumentos = z.object({
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
