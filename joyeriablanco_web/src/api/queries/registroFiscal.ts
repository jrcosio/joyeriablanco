import { keepPreviousData, queryOptions, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, unwrap } from '../client'
import type { ComprobacionEntrada, TipoEventoSif } from '../tipos'

/** Filtros de la lista de eventos (FR-016): días completos en hora de Madrid. */
export interface FiltrosEventos {
  tipo?: TipoEventoSif | undefined
  desde?: string | undefined // AAAA-MM-DD
  hasta?: string | undefined
  pagina: number
}

export const TAMANO_PAGINA_EVENTOS = 25

export const eventosQuery = (filtros: FiltrosEventos) =>
  queryOptions({
    queryKey: ['registro-fiscal', 'eventos', filtros],
    queryFn: () =>
      unwrap(
        api.GET('/api/v1/registro-fiscal/eventos', {
          params: {
            query: {
              ...(filtros.tipo ? { tipo: filtros.tipo } : {}),
              ...(filtros.desde ? { desde: filtros.desde } : {}),
              ...(filtros.hasta ? { hasta: filtros.hasta } : {}),
              pagina: filtros.pagina,
              tamano: TAMANO_PAGINA_EVENTOS,
            },
          },
        }),
      ),
    placeholderData: keepPreviousData,
  })

export const eventoQuery = (secuencia: number) =>
  queryOptions({
    queryKey: ['registro-fiscal', 'evento', secuencia],
    queryFn: () =>
      unwrap(
        api.GET('/api/v1/registro-fiscal/eventos/{secuencia}', {
          params: { path: { secuencia } },
        }),
      ),
  })

export const registroCadenaQuery = (secuencia: number) =>
  queryOptions({
    queryKey: ['registro-fiscal', 'registro', secuencia],
    queryFn: () =>
      unwrap(
        api.GET('/api/v1/registro-fiscal/registros/{secuencia}', {
          params: { path: { secuencia } },
        }),
      ),
    retry: false,
  })

/** Alarmas activas (FR-019): se consultan al cambiar de ruta y cada minuto. */
export const ALARMAS_KEY = ['alarmas'] as const

export const alarmasQuery = queryOptions({
  queryKey: ALARMAS_KEY,
  queryFn: () => unwrap(api.GET('/api/v1/alarmas')),
  refetchInterval: 60_000,
})

/** «Comprobar integridad» (FR-017): genera eventos y puede apagar la alarma. */
export function useComprobarIntegridad() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: ComprobacionEntrada) =>
      unwrap(api.POST('/api/v1/registro-fiscal/comprobaciones', { body })),
    onSuccess: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: ['registro-fiscal'] }),
        queryClient.invalidateQueries({ queryKey: ALARMAS_KEY }),
      ]),
  })
}
