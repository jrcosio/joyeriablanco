import { keepPreviousData, queryOptions } from '@tanstack/react-query'
import { api, unwrap } from '../client'
import type { TipoEvento } from '../tipos'

export interface FiltrosAuditoria {
  desde?: string | undefined // ISO con zona
  hasta?: string | undefined
  usuario_id?: string | undefined
  tipo?: TipoEvento | undefined
  cliente_id?: string | undefined
  pagina: number
}

export const TAMANO_PAGINA_AUDITORIA = 25

export const auditoriaQuery = (filtros: FiltrosAuditoria) =>
  queryOptions({
    queryKey: ['auditoria', filtros],
    queryFn: () =>
      unwrap(
        api.GET('/api/v1/auditoria', {
          params: {
            query: {
              ...(filtros.desde ? { desde: filtros.desde } : {}),
              ...(filtros.hasta ? { hasta: filtros.hasta } : {}),
              ...(filtros.usuario_id ? { usuario_id: filtros.usuario_id } : {}),
              ...(filtros.tipo ? { tipo: filtros.tipo } : {}),
              ...(filtros.cliente_id ? { cliente_id: filtros.cliente_id } : {}),
              pagina: filtros.pagina,
              tamano: TAMANO_PAGINA_AUDITORIA,
            },
          },
        }),
      ),
    placeholderData: keepPreviousData,
  })
