import { keepPreviousData, queryOptions, useMutation, useQueryClient } from '@tanstack/react-query'
import type { FiltrosDocumentos } from '../../lib/filtros-documentos'
import { api, unwrap } from '../client'
import type { PresupuestoEntrada } from '../tipos'
import { CLIENTES_KEY } from './clientes'

/** Presupuestos, sus borradores y los parámetros del modal cuelgan de esta clave (005). */
export const PRESUPUESTOS_KEY = ['presupuestos'] as const
export const TAMANO_PAGINA_PRESUPUESTOS = 25

export const presupuestosListaQuery = (filtros: FiltrosDocumentos) =>
  queryOptions({
    queryKey: [...PRESUPUESTOS_KEY, 'lista', filtros],
    queryFn: () =>
      unwrap(
        api.GET('/api/v1/presupuestos', {
          params: {
            query: {
              ...(filtros.q ? { q: filtros.q } : {}),
              ...(filtros.anio !== undefined ? { anio: filtros.anio } : {}),
              ...(filtros.mes !== undefined ? { mes: filtros.mes } : {}),
              orden: filtros.orden,
              pagina: filtros.pagina,
              tamano: TAMANO_PAGINA_PRESUPUESTOS,
            },
          },
        }),
      ),
    placeholderData: keepPreviousData,
  })

export const presupuestoQuery = (id: string) =>
  queryOptions({
    queryKey: [...PRESUPUESTOS_KEY, 'detalle', id],
    queryFn: () =>
      unwrap(
        api.GET('/api/v1/presupuestos/{presupuesto_id}', {
          params: { path: { presupuesto_id: id } },
        }),
      ),
  })

/** IVA vigente, validez por defecto, si se puede emitir y el próximo número (FR-009, FR-011). */
export const parametrosPresupuestoQuery = queryOptions({
  queryKey: [...PRESUPUESTOS_KEY, 'parametros'],
  queryFn: () => unwrap(api.GET('/api/v1/presupuestos/parametros')),
})

/** Invalida presupuestos y clientes (tienen documentos, FR-033). */
export function useInvalidarPresupuestos() {
  const queryClient = useQueryClient()
  return async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: PRESUPUESTOS_KEY }),
      queryClient.invalidateQueries({ queryKey: CLIENTES_KEY }),
    ])
  }
}

/** Emite un presupuesto nuevo (FR-014). La clave de operación hace idempotente el reintento. */
export function useEmitirPresupuesto() {
  const invalidar = useInvalidarPresupuestos()
  return useMutation({
    mutationFn: ({ body, clave }: { body: PresupuestoEntrada; clave: string }) =>
      unwrap(
        api.POST('/api/v1/presupuestos', {
          params: { header: { 'Idempotency-Key': clave } },
          body,
        }),
      ),
    onSuccess: invalidar,
  })
}
