import { queryOptions, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, unwrap } from '../client'
import type { BorradorPresupuestoEdicionEntrada, BorradorPresupuestoEntrada } from '../tipos'
import { PRESUPUESTOS_KEY, useInvalidarPresupuestos } from './presupuestos'

/** Los borradores cuelgan de `['presupuestos']`: el listado los muestra junto a los emitidos. */
export const borradorPresupuestoQuery = (id: string) =>
  queryOptions({
    queryKey: [...PRESUPUESTOS_KEY, 'borrador', id],
    queryFn: () =>
      unwrap(
        api.GET('/api/v1/borradores-presupuesto/{borrador_id}', {
          params: { path: { borrador_id: id } },
        }),
      ),
  })

export function useCrearBorradorPresupuesto() {
  const invalidar = useInvalidarPresupuestos()
  return useMutation({
    mutationFn: (body: BorradorPresupuestoEntrada) =>
      unwrap(api.POST('/api/v1/borradores-presupuesto', { body })),
    onSuccess: invalidar,
  })
}

/** Guarda un borrador (FR-013: con su versión) y deja en la caché lo que devuelve la API. */
export function useGuardarBorradorPresupuesto() {
  const queryClient = useQueryClient()
  const invalidar = useInvalidarPresupuestos()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: BorradorPresupuestoEdicionEntrada }) =>
      unwrap(
        api.PUT('/api/v1/borradores-presupuesto/{borrador_id}', {
          params: { path: { borrador_id: id } },
          body,
        }),
      ),
    onSuccess: async (guardado) => {
      queryClient.setQueryData(borradorPresupuestoQuery(guardado.id).queryKey, guardado)
      await invalidar()
    },
  })
}

export function useEliminarBorradorPresupuesto() {
  const queryClient = useQueryClient()
  const invalidar = useInvalidarPresupuestos()
  return useMutation({
    mutationFn: (id: string) =>
      unwrap(
        api.DELETE('/api/v1/borradores-presupuesto/{borrador_id}', {
          params: { path: { borrador_id: id } },
        }),
      ),
    onSuccess: async (_, id) => {
      queryClient.removeQueries({ queryKey: borradorPresupuestoQuery(id).queryKey })
      await invalidar()
    },
  })
}

/** Emite el borrador con el contenido del modal; la clave hace idempotente el reintento. */
export function useEmitirBorradorPresupuesto() {
  const queryClient = useQueryClient()
  const invalidar = useInvalidarPresupuestos()
  return useMutation({
    mutationFn: ({
      id,
      body,
      clave,
    }: {
      id: string
      body: BorradorPresupuestoEdicionEntrada
      clave: string
    }) =>
      unwrap(
        api.POST('/api/v1/borradores-presupuesto/{borrador_id}/emision', {
          params: { path: { borrador_id: id }, header: { 'Idempotency-Key': clave } },
          body,
        }),
      ),
    onSuccess: async (_, { id }) => {
      queryClient.removeQueries({ queryKey: borradorPresupuestoQuery(id).queryKey })
      await invalidar()
    },
  })
}
