import { queryOptions, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, unwrap } from '../client'
import type { BorradorEdicionEntrada, BorradorEntrada } from '../tipos'
import { FACTURAS_KEY, useInvalidarFacturas } from './facturas'
import { PRESUPUESTOS_KEY } from './presupuestos'

/**
 * Emitir o eliminar un borrador vinculado cambia el estado de su presupuesto (005, FR-020): se
 * invalida también `['presupuestos']`.
 */
function useInvalidarTrasCerrarBorrador() {
  const queryClient = useQueryClient()
  const invalidar = useInvalidarFacturas()
  return async (id: string) => {
    queryClient.removeQueries({ queryKey: borradorQuery(id).queryKey })
    await Promise.all([invalidar(), queryClient.invalidateQueries({ queryKey: PRESUPUESTOS_KEY })])
  }
}

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
  const invalidar = useInvalidarTrasCerrarBorrador()
  return useMutation({
    mutationFn: (id: string) =>
      unwrap(
        api.DELETE('/api/v1/borradores-factura/{borrador_id}', {
          params: { path: { borrador_id: id } },
        }),
      ),
    onSuccess: (_, id) => invalidar(id),
  })
}

/** Emite el borrador con el contenido del modal; la clave hace idempotente el reintento (R-18). */
export function useEmitirBorrador() {
  const invalidar = useInvalidarTrasCerrarBorrador()
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
    onSuccess: (_, { id }) => invalidar(id),
  })
}
