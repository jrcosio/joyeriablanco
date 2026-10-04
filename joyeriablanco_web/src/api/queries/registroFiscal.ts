import { keepPreviousData, queryOptions } from '@tanstack/react-query'
import { api, unwrap } from '../client'
import type { TipoEventoSif } from '../tipos'

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
