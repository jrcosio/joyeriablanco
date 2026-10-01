import { keepPreviousData, queryOptions, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, unwrap } from '../client'
import type { AnulacionEntrada, FacturaEntrada, ModificacionEntrada } from '../tipos'
import { CLIENTES_KEY } from './clientes'

export const FACTURAS_KEY = ['facturas'] as const

export type OrdenFacturas = 'recientes' | 'antiguas' | 'total_desc' | 'total_asc'

/** Filtros del listado en la URL (contracts/ui-rutas.md). Sin `anio`, el año en curso. */
export interface FiltrosFacturas {
  q?: string | undefined
  anio?: number | 'todos' | undefined
  mes?: number | undefined
  orden: OrdenFacturas
  pagina: number
}

export const TAMANO_PAGINA_FACTURAS = 25

export const facturasListaQuery = (filtros: FiltrosFacturas) =>
  queryOptions({
    queryKey: [...FACTURAS_KEY, 'lista', filtros],
    queryFn: () =>
      unwrap(
        api.GET('/api/v1/facturas', {
          params: {
            query: {
              ...(filtros.q ? { q: filtros.q } : {}),
              ...(filtros.anio !== undefined ? { anio: filtros.anio } : {}),
              ...(filtros.mes !== undefined ? { mes: filtros.mes } : {}),
              orden: filtros.orden,
              pagina: filtros.pagina,
              tamano: TAMANO_PAGINA_FACTURAS,
            },
          },
        }),
      ),
    placeholderData: keepPreviousData,
  })

export const facturaQuery = (id: string) =>
  queryOptions({
    queryKey: [...FACTURAS_KEY, 'detalle', id],
    queryFn: () =>
      unwrap(api.GET('/api/v1/facturas/{factura_id}', { params: { path: { factura_id: id } } })),
  })

/** Invalida facturas (listado, detalle y parámetros) y clientes (tienen documentos, FR-042). */
export function useInvalidarFacturas() {
  const queryClient = useQueryClient()
  return async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: FACTURAS_KEY }),
      queryClient.invalidateQueries({ queryKey: CLIENTES_KEY }),
    ])
  }
}

/** Emite una factura nueva (FR-021). La clave de operación hace idempotente el reintento (R-18). */
export function useEmitirFactura() {
  const invalidar = useInvalidarFacturas()
  return useMutation({
    mutationFn: ({ body, clave }: { body: FacturaEntrada; clave: string }) =>
      unwrap(
        api.POST('/api/v1/facturas', { params: { header: { 'Idempotency-Key': clave } }, body }),
      ),
    onSuccess: invalidar,
  })
}

/** Anula una factura sin reemitirla (FR-025). Solo administradores; idempotente por clave. */
export function useAnularFactura() {
  const invalidar = useInvalidarFacturas()
  return useMutation({
    mutationFn: ({ id, body, clave }: { id: string; body: AnulacionEntrada; clave: string }) =>
      unwrap(
        api.POST('/api/v1/facturas/{factura_id}/anulacion', {
          params: { path: { factura_id: id }, header: { 'Idempotency-Key': clave } },
          body,
        }),
      ),
    onSuccess: invalidar,
  })
}

/** Modifica una factura mediante corrección trazable (FR-024): devuelve la factura nueva. */
export function useModificarFactura() {
  const invalidar = useInvalidarFacturas()
  return useMutation({
    mutationFn: ({ id, body, clave }: { id: string; body: ModificacionEntrada; clave: string }) =>
      unwrap(
        api.POST('/api/v1/facturas/{factura_id}/modificacion', {
          params: { path: { factura_id: id }, header: { 'Idempotency-Key': clave } },
          body,
        }),
      ),
    onSuccess: invalidar,
  })
}
