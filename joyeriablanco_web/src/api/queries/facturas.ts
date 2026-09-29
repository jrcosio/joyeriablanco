import { queryOptions, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, unwrap } from '../client'
import type { FacturaEntrada } from '../tipos'
import { CLIENTES_KEY } from './clientes'

export const FACTURAS_KEY = ['facturas'] as const

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
