import { keepPreviousData, queryOptions, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, unwrap } from '../client'
import type { ClienteEdicionEntrada, ClienteEntrada } from '../tipos'

export const CLIENTES_KEY = ['clientes'] as const

export const clienteQuery = (id: string) =>
  queryOptions({
    queryKey: [...CLIENTES_KEY, 'ficha', id],
    queryFn: () =>
      unwrap(api.GET('/api/v1/clientes/{cliente_id}', { params: { path: { cliente_id: id } } })),
  })

function useInvalidarClientes() {
  const queryClient = useQueryClient()
  return () => queryClient.invalidateQueries({ queryKey: CLIENTES_KEY })
}

export function useCrearCliente() {
  const invalidar = useInvalidarClientes()
  return useMutation({
    mutationFn: (body: ClienteEntrada) => unwrap(api.POST('/api/v1/clientes', { body })),
    onSuccess: invalidar,
  })
}

export function useEditarCliente(id: string) {
  const invalidar = useInvalidarClientes()
  return useMutation({
    mutationFn: (body: ClienteEdicionEntrada) =>
      unwrap(
        api.PUT('/api/v1/clientes/{cliente_id}', { params: { path: { cliente_id: id } }, body }),
      ),
    onSuccess: invalidar,
  })
}

export interface FiltrosClientes {
  q?: string | undefined
  provincia?: string | undefined
  tipo?: 'particular' | 'empresa' | undefined
  estado: 'activos' | 'inactivos' | 'todos'
  orden: 'nombre_asc' | 'nombre_desc' | 'recientes' | 'antiguos'
  pagina: number
}

export const TAMANO_PAGINA = 25

export const clientesListaQuery = (filtros: FiltrosClientes) =>
  queryOptions({
    queryKey: [...CLIENTES_KEY, 'lista', filtros],
    queryFn: () =>
      unwrap(
        api.GET('/api/v1/clientes', {
          params: {
            query: {
              ...(filtros.q ? { q: filtros.q } : {}),
              ...(filtros.provincia ? { provincia: filtros.provincia } : {}),
              ...(filtros.tipo ? { tipo: filtros.tipo } : {}),
              estado: filtros.estado,
              orden: filtros.orden,
              pagina: filtros.pagina,
              tamano: TAMANO_PAGINA,
            },
          },
        }),
      ),
    placeholderData: keepPreviousData,
  })

export const indicadoresQuery = queryOptions({
  queryKey: [...CLIENTES_KEY, 'indicadores'],
  queryFn: () => unwrap(api.GET('/api/v1/clientes/indicadores')),
})
