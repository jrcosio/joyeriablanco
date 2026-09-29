import { queryOptions, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, unwrap } from '../client'
import type { BorradorEdicionEntrada, BorradorEntrada } from '../tipos'
import { FACTURAS_KEY, useInvalidarFacturas } from './facturas'

/** Los borradores cuelgan de `['facturas']`: el listado los muestra junto a las emitidas. */
export const borradorQuery = (id: string) =>
  queryOptions({
    queryKey: [...FACTURAS_KEY, 'borrador', id],
    queryFn: () =>
      unwrap(
        api.GET('/api/v1/borradores-factura/{borrador_id}', {
          params: { path: { borrador_id: id } },
        }),
      ),
  })

export function useCrearBorrador() {
  const invalidar = useInvalidarFacturas()
  return useMutation({
    mutationFn: (body: BorradorEntrada) => unwrap(api.POST('/api/v1/borradores-factura', { body })),
    onSuccess: invalidar,
  })
}

/** Guarda un borrador (FR-020: con su versión) y deja en la caché lo que devuelve la API. */
export function useGuardarBorrador() {
  const queryClient = useQueryClient()
  const invalidar = useInvalidarFacturas()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: BorradorEdicionEntrada }) =>
      unwrap(
        api.PUT('/api/v1/borradores-factura/{borrador_id}', {
          params: { path: { borrador_id: id } },
          body,
        }),
      ),
    onSuccess: async (guardado) => {
      queryClient.setQueryData(borradorQuery(guardado.id).queryKey, guardado)
      await invalidar()
    },
  })
}

export function useEliminarBorrador() {
  const queryClient = useQueryClient()
  const invalidar = useInvalidarFacturas()
  return useMutation({
    mutationFn: (id: string) =>
      unwrap(
        api.DELETE('/api/v1/borradores-factura/{borrador_id}', {
          params: { path: { borrador_id: id } },
        }),
      ),
    onSuccess: async (_, id) => {
      queryClient.removeQueries({ queryKey: borradorQuery(id).queryKey })
      await invalidar()
    },
  })
}

/** Emite el borrador con el contenido del modal; la clave hace idempotente el reintento (R-18). */
export function useEmitirBorrador() {
  const queryClient = useQueryClient()
  const invalidar = useInvalidarFacturas()
  return useMutation({
    mutationFn: ({
      id,
      body,
      clave,
    }: {
      id: string
      body: BorradorEdicionEntrada
      clave: string
    }) =>
      unwrap(
        api.POST('/api/v1/borradores-factura/{borrador_id}/emision', {
          params: { path: { borrador_id: id }, header: { 'Idempotency-Key': clave } },
          body,
        }),
      ),
    onSuccess: async (_, { id }) => {
      queryClient.removeQueries({ queryKey: borradorQuery(id).queryKey })
      await invalidar()
    },
  })
}
