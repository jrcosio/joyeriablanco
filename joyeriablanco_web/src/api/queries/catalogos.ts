import { queryOptions, useQuery } from '@tanstack/react-query'
import { api, unwrap } from '../client'

export const catalogosQuery = queryOptions({
  queryKey: ['catalogos'],
  queryFn: () => unwrap(api.GET('/api/v1/catalogos')),
  staleTime: Infinity,
})

export function useCatalogos() {
  return useQuery(catalogosQuery)
}
