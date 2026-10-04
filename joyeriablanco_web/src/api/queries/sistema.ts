import { queryOptions } from '@tanstack/react-query'
import { api, unwrap } from '../client'

/** Datos del sistema y declaración responsable (004, FR-027): para cualquier sesión. */
export const sistemaQuery = queryOptions({
  queryKey: ['sistema'],
  queryFn: () => unwrap(api.GET('/api/v1/sistema')),
  staleTime: Infinity, // cambian con la versión desplegada
})

export const URL_DECLARACION_PDF = '/api/v1/sistema/declaracion-responsable/pdf'
